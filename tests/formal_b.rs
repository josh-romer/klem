use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "ending.formal_b";

fn path(analysis: &klem::Analysis, lemmas: &[&str]) -> bool {
    analysis
        .lemmas
        .iter()
        .map(|l| l.text.as_str())
        .eq(lemmas.iter().copied())
        && analysis.rules.iter().any(|r| r == RULE)
}

#[test]
fn all_complete_original_targets_preserve_prior_paths_and_unicode_forms() {
    let proposals: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/formal-b-proposals.json")).unwrap();
    assert_eq!(proposals.len(), 46);
    let engine = Lemmatizer::new();
    for proposal in proposals {
        let surface = proposal["surface"].as_str().unwrap();
        let expected: Vec<String> =
            serde_json::from_value(proposal["proposed_lemmas"].clone()).unwrap();
        let before: WordAnalysis =
            serde_json::from_value(proposal["baseline_records"]["raw"]["analysis"].clone())
                .unwrap();
        let after = engine.analyze_word(surface).unwrap();
        assert_eq!(
            after,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            after
                .analyses
                .iter()
                .filter(|a| before.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            before.analyses
        );
        assert!(
            after
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().map(|l| &l.text).eq(expected.iter())
                    && a.rules.iter().any(|r| r == RULE)
                    && a.breakdown().is_some()),
            "{} {surface}: {after:?}",
            proposal["id"]
        );
        assert!(
            after
                .analyses
                .iter()
                .all(|a| a.rules.iter().all(|r| klem::rule_explanation(r).is_some()))
        );
    }
}

#[test]
fn formal_allomorphs_and_unlisted_retrospectives_keep_separate_boundaries() {
    let engine = Lemmatizer::new();
    for (full, short) in [
        ("습디다", "디다"),
        ("습디까", "디까"),
        ("습지요", "지요"),
        ("습죠", "죠"),
        ("습네", "네"),
    ] {
        assert!(
            engine
                .analyze_word(&format!("갑{short}"))
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &["가다"]))
        );
        assert!(
            engine
                .analyze_word(&format!("먹{full}"))
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &["먹다"]))
        );
        for (surface, lemma) in [
            (format!("가{full}"), "가다"),
            (format!("먹{short}"), "먹다"),
            (format!("알{full}"), "알다"),
            (format!("먹더{full}"), "먹다"),
        ] {
            assert!(
                !engine
                    .analyze_word(&surface)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| path(a, &[lemma])),
                "{surface}"
            );
        }
    }
    let source = engine.analyze_word("아름답네").unwrap();
    assert!(
        source
            .analyses
            .iter()
            .any(|a| path(a, &["아름답다"])
                && a.rules.iter().any(|r| r == "formal_b.attested_stem_b"))
    );
    assert!(source.analyses.iter().any(
        |a| a.lemmas.iter().map(|l| l.text.as_str()).eq(["아름답다"])
            && a.morphemes.iter().map(|m| m.form.as_str()).eq(["네"])
            && !a.rules.iter().any(|r| r == RULE)
    ));
    for word in ["춥네", "아름답더네", "아름답겠네"] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "formal_b.attested_stem_b")),
            "{word}"
        );
    }
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn complete_native_identities_and_original_source_tension_stay_exact() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    let file = std::env::temp_dir().join(format!("klem-formal-b-native-{}.db", std::process::id()));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/formal-b-native.json",
        )],
        &file,
        "complete-original-formal-b-source",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let expected: std::collections::BTreeMap<String, Value> =
        serde_json::from_str(include_str!("fixtures/formal-b-native-entries.json")).unwrap();
    assert_eq!(expected.len(), 92);
    for (id, expected) in expected {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let word = Lemmatizer::new().analyze_word("아름답네").unwrap();
    let mut session = DictionarySession::new(&dictionary, 4096);
    let annotation = session.annotate(&word).unwrap();
    let alias = word
        .analyses
        .iter()
        .find(|a| path(a, &["아름답다"]) && a.rules.iter().any(|r| r == "formal_b.attested_stem_b"))
        .unwrap();
    assert_eq!(annotation.assess(alias).status, Compatibility::Unknown);
    let plain = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).eq(["아름답다"])
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["네"])
                && !a.rules.iter().any(|r| r == RULE)
        })
        .unwrap();
    assert_eq!(annotation.assess(plain).status, Compatibility::Compatible);
}

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn individual_source_and_boundary_judgments_have_stable_case_ids() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/formal-b-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 71);
    assert_eq!(report.forbidden_total, 28);
}

