//! COV-017bv: source-scoped refuting questions and immutable prior candidates.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, Session};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "ending.refuting_question";
fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/gam-question-sources.json")).unwrap()
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == c["lemmas"]
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == c["lemma_kinds"]
        && serde_json::to_value(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()).unwrap()
            == c["morphemes"]
        && serde_json::to_value(a.morphemes.iter().map(|m| m.kind).collect::<Vec<_>>()).unwrap()
            == c["morpheme_kinds"]
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-gam-question-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-gam-question.json")],
            &path,
            "gam-question-test",
        )
        .unwrap();
        Self(path)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

#[test]
fn native_entries_and_proposal_identity_are_preserved() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    assert_eq!(fixture["cases"].as_array().unwrap().len(), 69);
    assert_eq!(
        fixture["cases"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|c| c["verdict"] == "required")
            .count(),
        57
    );
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    for c in fixture["cases"].as_array().unwrap() {
        assert_eq!(c["contextual_verdict"], "unjudged");
        assert_eq!(c["independent_review"], "pending");
    }
    let catalog: Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    assert_eq!(catalog["-은감"]["sources"][0]["id"], 73878);
    assert_eq!(catalog["-은감"]["sources"][1]["id"], 73888);
}

#[test]
fn all_named_paths_unicode_and_cache_budgets_agree() {
    let fixture = evidence();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        for c in fixture["cases"].as_array().unwrap() {
            let surface = c["surface"].as_str().unwrap();
            let word = session.analyze_word(surface).unwrap();
            assert_eq!(
                word,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            let paths: Vec<_> = word.analyses.iter().filter(|a| matches(a, c)).collect();
            if c["verdict"] == "required" {
                assert!(!paths.is_empty(), "{}: {word:?}", c["id"]);
                for a in paths {
                    assert!(a.rules.iter().any(|r| r == RULE));
                }
            } else {
                assert!(paths.is_empty(), "{}: {paths:?}", c["id"]);
            }
            for a in &word.analyses {
                assert!(a.breakdown().is_some(), "{surface}: {a:?}");
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            }
        }
    }
}

#[test]
fn central_regressions_and_dictionary_owner_classes_agree() {
    let file = Fixture::new("policy");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut raw: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    raw.cases.retain(|c| c.id.starts_with("gam-question-"));
    let report = validity::evaluate(&raw).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (57, 12));
    let mut policy: validity::Suite =
        serde_json::from_str(include_str!("fixtures/dictionary-attachments.json")).unwrap();
    policy.cases.retain(|c| c.id.starts_with("gam-question-"));
    for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
        let report = validity::evaluate_with(&policy, |w| {
            let mut word = engine.analyze_word(w).unwrap();
            let mut native = dictionary.annotate(&word).unwrap();
            native.filter(&mut word, filter);
            Ok(word)
        })
        .unwrap();
        assert_eq!(report.required_present, 4);
        assert_eq!(
            report.forbidden_present,
            if filter == DictionaryFilter::Headword {
                2
            } else {
                0
            }
        );
    }
    // These are non-listed prefinal extensions, not evidence of impossibility.
    let word = engine.analyze_word("좋았은감").unwrap();
    let native = dictionary.annotate(&word).unwrap();
    let mut unknowns = 0;
    for (a, r) in word.analyses.iter().zip(&native.readings) {
        if a.lemmas.len() == 1
            && a.lemmas[0].text == "좋다"
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["었", "은감"])
        {
            assert_eq!(r.status, klem::dictionary::Compatibility::Unknown);
            unknowns += 1;
        }
    }
    assert!(unknowns > 0);
    for surface in ["먹어본감", "먹고싶는감", "학생이는감", "아이답는감"] {
        let word = engine.analyze_word(surface).unwrap();
        assert!(
            !word.analyses.iter().any(|a| {
                a.rules.iter().any(|r| r == RULE)
                    && ((surface == "먹어본감"
                        && a.lemmas
                            .iter()
                            .any(|l| l.kind == klem::LemmaKind::Auxiliary && l.text == "보다"))
                        || (surface == "먹고싶는감"
                            && a.lemmas
                                .iter()
                                .any(|l| l.kind == klem::LemmaKind::Auxiliary && l.text == "싶다"))
                        || (surface == "학생이는감"
                            && a.lemmas.iter().any(|l| l.kind == klem::LemmaKind::Copula))
                        || (surface == "아이답는감"
                            && a.morphemes.iter().any(|m| m.form == "답다")))
            }),
            "{surface}"
        );
    }
}

#[test]
fn every_frozen_candidate_retains_its_native_reading_and_cli_filters_agree() {
    let file = Fixture::new("retention");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, before) in evidence()["before_words"].as_object().unwrap() {
        let word = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let original: Vec<Analysis> =
            serde_json::from_value(before["analysis"]["analyses"].clone()).unwrap();
        let readings = before["dictionary"]["readings"].as_array().unwrap();
        let mut cursor = 0;
        for (i, prior) in original.iter().enumerate() {
            let position = word.analyses[cursor..]
                .iter()
                .position(|a| a == prior)
                .unwrap_or_else(|| panic!("{surface}: prior path lost: {prior:?}"))
                + cursor;
            assert_eq!(
                serde_json::to_value(&annotation.readings[position]).unwrap(),
                readings[i],
                "{surface}"
            );
            cursor = position + 1;
        }
        for a in &word.analyses {
            if !original.contains(a) {
                assert!(a.rules.iter().any(|r| r == RULE), "{surface}: {a:?}");
            }
        }
        for filter in [
            None,
            Some(DictionaryFilter::Headword),
            Some(DictionaryFilter::Compatible),
        ] {
            let mut expected = word.clone();
            let mut native = annotation.clone();
            if let Some(f) = filter {
                native.filter(&mut expected, f);
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", surface, "--dictionary"]).arg(&file.0);
            if let Some(f) = filter {
                cmd.arg(if f == DictionaryFilter::Headword {
                    "--dict-only"
                } else {
                    "--dict-compatible"
                });
            }
            let result = cmd.output().unwrap();
            assert!(result.status.success());
            let mut actual: Value = serde_json::from_slice(&result.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(native).unwrap()
            );
            assert_eq!(actual, serde_json::to_value(expected).unwrap());
        }
    }
}
