use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "ending.reported_experience";
#[path = "../tools/validity.rs"]
mod validity;

fn proposals() -> Vec<Value> {
    serde_json::from_str(include_str!("fixtures/reported-experience-proposals.json")).unwrap()
}

#[test]
fn all_51_complete_original_source_targets_preserve_paths_order_and_unicode_forms() {
    let proposals = proposals();
    assert_eq!(proposals.len(), 51);
    let engine = Lemmatizer::new();
    for p in proposals {
        let surface = p["surface"].as_str().unwrap();
        let previous: WordAnalysis =
            serde_json::from_value(p["baseline_records"]["raw"]["analysis"].clone()).unwrap();
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
                .filter(|a| previous.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses
        );
        let lemmas: Vec<String> = serde_json::from_value(p["proposed_lemmas"].clone()).unwrap();
        let morphs: Vec<String> = serde_json::from_value(p["proposed_morphemes"].clone()).unwrap();
        assert!(
            current
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().map(|l| &l.text).eq(lemmas.iter())
                    && a.morphemes.iter().map(|m| &m.form).eq(morphs.iter())
                    && a.rules.iter().any(|r| r == RULE)),
            "{}: {surface}",
            p["id"]
        );
        for a in current
            .analyses
            .iter()
            .filter(|a| !previous.analyses.contains(a))
        {
            assert!(a.rules.iter().any(|r| r == RULE));
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            assert!(a.breakdown().is_some());
        }
    }
}

#[test]
fn individual_source_boundary_and_novel_judgments_have_stable_case_ids() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/reported-experience-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 79);
    assert_eq!(report.forbidden_total, 18);
    assert!(!report.review_queue.is_empty());
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn complete_native_source_and_lexical_homonyms_survive_without_pos_rewriting() {
    use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!(
        "klem-reported-experience-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/reported-experience-native.json",
        )],
        &path,
        "complete-original-reported-experience",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let expected: std::collections::BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/reported-experience-native-entries.json"
    ))
    .unwrap();
    assert_eq!(expected.len(), 92);
    for (id, expected) in expected {
        assert_eq!(
            serde_json::to_value(db.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let mut session = DictionarySession::new(&db, 4096);
    for proposal in proposals() {
        let word = Lemmatizer::new()
            .analyze_word(proposal["surface"].as_str().unwrap())
            .unwrap();
        let annotation = session.annotate(&word).unwrap();
        let lemmas: Vec<String> =
            serde_json::from_value(proposal["proposed_lemmas"].clone()).unwrap();
        let morphs: Vec<String> =
            serde_json::from_value(proposal["proposed_morphemes"].clone()).unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas.iter().map(|l| &l.text).eq(lemmas.iter())
                    && a.morphemes.iter().map(|m| &m.form).eq(morphs.iter())
                    && a.rules.iter().any(|r| r == RULE)
                    && annotation.assess(a).status
                        != klem::dictionary::Compatibility::Incompatible),
            "{}",
            proposal["id"]
        );
    }
}

#[test]
fn native_dependent_adjective_commands_are_rejected_only_by_owned_dictionary_filtering() {
    use klem::dictionary::{Compatibility, DictionarySession, SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!(
        "klem-reported-experience-conditional-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/reported-experience-native.json",
        )],
        &path,
        "complete-original-reported-experience",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut session = DictionarySession::new(&db, 4096);
    let cases: Value = serde_json::from_str(include_str!(
        "fixtures/reported-experience-native-conditional-cases.json"
    ))
    .unwrap();
    assert_eq!(cases["cases"].as_array().unwrap().len(), 2);
    for case in cases["cases"].as_array().unwrap() {
        let word = Lemmatizer::new()
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        let expected_morphs: Vec<String> =
            serde_json::from_value(case["judgments"][0]["morphemes"].clone()).unwrap();
        let path = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.iter().map(|l| l.text.as_str()).eq(["좋다"])
                    && a.morphemes
                        .iter()
                        .map(|m| &m.form)
                        .eq(expected_morphs.iter())
                    && a.rules.iter().any(|r| r == RULE)
            })
            .unwrap();
        let annotation = session.annotate(&word).unwrap();
        let assessment = annotation.assess(path);
        assert_eq!(
            assessment.status,
            Compatibility::Incompatible,
            "{}",
            case["id"]
        );
        assert!(
            assessment.lemmas[0]
                .entries
                .iter()
                .all(|e| e.status == Compatibility::Incompatible && !e.conflicts.is_empty())
        );
        let mut headword_word = word.clone();
        annotation.clone().filter(
            &mut headword_word,
            klem::dictionary::DictionaryFilter::Headword,
        );
        assert!(headword_word.analyses.contains(path));
        let mut compatible_word = word.clone();
        annotation.clone().filter(
            &mut compatible_word,
            klem::dictionary::DictionaryFilter::Compatible,
        );
        assert!(!compatible_word.analyses.contains(path));
    }
}

#[test]
fn every_novel_addition_keeps_its_complete_original_native_assessment() {
    use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
    let file = std::env::temp_dir().join(format!(
        "klem-reported-experience-novel-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/reported-experience-novel-native.json",
        )],
        &file,
        "complete-original-reported-experience-novel",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let entries: std::collections::BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/reported-experience-novel-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 2);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected
        );
    }
    let history: Value = serde_json::from_str(include_str!(
        "fixtures/reported-experience-novel-history.json"
    ))
    .unwrap();
    assert_eq!(history["raw_changed_frames"].as_array().unwrap().len(), 2);
    let observations = history["individual_additions"].as_array().unwrap();
    assert_eq!(observations.len(), 16);
    let mut session = DictionarySession::new(&dictionary, 4096);
    for observation in observations.iter().filter(|o| o["mode"] == "novel-raw") {
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
    }
}
