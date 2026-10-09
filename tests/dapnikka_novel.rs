use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;

#[test]
fn original_novel_command_keeps_prior_paths_and_exposes_malda() {
    let case: Value =
        serde_json::from_str(include_str!("fixtures/dapnikka-novel-case.json")).unwrap();
    let before: WordAnalysis = serde_json::from_value(case["before"]["analysis"].clone()).unwrap();
    let after: WordAnalysis = serde_json::from_value(case["after"]["analysis"].clone()).unwrap();
    let current = Lemmatizer::new().analyze_word("말랍니까").unwrap();
    assert_eq!(current, after);
    assert_eq!(
        current
            .analyses
            .iter()
            .filter(|a| before.analyses.contains(a))
            .cloned()
            .collect::<Vec<_>>(),
        before.analyses
    );
    assert!(current.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "말다"
        && a.morphemes.iter().any(|m| m.form == "으랍니까")
        && a.rules.iter().any(|r| r == "ending.question_dapnikka")));
    assert!(
        case["complete_original_line"]
            .as_str()
            .unwrap()
            .contains("누가 가시지를 말랍니까")
    );
    assert_eq!(case["contextual_verdict"], "unjudged");
}

#[test]
fn novel_malda_owners_keep_all_four_complete_native_identities() {
    use klem::dictionary::{Dictionary, SqliteDictionary, import_krdict};
    struct Cleanup(std::path::PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let path = std::env::temp_dir().join(format!("klem-dapnikka-novel-{}.db", std::process::id()));
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/dapnikka-novel-native.json",
        )],
        &path,
        "original-novel-native",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    let entries: std::collections::BTreeMap<String, Value> =
        serde_json::from_str(include_str!("fixtures/dapnikka-novel-entries.json")).unwrap();
    assert_eq!(entries.len(), 4);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
}
