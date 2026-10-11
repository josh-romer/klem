//! Finite runtime observations; these do not certify lexical or contextual truth.
use klem::{Analysis, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

pub fn assert_addition(source: &str, surface: &str, actual: &Analysis) {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        let raw = include_str!("../fixtures/friendly-command-gena-history.json");
        assert_eq!(
            format!("{:x}", Sha256::digest(raw.as_bytes())),
            "93f219320d7f05c3f4d7648d87590b278c40c23bf6d1b9cc280f6f7a7932db00",
            "original history observation bytes"
        );
        serde_json::from_str(raw).unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-gena-history-and-unchanged-parent-fixture-capture-passed"
    );
    assert_eq!(history["inputs_unchanged"], true);
    assert_eq!(history["observations_precede_runtime"], false);
    assert_eq!(
        history["individual_additions"].as_array().unwrap().len(),
        11
    );
    let rows: Vec<_> = history["individual_additions"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|row| {
            row["surface"] == surface
                && serde_json::from_value::<Analysis>(row["analysis"].clone()).unwrap() == *actual
        })
        .collect();
    assert_eq!(
        rows.len(),
        1,
        "uncaptured -게나 addition {source}/{surface}: {actual:?}"
    );
    let row = rows[0];
    assert_eq!(row["contextual_verdict"], "unjudged");
    assert_eq!(row["independent_review"], "pending");
    assert!(
        row["id"]
            .as_str()
            .unwrap()
            .starts_with("friendly-command-gena-history-")
    );
    let raw = std::fs::read(source).unwrap();
    let digest = format!("{:x}", Sha256::digest(&raw));
    assert_eq!(history["source_files_sha256"][source], digest);
    let original: Value = serde_json::from_slice(&raw).unwrap();
    let witnesses: Vec<_> = row["original_occurrences"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|w| w["source"] == source)
        .collect();
    assert!(
        !witnesses.is_empty(),
        "no original source witness for {source}/{surface}"
    );
    for witness in witnesses {
        assert_eq!(witness["source_sha256"], digest);
        assert_eq!(
            original
                .pointer(witness["pointer"].as_str().unwrap())
                .unwrap(),
            &witness["complete_original_record"]
        );
    }
    let changed = &history["changed_words"][surface];
    let before: WordAnalysis = serde_json::from_value(changed["before"].clone()).unwrap();
    let after: WordAnalysis = serde_json::from_value(changed["after"].clone()).unwrap();
    assert!(!before.analyses.contains(actual) && after.analyses.contains(actual));
    assert_eq!(
        after
            .analyses
            .iter()
            .filter(|a| before.analyses.contains(a))
            .cloned()
            .collect::<Vec<_>>(),
        before.analyses
    );
    assert_eq!(
        actual
            .rules
            .iter()
            .filter(|r| *r == "ending.friendly_command.gena")
            .count(),
        1
    );
    assert!(actual.breakdown().is_some());
    assert!(
        actual
            .rules
            .iter()
            .all(|r| klem::rule_explanation(r).is_some())
    );
}
