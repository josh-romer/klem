//! Exact later additions to the original formal-ending novel snapshots.
use klem::WordAnalysis;
use serde_json::Value;
use std::sync::OnceLock;

pub fn project(frame: &Value, actual: &WordAnalysis) -> WordAnalysis {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        serde_json::from_str(include_str!(
            "../fixtures/reported-experience-novel-history.json"
        ))
        .unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-reported-experience-novel-path-preservation-passed"
    );
    assert_eq!(
        history["source_sha256"],
        "50a02d2f5f11f148497f2f00c782733ee3f8c2e331e1c0e5f74e3b7c8b0ca4dc"
    );
    let matches: Vec<_> = history["raw_changed_frames"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|later| later["before"] == frame["after"])
        .collect();
    if matches.is_empty() {
        return actual.clone();
    }
    assert_eq!(matches.len(), 1, "ambiguous historical novel frame");
    let later = matches[0];
    assert_eq!(later["record"], frame["record"]);
    assert_eq!(
        later["complete_original_line"],
        frame["complete_original_line"]
    );
    let previous: WordAnalysis =
        serde_json::from_value(later["before"]["analysis"].clone()).unwrap();
    let captured: WordAnalysis =
        serde_json::from_value(later["after"]["analysis"].clone()).unwrap();
    assert_eq!(actual, &captured, "uncaptured later novel candidate");
    assert_eq!(
        actual
            .analyses
            .iter()
            .filter(|a| previous.analyses.contains(a))
            .cloned()
            .collect::<Vec<_>>(),
        previous.analyses
    );
    let additions: Vec<_> = actual
        .analyses
        .iter()
        .filter(|a| !previous.analyses.contains(a))
        .collect();
    assert_eq!(additions.len(), 4);
    for path in additions {
        let observations: Vec<_> = history["individual_additions"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|o| {
                o["mode"] == "novel-raw"
                    && o["record"] == later["record"]
                    && serde_json::from_value::<klem::Analysis>(o["analysis"].clone()).unwrap()
                        == *path
            })
            .collect();
        assert_eq!(
            observations.len(),
            1,
            "missing individual novel path witness"
        );
        let observation = observations[0];
        assert!(
            observation["id"]
                .as_str()
                .unwrap()
                .starts_with("reported-experience-broad-")
        );
        assert_eq!(
            observation["complete_original_line"],
            later["complete_original_line"]
        );
        assert_eq!(observation["span"], later["after"]["span"]);
        assert_eq!(observation["source_sha256"], history["source_sha256"]);
        assert_eq!(observation["contextual_verdict"], "unjudged");
        assert_eq!(observation["independent_review"], "pending");
        assert!(path.rules.iter().any(|r| r == "ending.reported_experience"));
        assert!(
            path.rules
                .iter()
                .all(|r| klem::rule_explanation(r).is_some())
        );
        assert!(path.breakdown().is_some());
    }
    previous
}
