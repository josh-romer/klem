//! Complete Native and homonym closure for all matched broader RI owners.
use klem::dictionary::{Dictionary, SqliteDictionary, import_krdict};
use serde_json::Value;
use std::{collections::BTreeMap, path::PathBuf};
#[test]
fn every_matched_broad_owner_preserves_native_fields_and_all_headword_homonyms() {
    let native: BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/literary-ri-prefinal-broad-native.json"
    ))
    .unwrap();
    assert_eq!(native.len(), 182);
    let path = std::env::temp_dir().join(format!("klem-ri-broad-owners-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-literary-ri-prefinal-broad-english.json",
        )],
        &path,
        "ri-broad-owner-source",
    )
    .unwrap();
    let db = SqliteDictionary::open(path).unwrap();
    let mut heads: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for (id, expected) in native {
        let mut english = expected.clone();
        for sense in english["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(&id).unwrap().unwrap()).unwrap(),
            english,
            "{id}"
        );
        heads
            .entry(expected["headword"].as_str().unwrap().to_owned())
            .or_default()
            .push(id);
    }
    for (head, mut ids) in heads {
        let mut actual = db
            .lookup(&head)
            .unwrap()
            .iter()
            .map(|e| e.id.clone())
            .collect::<Vec<_>>();
        ids.sort();
        actual.sort();
        assert_eq!(actual, ids, "{head}: every source homonym survives");
    }
}
