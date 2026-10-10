use klem::dictionary::{
    Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;
#[path = "../tools/validity.rs"]
mod validity;
const RULE: &str = "ending.formal_volitional";

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn original_dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-formal-volitional-{test}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/formal-volitional-native.json",
        )],
        &path,
        "complete-original-formal-volitional",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), dictionary)
}

#[test]
fn raw_rules_enforce_all_independent_spelling_and_prefinal_boundaries() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/formal-volitional-validity.json")).unwrap();
    let policy: Value = serde_json::from_str(include_str!(
        "fixtures/formal-volitional-evaluation-policy.json"
    ))
    .unwrap();
    let dictionary_cases: Vec<String> =
        serde_json::from_value(policy["dictionary_required_case_ids"].clone()).unwrap();
    assert_eq!(dictionary_cases.len(), 6);
    suite
        .cases
        .retain(|case| !dictionary_cases.contains(&case.id));
    assert_eq!(suite.cases.len(), 53);
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (33, 20));
    assert!(!report.review_queue.is_empty());
}

#[test]
fn all_authored_paths_obey_original_dictionary_owner_classes() {
    let suite =
        serde_json::from_str(include_str!("fixtures/formal-volitional-validity.json")).unwrap();
    let (_cleanup, dictionary) = original_dictionary("validity");
    let mut session = DictionarySession::new(&dictionary, 4096);
    let engine = Lemmatizer::new();
    let report = validity::evaluate_with(&suite, |surface| {
        let mut word = engine
            .analyze_word(surface)
            .map_err(|error| error.to_string())?;
        let annotation = session.annotate(&word).map_err(|error| error.to_string())?;
        word.analyses
            .retain(|path| annotation.assess(path).status != Compatibility::Incompatible);
        Ok(word)
    })
    .unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (59, 33, 26)
    );
}

#[test]
fn complete_original_targets_keep_prior_order_and_unicode_equivalence() {
    let proposals: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/formal-volitional-proposals.json")).unwrap();
    assert_eq!(proposals.len(), 17);
    let engine = Lemmatizer::new();
    for proposal in proposals {
        let surface = proposal["surface"].as_str().unwrap();
        let previous: WordAnalysis =
            serde_json::from_value(proposal["baseline_records"]["raw"]["analysis"].clone())
                .unwrap();
        let current = engine.analyze_word(surface).unwrap();
        assert_eq!(
            current,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            current
                .analyses
                .iter()
                .filter(|path| previous.analyses.contains(path))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses
        );
        let lemmas: Vec<String> =
            serde_json::from_value(proposal["proposed_lemmas"].clone()).unwrap();
        let morphs: Vec<String> =
            serde_json::from_value(proposal["proposed_morphemes"].clone()).unwrap();
        assert!(
            current.analyses.iter().any(|path| path
                .lemmas
                .iter()
                .map(|lemma| &lemma.text)
                .eq(lemmas.iter())
                && path
                    .morphemes
                    .iter()
                    .map(|morpheme| &morpheme.form)
                    .eq(morphs.iter())
                && path.rules.iter().any(|rule| rule == RULE)),
            "{}",
            proposal["id"]
        );
        for path in current
            .analyses
            .iter()
            .filter(|path| !previous.analyses.contains(path))
        {
            assert!(path.rules.iter().any(|rule| rule == RULE));
            assert!(
                path.rules
                    .iter()
                    .all(|rule| klem::rule_explanation(rule).is_some())
            );
            assert!(path.breakdown().is_some());
        }
    }
}

#[test]
fn native_entries_keep_every_original_field_and_lexical_homonym() {
    let (_cleanup, dictionary) = original_dictionary("native");
    let owners: std::collections::BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/formal-volitional-native-entries.json"
    ))
    .unwrap();
    assert_eq!(owners.len(), 43);
    for (id, expected) in owners {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
}

#[test]
fn every_observed_source_path_has_exact_complete_native_ownership() {
    use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
    let file = std::env::temp_dir().join(format!(
        "klem-formal-volitional-closure-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/formal-volitional-additional-native.json",
        )],
        &file,
        "complete-original-formal-volitional-source-closure",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let entries: std::collections::BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/formal-volitional-additional-native-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 63);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected
        );
    }
    let observations: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/formal-volitional-source-observations.json"
    ))
    .unwrap();
    assert_eq!(observations.len(), 404);
    let mut session = DictionarySession::new(&dictionary, 4096);
    for observation in observations {
        let word = Lemmatizer::new()
            .analyze_word(observation["surface"].as_str().unwrap())
            .unwrap();
        let path: klem::Analysis = serde_json::from_value(observation["analysis"].clone()).unwrap();
        assert!(word.analyses.contains(&path), "{}", observation["id"]);
        assert_eq!(
            serde_json::to_value(session.annotate(&word).unwrap().assess(&path)).unwrap(),
            observation["dictionary_assessment"],
            "{}",
            observation["id"]
        );
        assert_eq!(observation["contextual_verdict"], "unjudged");
        assert_eq!(observation["independent_review"], "pending");
    }
}
