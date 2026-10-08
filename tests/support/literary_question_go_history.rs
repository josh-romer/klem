//! Explicit per-path attribution; raw alternatives remain unjudged.
use klem::{Analysis, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

pub fn assert_addition(source: &str, surface: &str, candidate: &Analysis) {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        serde_json::from_str(include_str!(
            "../fixtures/literary-question-go-history.json"
        ))
        .unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-legacy-candidate-preservation-passed"
    );
    assert_eq!(
        history["source_files_sha256"][source],
        format!("{:x}", Sha256::digest(std::fs::read(source).unwrap()))
    );
    let changed = &history["changes"][surface];
    assert!(
        changed["origins"]
            .as_array()
            .unwrap()
            .iter()
            .any(|o| o["source"] == source)
    );
    let before: WordAnalysis = serde_json::from_value(changed["before"].clone()).unwrap();
    let after: WordAnalysis = serde_json::from_value(changed["after"].clone()).unwrap();
    assert_eq!(
        after
            .analyses
            .iter()
            .filter(|a| before.analyses.contains(a))
            .cloned()
            .collect::<Vec<_>>(),
        before.analyses
    );
    assert!(after.analyses.contains(candidate));
    assert!(!before.analyses.contains(candidate));
    let addition = changed["additions"]
        .as_array()
        .unwrap()
        .iter()
        .find(|a| serde_json::from_value::<Analysis>(a["analysis"].clone()).unwrap() == *candidate)
        .expect("missing exact literary-question attribution");
    assert!(
        addition["id"]
            .as_str()
            .unwrap()
            .starts_with("literary-question-go-legacy-")
    );
    assert_eq!(
        addition["structural_verdict"],
        "unjudged broader composition"
    );
    assert_eq!(addition["contextual_verdict"], "unjudged");
    assert_eq!(addition["independent_review"], "pending");
    assert_eq!(
        addition["source_entries"],
        serde_json::json!(["krdict:73889", "krdict:73901"])
    );
    assert!(
        candidate
            .rules
            .iter()
            .any(|r| r == "ending.literary_question_go")
    );
    assert_eq!(candidate.morphemes.len(), 1);
    assert_eq!(candidate.morphemes[0].kind, MorphemeKind::Ending);
    assert_eq!(candidate.morphemes[0].form, "은고");
    let mut inverse = candidate.clone();
    inverse.rules.retain(|r| r != "ending.literary_question_go");
    inverse.morphemes[0].form = "은".into();
    let parent_surface = if candidate.rules.iter().any(|r| r == "copula.omitted_ending") {
        inverse.rules.retain(|r| r != "copula.omitted_ending");
        inverse.rules.push("boundary.attached".into());
        inverse.rules.sort();
        inverse.rules.dedup();
        let explicit_surface = format!("{}인고", candidate.lemmas[0].text);
        let explicit: WordAnalysis =
            serde_json::from_value(history["explicit_question_parents"][&explicit_surface].clone())
                .unwrap();
        let mut explicit_analysis = inverse.clone();
        explicit_analysis.morphemes[0].form = "은고".into();
        explicit_analysis
            .rules
            .push("ending.literary_question_go".into());
        explicit_analysis.rules.sort();
        assert!(explicit.analyses.contains(&explicit_analysis));
        assert_eq!(
            serde_json::from_value::<Analysis>(
                addition["explicit_question_parent"]["analysis"].clone()
            )
            .unwrap(),
            explicit_analysis
        );
        assert_eq!(
            addition["explicit_question_parent"]["surface"],
            explicit_surface
        );
        assert!(
            Lemmatizer::new()
                .analyze_word(&explicit_surface)
                .unwrap()
                .analyses
                .contains(&explicit_analysis)
        );
        format!("{}인", candidate.lemmas[0].text)
    } else {
        surface.strip_suffix('고').unwrap().to_owned()
    };
    assert_eq!(addition["earlier_parent"]["surface"], parent_surface);
    assert_eq!(
        serde_json::from_value::<Analysis>(addition["earlier_parent"]["analysis"].clone()).unwrap(),
        inverse
    );
    let parent: WordAnalysis =
        serde_json::from_value(history["earlier_parents"][&parent_surface].clone()).unwrap();
    assert!(parent.analyses.contains(&inverse));
    assert!(
        Lemmatizer::new()
            .analyze_word(&parent_surface)
            .unwrap()
            .analyses
            .contains(&inverse)
    );
    assert!(candidate.breakdown().is_some());
    assert!(
        candidate
            .rules
            .iter()
            .all(|r| klem::rule_explanation(r).is_some())
    );
}
