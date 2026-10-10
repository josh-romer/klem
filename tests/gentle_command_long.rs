use klem::dictionary::{
    AttachmentRule, Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

const RULE: &str = "ending.gentle_command_long";

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-gentle-command-long-{test}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[
            "tests/fixtures/gentle-command-long-native.json".into(),
            "tests/fixtures/gentle-command-long-boundary-native.json".into(),
            "tests/fixtures/gentle-command-long-novel-boundary-native.json".into(),
        ],
        &path,
        "complete-original-gentle-command",
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
            && path.morphemes[0].form == "으려무나"
            && path.morphemes[0].kind == MorphemeKind::Ending
            && path.rules.iter().any(|rule| rule == RULE)
    })
}

#[test]
fn all_independent_source_stem_class_and_auxiliary_judgments_pass() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/gentle-command-long-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (25, 16, 9)
    );
    assert!(!report.review_queue.is_empty());
}

#[test]
fn required_paths_keep_native_owners_ordered_components_and_unicode() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/gentle-command-long-validity.json")).unwrap();
    let (_cleanup, dictionary) = dictionary("targets");
    let mut session = DictionarySession::new(&dictionary, 4096);
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let word = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap(),
            "{}",
            case.id
        );
        let target = &case.judgments[0];
        if target.verdict != validity::Verdict::Required {
            continue;
        }
        let path = word
            .analyses
            .iter()
            .find(|path| {
                path.lemmas
                    .iter()
                    .map(|head| &head.text)
                    .eq(target.lemmas.iter())
                    && path.lemmas.iter().map(|head| &head.kind).eq(target
                        .lemma_kinds
                        .as_ref()
                        .unwrap()
                        .iter())
                    && path.morphemes.iter().map(|part| &part.form).eq(target
                        .morphemes
                        .as_ref()
                        .unwrap()
                        .iter())
                    && path.morphemes.iter().map(|part| &part.kind).eq(target
                        .morpheme_kinds
                        .as_ref()
                        .unwrap()
                        .iter())
                    && path.rules.iter().any(|rule| rule == RULE)
            })
            .unwrap();
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
fn all_previous_source_alternatives_and_their_order_are_preserved() {
    let observations: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/gentle-command-long-prior-paths.json"
    ))
    .unwrap();
    assert_eq!(observations.len(), 8);
    let engine = Lemmatizer::new();
    for observation in observations {
        let previous: WordAnalysis =
            serde_json::from_value(observation["actual_record"]["analysis"].clone()).unwrap();
        let word = engine
            .analyze_word(observation["actual_record"]["surface"].as_str().unwrap())
            .unwrap();
        assert_eq!(
            word.analyses
                .iter()
                .filter(|path| previous.analyses.contains(path))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses
        );
    }
}

#[test]
fn native_import_preserves_every_complete_field_and_homonym() {
    let (_cleanup, dictionary) = dictionary("fields");
    for fixture in [
        include_str!("fixtures/gentle-command-long-native-entries.json"),
        include_str!("fixtures/gentle-command-long-boundary-native-entries.json"),
    ] {
        let entries: serde_json::Map<String, Value> = serde_json::from_str(fixture).unwrap();
        for (ident, original) in entries {
            let actual = dictionary.entry(&ident).unwrap().unwrap();
            assert_eq!(serde_json::to_value(actual).unwrap(), original, "{ident}");
        }
    }
}

#[test]
fn verb_and_adjective_homonyms_receive_separate_ending_assessments() {
    let (_cleanup, dictionary) = dictionary("class");
    let mut session = DictionarySession::new(&dictionary, 0);
    let word = Lemmatizer::new().analyze_word("나으려무나").unwrap();
    let path = reading(&word, "낫다").unwrap();
    let annotation = session.annotate(&word).unwrap();
    let assessment = annotation.assess(path);
    assert_eq!(assessment.status, Compatibility::Compatible);
    let native = dictionary.lookup("낫다").unwrap();
    assert!(native.iter().any(|entry| entry.pos == "동사"));
    assert!(native.iter().any(|entry| entry.pos == "형용사"));
    for entry in &assessment.lemmas[0].entries {
        let owner = native.iter().find(|owner| owner.id == entry.id).unwrap();
        if owner.pos == "형용사" {
            assert_eq!(entry.status, Compatibility::Incompatible);
            assert!(
                entry
                    .conflicts
                    .iter()
                    .any(|conflict| conflict.rule == AttachmentRule::GentleCommandLongVerb)
            );
        }
    }
    let word = Lemmatizer::new().analyze_word("예쁘려무나").unwrap();
    let path = reading(&word, "예쁘다").unwrap();
    assert_eq!(
        session.annotate(&word).unwrap().assess(path).status,
        Compatibility::Incompatible
    );
}

