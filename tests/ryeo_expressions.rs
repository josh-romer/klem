//! COV-017ax: shortened intention expressions and the assumption homonym.
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
        .retain(|c| c.id.starts_with("ryeo-expressions-"));
    suite
}

#[test]
fn ryeo_expressions_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (230, 63));
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
            if a.morphemes.iter().any(|m| {
                matches!(
                    m.form.as_str(),
                    "으려니" | "으려니까" | "으려더라" | "으려던" | "으려면서" | "으려든지"
                )
            }) {
                assert!(
                    a.rules.iter().any(|r| r == "ending.ryeo_expression"),
                    "{}: {a:?}",
                    case.surface
                );
            }
        }
    }
}

#[test]
fn ryeo_expressions_dictionary_filters_preserve_roles_and_cli_parity() {
    let path =
        std::env::temp_dir().join(format!("klem-ryeo_expressions-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-ryeo-expressions.json")],
        &path,
        "ryeo_expressions",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let mut known = suite();
        known.cases.retain(|c| {
            !c.judgments.iter().any(|j| {
                j.lemmas
                    .iter()
                    .any(|l| matches!(l.as_str(), "유학가다" | "쀍다"))
            })
        });
        let report = validity::evaluate_with(&known, |word| {
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
fn ryeo_expressions_sources_preserve_all_entries_senses_and_example_excerpts() {
    use klem::dictionary::Dictionary;
    let path = std::env::temp_dir().join(format!(
        "klem-ryeo_expressions-sources-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-ryeo-expressions.json")],
        &path,
        "ryeo_expressions",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let review: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/ryeo-expressions-sources.json")).unwrap();
    let entries = review["source_entries"].as_array().unwrap();
    let attestations = review["attestations"].as_array().unwrap();
    assert_eq!(entries.len(), 14);
    assert_eq!(attestations.len(), 82);
    let suite = suite();
    let mut senses = 0;
    for expected in entries {
        let entry = db.entry(expected["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        for sense in entry.senses {
            senses += 1;
            assert!(
                attestations
                    .iter()
                    .any(|a| a["entry"] == entry.summary.id && a["sense"] == sense.id)
            );
        }
    }
    assert_eq!(senses, 20);
    for a in attestations {
        let entry = db.entry(a["entry"].as_str().unwrap()).unwrap().unwrap();
        let sense = entry.senses.iter().find(|s| a["sense"] == s.id).unwrap();
        let group = &sense.examples[a["example_group"].as_u64().unwrap() as usize];
        let excerpt = a["excerpt"].as_str().unwrap();
        assert!(group.iter().any(|s| s.contains(excerpt)));
        assert_eq!(a["examples"], serde_json::to_value(group).unwrap());
        let case = suite.cases.iter().find(|c| a["case"] == c.id).unwrap();
        assert_eq!(case.surface, excerpt.replace(' ', ""));
    }
    drop(db);
    fs::remove_file(path).unwrap();
}

#[test]
fn dictionary_absence_does_not_erase_the_raw_source_hypothesis() {
    let path = std::env::temp_dir().join(format!("klem-ryeo-absent-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-ryeo-expressions.json")],
        &path,
        "ryeo",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (word, head) in [("유학가려면서", "유학가다"), ("쀍으려던", "쀍다")] {
        let raw = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            raw.analyses
                .iter()
                .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == head)
        );
        for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut filtered = raw.clone();
            let mut annotation = dictionary.annotate(&filtered).unwrap();
            annotation.filter(&mut filtered, policy);
            assert!(
                !filtered
                    .analyses
                    .iter()
                    .any(|a| a.lemmas.iter().any(|l| l.text == head))
            );
        }
    }
    drop(dictionary);
    drop(db);
    fs::remove_file(path).unwrap();
}
