//! COV-021n: finite written vowel paradigms and unchanged corpus gold.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, SpellingClass, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-finite-vowel-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-finite-vowel.json")],
            &path,
            "finite-vowel",
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
    serde_json::from_str(include_str!("fixtures/finite-vowel-sources.json")).unwrap()
}
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("finite-vowel-"));
    s
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn native_written_forms_full_entries_and_original_sentences_keep_source_identity() {
    let f = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    assert_eq!(f["source_entries"].as_array().unwrap().len(), 106);
    for e in f["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    assert_eq!(f["native_pairs"].as_array().unwrap().len(), 8);
    for pair in f["native_pairs"].as_array().unwrap() {
        let entry = f["source_entries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| {
                e["headword"] == pair[1] && matches!(e["pos"].as_str(), Some("동사" | "형용사"))
            })
            .unwrap();
        assert!(
            entry["forms"]
                .as_array()
                .unwrap()
                .iter()
                .any(|form| form["kind"] == "활용" && form["written"] == pair[0])
        );
    }
    let sentences = include_str!("fixtures/kaist-finite-vowel.conllu");
    assert_eq!(f["corpus_rows"].as_array().unwrap().len(), 4);
    for row in f["corpus_rows"].as_array().unwrap() {
        assert!(sentences.contains(row["original_sentence"].as_str().unwrap()));
        assert!(sentences.lines().any(|l| l == row["original_row"]));
        assert!(suite().cases.iter().any(|c| c.id == row["case_id"]));
    }
}

#[test]
fn scoped_paths_preserve_all_before_hypotheses_unicode_and_lexical_owners() {
    let f = sources();
    let engine = Lemmatizer::new();
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (96, 8));
    for (surface, before) in f["before_words"].as_object().unwrap() {
        let old: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
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
                .filter(|a| old.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            old.analyses,
            "{surface}"
        );
        assert!(current.analyses.iter().all(|a| a.breakdown().is_some()));
    }
    for c in f["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["verdict"] == "required")
    {
        let word = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        let a = word.analyses.iter().find(|a| matches(a, c)).unwrap();
        let entry = f["source_entries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["id"] == c["source_id"])
            .unwrap();
        if entry["pos"] == "형용사" {
            assert!(
                a.spelling_paths
                    .iter()
                    .flatten()
                    .any(|p| p.class == SpellingClass::HieutIrregular && p.morpheme_index == 0),
                "{}: {a:?}",
                c["id"]
            );
        } else {
            assert!(
                !a.spelling_paths
                    .iter()
                    .flatten()
                    .any(|p| p.class == SpellingClass::HieutIrregular),
                "{}: {a:?}",
                c["id"]
            );
            assert_eq!(
                a.rules.iter().any(|r| r == "contraction.deictic_verb"),
                entry["headword"] != "어쩌다"
            );
        }
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        if a.lemmas.len() == 2 {
            use klem::breakdown::Component::{Lemma as L, Morpheme as M};
            assert_eq!(a.breakdown().unwrap(), vec![L(0), M(0), L(1), M(1), M(2)]);
        }
    }
}

#[test]
fn dictionary_filters_caches_and_cli_preserve_finite_lexical_alternatives() {
    let f = sources();
    let fixture = Fixture::new("filters");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let mut cached = DictionarySession::new(&db, 4096);
    let mut uncached = DictionarySession::new(&db, 0);
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let report = validity::evaluate_with(&suite(), |surface| {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = cached.annotate(&word).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut word, filter);
            }
            Ok(word)
        })
        .unwrap();
        assert!(report.passed(), "{flag:?}: {:?}", report.violations);
        for surface in f["before_words"].as_object().unwrap().keys() {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = cached.annotate(&word).unwrap();
            assert_eq!(annotation, uncached.annotate(&word).unwrap());
            assert!(cached.cache_bytes() <= 4096);
            assert_eq!(uncached.cache_bytes(), 0);
            if let Some(filter) = filter {
                annotation.filter(&mut word, filter);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let output = command.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let mut cli: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                cli.as_object_mut().unwrap().remove("dictionary").unwrap(),
                serde_json::to_value(annotation).unwrap()
            );
            assert_eq!(serde_json::from_value::<WordAnalysis>(cli).unwrap(), word);
        }
    }
}

#[test]
fn prefix_controls_do_not_borrow_the_exact_finite_stems() {
    let f = sources();
    let engine = Lemmatizer::new();
    for c in f["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["verdict"] == "forbidden")
    {
        let word = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        assert!(!word.analyses.iter().any(|a| matches(a, c)));
        assert!(
            !word
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "contraction.deictic_verb"))
        );
    }
}
