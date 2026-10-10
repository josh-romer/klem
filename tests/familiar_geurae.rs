use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn independent_source_boundaries_and_written_variants_match_named_paths() {
    let suite =
        serde_json::from_str(include_str!("fixtures/familiar-geurae-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (19, 8));
    assert!(!report.review_queue.is_empty());
}

#[test]
fn prior_lexical_and_particle_readings_remain_in_order_with_unicode_parity() {
    let previous: std::collections::BTreeMap<String, WordAnalysis> =
        serde_json::from_str(include_str!("fixtures/familiar-geurae-baselines.json")).unwrap();
    let engine = Lemmatizer::new();
    assert_eq!(previous.len(), 32);
    for (surface, old) in previous {
        let current = engine.analyze_word(&surface).unwrap();
        assert_eq!(current.normalized, old.normalized);
        assert_eq!(
            current
                .analyses
                .iter()
                .filter(|path| old.analyses.contains(path))
                .cloned()
                .collect::<Vec<_>>(),
            old.analyses,
            "{surface}"
        );
        assert_eq!(
            current,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        for path in current
            .analyses
            .iter()
            .filter(|path| !old.analyses.contains(path))
        {
            assert!(
                path.rules
                    .iter()
                    .any(|rule| matches!(rule.as_str(), "particle.familiar_geurae"))
            );
            assert!(
                path.rules
                    .iter()
                    .all(|rule| klem::rule_explanation(rule).is_some())
            );
            assert!(path.breakdown().is_some());
        }
        if ["그래", "그려", "오랜만이구먼", "좋구먼", "먹는구먼"].contains(&surface.as_str())
        {
            assert_eq!(current, old, "unrelated standalone/canonical {surface}");
        }
    }
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn complete_original_native_homonyms_retain_fields_and_nonconflicting_source_paths() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    let path = std::env::temp_dir().join(format!(
        "klem-familiar-geurae-native-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/familiar-geurae-native.json",
        )],
        &path,
        "complete-original-familiar-geurae",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let entries: std::collections::BTreeMap<String, Value> =
        serde_json::from_str(include_str!("fixtures/familiar-geurae-native-entries.json")).unwrap();
    assert!(entries.len() > 21);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let mut session = DictionarySession::new(&dictionary, 4096);
    let suite: Value =
        serde_json::from_str(include_str!("fixtures/familiar-geurae-validity.json")).unwrap();
    for case in &suite["cases"].as_array().unwrap()[..4] {
        let judgment = &case["judgments"][0];
        let word = Lemmatizer::new()
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        let annotation = session.annotate(&word).unwrap();
        assert!(
            word.analyses.iter().any(|path| {
                path.lemmas
                    .iter()
                    .map(|lemma| lemma.text.as_str())
                    .eq(judgment["lemmas"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|s| s.as_str().unwrap()))
                    && path.morphemes.iter().map(|morph| morph.form.as_str()).eq(
                        judgment["morphemes"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .map(|s| s.as_str().unwrap()),
                    )
                    && path
                        .rules
                        .iter()
                        .any(|rule| rule == "particle.familiar_geurae")
                    && annotation.assess(path).status != Compatibility::Incompatible
            }),
            "{}",
            case["id"]
        );
    }
}

#[test]
fn every_observed_source_path_has_exact_complete_native_ownership() {
    use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
    let file = std::env::temp_dir().join(format!(
        "klem-familiar-geurae-closure-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/familiar-geurae-additional-native.json",
        )],
        &file,
        "complete-original-familiar-geurae-source-closure",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let entries: std::collections::BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/familiar-geurae-additional-native-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 50);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected
        );
    }
    let observations: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/familiar-geurae-source-observations.json"
    ))
    .unwrap();
    assert_eq!(observations.len(), 152);
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
