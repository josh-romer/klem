use klem::{Analysis, Lemmatizer};
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn all_39_source_occurrences_have_individual_required_judgments() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/literary-question-go-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.cases, 39);
    assert_eq!(report.required_total, 39);
}

fn expected_path(a: &Analysis, expected: &serde_json::Value) -> bool {
    let value = serde_json::to_value(a).unwrap();
    value["lemmas"]
        .as_array()
        .unwrap()
        .iter()
        .map(|l| &l["text"])
        .eq(expected["lemmas"].as_array().unwrap())
        && value["lemmas"]
            .as_array()
            .unwrap()
            .iter()
            .map(|l| &l["kind"])
            .eq(expected["lemma_kinds"].as_array().unwrap())
        && value["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| &m["form"])
            .eq(expected["morphemes"].as_array().unwrap())
        && value["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| &m["kind"])
            .eq(expected["morpheme_kinds"].as_array().unwrap())
        && a.rules.iter().any(|r| r == "ending.literary_question_go")
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(name: &str) -> (klem::dictionary::SqliteDictionary, Cleanup) {
    use klem::dictionary::{SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!(
        "klem-literary-question-go-{name}-{}.db",
        std::process::id()
    ));
    assert!(!path.exists());
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/literary-question-go-english.json",
        )],
        &path,
        "literary-question-go-source",
    )
    .unwrap();
    (SqliteDictionary::open(path).unwrap(), cleanup)
}

#[test]
fn all_original_paths_survive_every_mode_without_certifying_the_conflicting_note() {
    use klem::dictionary::{DictionaryFilter, DictionarySession};
    let engine = Lemmatizer::new();
    let cases: Vec<serde_json::Value> = serde_json::from_str(include_str!(
        "fixtures/literary-question-go-original-cases.json"
    ))
    .unwrap();
    let (db, _cleanup) = dictionary("original-modes");
    let mut session = DictionarySession::new(&db, 1024);
    for case in cases {
        let before: klem::WordAnalysis = serde_json::from_value(case["before"].clone()).unwrap();
        let word = case["surface"].as_str().unwrap();
        for text in [word.to_string(), word.nfd().collect()] {
            let raw = engine.analyze_word(&text).unwrap();
            assert_eq!(
                raw.analyses
                    .iter()
                    .filter(|a| before.analyses.contains(a))
                    .cloned()
                    .collect::<Vec<_>>(),
                before.analyses,
                "{} lost earlier candidates",
                case["id"]
            );
            let target = raw
                .analyses
                .iter()
                .find(|a| expected_path(a, &case["expected"]))
                .unwrap();
            let annotation = session.annotate(&raw).unwrap();
            if case["source_occurrence"]["source"] == "krdict:73892" {
                assert_eq!(
                    serde_json::to_value(annotation.assess(target)).unwrap()["status"],
                    "unknown",
                    "{}",
                    case["id"]
                );
            }
            for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = raw.clone();
                let mut annotation = annotation.clone();
                annotation.filter(&mut filtered, mode);
                assert!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| expected_path(a, &case["expected"])),
                    "{} {mode:?}: {:?}",
                    case["id"],
                    filtered
                );
            }
        }
    }
}

#[test]
fn all_native_fields_and_same_head_homonyms_survive_the_production_importer() {
    use klem::dictionary::Dictionary;
    let native: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/literary-question-go-native.json")).unwrap();
    assert_eq!(native.as_object().unwrap().len(), 115);
    let (db, _cleanup) = dictionary("native");
    for (id, expected) in native.as_object().unwrap() {
        let actual = serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap();
        let mut projected = expected.clone();
        for sense in projected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(actual, projected, "{id}");
        let ids: Vec<_> = db
            .lookup(expected["headword"].as_str().unwrap())
            .unwrap()
            .into_iter()
            .map(|entry| entry.id)
            .collect();
        for (other, value) in native.as_object().unwrap() {
            if value["headword"] == expected["headword"] {
                assert!(ids.contains(other), "{id} lost {other}");
            }
        }
    }
}

#[test]
fn individual_conditional_modes_use_each_native_owner_and_preserve_unknowns() {
    use klem::dictionary::{DictionaryFilter, DictionarySession};
    let matrix: serde_json::Value = serde_json::from_str(include_str!(
        "fixtures/literary-question-go-mode-scope.json"
    ))
    .unwrap();
    let cases = matrix["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 16);
    let mut ids = std::collections::HashSet::new();
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("conditional-modes");
    let mut session = DictionarySession::new(&db, 1024);
    for case in cases {
        assert!(ids.insert(case["id"].as_str().unwrap()));
        assert_eq!(case["contextual_verdict"], "unjudged");
        let word = case["surface"].as_str().unwrap();
        for text in [word.to_string(), word.nfd().collect()] {
            let raw = engine.analyze_word(&text).unwrap();
            let annotation = session.annotate(&raw).unwrap();
            let targets: Vec<_> = raw
                .analyses
                .iter()
                .filter(|a| expected_path(a, &case["expected"]))
                .collect();
            assert_eq!(
                !targets.is_empty(),
                case["expected_presence"]["raw"].as_bool().unwrap(),
                "{}",
                case["id"]
            );
            for target in targets {
                let assessment = serde_json::to_value(annotation.assess(target)).unwrap();
                for expected in case["expected_entry_statuses"].as_array().unwrap() {
                    let slot = expected["lemma"].as_u64().unwrap() as usize;
                    let actual = assessment["lemmas"][slot]["entries"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .find(|e| e["id"] == expected["id"])
                        .unwrap();
                    assert_eq!(
                        actual["status"], expected["status"],
                        "{}: {}",
                        case["id"], expected["id"]
                    );
                }
            }
            for (mode, key) in [
                (DictionaryFilter::Headword, "headword"),
                (DictionaryFilter::Compatible, "compatible"),
            ] {
                let mut filtered = raw.clone();
                let mut annotation = annotation.clone();
                annotation.filter(&mut filtered, mode);
                assert_eq!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| expected_path(a, &case["expected"])),
                    case["expected_presence"][key].as_bool().unwrap(),
                    "{} {key}",
                    case["id"]
                );
            }
        }
    }
}
