use klem::Lemmatizer;
use unicode_normalization::UnicodeNormalization;
#[test]
fn complete_original_examples_recover_each_authored_lemma_with_a_self_question_ending() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/self-question-proposals.json")).unwrap();
    let engine = Lemmatizer::new();
    for case in source.as_array().unwrap() {
        let surface = case["surface"].as_str().unwrap();
        let lemma = case["proposed_lemma"].as_str().unwrap();
        let current = engine.analyze_word(surface).unwrap();
        assert_eq!(
            current,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(
            current
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.text == lemma)
                    && a.morphemes
                        .iter()
                        .any(|m| matches!(m.form.as_str(), "담" | "는담" | "남"))
                    && a.rules.iter().any(|r| r == "ending.self_question")
                    && a.breakdown().is_some()),
            "{} {}: {:?}",
            case["id"],
            surface,
            current
        );
        let before: klem::WordAnalysis =
            serde_json::from_value(case["baseline_records"]["raw"]["analysis"].clone()).unwrap();
        assert_eq!(
            current
                .analyses
                .iter()
                .filter(|a| before.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            before.analyses
        );
    }
}
#[test]
fn present_and_plain_endings_keep_distinct_immediate_prefinal_boundaries() {
    let engine = Lemmatizer::new();
    for surface in ["먹었는담", "먹겠는담", "먹더담", "먹더남"] {
        let current = engine.analyze_word(surface).unwrap();
        assert!(
            !current
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.text == "먹다")
                    && a.rules.iter().any(|r| r == "ending.self_question")),
            "{surface}: {current:?}"
        );
    }
    assert!(klem::rule_explanation("ending.self_question").is_some());
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
fn dictionary() -> (klem::dictionary::SqliteDictionary, Cleanup) {
    use klem::dictionary::{SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!("klem-self-question-{}.db", std::process::id()));
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/self-question-native.json",
        )],
        &path,
        "self-question-original-native",
    )
    .unwrap();
    (SqliteDictionary::open(&path).unwrap(), Cleanup(path))
}

#[test]
fn original_dictionary_owners_survive_filters_and_exact_source_tension_remains_unknown() {
    use klem::dictionary::{Compatibility, DictionarySession};
    let (db, _cleanup) = dictionary();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/self-question-proposals.json")).unwrap();
    let engine = Lemmatizer::new();
    for case in source.as_array().unwrap() {
        let surface = case["surface"].as_str().unwrap();
        let lemma = case["proposed_lemma"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.text == lemma)
                    && a.lemmas.iter().all(|l| l.text == lemma || l.text == "이다")
                    && a.morphemes
                        .iter()
                        .any(|m| matches!(m.form.as_str(), "담" | "는담" | "남"))
                    && annotation
                        .assess(a)
                        .lemmas
                        .iter()
                        .all(|l| !l.entries.is_empty())
                    && annotation.assess(a).status != Compatibility::Incompatible),
            "{surface}: {annotation:?}"
        );
    }
    let word = engine.analyze_word("웃기담").unwrap();
    let annotation = dictionary.annotate(&word).unwrap();
    let path = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "웃기다"
                && a.morphemes.iter().any(|m| m.form == "담")
        })
        .unwrap();
    let assessment = annotation.assess(path);
    let original = assessment.lemmas[0]
        .entries
        .iter()
        .find(|e| e.id == "krdict:63516")
        .unwrap();
    assert_eq!(original.status, Compatibility::Unknown);
    for (surface, lemma, form) in [
        ("먹담", "먹다", "담"),
        ("예쁜담", "예쁘다", "는담"),
        ("예쁘남", "예쁘다", "남"),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let paths: Vec<_> = word
            .analyses
            .iter()
            .filter(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.morphemes.iter().any(|m| m.form == form)
            })
            .collect();
        assert!(!paths.is_empty(), "{surface}");
        for path in paths {
            assert_eq!(
                annotation.assess(path).status,
                Compatibility::Incompatible,
                "{surface}: {path:?}"
            );
        }
    }
}

#[path = "../tools/validity.rs"]
mod validity;
#[test]
fn individual_source_and_boundary_cases_have_executable_stable_judgments() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/self-question-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 25);
    assert_eq!(report.forbidden_total, 4);
}
