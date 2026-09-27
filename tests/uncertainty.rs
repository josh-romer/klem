//! COV-017ad: uncertain possibility and shortened intention questions.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("uncertainty-"));
    suite
}

#[test]
fn uncertainty_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (55, 37));
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
            .analyze_word("쀍을는지")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "쀍다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "을는지")
    );
}

#[test]
fn annotated_uncertainty_recovers_the_unchanged_kaist_gold() {
    let source = include_str!("fixtures/kaist-uncertainty.conllu");
    let fields: Vec<_> = source
        .lines()
        .find(|l| l.starts_with("16\t"))
        .unwrap()
        .split('\t')
        .collect();
    assert_eq!(
        (&fields[1..3], fields[4]),
        (&["같을는지", "같+을는지"][..], "paa+ecs")
    );
    let result = Lemmatizer::new().analyze_word(fields[1]).unwrap();
    assert!(result.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "같다"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "을는지"
        && a.rules.iter().any(|r| r == "ending.uncertainty")));
}

#[test]
fn uncertainty_endings_do_not_invent_an_auxiliary_connector() {
    let engine = Lemmatizer::new();
    for (word, ending) in [
        ("먹을는지보다", "을는지"),
        ("먹으려는가보다", "으려는가"),
        ("먹으려는지보다", "으려는지"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(["먹다", "보다"])
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq([ending, "다"])
            }),
            "{word}"
        );
    }
}

#[test]
fn uncertainty_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-uncertainty-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-uncertainty.json")],
        &path,
        "uncertainty",
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
