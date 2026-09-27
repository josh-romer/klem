//! COV-017ah / COV-019l: expectation questions and inference 보다.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("ryeona-"));
    suite
}

#[test]
fn ryeona_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (69, 23));
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
    // An unknown lexical head remains a hypothesis, not a dictionary assertion.
    assert!(
        engine
            .analyze_word("쀍으려나")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "쀍다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "으려나")
    );
}

#[test]
fn ryeona_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-ryeona-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-ryeona.json")],
        &path,
        "ryeona",
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
fn annotated_ryeona_preserves_gold_and_dictionary_decomposition() {
    let source = include_str!("fixtures/kaist-ryeona.conllu");
    assert!(source.contains("# sent_id = MH2_0010-s336\n"));
    let row: Vec<_> = source
        .lines()
        .find(|l| l.starts_with("7\t"))
        .unwrap()
        .split('\t')
        .collect();
    assert_eq!(
        (&row[1..3], row[4]),
        (&["좋아지려나", "좋아지+려나"][..], "pvg+ecx")
    );
    assert!(source.lines().any(|l| l.starts_with("8\t보다\t보+다\t")));
    let engine = Lemmatizer::new();
    let word = engine.analyze_word(row[1]).unwrap();
    assert!(word.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "좋아지다"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "으려나"
        && a.rules.iter().any(|r| r == "ending.expectation_question")));
    assert!(word.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["좋다", "지다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["어", "으려나"])
    }));
    let joined = engine.analyze_word("좋아지려나보다").unwrap();
    assert!(joined.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["좋다", "지다", "보다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["어", "으려나", "다"])
    }));
    // The expression's implicit intention 하다 is not an emitted lemma.
    let contracted = engine.analyze_word("먹으려나").unwrap();
    assert!(!contracted.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["먹다", "하다"])
    }));
}
