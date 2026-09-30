//! COV-017az: optsi prefinal paradigm, work in progress.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("optsi-"));
    suite
}

#[test]
fn optsi_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (132, 35));
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
fn optsi_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-optsi-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-optsi.json")],
        &path,
        "optsi",
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
fn optsi_primary_references_do_not_impersonate_dictionary_entries() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/optsi-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-optsi.json")).unwrap();
    let entries = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 42);
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), entries.len());
    let suite = suite();
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 4);
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
    for (key, source_ids) in [
        ("-으옵시-", vec![503872, 431790]),
        ("-사옵시-", vec![185242]),
    ] {
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
fn optsi_spelling_constraints_belong_to_the_recovered_boundary() {
    use klem::SpellingClass;
    let engine = Lemmatizer::new();
    for (surface, heads, forms, class, index) in [
        (
            "들으옵시고",
            vec!["듣다"],
            vec!["으옵시", "고"],
            SpellingClass::DigeutIrregular,
            0,
        ),
        (
            "들어주옵시고",
            vec!["듣다", "주다"],
            vec!["어", "으옵시", "고"],
            SpellingClass::DigeutIrregular,
            0,
        ),
        (
            "먹어놓으옵시고",
            vec!["먹다", "놓다"],
            vec!["어", "으옵시", "고"],
            SpellingClass::HieutRegular,
            1,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(heads.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        assert!(
            a.spelling_paths
                .iter()
                .flatten()
                .any(|s| s.class == class && s.morpheme_index == index),
            "{surface}: {a:?}"
        );
        assert!(
            a.spelling_paths
                .iter()
                .flatten()
                .all(|s| s.morpheme_index < a.morphemes.len())
        );
        assert!(a.breakdown().is_some());
    }
    for (surface, head, forms) in [
        ("알사옵시고", "알다", vec!["사옵시", "고"]),
        ("듣사옵시고", "듣다", vec!["사옵시", "고"]),
        ("짓사옵시고", "짓다", vec!["사옵시", "고"]),
        ("돕사옵시고", "돕다", vec!["사옵시", "고"]),
        ("싶으옵시고", "싶다", vec!["으옵시", "고"]),
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
                        .eq(forms.iter().copied())
            })
            .unwrap();
        assert!(a.spelling_paths.is_empty(), "{surface}: {a:?}");
        assert!(!a.rules.iter().any(|r| r == "deletion.rieul"));
        assert!(a.rules.iter().any(|r| r == "prefinal.honorific_polite"));
    }
}
