use klem::dictionary::{
    AttachmentRule, Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

const RULE: &str = "ending.gentle_command";

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-gentle-command-{test}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[
            "tests/fixtures/gentle-command-native.json".into(),
            "tests/fixtures/gentle-command-boundary-native.json".into(),
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
            && path.morphemes[0].form == "으렴"
            && path.morphemes[0].kind == MorphemeKind::Ending
            && path.rules.iter().any(|rule| rule == RULE)
    })
}

#[test]
fn all_independent_source_stem_class_and_auxiliary_judgments_pass() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/gentle-command-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (23, 15, 8)
    );
    assert!(!report.review_queue.is_empty());
}

#[test]
fn required_paths_keep_native_owners_ordered_components_and_unicode() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/gentle-command-validity.json")).unwrap();
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
    let observations: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/gentle-command-prior-paths.json")).unwrap();
    assert_eq!(observations.len(), 8);
    let engine = Lemmatizer::new();
    for observation in observations {
        let previous: WordAnalysis =
            serde_json::from_value(observation["actual_record"]["analysis"].clone()).unwrap();
        let word = engine
            .analyze_word(observation["surface"].as_str().unwrap())
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
        include_str!("fixtures/gentle-command-native-entries.json"),
        include_str!("fixtures/gentle-command-boundary-native-entries.json"),
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
    let word = Lemmatizer::new().analyze_word("나으렴").unwrap();
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
                    .any(|conflict| conflict.rule == AttachmentRule::GentleCommandVerb)
            );
        }
    }
    let word = Lemmatizer::new().analyze_word("예쁘렴").unwrap();
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
        ("오시렴", "오다", ["시", "으렴"]),
        ("먹었으렴", "먹다", ["었", "으렴"]),
        ("먹겠으렴", "먹다", ["겠", "으렴"]),
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
