#[path = "../tools/validity.rs"]
mod validity;

fn fixture() -> validity::Suite {
    serde_json::from_str(include_str!("fixtures/validity.json")).unwrap()
}

#[test]
fn source_backed_judgments_pass_and_unreviewed_outputs_stay_visible() {
    let report = validity::evaluate(&fixture()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 8460);
    assert_eq!(report.forbidden_total, 3300);
    assert!(!report.review_queue.is_empty());
    assert_eq!(
        report.emitted_nonidentity,
        report.judged_nonidentity + report.review_queue.len()
    );
    assert!(report.review_queue.iter().all(|i| !i.analysis.unchanged));
}

#[test]
fn missing_required_and_emitted_forbidden_paths_are_reported() {
    let mut suite = fixture();
    suite.cases.retain(|c| c.id == "digeut-ambiguity");
    suite.cases[0].judgments[0].verdict = validity::Verdict::Forbidden;
    suite.cases[0].judgments[1].morphemes = Some(vec!["고".into()]);
    let report = validity::evaluate(&suite).unwrap();
    assert!(!report.passed());
    assert_eq!(report.required_present, 0);
    assert_eq!(report.forbidden_present, 1);
    assert_eq!(report.violations.len(), 2);
    assert!(
        report
            .violations
            .iter()
            .all(|s| s.contains("digeut-ambiguity/"))
    );
}

#[test]
fn conflicting_scopes_duplicate_ids_and_missing_sources_fail() {
    let mut suite = fixture();
    suite.cases.retain(|c| c.id == "digeut-ambiguity");
    suite.cases[0].judgments[1].lemmas = vec!["들다".into()];
    suite.cases[0].judgments[1].morphemes = None;
    suite.cases[0].judgments[1].verdict = validity::Verdict::Forbidden;
    assert!(
        validity::evaluate(&suite)
            .unwrap_err()
            .contains("conflicting")
    );
    let mut suite = fixture();
    suite.cases[1].id = suite.cases[0].id.clone();
    assert!(validity::evaluate(&suite).is_err());
    let mut suite = fixture();
    suite.sources.clear();
    assert!(validity::evaluate(&suite).is_err());
}

#[test]
fn homonymous_forms_are_judged_by_optional_roles_without_hiding_alternatives() {
    let mut suite = fixture();
    suite.cases.retain(|c| c.id == "adverb-root-nominal");
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed());
    assert_eq!(report.required_present, 1);
    assert!(
        report
            .review_queue
            .iter()
            .any(|r| r.analysis.lemmas[0].text == "낱낱"
                && r.analysis.morphemes.len() == 1
                && r.analysis.morphemes[0].kind == klem::MorphemeKind::Particle)
    );
    let mut alternative = serde_json::from_value::<validity::Judgment>(serde_json::json!({
        "id":"particle", "lemmas":["낱낱"], "lemma_kinds":["nominal"],
        "morphemes":["이"], "morpheme_kinds":["particle"], "verdict":"forbidden",
        "source":"adverb-root-i", "reason":"Synthetic mutation: ensure the distinct particle candidate is detected."
    })).unwrap();
    suite.cases[0].judgments.push(alternative);
    let report = validity::evaluate(&suite).unwrap();
    assert_eq!(report.required_present, 1);
    assert_eq!(report.forbidden_present, 1);
    assert_eq!(report.violations.len(), 1);
    // Removing a role constraint broadens the forbidden scope and conflicts.
    suite.cases[0].judgments[1].morpheme_kinds = None;
    assert!(
        validity::evaluate(&suite)
            .unwrap_err()
            .contains("conflicting")
    );
    alternative = suite.cases[0].judgments.pop().unwrap();
    alternative.morpheme_kinds = Some(vec![
        klem::MorphemeKind::Particle,
        klem::MorphemeKind::Particle,
    ]);
    suite.cases[0].judgments.push(alternative);
    assert!(
        validity::evaluate(&suite)
            .unwrap_err()
            .contains("invalid judgment")
    );
    suite.cases[0].judgments.pop();
    suite.cases[0].judgments[0].lemma_kinds = Some(vec![]);
    assert!(validity::evaluate(&suite).is_err());
}
