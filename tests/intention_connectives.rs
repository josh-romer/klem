//! COV-017ae / COV-019j: reviewed intention connectives and interrupted-intention auxiliaries.
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
        .retain(|c| c.id.starts_with("intention-connectives-"));
    suite
}

#[test]
fn intention_connectives_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (130, 122));
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
            .analyze_word("쀍으려다")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "쀍다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "으려다")
    );
}

#[test]
fn annotated_intention_keeps_sources_and_distinguishes_incidental_gold() {
    let source = include_str!("fixtures/kaist-intention-connectives.conllu");
    let fields: Vec<_> = source
        .lines()
        .find(|l| l.starts_with("4\t"))
        .unwrap()
        .split('\t')
        .collect();
    assert_eq!(
        (&fields[1..3], fields[4]),
        (&["하려다", "하+려다"][..], "pvg+ecs")
    );
    let engine = Lemmatizer::new();
    let result = engine.analyze_word(fields[1]).unwrap();
    assert!(result.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "하다"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "으려다"
        && a.rules.iter().any(|r| r == "ending.intention_connective")));
    // The same source sentence has separately written 하려다 보니.
    let joined = engine.analyze_word("하려다보니").unwrap();
    assert!(joined.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["하다", "보다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["으려다", "으니"])
    }));
    let source = include_str!("fixtures/gsd-intention-connectives.conllu");
    let fields: Vec<_> = source
        .lines()
        .find(|l| l.starts_with("3\t"))
        .unwrap()
        .split('\t')
        .collect();
    assert_eq!(
        (&fields[1..3], fields[4]),
        (&["갈려는데", "갈+려는데"][..], "VV+EC")
    );
    let result = engine.analyze_word(fields[1]).unwrap();
    // 갈다 matches the annotation, but the sentence about going to Daejeon
    // appears to intend 가다. Keep the annotation unchanged, not a correction.
    assert!(result.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "갈다"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "으려는데"));
    assert!(!result.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "가다"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "으려는데"));
}

#[test]
fn intention_connectives_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!(
        "klem-intention-connectives-{}.db",
        std::process::id()
    ));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-intention-connectives.json",
        )],
        &path,
        "intention_connectives",
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
