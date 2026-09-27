//! COV-018y: case phrases before comparison, distinct from spaced adverb 같이.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("comparison-case-"));
    suite
}

#[test]
fn comparison_case_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (18, 4));
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
fn comparison_case_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-comparison-case-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-comparison-case.json")],
        &path,
        "comparison_case",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let mut filtered_suite = suite();
        // The training corpus includes place names absent from KRDict.
        // Preserve these raw paths while testing the dictionary coverage gap.
        for case in &mut filtered_suite.cases {
            if matches!(
                case.id.as_str(),
                "comparison-case-corpus-모스크바" | "comparison-case-corpus-로스앤젤레스"
            ) {
                case.judgments[0].verdict = validity::Verdict::Forbidden;
            }
        }
        let report = validity::evaluate_with(&filtered_suite, |word| {
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
fn comparison_case_provenance_and_spaced_adverb_remain_distinct() {
    let engine = Lemmatizer::new();
    for word in [
        "학교에서처럼만",
        "전에처럼",
        "집서처럼",
        "회사들에서처럼",
        "읽기에서처럼",
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "particle.comparison_case")),
            "{word}"
        );
    }
    // These limit this ordering exception, rather than declaring every
    // alternative lexical reading of the surface linguistically invalid.
    for word in [
        "학교에서에서처럼",
        "친구와같이",
        "학교에서같이",
        "학교에서대로",
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(!result.analyses.iter().any(|a| {
            a.lemmas[0].text == "학교"
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["에서", "에서", "처럼"])
        }));
        if !word.ends_with("처럼") {
            assert!(
                result
                    .analyses
                    .iter()
                    .all(|a| !a.rules.iter().any(|r| r == "particle.comparison_case"))
            );
        }
    }
    let text = "친구와 같이";
    let tokens: Vec<_> = engine.analyze_text(text).collect();
    assert_eq!(
        tokens
            .iter()
            .map(|t| t.surface.as_str())
            .collect::<Vec<_>>(),
        ["친구와", " ", "같이"]
    );
    for token in &tokens {
        assert_eq!(&text[token.span.clone()], token.surface);
    }
    let together = tokens[2].analysis.as_ref().unwrap();
    assert!(together.analyses.iter().any(|a| a.unchanged));
    assert!(together.analyses.iter().any(|a| a.lemmas[0].text == "같다"));
}