#[test]
fn unlisted_prefinal_combinations_keep_unknown_compatibility() {
    let (_cleanup, dictionary) = dictionary("prefinal");
    let mut session = DictionarySession::new(&dictionary, 0);
    for (surface, lemma, forms) in [
        ("오시려무나", "오다", ["시", "으려무나"]),
        ("먹었으려무나", "먹다", ["었", "으려무나"]),
        ("먹겠으려무나", "먹다", ["겠", "으려무나"]),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let path = word
            .analyses
            .iter()
            .find(|path| {
                path.lemmas.len() == 1
                    && path.lemmas[0].text == lemma
                    && path
                        .morphemes
                        .iter()
                        .map(|part| part.form.as_str())
                        .eq(forms)
                    && path.rules.iter().any(|rule| rule == RULE)
            })
            .unwrap();
        assert_eq!(
            session.annotate(&word).unwrap().assess(path).status,
            Compatibility::Unknown,
            "{surface}"
        );
    }
}

#[test]
fn existential_homonyms_keep_individual_verb_attachment_without_selecting_context() {
    let (_cleanup, dictionary) = dictionary("existential");
    let mut session = DictionarySession::new(&dictionary, 0);
    let word = Lemmatizer::new().analyze_word("있으려무나").unwrap();
    let path = reading(&word, "있다").unwrap();
    let annotation = session.annotate(&word).unwrap();
    let assessment = annotation.assess(path);
    assert_eq!(assessment.status, Compatibility::Compatible);
    let native = dictionary.lookup("있다").unwrap();
    assert_eq!(native.len(), 3);
    for entry in &assessment.lemmas[0].entries {
        let owner = native.iter().find(|owner| owner.id == entry.id).unwrap();
        if owner.pos == "형용사" {
            assert_eq!(entry.status, Compatibility::Incompatible);
            assert!(
                entry
                    .conflicts
                    .iter()
                    .any(|conflict| conflict.rule == AttachmentRule::GentleCommandLongVerb)
            );
        } else if owner.pos == "동사" {
            assert_eq!(entry.status, Compatibility::Compatible);
        }
    }
}

#[test]
fn correctly_inflected_dapda_exclusions_use_the_actual_nominal_suffix_shape() {
    let raw = include_str!("fixtures/gentle-command-class-interaction-validity.json");
    let suite: validity::Suite = serde_json::from_str(raw).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (3, 1, 2)
    );

    // Exercise the same target shape against an actually emitted ordinary
    // adjective path, so an incorrect lemma/suffix representation cannot make
    // all forbidden assertions vacuously pass.
    let mut altered: validity::Suite = serde_json::from_str(raw).unwrap();
    altered
        .cases
        .retain(|case| case.id == "dapda-gentle-boundary-short-gentle");
    altered.cases[0].surface = "학생다워요".into();
    altered.cases[0].judgments[0].morphemes = Some(vec!["답다".into(), "어요".into()]);
    altered.cases[0].judgments[0].required_rules = Some(vec!["suffix.adjectival.dap".into()]);
    let report = validity::evaluate(&altered).unwrap();
    assert!(!report.passed());
    assert_eq!(report.forbidden_present, 1);
    assert_eq!(report.violations.len(), 1);
}

#[test]
fn all_individual_novel_targets_keep_dictionary_verbs_and_complete_native_owners() {
    let suite: validity::Suite = serde_json::from_str(include_str!(
        "fixtures/gentle-command-long-novel-validity.json"
    ))
    .unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (8, 8, 0)
    );
    let (_cleanup, dictionary) = dictionary("novel");
    let mut session = DictionarySession::new(&dictionary, 4096);
    for case in suite.cases {
        let word = Lemmatizer::new().analyze_word(&case.surface).unwrap();
        let target = &case.judgments[0];
        let path = reading(&word, &target.lemmas[0]).unwrap();
        assert_eq!(
            session.annotate(&word).unwrap().assess(path).status,
            Compatibility::Compatible,
            "{}",
            case.id
        );
    }
    let entries: serde_json::Map<String, Value> = serde_json::from_str(include_str!(
        "fixtures/gentle-command-long-novel-native-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 15);
    for (ident, original) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&ident).unwrap().unwrap()).unwrap(),
            original,
            "{ident}"
        );
    }
}
