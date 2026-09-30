//! COV-017az: polite prefinal paradigm, work in progress.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("polite-"));
    suite
}

#[test]
fn polite_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (93, 40));
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
fn polite_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-polite-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-polite.json")],
        &path,
        "polite",
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
fn polite_native_sources_preserve_full_entries_and_final_bundles() {
    use klem::dictionary::Dictionary;
    let path = std::env::temp_dir().join(format!("klem-polite-sources-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-polite.json")],
        &path,
        "polite-sources",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let sources: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/polite-sources.json")).unwrap();
    assert_eq!(sources["entry_ids"].as_array().unwrap().len(), 48);
    assert_eq!(sources["source_entries"].as_array().unwrap().len(), 4);
    for expected in sources["source_entries"].as_array().unwrap() {
        let entry = db.entry(expected["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        assert_eq!(entry.senses.len(), 1);
        assert_eq!(entry.senses[0].examples.len(), 4);
        for case in suite().cases.into_iter().filter(|c| {
            ["polite-source-", "polite-ri-source-"]
                .iter()
                .any(|prefix| {
                    c.id.starts_with(&format!(
                        "{prefix}{}-",
                        entry.summary.id.trim_start_matches("krdict:")
                    ))
                })
        }) {
            assert!(
                entry.senses[0]
                    .examples
                    .iter()
                    .flatten()
                    .any(|text| text.contains(&case.surface)),
                "{}",
                case.id
            );
        }
    }
    assert_eq!(
        suite()
            .cases
            .iter()
            .filter(|c| c.id.starts_with("polite-source-") || c.id.starts_with("polite-ri-source-"))
            .count(),
        10
    );
    assert!(
        sources["remaining_source_tokens"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    for word in ["드리오리다", "떠나오리다", "먹으오리다"] {
        assert!(suite().cases.iter().any(|c| c.surface == word));
    }
    drop(db);
    fs::remove_file(path).unwrap();
}

#[test]
fn polite_prefinals_preserve_lexical_oda_and_spelling_ownership() {
    use klem::SpellingClass;
    let engine = Lemmatizer::new();
    let word = engine.analyze_word("들어오니").unwrap();
    assert!(word.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["들다", "오다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["어", "으니"])
    }));
    for (surface, heads, forms, class, index) in [
        (
            "들으옵고",
            vec!["듣다"],
            vec!["으옵", "고"],
            SpellingClass::DigeutIrregular,
            0,
        ),
        (
            "들어주시옵고",
            vec!["듣다", "주다"],
            vec!["어", "시", "으옵", "고"],
            SpellingClass::DigeutIrregular,
            0,
        ),
        (
            "먹어놓으옵고",
            vec!["먹다", "놓다"],
            vec!["어", "으옵", "고"],
            SpellingClass::HieutRegular,
            1,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(heads.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap_or_else(|| panic!("{surface}"));
        assert!(
            a.spelling_paths
                .iter()
                .flatten()
                .any(|r| r.class == class && r.morpheme_index == index),
            "{surface}: {a:?}"
        );
        assert!(
            a.spelling_paths
                .iter()
                .flatten()
                .all(|r| r.morpheme_index < a.morphemes.len())
        );
        assert!(a.breakdown().is_some());
        assert!(a.rules.iter().any(|r| r == "prefinal.polite"));
    }
    let word = engine.analyze_word("먹고싶으옵고").unwrap();
    let reading = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["먹다", "싶다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["고", "으옵", "고"])
        })
        .unwrap();
    // 싶 ends in ㅍ, not ㅂ; it must not acquire a ㅂ paradigm constraint.
    assert!(reading.spelling_paths.is_empty(), "{reading:?}");
}
