//! COV-017aw: derived rhetorical adjectives; broader attachment audit remains open.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("ryeogo-"));
    suite
}

#[test]
fn ryeogo_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (28, 32));
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
            if a.morphemes.iter().any(|m| m.form == "답다")
                && a.morphemes.first().is_some_and(|m| m.form == "답다")
                && a.morphemes.get(1).is_some_and(|m| m.form == "으려고")
            {
                assert!(a.rules.iter().any(|r| r == "irregular.bieup"));
            }
        }
    }
}

#[test]
fn ryeogo_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-ryeogo-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-llago.json"),
            PathBuf::from("tests/fixtures/krdict-ryeogo-extra.json"),
        ],
        &path,
        "llago",
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
fn source_conflicted_expansions_remain_hypotheses_pending_review() {
    // These are preservation checks, not positive grammaticality judgments.
    // KRDict's shortened expressions have broader notes than the direct
    // intention entries; COV-017aw must resolve those conflicts explicitly.
    for (word, lemmas, forms) in [
        (
            "학생이려고하니까",
            vec!["학생", "이다", "하다"],
            vec!["으려고", "으니까"],
        ),
        (
            "먹었으려고하더라",
            vec!["먹다", "하다"],
            vec!["었", "으려고", "더라"],
        ),
        (
            "먹겠으려고하던",
            vec!["먹다", "하다"],
            vec!["겠", "으려고", "던"],
        ),
        ("좋으려고한다", vec!["좋다", "하다"], vec!["으려고", "는다"]),
    ] {
        let analysis = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            analysis.analyses.iter().any(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            }),
            "{word}"
        );
    }
}
