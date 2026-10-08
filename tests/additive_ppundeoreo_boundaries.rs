use klem::{Analysis, Lemmatizer};
use unicode_normalization::UnicodeNormalization;

fn matches(a: &Analysis, expected: &serde_json::Value) -> bool {
    let a = serde_json::to_value(a).unwrap();
    a["lemmas"]
        .as_array()
        .unwrap()
        .iter()
        .map(|l| &l["text"])
        .eq(expected["lemmas"].as_array().unwrap())
        && a["lemmas"]
            .as_array()
            .unwrap()
            .iter()
            .map(|l| &l["kind"])
            .eq(expected["lemma_kinds"].as_array().unwrap())
        && a["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| &m["form"])
            .eq(expected["morphemes"].as_array().unwrap())
        && a["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| &m["kind"])
            .eq(expected["morpheme_kinds"].as_array().unwrap())
        && a["rules"]
            .as_array()
            .unwrap()
            .iter()
            .any(|r| r == "ending.additive_ppundeoreo")
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn individual_allomorph_and_spelling_cases_keep_raw_and_native_policy_separate() {
    use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
    let fixture: serde_json::Value = serde_json::from_str(include_str!(
        "fixtures/additive-ppundeoreo-authored-boundaries.json"
    ))
    .unwrap();
    let cases = fixture["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 36);
    let path = std::env::temp_dir().join(format!(
        "klem-additive-ppundeoreo-boundaries-{}.db",
        std::process::id()
    ));
    assert!(!path.exists());
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &["tests/fixtures/additive-ppundeoreo-english.json".into()],
        &path,
        "additive-ppundeoreo-source",
    )
    .unwrap();
    let db = SqliteDictionary::open(path).unwrap();
    let mut session = DictionarySession::new(&db, 1024);
    let engine = Lemmatizer::new();
    let mut ids = std::collections::HashSet::new();
    for case in cases {
        assert!(ids.insert(case["id"].as_str().unwrap()));
        let word = case["surface"].as_str().unwrap();
        for input in [word.to_string(), word.nfd().collect()] {
            let raw = engine.analyze_word(&input).unwrap();
            let annotation = session.annotate(&raw).unwrap();
            let targets: Vec<_> = raw.analyses.iter().filter(|a| matches(a, case)).collect();
            assert_eq!(
                !targets.is_empty(),
                case["expected_presence"]["raw"].as_bool().unwrap(),
                "{}: {raw:?}",
                case["id"]
            );
            for target in targets {
                let assessment = serde_json::to_value(annotation.assess(target)).unwrap();
                if let Some(statuses) = case.get("expected_entry_statuses") {
                    for (id, status) in statuses.as_object().unwrap() {
                        let entry = assessment["lemmas"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .flat_map(|lemma| lemma["entries"].as_array().unwrap())
                            .find(|entry| entry["id"] == *id)
                            .unwrap_or_else(|| panic!("{} lost Native owner {id}", case["id"]));
                        assert_eq!(entry["status"], *status, "{} {id}", case["id"]);
                    }
                }
                if case["expected_status"] == "not-incompatible" {
                    assert_ne!(assessment["status"], "incompatible", "{}", case["id"]);
                } else {
                    assert_eq!(
                        assessment["status"], case["expected_status"],
                        "{}",
                        case["id"]
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
                    filtered.analyses.iter().any(|a| matches(a, case)),
                    case["expected_presence"][key].as_bool().unwrap(),
                    "{} {key}: {filtered:?}",
                    case["id"]
                );
            }
        }
    }
}