#[test]
fn assured_honorific_paths_keep_unlisted_source_scope_unknown() {
    use klem::dictionary::{Compatibility, DictionarySession, SqliteDictionary, import_krdict};
    let file =
        std::env::temp_dir().join(format!("klem-formal-b-markers-{}.db", std::process::id()));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/formal-b-native.json",
        )],
        &file,
        "complete-original-formal-b-source",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let mut session = DictionarySession::new(&dictionary, 4096);
    for (surface, lemma, status) in [
        ("가십지요", "가다", Compatibility::Unknown),
        ("가십죠", "가다", Compatibility::Unknown),
        ("가십디다", "가다", Compatibility::Compatible),
        ("가십디까", "가다", Compatibility::Compatible),
        ("가십네", "가다", Compatibility::Compatible),
        ("가셨습지요", "가다", Compatibility::Compatible),
        ("가셨습죠", "가다", Compatibility::Compatible),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let annotation = session.annotate(&word).unwrap();
        let formal = word.analyses.iter().find(|a| path(a, &[lemma])).unwrap();
        assert_eq!(annotation.assess(formal).status, status, "{surface}");
    }
}

#[test]
fn original_novel_forms_preserve_all_prior_paths_and_unicode_equivalence() {
    let history: Value =
        serde_json::from_str(include_str!("fixtures/formal-b-novel-history.json")).unwrap();
    let frames = history["raw_changed_frames"].as_array().unwrap();
    assert_eq!(frames.len(), 11);
    let engine = Lemmatizer::new();
    for frame in frames {
        let surface = frame["after"]["surface"].as_str().unwrap();
        assert!(
            frame["complete_original_line"]
                .as_str()
                .unwrap()
                .contains(surface)
        );
        let before: WordAnalysis =
            serde_json::from_value(frame["before"]["analysis"].clone()).unwrap();
        let expected: WordAnalysis =
            serde_json::from_value(frame["after"]["analysis"].clone()).unwrap();
        let actual = engine.analyze_word(surface).unwrap();
        assert_eq!(actual, expected, "{surface}");
        assert_eq!(
            actual,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            actual
                .analyses
                .iter()
                .filter(|a| before.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            before.analyses
        );
        for path in actual
            .analyses
            .iter()
            .filter(|a| !before.analyses.contains(a))
        {
            assert!(path.rules.iter().any(|r| r == RULE), "{surface}: {path:?}");
            assert!(path.breakdown().is_some(), "{surface}: {path:?}");
        }
    }
}

#[test]
fn novel_structural_readings_have_individual_judgments_without_promoting_spacing_to_gold() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/formal-b-novel-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 8);
    assert_eq!(report.forbidden_total, 1);
    assert!(!report.review_queue.is_empty());
    let history: Value =
        serde_json::from_str(include_str!("fixtures/formal-b-novel-history.json")).unwrap();
    let spacing = history["individual_spacing_additions"].as_array().unwrap();
    assert_eq!(spacing.len(), 2);
    assert!(
        spacing
            .iter()
            .all(|o| o["contextual_verdict"] == "unjudged" && o["independent_review"] == "pending")
    );
    assert!(
        history["individual_additions"]
            .as_array()
            .unwrap()
            .iter()
            .all(|o| o["contextual_verdict"] == "unjudged")
    );
}

#[test]
fn novel_native_entries_and_each_new_path_assessment_match_original_dictionary() {
    use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
    let file = std::env::temp_dir().join(format!("klem-formal-b-novel-{}.db", std::process::id()));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/formal-b-novel-native.json",
        )],
        &file,
        "complete-original-formal-b-novel-source",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let entries: std::collections::BTreeMap<String, Value> =
        serde_json::from_str(include_str!("fixtures/formal-b-novel-entries.json")).unwrap();
    assert_eq!(entries.len(), 33);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let history: Value =
        serde_json::from_str(include_str!("fixtures/formal-b-novel-history.json")).unwrap();
    let mut session = DictionarySession::new(&dictionary, 4096);
    for observation in history["individual_additions"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|o| o["mode"] == "novel-raw")
    {
        let surface = observation["surface"].as_str().unwrap();
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let path: klem::Analysis = serde_json::from_value(observation["analysis"].clone()).unwrap();
        assert!(word.analyses.contains(&path), "{surface}");
        let annotation = session.annotate(&word).unwrap();
        assert_eq!(
            serde_json::to_value(annotation.assess(&path)).unwrap(),
            observation["dictionary_assessment"],
            "{}",
            observation["id"]
        );
    }
}
