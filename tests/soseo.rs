//! COV-017ay: modern literary/request 기원 endings.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("soseo-"));
    suite
}

#[test]
fn soseo_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (59, 32));
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
            .analyze_word("쀍으소서")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "쀍다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "으소서")
    );
}

#[test]
fn soseo_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-soseo-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-soseo.json")],
        &path,
        "soseo",
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
fn native_prayer_sources_retain_all_senses_and_example_groups() {
    use klem::dictionary::Dictionary;
    let path = std::env::temp_dir().join(format!("klem-soseo-sources-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-soseo.json")],
        &path,
        "soseo-sources",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/soseo-sources.json")).unwrap();
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), 68);
    let entries = source["source_entries"].as_array().unwrap();
    assert_eq!(entries.len(), 4);
    for expected in entries {
        let entry = db.entry(expected["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        assert_eq!(entry.summary.pos, "어미");
        assert_eq!(entry.senses.len(), 1);
        assert_eq!(entry.senses[0].examples.len(), 4);
        for case in suite().cases.into_iter().filter(|c| {
            c.id.starts_with(&format!(
                "soseo-source-{}-",
                entry.summary.id.trim_start_matches("krdict:")
            ))
        }) {
            assert!(
                entry.senses[0]
                    .examples
                    .iter()
                    .flatten()
                    .any(|s| s.contains(&case.surface)),
                "{}",
                case.id
            );
        }
    }
    // This full original example concerns a polite prefinal, beyond the final
    // -옵소서 bundle. Its absence from required judgments is intentional.
    let outside = entries.iter().find(|e| e["id"] == "krdict:86110").unwrap();
    assert!(
        outside["senses"][0]["examples"]
            .as_array()
            .unwrap()
            .iter()
            .any(|e| e.to_string().contains("읽으옵고"))
    );
    assert_eq!(
        suite()
            .cases
            .iter()
            .filter(|c| c.id.starts_with("soseo-source-"))
            .count(),
        15
    );
    drop(db);
    fs::remove_file(path).unwrap();
}

#[test]
fn prayer_endings_keep_spelling_ownership_on_the_right_auxiliary() {
    use klem::SpellingClass;
    let engine = Lemmatizer::new();
    for (surface, heads, forms, class, index) in [
        (
            "먹어주소서",
            vec!["먹다", "주다"],
            vec!["어", "으소서"],
            None,
            0,
        ),
        (
            "먹어주시옵소서",
            vec!["먹다", "주다"],
            vec!["어", "시", "으옵소서"],
            None,
            0,
        ),
        (
            "먹고계시소서",
            vec!["먹다", "계시다"],
            vec!["고", "으소서"],
            None,
            0,
        ),
        (
            "먹고계시옵소서",
            vec!["먹다", "계시다"],
            vec!["고", "으옵소서"],
            None,
            0,
        ),
        (
            "들어주시옵소서",
            vec!["듣다", "주다"],
            vec!["어", "시", "으옵소서"],
            Some(SpellingClass::DigeutIrregular),
            0,
        ),
        (
            "먹지마옵소서",
            vec!["먹다", "말다"],
            vec!["지", "으옵소서"],
            None,
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
        if let Some(class) = class {
            assert!(
                a.spelling_paths
                    .iter()
                    .flatten()
                    .any(|r| r.class == class && r.morpheme_index == index),
                "{surface}: {a:?}"
            );
        }
        assert!(
            a.spelling_paths
                .iter()
                .flatten()
                .all(|r| r.morpheme_index < a.morphemes.len())
        );
        assert!(a.rules.iter().any(|r| r == "auxiliary"));
        if surface == "먹지마옵소서" {
            assert!(a.rules.iter().any(|r| r == "deletion.rieul"));
        }
        assert!(a.breakdown().is_some());
    }
}
