//! COV-021l: complete source examples, unchanged corpus gold and past senses.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Annotation, Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary,
    import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{collections::BTreeMap, fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-direct-command-review-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-gera-nera.json"),
                PathBuf::from("tests/fixtures/krdict-direct-command-review.json"),
            ],
            &path,
            "direct-command-review",
        )
        .unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/direct-command-review-sources.json")).unwrap()
}
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases
        .retain(|c| c.id.starts_with("direct-command-review-"));
    s
}
fn indices(word: &WordAnalysis, c: &Value) -> Vec<usize> {
    word.analyses
        .iter()
        .enumerate()
        .filter(|(_, a)| {
            serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
                && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
        })
        .map(|(i, _)| i)
        .collect()
}

#[test]
fn complete_native_command_examples_and_original_gold_have_individual_cases() {
    let f = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    assert_eq!(f["new_source_ids"].as_array().unwrap().len(), 13);
    assert_eq!(f["source_entries"].as_array().unwrap().len(), 16);
    for e in f["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    assert_eq!(f["attestations"].as_array().unwrap().len(), 9);
    let cases = suite();
    for ident in ["krdict:66953", "krdict:68835"] {
        let e = db.entry(ident).unwrap().unwrap();
        for sense in e.senses {
            for (i, group) in sense.examples.iter().enumerate() {
                let matched: Vec<_> = f["attestations"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .filter(|a| {
                        a["source_id"] == ident
                            && a["sense"] == sense.id
                            && a["example_group_index"] == i
                    })
                    .collect();
                assert_eq!(matched.len(), 1);
                let a = matched[0];
                assert_eq!(a["examples"], serde_json::to_value(group).unwrap());
                assert!(
                    group
                        .iter()
                        .any(|line| line.contains(a["surface"].as_str().unwrap()))
                );
                assert!(
                    cases
                        .cases
                        .iter()
                        .any(|c| c.id == a["case"] && c.surface == a["surface"])
                );
            }
        }
    }
    let kaist = include_str!("fixtures/kaist-direct-command-review.conllu");
    let gsd = include_str!("fixtures/gsd-direct-command-review.conllu");
    assert_eq!(f["corpus_rows"].as_array().unwrap().len(), 4);
    for row in f["corpus_rows"].as_array().unwrap() {
        let text = if row["path"].as_str().unwrap().contains("kaist") {
            kaist
        } else {
            gsd
        };
        assert!(text.contains(row["original_sentence"].as_str().unwrap()));
        assert!(text.lines().any(|line| line == row["original_row"]));
        assert!(cases.cases.iter().any(|c| c.id == row["case_id"]));
    }
    let report = validity::evaluate(&cases).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (15, 3));
}

#[test]
fn every_original_raw_hypothesis_and_entry_judgment_preserves_its_owner() {
    let f = sources();
    let fixture = Fixture::new("entries");
    let db = fixture.open();
    let mut session = DictionarySession::new(&db, 4096);
    let mut uncached = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    let mut words = BTreeMap::new();
    for (surface, before) in f["before_words"].as_object().unwrap() {
        let w = engine.analyze_word(surface).unwrap();
        assert_eq!(
            w,
            serde_json::from_value::<WordAnalysis>(before.clone()).unwrap()
        );
        assert_eq!(
            w,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(w.analyses.iter().all(|a| a.breakdown().is_some()));
        let annotation = session.annotate(&w).unwrap();
        assert_eq!(annotation, uncached.annotate(&w).unwrap());
        assert!(session.cache_bytes() <= 4096);
        assert_eq!(uncached.cache_bytes(), 0);
        words.insert(surface.clone(), (w, annotation));
    }
    let mut upgrades = 0;
    for c in f["entry_cases"].as_array().unwrap() {
        let (w, annotation) = &words[c["surface"].as_str().unwrap()];
        let current = indices(w, c);
        assert_eq!(
            serde_json::to_value(&current).unwrap(),
            c["before_candidate_indices"]
        );
        assert!(!current.is_empty());
        for (n, i) in current.into_iter().enumerate() {
            let assessment = annotation.assess(&w.analyses[i]);
            let owner = &assessment.lemmas[c["lemma_index"].as_u64().unwrap() as usize];
            if let Some(ident) = c["entry_id"].as_str() {
                let e = owner.entries.iter().find(|e| e.id == ident).unwrap();
                assert_eq!(
                    serde_json::to_value(e.status).unwrap(),
                    c["expected_status"],
                    "{}",
                    c["id"]
                );
                if c["before_entry_statuses"][n] != c["expected_status"] {
                    upgrades += 1;
                    assert_eq!(c["before_entry_statuses"][n], "unknown");
                    assert_eq!(e.status, Compatibility::Compatible);
                    assert!(matches!(ident, "krdict:68756" | "krdict:55296"));
                    assert!(e.conflicts.is_empty());
                }
                if c["surface"] == "무렀거라" {
                    assert_eq!(e.status, Compatibility::Incompatible);
                    assert_eq!(
                        serde_json::to_value(&e.conflicts).unwrap(),
                        serde_json::json!([
                            {"rule":"lexical_spelling", "morpheme_index":0}
                        ])
                    );
                }
            } else {
                assert_eq!(
                    serde_json::to_value(owner).unwrap(),
                    c["before_assessments"][n]
                );
                assert_eq!(owner.status, Compatibility::Unknown);
            }
        }
    }
    assert_eq!(upgrades, 2);
}

#[test]
fn unknown_roles_provider_ids_and_wrong_heads_cannot_borrow_a_past_license() {
    let fixture = Fixture::new("providers");
    let db = fixture.open();
    let mut session = DictionarySession::new(&db, 4096);
    let w = Lemmatizer::new().analyze_word("섰거라").unwrap();
    let f = sources();
    let c = f["entry_cases"]
        .as_array()
        .unwrap()
        .iter()
        .find(|c| c["entry_id"] == "krdict:68756" && c["surface"] == "섰거라")
        .unwrap();
    let a: &Analysis = &w.analyses[indices(&w, c)[0]];
    let original = session.annotate(&w).unwrap();
    for variant in 0..3 {
        let mut annotation: Annotation = original.clone();
        let entry = annotation
            .lemmas
            .iter_mut()
            .find(|l| l.lemma.text == "서다")
            .unwrap()
            .entries
            .iter_mut()
            .find(|e| e.entry.id == "krdict:68756")
            .unwrap();
        match variant {
            0 => entry.entry.id = "other:68756".into(),
            1 => entry.entry.headword = "다른말".into(),
            _ => entry.pos_compatibility = Compatibility::Unknown,
        }
        assert_eq!(annotation.assess(a).status, Compatibility::Unknown);
    }
}

#[test]
fn all_review_cases_keep_cli_filter_and_entry_assessment_parity() {
    let fixture = Fixture::new("parity");
    let db = fixture.open();
    let mut session = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let f = sources();
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let report = validity::evaluate_with(&suite(), |surface| {
            let mut w = engine.analyze_word(surface).unwrap();
            let mut annotation = session.annotate(&w).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut w, filter);
            }
            Ok(w)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
        for surface in f["before_words"].as_object().unwrap().keys() {
            let mut w = engine.analyze_word(surface).unwrap();
            let mut annotation = session.annotate(&w).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut w, filter);
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", surface, "--dictionary"]).arg(&fixture.0);
            if let Some(flag) = flag {
                cmd.arg(flag);
            }
            let output = cmd.output().unwrap();
            assert!(output.status.success());
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(actual.clone()).unwrap(),
                w
            );
            assert_eq!(
                actual["dictionary"],
                serde_json::to_value(&annotation).unwrap()
            );
        }
    }
}
