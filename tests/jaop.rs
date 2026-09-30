//! COV-017az: jaop prefinal paradigm, work in progress.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("jaop-"));
    suite
}

#[test]
fn jaop_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (154, 182));
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let result = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            result,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for a in result.analyses {
            assert!(a.breakdown().is_some(), "{}: {a:?}", case.surface);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn jaop_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-jaop-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-jaop.json")],
        &path,
        "jaop",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let report = validity::evaluate_with(&suite(), |word| {
            let mut analysis = engine.analyze_word(word).unwrap();
            let mut annotation = dictionary.annotate(&analysis).unwrap();
            annotation.filter(&mut analysis, policy);
            let cli = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", word, "--dictionary"])
                .arg(&path)
                .arg(flag)
                .output()
                .unwrap();
            assert!(
                cli.status.success(),
                "{}",
                String::from_utf8_lossy(&cli.stderr)
            );
            let value: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                analysis
            );
            assert_eq!(
                value["dictionary"],
                serde_json::to_value(&annotation).unwrap()
            );
            assert!(dictionary.cache_bytes() <= 4096);
            Ok(analysis)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
    }
}

#[test]
fn jaop_primary_references_and_complete_lexical_entries_remain_distinct() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/jaop-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-jaop.json")).unwrap();
    let entries = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 69);
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), entries.len());
    for id in [50558, 56543] {
        assert!(
            entries
                .iter()
                .any(|e| e["val"].as_str() == Some(&id.to_string()))
        );
    }
    let suite = suite();
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 24);
    for example in examples {
        let case = suite
            .cases
            .iter()
            .find(|c| c.id == example["case_id"])
            .unwrap();
        assert_eq!(case.surface, example["surface"]);
        assert_eq!(suite.sources[&case.judgments[0].source], example["url"]);
        assert_eq!(case.judgments[0].verdict, validity::Verdict::Required);
    }
    let labels: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    for (key, kind, ids) in [
        ("-자옵-", "prefinal", vec![257489, 257308]),
        ("-잡-", "prefinal", vec![258781]),
        ("-자옵시-", "prefinal", vec![543046]),
        ("-나이다", "ending", vec![112447]),
    ] {
        assert_eq!(labels[key]["kind"], kind);
        assert!(labels[key]["sources"].as_array().unwrap().is_empty());
        let references = labels[key]["references"].as_array().unwrap();
        assert_eq!(references.len(), ids.len());
        for (reference, id) in references.iter().zip(ids) {
            assert_eq!(
                reference["url"],
                format!("https://opendict.korean.go.kr/dictionary/view?sense_no={id}")
            );
        }
    }
}

#[test]
fn lexical_and_segmented_paths_keep_separate_spelling_ownership() {
    use klem::SpellingClass;
    let engine = Lemmatizer::new();
    for root in ["듣", "받"] {
        let surface = format!("{root}자와놓으니");
        let word = engine.analyze_word(&surface).unwrap();
        let segmented = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq([format!("{root}다").as_str(), "놓다"])
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(["자옵", "어", "으니"])
            })
            .unwrap();
        assert!(
            segmented
                .spelling_paths
                .iter()
                .flatten()
                .any(|s| s.class == SpellingClass::HieutRegular && s.morpheme_index == 2)
        );
        assert!(!segmented.spelling_paths.iter().flatten().any(|s| matches!(
            s.class,
            SpellingClass::DigeutIrregular | SpellingClass::BieupIrregular
        )));
        let whole = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq([format!("{root}잡다").as_str(), "놓다"])
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(["어", "으니"])
            })
            .unwrap();
        assert!(
            whole
                .spelling_paths
                .iter()
                .flatten()
                .any(|s| s.class == SpellingClass::BieupIrregular && s.morpheme_index == 0)
        );
        assert!(
            whole
                .spelling_paths
                .iter()
                .flatten()
                .any(|s| s.class == SpellingClass::HieutRegular && s.morpheme_index == 1)
        );
        assert!(segmented.breakdown().is_some());
        assert!(whole.breakdown().is_some());
    }
}

#[test]
fn naida_ambiguity_does_not_replace_the_annotated_hana_copula() {
    // Frozen KAIST/GSD dev and test annotate 하나 + 이 + 다. A rule-based
    // analyzer must retain that path alongside the literary 하 + 나이다
    // alternative; annotation does not certify every emitted hypothesis.
    let word = Lemmatizer::new().analyze_word("하나이다").unwrap();
    assert!(word.analyses.iter().any(|a| {
        a.lemmas.iter().map(|l| (l.text.as_str(), l.kind)).eq([
            ("하나", klem::LemmaKind::Nominal),
            ("이다", klem::LemmaKind::Copula),
        ]) && a
            .morphemes
            .iter()
            .map(|m| (m.form.as_str(), m.kind))
            .eq([("다", klem::MorphemeKind::Ending)])
    }));
    assert!(
        word.analyses
            .iter()
            .any(|a| a.lemmas.iter().map(|l| l.text.as_str()).eq(["하다"])
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["나이다"]))
    );
    assert!(word.analyses.iter().any(|a| a.unchanged));
}
