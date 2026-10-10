//! Exact later formal-ending additions and the original historical witnesses.
use klem::{Analysis, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

pub fn assert_addition(source: &str, surface: &str, actual: &Analysis) {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        serde_json::from_str(include_str!("../fixtures/formal-b-history.json")).unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-formal-b-cohort-preservation-passed"
    );
    let rows: Vec<_> = history["individual_additions"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|r| {
            r["surface"] == surface
                && serde_json::from_value::<Analysis>(r["analysis"].clone()).unwrap() == *actual
        })
        .collect();
    assert_eq!(
        rows.len(),
        1,
        "uncaptured formal path {source}/{surface}: {actual:?}"
    );
    let row = rows[0];
    assert!(row["id"].as_str().unwrap().starts_with("formal-b-history-"));
    assert_eq!(row["contextual_verdict"], "unjudged");
    assert_eq!(row["independent_review"], "pending");
    let raw = std::fs::read(source).unwrap();
    let digest = format!("{:x}", Sha256::digest(&raw));
    let original: Value = serde_json::from_slice(&raw).unwrap();
    let witnesses: Vec<_> = row["original_occurrences"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|w| w["source"] == source)
        .collect();
    assert!(!witnesses.is_empty(), "missing original source witness");
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
    assert!(actual.rules.iter().any(|r| r == "ending.formal_b"));
    assert!(actual.breakdown().is_some());
    assert!(
        actual
            .rules
            .iter()
            .all(|r| klem::rule_explanation(r).is_some())
    );
}

// Only the Native POS snapshot uses a projection; the other historical
// regressions check each captured addition directly.
#[allow(dead_code)]
pub fn project(source: &str, surface: &str, word: &WordAnalysis) -> WordAnalysis {
    let mut historical = word.clone();
    historical.analyses.retain(|a| {
        if a.rules.iter().any(|r| r == "ending.formal_b") {
            assert_addition(source, surface, a);
            false
        } else {
            true
        }
    });
    historical
}
