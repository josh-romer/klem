//! COV-017az: humble prefinal paradigm, work in progress.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("humble-"));
    suite
}

#[test]
fn humble_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (96, 34));
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
fn humble_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-humble-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-humble.json")],
        &path,
        "humble",
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
fn humble_primary_references_are_distinct_from_dictionary_entries() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/humble-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-humble.json")).unwrap();
    let entries = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 30);
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), entries.len());
    let suite = suite();
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 5);
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
    for (key, source_ids) in [("-사옵-", vec![185238, 188130]), ("-삽-", vec![189947])] {
        assert_eq!(labels[key]["kind"], "prefinal");
        assert!(labels[key]["sources"].as_array().unwrap().is_empty());
        let references = labels[key]["references"].as_array().unwrap();
        assert_eq!(references.len(), source_ids.len());
        for (reference, id) in references.iter().zip(source_ids) {
            assert_eq!(
                reference["url"],
                format!("https://opendict.korean.go.kr/dictionary/view?sense_no={id}")
            );
        }
    }
}

#[test]
fn humble_consonant_boundaries_retain_codas_and_prior_spelling_ownership() {
    use klem::SpellingClass;
    let engine = Lemmatizer::new();
    for (surface, head) in [
        ("알사옵고", "알다"),
        ("듣사옵고", "듣다"),
        ("짓사옵고", "짓다"),
        ("돕사옵고", "돕다"),
        ("좋사옵고", "좋다"),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.iter().map(|l| l.text.as_str()).eq([head])
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(["사옵", "고"])
            })
            .unwrap();
        assert!(a.spelling_paths.is_empty(), "{surface}: {a:?}");
        assert!(!a.rules.iter().any(|r| r == "deletion.rieul"));
        assert!(a.rules.iter().any(|r| r == "prefinal.humble_saop"));
    }
    let word = engine.analyze_word("들어주었사옵고").unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["듣다", "주다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["어", "었", "사옵", "고"])
        })
        .unwrap();
    assert!(
        a.spelling_paths
            .iter()
            .flatten()
            .any(|s| s.class == SpellingClass::DigeutIrregular && s.morpheme_index == 0)
    );
    assert!(
        a.spelling_paths
            .iter()
            .flatten()
            .all(|s| s.morpheme_index < a.morphemes.len())
    );
    assert!(a.breakdown().is_some());
}
