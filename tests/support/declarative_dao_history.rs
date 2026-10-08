//! Every later dao addition keeps an individually captured prior report parent.
use klem::{Analysis, MorphemeKind, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

pub fn assert_addition(source: &str, surface: &str, actual: &Analysis) {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        serde_json::from_str(include_str!("../fixtures/declarative-dao-history.json")).unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-four-cohort-prior-preservation-and-parent-capture-passed"
    );
    assert_eq!(
        history["source_files_sha256"][source],
        format!("{:x}", Sha256::digest(std::fs::read(source).unwrap()))
    );
    let rows: Vec<_> = history["individual_additions"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|row| {
            row["source"] == source
                && row["surface"] == surface
                && serde_json::from_value::<Analysis>(row["analysis"].clone()).unwrap() == *actual
        })
        .collect();
    assert_eq!(
        rows.len(),
        1,
        "uncaptured dao history {source}/{surface}: {actual:?}"
    );
    let row = rows[0];
    assert!(
        row["id"]
            .as_str()
            .unwrap()
            .starts_with("declarative-dao-history-")
    );
    assert_eq!(row["contextual_verdict"], "unjudged");
    assert_eq!(row["independent_review"], "pending");
    assert_eq!(
        actual
            .rules
            .iter()
            .filter(|r| *r == "ending.declarative_dao")
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
    let mut inverse = actual.clone();
    inverse.rules.retain(|r| r != "ending.declarative_dao");
    let ending = inverse.morphemes.last_mut().unwrap();
    assert_eq!(ending.kind, MorphemeKind::Ending);
    ending.form = match ending.form.as_str() {
        "다오" => "다고",
        "는다오" => "는다고",
        _ => panic!("wrong dao history ending"),
    }
    .into();
    assert_eq!(
        inverse,
        serde_json::from_value::<Analysis>(row["exact_parent"].clone()).unwrap()
    );
    assert!(surface.ends_with('오'));
    assert_eq!(
        row["parent_surface"],
        format!("{}고", surface.strip_suffix('오').unwrap())
    );
    let parent: WordAnalysis = serde_json::from_value(
        history["actual_prior_companions"][row["parent_surface"].as_str().unwrap()].clone(),
    )
    .unwrap();
    assert!(parent.analyses.contains(&inverse));
}
