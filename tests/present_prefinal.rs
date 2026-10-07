//! Whole ending licenses refine broad prefinal notes; contextual senses stay open.
use klem::Lemmatizer;
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn original_prefinal_occurrences_and_specific_allomorph_boundaries() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/present-prefinal-validity.json")).unwrap();
    for encoding in ["NFC", "NFD"] {
        if encoding == "NFD" {
            for case in &mut suite.cases {
                case.surface = case.surface.nfd().collect();
            }
        }
        let report = validity::evaluate(&suite).unwrap();
        assert!(report.passed(), "{encoding}: {:?}", report.violations);
        assert_eq!((report.required_total, report.forbidden_total), (10, 5));
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
        "klem-present-prefinal-{name}-{}.db",
        std::process::id()
    ));
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/krdict-present-prefinal-english.json",
        )],
        &path,
        "present-prefinal-source",
    )
    .unwrap();
    (SqliteDictionary::open(path).unwrap(), cleanup)
}

#[test]
fn all_primary_ending_and_lexical_sources_survive_import() {
    use klem::dictionary::Dictionary;
    let expected: Value =
        serde_json::from_str(include_str!("fixtures/present-prefinal-native.json")).unwrap();
    assert_eq!(expected.as_object().unwrap().len(), 45);
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
fn dictionary_filter_preserves_sources_and_rejects_the_known_adjective_owner() {
    use klem::dictionary::{DictionaryFilter, DictionarySession};
    let (db, _cleanup) = dictionary("policy");
    let mut session = DictionarySession::new(&db, 1048576);
    let engine = Lemmatizer::new();
    let raw = engine.analyze_word("좋는다").unwrap();
    assert!(raw.analyses.iter().any(|path| {
        path.lemmas
            .iter()
            .map(|lemma| lemma.text.as_str())
            .eq(["좋다"])
            && path
                .morphemes
                .iter()
                .map(|morpheme| morpheme.form.as_str())
                .eq(["는다"])
    }));
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/present-prefinal-policy.json")).unwrap();
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
        assert_eq!((report.required_total, report.forbidden_total), (10, 6));
    }
}
