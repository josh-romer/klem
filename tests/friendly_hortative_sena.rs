use klem::dictionary::{
    AttachmentRule, Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

const RULE: &str = "ending.friendly_hortative.sena";
struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
fn dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!("klem-sena-{test}-{}.db", std::process::id()));
    import_krdict(
        &["tests/fixtures/friendly-hortative-sena-native.json".into()],
        &path,
        "complete-original-sena",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), dictionary)
}
fn reading<'a>(word: &'a WordAnalysis, lemma: &str, forms: &[&str]) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
                && a.rules.iter().any(|r| r == RULE)
        })
        .unwrap()
}

#[test]
fn all_independent_source_regular_irregular_honorific_and_auxiliary_judgments_pass() {
    let suite: validity::Suite = serde_json::from_str(include_str!(
        "fixtures/friendly-hortative-sena-validity.json"
    ))
    .unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (25, 19, 6)
    );
    assert!(!report.review_queue.is_empty());
}

#[test]
fn required_paths_keep_native_owners_ordered_components_and_unicode() {
    let suite: validity::Suite = serde_json::from_str(include_str!(
        "fixtures/friendly-hortative-sena-validity.json"
    ))
    .unwrap();
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
        let j = &case.judgments[0];
        if j.verdict != validity::Verdict::Required {
            continue;
        }
        let path = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
                    && a.lemmas
                        .iter()
                        .map(|l| &l.kind)
                        .eq(j.lemma_kinds.as_ref().unwrap().iter())
                    && a.morphemes
                        .iter()
                        .map(|m| &m.form)
                        .eq(j.morphemes.as_ref().unwrap().iter())
                    && a.morphemes.iter().map(|m| &m.kind).eq(j
                        .morpheme_kinds
                        .as_ref()
                        .unwrap()
                        .iter())
                    && a.rules.iter().any(|r| r == RULE)
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
                .all(|r| klem::rule_explanation(r).is_some())
        );
    }
}

#[test]
fn all_63_previous_word_records_keep_every_candidate_and_relative_order() {
    let frames: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/friendly-hortative-sena-prior-paths.json"
    ))
    .unwrap();
    assert_eq!(frames.len(), 63);
    let engine = Lemmatizer::new();
    for frame in frames {
        let previous: WordAnalysis = serde_json::from_value(frame["analysis"].clone()).unwrap();
        let current = engine
            .analyze_word(frame["surface"].as_str().unwrap())
            .unwrap();
        assert_eq!(
            current
                .analyses
                .iter()
                .filter(|a| previous.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses
        );
    }
}

#[test]
fn all_36_native_owners_preserve_every_field_and_homonym() {
    let (_cleanup, dictionary) = dictionary("native");
    let entries: serde_json::Map<String, Value> = serde_json::from_str(include_str!(
        "fixtures/friendly-hortative-sena-native-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 36);
    for (ident, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&ident).unwrap().unwrap()).unwrap(),
            expected,
            "{ident}"
        );
    }
}

#[test]
fn known_adjective_owners_are_excluded_individually_at_the_bare_boundary() {
    let (_cleanup, dictionary) = dictionary("class");
    let mut session = DictionarySession::new(&dictionary, 0);
    let engine = Lemmatizer::new();
    for (surface, lemma) in [("낫세나", "낫다"), ("예쁘세나", "예쁘다")] {
        let word = engine.analyze_word(surface).unwrap();
        let path = reading(&word, lemma, &["세나"]);
        let annotation = session.annotate(&word).unwrap();
        let assessment = annotation.assess(path);
        let native = dictionary.lookup(lemma).unwrap();
        for entry in &assessment.lemmas[0].entries {
            let owner = native.iter().find(|o| o.id == entry.id).unwrap();
            if owner.pos == "형용사" {
                assert_eq!(entry.status, Compatibility::Incompatible);
                assert!(
                    entry
                        .conflicts
                        .iter()
                        .any(|c| c.rule == AttachmentRule::FriendlyHortativeSenaVerb)
                );
            } else if owner.pos == "동사" {
                assert_eq!(entry.status, Compatibility::Compatible);
            }
        }
        assert_eq!(
            assessment.status,
            if lemma == "낫다" {
                Compatibility::Compatible
            } else {
                Compatibility::Incompatible
            }
        );
    }
}

#[test]
fn unreviewed_prefinal_and_honorific_adjective_copula_paths_remain_unknown() {
    let (_cleanup, dictionary) = dictionary("prefinals");
    let mut session = DictionarySession::new(&dictionary, 0);
    let engine = Lemmatizer::new();
    for (surface, lemma, forms) in [
        ("먹었세나", "먹다", ["었", "세나"]),
        ("먹겠세나", "먹다", ["겠", "세나"]),
        ("예쁘시세나", "예쁘다", ["시", "세나"]),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let path = reading(&word, lemma, &forms);
        assert_eq!(
            session.annotate(&word).unwrap().assess(path).status,
            Compatibility::Unknown,
            "{surface}"
        );
    }
    let word = engine.analyze_word("학생이시세나").unwrap();
    let path = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["학생", "이다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["시", "세나"])
                && a.rules.iter().any(|r| r == RULE)
        })
        .unwrap();
    assert_eq!(
        session.annotate(&word).unwrap().assess(path).status,
        Compatibility::Unknown
    );
}

#[test]
fn derived_adjective_boundary_keeps_the_nominal_suffix_shape() {
    let word = Lemmatizer::new().analyze_word("학생답세나").unwrap();
    assert!(!word.analyses.iter().any(|a| {
        a.lemmas.len() == 1
            && a.lemmas[0].text == "학생"
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["답다", "세나"])
            && a.morphemes[0].kind == MorphemeKind::Suffix
    }));
}

#[test]
fn source_rieul_deletion_keeps_the_independent_sada_reading() {
    let word = Lemmatizer::new().analyze_word("사세나").unwrap();
    let live = reading(&word, "살다", &["세나"]);
    let buy = reading(&word, "사다", &["세나"]);
    assert!(live.rules.iter().any(|r| r == "deletion.rieul"));
    assert!(!buy.rules.iter().any(|r| r == "deletion.rieul"));
    let (_cleanup, dictionary) = dictionary("rieul");
    let mut session = DictionarySession::new(&dictionary, 4096);
    let annotated = session.annotate(&word).unwrap();
    assert_eq!(annotated.assess(live).status, Compatibility::Compatible);
    assert_eq!(annotated.assess(buy).status, Compatibility::Compatible);
}
