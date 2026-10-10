use klem::dictionary::{
    Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

const RULE: &str = "ending.willingness_question";

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path =
        std::env::temp_dir().join(format!("klem-willingness-{test}-{}.db", std::process::id()));
    import_krdict(
        &[
            "tests/fixtures/willingness-question-native.json".into(),
            "tests/fixtures/willingness-question-pos-native.json".into(),
        ],
        &path,
        "complete-original-willingness-question",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), dictionary)
}

fn reading<'a>(word: &'a WordAnalysis, lemma: &str) -> Option<&'a Analysis> {
    word.analyses.iter().find(|path| {
        path.lemmas.len() == 1
            && path.lemmas[0].text == lemma
            && path.morphemes.len() == 1
            && path.morphemes[0].form == "으련"
            && path.morphemes[0].kind == MorphemeKind::Ending
            && path.rules.iter().any(|rule| rule == RULE)
    })
}

#[test]
fn all_ten_independent_original_ending_targets_have_exact_paths() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/willingness-question-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (10, 10, 0)
    );
    let (_cleanup, dictionary) = dictionary("source");
    let mut session = DictionarySession::new(&dictionary, 4096);
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let word = engine.analyze_word(&case.surface).unwrap();
        let path = reading(&word, &case.judgments[0].lemmas[0]).unwrap();
        assert_eq!(
            session.annotate(&word).unwrap().assess(path).status,
            Compatibility::Compatible,
            "{}",
            case.id
        );
        assert!(path.breakdown().is_some());
        assert!(
            path.rules
                .iter()
                .all(|rule| klem::rule_explanation(rule).is_some())
        );
    }
}

#[test]
fn original_attachment_notes_select_the_short_and_full_stem_boundaries() {
    let cases: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/willingness-question-boundaries.json"
    ))
    .unwrap();
    assert_eq!(cases.len(), 12);
    let engine = Lemmatizer::new();
    for case in cases {
        let word = engine
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        assert_eq!(
            reading(&word, case["lemma"].as_str().unwrap()).is_some(),
            case["expected"].as_bool().unwrap(),
            "{}",
            case["surface"]
        );
    }
}

#[test]
fn all_original_ending_and_expression_targets_keep_prior_alternatives_and_nfd() {
    let observations: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/willingness-question-prior-paths.json"
    ))
    .unwrap();
    assert_eq!(observations.len(), 18);
    let engine = Lemmatizer::new();
    for observation in observations {
        let surface = observation["surface"].as_str().unwrap();
        let previous: WordAnalysis =
            serde_json::from_value(observation["actual_record"]["analysis"].clone()).unwrap();
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            word.analyses
                .iter()
                .filter(|path| previous.analyses.contains(path))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses,
            "{}",
            observation["id"]
        );
        for path in word
            .analyses
            .iter()
            .filter(|path| !previous.analyses.contains(path))
        {
            assert!(path.rules.iter().any(|rule| rule == RULE));
            assert!(path.breakdown().is_some());
        }
    }
}

#[test]
fn native_fixture_preserves_every_field_and_all_same_head_homonyms() {
    let (_cleanup, dictionary) = dictionary("native");
    let owners: std::collections::BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/willingness-question-native-entries.json"
    ))
    .unwrap();
    assert_eq!(owners.len(), 29);
    for (id, expected) in owners {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
}

#[test]
fn source_iss_and_geot_paths_assess_each_original_lexical_owner() {
    let (_cleanup, dictionary) = dictionary("homonyms");
    let mut session = DictionarySession::new(&dictionary, 4096);
    let engine = Lemmatizer::new();
    for (surface, lemma, required, incompatible) in [
        ("있으련", "있다", "krdict:68796", "krdict:68797"),
        ("걷으련", "걷다", "krdict:25357", "krdict:29667"),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let path = reading(&word, lemma).unwrap();
        let assessment = session.annotate(&word).unwrap().assess(path);
        assert_eq!(assessment.status, Compatibility::Compatible);
        let entries = &assessment.lemmas[0].entries;
        assert_eq!(
            entries
                .iter()
                .find(|entry| entry.id == required)
                .unwrap()
                .status,
            Compatibility::Compatible
        );
        assert_eq!(
            entries
                .iter()
                .find(|entry| entry.id == incompatible)
                .unwrap()
                .status,
            Compatibility::Incompatible
        );
    }
}

#[test]
fn unlisted_prefinals_remain_candidates_without_automatic_compatibility() {
    let (_cleanup, dictionary) = dictionary("prefinal");
    let mut session = DictionarySession::new(&dictionary, 4096);
    let engine = Lemmatizer::new();
    let word = engine.analyze_word("먹었으련").unwrap();
    let path = word
        .analyses
        .iter()
        .find(|path| {
            path.lemmas.len() == 1
                && path.lemmas[0].text == "먹다"
                && path
                    .morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["었", "으련"])
                && path.rules.iter().any(|rule| rule == RULE)
        })
        .unwrap();
    assert_eq!(
        session.annotate(&word).unwrap().assess(path).status,
        Compatibility::Unknown
    );
}

#[test]
fn bare_known_copula_and_derived_adjective_do_not_borrow_the_verb_ending() {
    let engine = Lemmatizer::new();
    {
        let (surface, lemma) = ("학생이련", "이다");
        let word = engine.analyze_word(surface).unwrap();
        assert!(
            !word.analyses.iter().any(|path| {
                path.lemmas.iter().any(|head| head.text == lemma)
                    && path.morphemes.iter().any(|m| m.form == "으련")
                    && path.rules.iter().any(|r| r == RULE)
            }),
            "{surface}"
        );
    }
    let word = engine.analyze_word("학생답련").unwrap();
    assert!(!word.analyses.iter().any(|path| {
        path.lemmas.iter().any(|head| head.text == "학생")
            && path
                .morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["답다", "으련"])
            && path.rules.iter().any(|r| r == RULE)
    }));
}

#[test]
fn unknown_raw_head_is_preserved_and_original_adjective_pos_is_incompatible() {
    let engine = Lemmatizer::new();
    let word = engine.analyze_word("예쁘련").unwrap();
    // The rule engine's finite class inventory has no lexical entry here.
    // A dictionary-backed POS conflict must not erase the raw hypothesis.
    let path = reading(&word, "예쁘다").unwrap();
    let (_cleanup, dictionary) = dictionary("adjective");
    let mut session = DictionarySession::new(&dictionary, 4096);
    assert_eq!(
        session.annotate(&word).unwrap().assess(path).status,
        Compatibility::Incompatible
    );
}
