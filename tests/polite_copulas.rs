//! COV-017az: omitted copular 이 before basic literary polite 오/옵.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("copula-polite-"));
    suite
}

#[test]
fn polite_copula_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (13, 12));
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
fn polite_copula_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-polite-copula-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-polite-copula.json")],
        &path,
        "polite_copula",
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
fn omission_keeps_nominal_roles_and_local_spelling_owners() {
    let engine = Lemmatizer::new();
    for word in ["누구오리까", "어디오리까", "친구오리까", "ABC오리까"] {
        let a = engine.analyze_word(word).unwrap();
        let omitted = a
            .analyses
            .iter()
            .filter(|a| a.rules.iter().any(|r| r == "copula.omitted_polite"))
            .collect::<Vec<_>>();
        assert!(!omitted.is_empty(), "{word}");
        for path in omitted {
            assert_eq!(path.lemmas.last().unwrap().kind, klem::LemmaKind::Copula);
            assert_eq!(path.lemmas[0].kind, klem::LemmaKind::Nominal);
            assert!(path.spelling_paths.is_empty(), "{word}: {path:?}");
        }
    }
    // Nominalization keeps the earlier lexical owner's irregular spelling.
    let a = engine.analyze_word("들어보기오리까").unwrap();
    let path = a
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["듣다", "보다", "이다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["어", "기", "으옵", "으리까"])
        })
        .unwrap();
    assert!(path.rules.iter().any(|r| r == "copula.omitted_polite"));
    assert!(
        path.spelling_paths
            .iter()
            .flatten()
            .any(|s| { s.class == klem::SpellingClass::DigeutIrregular && s.morpheme_index == 0 })
    );
    assert!(
        path.spelling_paths
            .iter()
            .flatten()
            .all(|s| s.morpheme_index < 2)
    );
    assert!(path.breakdown().is_some());
}

#[test]
fn other_polite_followers_and_lexical_contractions_keep_baseline_outputs() {
    let baseline: Vec<WordAnalysis> =
        serde_json::from_str(include_str!("fixtures/polite-copula-preserved.json")).unwrap();
    assert_eq!(baseline.len(), 8);
    let engine = Lemmatizer::new();
    for expected in baseline {
        assert_eq!(engine.analyze_word(&expected.normalized).unwrap(), expected);
    }
}
