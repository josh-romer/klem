//! COV-017af / COV-019k: result-transfer connectives and following auxiliaries.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("result-connectives-"));
    suite
}

#[test]
fn result_connectives_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (51, 34));
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
            .analyze_word("쀍어다")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "쀍다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "어다")
    );
}

#[test]
fn annotated_result_connectives_recover_short_forms_and_preserve_full_forms() {
    let engine = Lemmatizer::new();
    let source = include_str!("fixtures/gsd-result-connectives.conllu");
    let rows: Vec<_> = source
        .lines()
        .filter(|l| l.contains("\t내려다\t"))
        .collect();
    assert_eq!(rows.len(), 2);
    for row in rows {
        let f: Vec<_> = row.split('\t').collect();
        assert_eq!((&f[1..3], f[4]), (&["내려다", "내리+어다"][..], "VV+EC"));
        assert!(
            engine
                .analyze_word(f[1])
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == "내리다"
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == "어다"
                    && a.rules.iter().any(|r| r == "ending.result_connective"))
        );
    }
    let source = include_str!("fixtures/kaist-result-connectives.conllu");
    let f: Vec<_> = source
        .lines()
        .find(|l| l.contains("\t빌려다가\t"))
        .unwrap()
        .split('\t')
        .collect();
    assert_eq!(
        (&f[1..3], f[4]),
        (&["빌려다가", "빌리+어다가"][..], "pvg+ecs")
    );
    assert!(
        engine
            .analyze_word(f[1])
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "빌리다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "어다가")
    );
}

#[test]
fn additional_annotated_results_keep_directional_compound_limits_visible() {
    let engine = Lemmatizer::new();
    for (source, word, lemma, forms) in [
        (
            include_str!("fixtures/kaist-result-connectives.conllu"),
            "가져다",
            "가지다",
            vec!["어다"],
        ),
        (
            include_str!("fixtures/gsd-result-connectives.conllu"),
            "쳐다도",
            "치다",
            vec!["어다", "도"],
        ),
    ] {
        assert!(
            source
                .lines()
                .any(|line| line.split('\t').nth(1) == Some(word))
        );
        assert!(engine.analyze_word(word).unwrap().analyses.iter().any(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        }));
    }
    // GSD's 쳐다도 보지 is a directional compound construction. Its token
    // match does not license a generic result-transfer + auxiliary 보다 link.
    let joined = engine.analyze_word("가져다주었다").unwrap();
    assert!(joined.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["가지다", "주다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["어다", "었", "다"])
    }));
}

#[test]
fn result_connectives_dictionary_filters_preserve_roles_and_cli_parity() {
    let path =
        std::env::temp_dir().join(format!("klem-result-connectives-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-result-connectives.json",
        )],
        &path,
        "result_connectives",
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
