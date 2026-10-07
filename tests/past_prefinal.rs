//! Original past-allomorph examples and exact boundaries; contextual senses stay open.
use klem::Lemmatizer;
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn original_past_prefinal_structures_and_named_spelling_boundaries() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/past-prefinal-validity.json")).unwrap();
    for encoding in ["NFC", "NFD"] {
        if encoding == "NFD" {
            for case in &mut suite.cases {
                case.surface = case.surface.nfd().collect();
            }
        }
        let report = validity::evaluate(&suite).unwrap();
        assert!(report.passed(), "{encoding}: {:?}", report.violations);
        assert_eq!((report.required_total, report.forbidden_total), (45, 5));
    }
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
        "klem-past-prefinal-{name}-{}.db",
        std::process::id()
    ));
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/krdict-past-prefinal-english.json",
        )],
        &path,
        "past-prefinal-source",
    )
    .unwrap();
    (SqliteDictionary::open(path).unwrap(), cleanup)
}

#[test]
fn all_primary_ending_and_lexical_sources_survive_import() {
    use klem::dictionary::Dictionary;
    let expected: Value =
        serde_json::from_str(include_str!("fixtures/past-prefinal-native.json")).unwrap();
    assert_eq!(expected.as_object().unwrap().len(), 99);
    let (db, _cleanup) = dictionary("native");
    for (id, original) in expected.as_object().unwrap() {
        let mut english = original.clone();
        for sense in english["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|translation| translation["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            english,
            "{id}"
        );
    }
}

#[test]
fn dictionary_filter_retains_all_original_past_prefinal_structure_proposals() {
    use klem::dictionary::{DictionaryFilter, DictionarySession};
    let (db, _cleanup) = dictionary("policy");
    let mut session = DictionarySession::new(&db, 1048576);
    let engine = Lemmatizer::new();
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/past-prefinal-validity.json")).unwrap();
    for encoding in ["NFC", "NFD"] {
        if encoding == "NFD" {
            for case in &mut suite.cases {
                case.surface = case.surface.nfd().collect();
            }
        }
        let report = validity::evaluate_with(&suite, |word| {
            let mut analysis = engine
                .analyze_word(word)
                .map_err(|error| error.to_string())?;
            let mut annotation = session
                .annotate(&analysis)
                .map_err(|error| error.to_string())?;
            annotation.filter(&mut analysis, DictionaryFilter::Compatible);
            Ok(analysis)
        })
        .unwrap();
        assert!(report.passed(), "{encoding}: {:?}", report.violations);
        assert_eq!((report.required_total, report.forbidden_total), (45, 5));
    }
}
