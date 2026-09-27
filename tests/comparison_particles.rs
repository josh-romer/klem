//! COV-018w: source-attested nominal comparison particles and role boundaries.
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
        .retain(|c| c.id.starts_with("comparison-particle-"));
    suite
}

#[test]
fn comparison_particle_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (24, 9));
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
fn comparison_particle_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!(
        "klem-comparison-particle-{}.db",
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
            "tests/fixtures/krdict-comparison-particles.json",
        )],
        &path,
        "comparison_particle",
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

// Exhaustive candidates preserve alternatives; a dictionary example is not
// evidence that every other analysis of its surface should be removed.
#[test]
fn comparison_particles_preserve_derivation_and_lexical_ambiguity() {
    let engine = Lemmatizer::new();
    for word in ["꽃같이", "칠흑같이", "친구같이"] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.lemmas[0].kind == klem::LemmaKind::Predicate
                    && a.lemmas[0].text == format!("{}다", word.strip_suffix('이').unwrap())
                    && a.morphemes.len() == 1
                    && a.morphemes[0].kind == klem::MorphemeKind::Suffix
                    && a.morphemes[0].form == "이"),
            "{word}"
        );
    }
    let result = engine.analyze_word("같이").unwrap();
    assert!(result.analyses.iter().any(|a| a.unchanged));
    assert!(
        result.analyses.iter().any(
            |a| a.lemmas[0].text == "같다" && a.morphemes[0].kind == klem::MorphemeKind::Suffix
        )
    );
    let catalog: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    for (form, id) in [("같이", 22776), ("대로", 48410), ("처럼", 68275)] {
        assert_eq!(catalog[form]["kind"], "particle");
        assert!(
            catalog[form]["sources"]
                .as_array()
                .unwrap()
                .iter()
                .any(|s| s["id"] == id && s["pos"] == "조사")
        );
    }
}
