//! COV-018x: additive connectives, finite adverbs, and particle order.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("additive-"));
    suite
}

#[test]
fn additive_particle_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (42, 8));
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
fn additive_particle_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-additive-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-additive-particles.json",
        )],
        &path,
        "additive_particle",
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
        // A proper name in the source sentence is absent from KRDict. Filtering
        // removes its lexical path; that is a dictionary gap, not bad grammar.
        filtered_suite
            .cases
            .iter_mut()
            .find(|c| c.id == "additive-noun-승규")
            .unwrap()
            .judgments[0]
            .verdict = validity::Verdict::Forbidden;
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
fn additive_paths_keep_specific_provenance_and_finite_adverb_scope() {
    let engine = Lemmatizer::new();
    for (word, rule) in [
        ("대해서조차", "particle.additive_connective"),
        ("거룩하게조차", "particle.additive_connective"),
        ("대해서마저", "particle.additive_connective"),
        ("천천히조차도", "particle.additive_adverb"),
        ("선생님까지조차", "particle.additive_chain"),
        ("통신마저가", "particle.additive_chain"),
    ] {
        let a = engine.analyze_word(word).unwrap();
        assert!(
            a.analyses.iter().any(|a| a.rules.iter().any(|r| r == rule)),
            "{word}"
        );
        if rule == "particle.additive_connective" {
            assert!(
                a.analyses
                    .iter()
                    .filter(|a| a.rules.iter().any(|r| r == rule))
                    .all(|a| !a.rules.iter().any(|r| r == "nominalization"))
            );
        }
    }
    // These are implementation-scope observations, not linguistic bans:
    // the source's contextual negative examples do not justify global pruning.
    for word in ["자주조차", "오늘마저", "아주조차"] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|a| !a.rules.iter().any(|r| r == "particle.additive_adverb"))
        );
    }
}
