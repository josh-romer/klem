//! Exact additive RI overlays on preserved historical source cohorts.
use klem::{Analysis, MorphemeKind, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

pub fn assert_addition(source: &str, surface: &str, candidate: &Analysis) {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        serde_json::from_str(include_str!(
            "../fixtures/literary-ri-prefinal-history.json"
        ))
        .unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-legacy-candidate-preservation-passed"
    );
    let source_bytes = std::fs::read(source).unwrap();
    assert_eq!(
        history["source_files_sha256"][source],
        format!("{:x}", Sha256::digest(source_bytes))
    );
    let row = &history["changes"][surface];
    assert!(
        row["origins"]
            .as_array()
            .unwrap()
            .iter()
            .any(|origin| origin["source"] == source)
    );
    let captured: WordAnalysis = serde_json::from_value(row["after"].clone()).unwrap();
    let before: WordAnalysis = serde_json::from_value(row["before"].clone()).unwrap();
    assert!(captured.analyses.contains(candidate));
    assert!(!before.analyses.contains(candidate));
    assert_eq!(
        captured
            .analyses
            .iter()
            .filter(|a| before.analyses.contains(a))
            .cloned()
            .collect::<Vec<_>>(),
        before.analyses
    );
    let addition = row["additions"]
        .as_array()
        .unwrap()
        .iter()
        .find(|a| serde_json::from_value::<Analysis>(a["analysis"].clone()).unwrap() == *candidate)
        .expect("missing exact RI attribution");
    assert!(
        addition["id"]
            .as_str()
            .unwrap()
            .starts_with("literary-ri-prefinal-legacy-")
    );
    assert_eq!(
        addition["source_entries"],
        serde_json::json!(["krdict:52612", "krdict:86606"])
    );
    assert_eq!(
        addition["structural_verdict"],
        "unjudged broader composition"
    );
    assert_eq!(addition["contextual_verdict"], "unjudged");
    assert_eq!(addition["independent_review"], "pending");
    assert!(
        candidate
            .rules
            .iter()
            .any(|r| r == "prefinal.conjectural_ni")
    );
    assert!(
        candidate
            .morphemes
            .windows(2)
            .any(|pair| pair[0].kind == MorphemeKind::Prefinal
                && pair[0].form == "으리"
                && pair[1].kind == MorphemeKind::Ending
                && matches!(pair[1].form.as_str(), "니" | "으니라"))
    );
    assert!(candidate.breakdown().is_some());
    assert!(
        candidate
            .rules
            .iter()
            .all(|r| klem::rule_explanation(r).is_some())
    );
}
