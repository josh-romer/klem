//! Individually captured gentle-command paths preserve the original histories.
use klem::{Analysis, MorphemeKind, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

pub fn assert_addition(source: &str, surface: &str, actual: &Analysis) {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        let raw = include_str!("../fixtures/gentle-command-history.json");
        assert_eq!(
            format!("{:x}", Sha256::digest(raw.as_bytes())),
            "841da468a81b4c2bb713f37dac0615782bfe8f7a7edb1f1bab5f034690a6e7e5",
            "original history capture must not be refreshed"
        );
        serde_json::from_str(raw).unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-gentle-command-history-and-prior-parent-capture-passed"
    );
    assert_eq!(history["inputs_unchanged"], true);
    assert_eq!(
        history["individual_additions"].as_array().unwrap().len(),
        18
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
        "uncaptured gentle command {source}/{surface}: {actual:?}"
    );
    let row = rows[0];
    assert!(
        row["id"]
            .as_str()
            .unwrap()
            .starts_with("gentle-command-history-")
    );
    assert_eq!(row["contextual_verdict"], "unjudged");
    assert_eq!(row["independent_review"], "pending");
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
        "missing original witness {source}/{surface}"
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
            .filter(|r| *r == "ending.gentle_command")
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
    inverse.rules.retain(|r| r != "ending.gentle_command");
    inverse.rules.push("ending.willingness_question".into());
    inverse.rules.sort();
    inverse.rules.dedup();
    let endings: Vec<_> = inverse
        .morphemes
        .iter_mut()
        .filter(|m| m.kind == MorphemeKind::Ending)
        .collect();
    assert_eq!(endings.len(), 1);
    let ending = endings.into_iter().next().unwrap();
    assert_eq!(ending.form, "으렴");
    ending.form = "으련".into();
    assert_eq!(
        inverse,
        serde_json::from_value::<Analysis>(row["exact_parent"].clone()).unwrap()
    );
    assert_eq!(
        row["parent_surface"],
        format!("{}련", surface.strip_suffix('렴').unwrap())
    );
    let parent: WordAnalysis = serde_json::from_value(
        history["actual_prior_companions"][row["parent_surface"].as_str().unwrap()].clone(),
    )
    .unwrap();
    assert!(parent.analyses.contains(&inverse));
}
