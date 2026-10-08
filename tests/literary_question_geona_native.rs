use klem::{Analysis, Lemmatizer};
use unicode_normalization::UnicodeNormalization;

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
        && a.rules
            .iter()
            .any(|r| r == "ending.literary_question_geona")
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
        "klem-literary-question-geona-{name}-{}.db",
        std::process::id()
    ));
    assert!(!path.exists());
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/literary-question-geona-english.json",
        )],
        &path,
        "literary-question-geona-source",
    )
    .unwrap();
    (SqliteDictionary::open(path).unwrap(), cleanup)
}

#[test]
fn all_original_paths_preserve_earlier_candidates_and_survive_every_dictionary_mode() {
    use klem::dictionary::{DictionaryFilter, DictionarySession};
    let engine = Lemmatizer::new();
    let cases: Vec<serde_json::Value> = serde_json::from_str(include_str!(
        "fixtures/literary-question-geona-original-cases.json"
    ))
    .unwrap();
    let (db, _cleanup) = dictionary("original-modes");
    let mut session = DictionarySession::new(&db, 1024);
    assert_eq!(cases.len(), 8);
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
                .unwrap_or_else(|| panic!("{}: {:?}", case["id"], raw));
            let annotation = session.annotate(&raw).unwrap();
            assert_eq!(
                serde_json::to_value(annotation.assess(target)).unwrap()["status"],
                if word == "좋을거나" {
                    "unknown"
                } else {
                    "compatible"
                },
                "{} lost the original verb-note/adjective-example tension",
                case["id"]
            );
            assert_eq!(
                serde_json::to_value(target).unwrap()["spelling_paths"],
                case["earlier_parent"]["analysis"]["spelling_paths"],
                "{} changed its earlier spelling recovery",
                case["id"]
            );
            assert_ne!(
                serde_json::to_value(annotation.assess(target)).unwrap()["status"],
                "incompatible",
                "{}",
                case["id"]
            );
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
        serde_json::from_str(include_str!("fixtures/literary-question-geona-native.json")).unwrap();
    assert_eq!(native.as_object().unwrap().len(), 241);
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
