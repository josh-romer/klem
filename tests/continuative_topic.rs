//! COV-019i: internal contrastive 는 before 있다/계시다.
#[path = "../tools/validity.rs"]
mod validity;
use klem::breakdown::Component;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{LemmaKind, Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("continuative-topic-"));
    suite
}

#[test]
fn continuative_topic_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (33, 19));
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
    // Contracted 곤 keeps the same analyses as 고는, with extra provenance.
    for (short, full) in [
        ("먹곤있다네", "먹고는있다네"),
        ("먹곤계신다", "먹고는계신다"),
        ("먹어보곤있다", "먹어보고는있다"),
    ] {
        let a = engine.analyze_word(short).unwrap();
        let b = engine.analyze_word(full).unwrap();
        let paths: Vec<_> = a
            .analyses
            .iter()
            .filter(|a| {
                a.rules.iter().any(|r| r == "particle.contraction.n")
                    && a.lemmas
                        .last()
                        .is_some_and(|l| l.kind == LemmaKind::Auxiliary)
            })
            .collect();
        assert!(!paths.is_empty(), "{short}");
        for path in paths {
            assert!(
                b.analyses
                    .iter()
                    .any(|b| b.lemmas == path.lemmas && b.morphemes == path.morphemes)
            );
            assert!(
                path.rules
                    .iter()
                    .any(|r| r == "auxiliary.internal_particle")
            );
        }
    }
    let result = engine.analyze_word("먹고는있다네").unwrap();
    let a = result
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["먹다", "있다"])
        })
        .unwrap();
    assert_eq!(
        a.breakdown().unwrap(),
        vec![
            Component::Lemma(0),
            Component::Morpheme(0),
            Component::Morpheme(1),
            Component::Lemma(1),
            Component::Morpheme(2)
        ]
    );
    // The raw generator must not depend on a closed vocabulary of verb heads.
    let unknown = engine.analyze_word("쀍고는있다").unwrap();
    assert!(unknown.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["쀍다", "있다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["고", "는", "다"])
    }));
}

#[test]
fn continuative_topic_dictionary_filters_preserve_roles_and_cli_parity() {
    let path =
        std::env::temp_dir().join(format!("klem-continuative-topic-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-continuative-topic.json",
        )],
        &path,
        "continuative-topic",
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
