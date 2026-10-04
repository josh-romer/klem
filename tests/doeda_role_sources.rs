//! COV-019ag preflight: preserve native identities and historical role paths.
use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Analysis, Lemmatizer, Session};
use serde_json::Value;
use std::{fs, path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/doeda-role-sources.json")).unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-doeda-role-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-role.json")],
            &path,
            "doeda-role-source-test",
        )
        .unwrap();
        Self(path)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

#[test]
fn complete_case_native_entries_preserve_distinct_verb_and_adjective() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    assert_eq!(fixture["cases"].as_array().unwrap().len(), 81);
    assert_eq!(fixture["source_entries"].as_array().unwrap().len(), 35);
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    let verb = db.entry("krdict:89858").unwrap().unwrap();
    let adjective = db.entry("krdict:48214").unwrap().unwrap();
    assert_eq!(verb.summary.pos, "동사");
    assert_eq!(adjective.summary.pos, "형용사");
    assert_eq!(verb.senses.len(), 22);
    assert!(verb.senses.iter().any(|s| s.id == "23"));
    assert!(!verb.senses.iter().any(|s| s.id == "20"));
}

#[test]
fn prior_paths_readings_and_order_survive_unicode_and_cache_variants() {
    let file = Fixture::new("retention");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for (surface, before) in fixture["before_case_words"].as_object().unwrap() {
            let word = session.analyze_word(surface).unwrap();
            assert_eq!(
                word,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            let annotation = dictionary.annotate(&word).unwrap();
            let original: Vec<Analysis> =
                serde_json::from_value(before["analysis"]["analyses"].clone()).unwrap();
            let readings = before["dictionary"]["readings"].as_array().unwrap();
            let mut cursor = 0;
            for (index, prior) in original.iter().enumerate() {
                let position = word.analyses[cursor..]
                    .iter()
                    .position(|a| a == prior)
                    .unwrap_or_else(|| panic!("{surface}: historical path lost: {prior:?}"))
                    + cursor;
                assert_eq!(
                    serde_json::to_value(&annotation.readings[position]).unwrap(),
                    readings[index],
                    "{surface}: historical native reading changed"
                );
                cursor = position + 1;
            }
            for analysis in &word.analyses {
                assert!(analysis.breakdown().is_some(), "{surface}: {analysis:?}");
                assert!(
                    analysis
                        .rules
                        .iter()
                        .all(|r| klem::rule_explanation(r).is_some())
                );
            }
        }
    }
}
