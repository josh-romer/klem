//! COV-019ah preflight: retain source identities and every prior reading.
use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Analysis, Lemmatizer, Session};
use serde_json::Value;
use std::{fs, path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/doeda-complement-sources.json")).unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-doeda-complement-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-complement.json")],
            &path,
            "doeda-complement-source-test",
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
fn complete_native_sources_keep_negation_compounds_and_classifications_distinct() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    assert_eq!(fixture["cases"].as_array().unwrap().len(), 412);
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    for (id, headword, pos) in [
        ("krdict:89858", "되다", "동사"),
        ("krdict:48214", "되다", "형용사"),
        ("krdict:71372", "안", "부사"),
        ("krdict:74890", "안", "명사"),
        ("krdict:14773", "안", "명사"),
        ("krdict:73915", "안되다", "동사"),
        ("krdict:16005", "안되다", "형용사"),
    ] {
        let entry = db.entry(id).unwrap().unwrap();
        assert_eq!(entry.summary.headword, headword);
        assert_eq!(entry.summary.pos, pos);
    }
    let verb = db.entry("krdict:89858").unwrap().unwrap();
    assert_eq!(verb.senses.len(), 22);
    for id in ["17", "18", "19", "21"] {
        assert!(verb.senses.iter().any(|sense| sense.id == id));
    }
    assert!(!verb.senses.iter().any(|sense| sense.id == "20"));
    assert!(fixture["cases"].as_array().unwrap().iter().all(|case| {
        case["family"] != "scheduled-ki-ro"
            || case["morphemes"]
                .as_array()
                .unwrap()
                .starts_with(&[Value::String("기".into()), Value::String("로".into())])
    }));
}

#[test]
fn every_prior_case_candidate_and_native_reading_retains_order_under_unicode_and_caching() {
    let file = Fixture::new("retention");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for (surface, before) in fixture["before_case_words"].as_object().unwrap() {
            let current = session.analyze_word(surface).unwrap();
            assert_eq!(
                current,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            let annotation = dictionary.annotate(&current).unwrap();
            let prior: Vec<Analysis> =
                serde_json::from_value(before["analysis"]["analyses"].clone()).unwrap();
            let mut cursor = 0;
            for (index, old) in prior.iter().enumerate() {
                let position = current.analyses[cursor..]
                    .iter()
                    .position(|analysis| analysis == old)
                    .unwrap_or_else(|| panic!("{surface}: prior path lost: {old:?}"))
                    + cursor;
                assert_eq!(
                    serde_json::to_value(&annotation.readings[position]).unwrap(),
                    before["dictionary"]["readings"][index],
                    "{surface}: prior native assessment changed"
                );
                cursor = position + 1;
            }
            for slot in before["dictionary"]["lemmas"].as_array().unwrap() {
                assert!(
                    annotation
                        .lemmas
                        .iter()
                        .any(|current| { serde_json::to_value(current).unwrap() == *slot }),
                    "{surface}: prior native slot changed"
                );
            }
            for analysis in &current.analyses {
                assert!(analysis.breakdown().is_some(), "{surface}: {analysis:?}");
                assert!(
                    analysis
                        .rules
                        .iter()
                        .all(|rule| klem::rule_explanation(rule).is_some())
                );
            }
        }
    }
}
