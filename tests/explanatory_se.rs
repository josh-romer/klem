use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;
#[path = "../tools/validity.rs"]
mod validity;
const RULE: &str = "ending.explanatory_se";

#[test]
fn original_annotated_gold_is_recovered_in_its_complete_sentence() {
    let suite =
        serde_json::from_str(include_str!("fixtures/explanatory-se-gold-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 2);
    let contexts: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/explanatory-se-gold-contexts.json")).unwrap();
    let engine = Lemmatizer::new();
    for context in contexts {
        let expected: Vec<String> = serde_json::from_value(context["expected"].clone()).unwrap();
        for text in [
            context["text"].as_str().unwrap().to_owned(),
            context["text"].as_str().unwrap().nfd().collect(),
        ] {
            let mut cursor = 0;
            let mut recovered = false;
            for token in engine.analyze_text(&text) {
                assert_eq!(token.span.start, cursor);
                assert_eq!(&text[token.span.clone()], token.surface);
                cursor = token.span.end;
                if token.surface.nfc().collect::<String>() == context["surface"].as_str().unwrap() {
                    recovered = token
                        .analysis
                        .as_ref()
                        .unwrap()
                        .analyses
                        .iter()
                        .any(|path| {
                            path.lemmas
                                .iter()
                                .map(|lemma| &lemma.text)
                                .eq(expected.iter())
                                && path.rules.iter().any(|rule| rule == RULE)
                        });
                }
            }
            assert_eq!(cursor, text.len());
            assert!(recovered, "{}", context["id"]);
        }
    }
}

#[test]
fn lexical_collisions_keep_every_previous_reading_and_order() {
    let words: std::collections::BTreeMap<String, WordAnalysis> = serde_json::from_str(
        include_str!("fixtures/explanatory-se-lexical-baselines.json"),
    )
    .unwrap();
    let engine = Lemmatizer::new();
    for (surface, previous) in words {
        let current = engine.analyze_word(&surface).unwrap();
        assert_eq!(
            current
                .analyses
                .iter()
                .filter(|path| previous.analyses.contains(path))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses,
            "{surface}"
        );
        assert!(current.analyses.iter().any(
            |path| path.unchanged && path.lemmas.iter().map(|lemma| &lemma.text).eq([&surface])
        ));
        assert_eq!(
            current,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
    }
}

#[test]
fn each_independently_authored_source_and_boundary_case_matches_its_named_path() {
    let suite =
        serde_json::from_str(include_str!("fixtures/explanatory-se-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 37);
    assert_eq!(report.forbidden_total, 9);
    assert!(!report.review_queue.is_empty());
}

#[test]
fn complete_original_source_targets_keep_prior_paths_order_and_unicode_forms() {
    let proposals: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/explanatory-se-proposals.json")).unwrap();
    assert_eq!(proposals.len(), 21);
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
                .filter(|p| previous.analyses.contains(p))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses
        );
        let lemmas: Vec<String> =
            serde_json::from_value(proposal["proposed_lemmas"].clone()).unwrap();
        let morphs: Vec<String> =
            serde_json::from_value(proposal["proposed_morphemes"].clone()).unwrap();
        assert!(
            current
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().map(|l| &l.text).eq(lemmas.iter())
                    && a.morphemes.iter().map(|m| &m.form).eq(morphs.iter())
                    && proposal["proposed_required_rules"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .all(|r| a.rules.iter().any(|rule| rule == r.as_str().unwrap()))),
            "{}",
            proposal["id"]
        );
        for path in current
            .analyses
            .iter()
            .filter(|p| !previous.analyses.contains(p))
        {
            assert!(
                path.rules
                    .iter()
                    .any(|r| r == RULE || r == "particle.familiar_gryeo")
            );
            assert!(
                path.rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
            assert!(path.breakdown().is_some());
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
fn original_native_owners_homonyms_and_dictionary_assessments_remain_distinct() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    let file = std::env::temp_dir().join(format!(
        "klem-explanatory-se-native-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/explanatory-se-native.json",
        )],
        &file,
        "complete-original-explanatory-se",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let owners: std::collections::BTreeMap<String, Value> =
        serde_json::from_str(include_str!("fixtures/explanatory-se-native-entries.json")).unwrap();
    assert_eq!(owners.len(), 57);
    for (id, expected) in owners {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let mut session = DictionarySession::new(&dictionary, 4096);
    let proposals: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/explanatory-se-proposals.json")).unwrap();
    for proposal in proposals {
        let word = Lemmatizer::new()
            .analyze_word(proposal["surface"].as_str().unwrap())
            .unwrap();
        let annotation = session.annotate(&word).unwrap();
        let expected: Vec<String> =
            serde_json::from_value(proposal["proposed_lemmas"].clone()).unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas.iter().map(|l| &l.text).eq(expected.iter())
                    && proposal["proposed_required_rules"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .all(|r| a.rules.iter().any(|rule| rule == r.as_str().unwrap()))
                    && annotation.assess(a).status != Compatibility::Incompatible),
            "{}",
            proposal["id"]
        );
    }
}

#[test]
fn every_observed_source_path_has_exact_complete_native_ownership() {
    use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
    let file = std::env::temp_dir().join(format!(
        "klem-explanatory-se-closure-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/explanatory-se-additional-native.json",
        )],
        &file,
        "complete-original-explanatory-se-source-closure",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let entries: std::collections::BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/explanatory-se-additional-native-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 80);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected
        );
    }
    let observations: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/explanatory-se-source-observations.json"
    ))
    .unwrap();
    assert_eq!(observations.len(), 632);
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
