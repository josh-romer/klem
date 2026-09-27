//! COV-017au: short/full action reason endings and lexical ownership.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("neura-"));
    suite
}

#[test]
fn neura_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (56, 40));
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
            if a.morphemes
                .iter()
                .any(|m| matches!(m.form.as_str(), "느라" | "느라고"))
            {
                assert!(
                    a.rules.iter().any(|r| r == "ending.activity_reason"),
                    "{}: {a:?}",
                    case.surface
                );
            }
        }
    }
}

#[test]
fn neura_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-neura-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-neura.json")],
        &path,
        "neura",
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
fn neura_sources_preserve_all_entries_senses_and_example_excerpts() {
    use klem::dictionary::Dictionary;
    let path = std::env::temp_dir().join(format!("klem-neura-sources-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-neura.json")],
        &path,
        "neura",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let review: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/neura-sources.json")).unwrap();
    let entries = review["source_entries"].as_array().unwrap();
    let attestations = review["attestations"].as_array().unwrap();
    assert_eq!(entries.len(), 2);
    assert_eq!(attestations.len(), 8);
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
    assert_eq!(senses, 2);
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
fn neura_assesses_each_homonym_and_only_the_ending_owner() {
    use Compatibility::{Compatible, Incompatible, Unknown};
    use klem::dictionary::{AttachmentRule, Compatibility};
    let path = std::env::temp_dir().join(format!("klem-neura-homonyms-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-neura.json")],
        &path,
        "neura",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for form in ["느라", "느라고"] {
        for (stem, head, expected) in [
            (
                "늦",
                "늦다",
                &[("krdict:61181", Compatible), ("krdict:64526", Incompatible)][..],
            ),
            ("좋", "좋다", &[("krdict:79033", Incompatible)][..]),
            (
                "있",
                "있다",
                &[
                    ("krdict:68796", Compatible),
                    ("krdict:68797", Incompatible),
                    ("krdict:62595", Unknown),
                ][..],
            ),
            (
                "계시",
                "계시다",
                &[("krdict:17749", Compatible), ("krdict:61346", Unknown)][..],
            ),
        ] {
            let word = Lemmatizer::new()
                .analyze_word(&format!("{stem}{form}"))
                .unwrap();
            let annotation = dictionary.annotate(&word).unwrap();
            let i = word
                .analyses
                .iter()
                .position(|a| {
                    a.lemmas.len() == 1
                        && a.lemmas[0].text == head
                        && a.morphemes.first().is_some_and(|m| m.form == form)
                })
                .unwrap();
            for (id, status) in expected {
                let entry = annotation.readings[i].lemmas[0]
                    .entries
                    .iter()
                    .find(|e| e.id == *id)
                    .unwrap();
                assert_eq!(entry.status, *status, "{stem}{form}: {id}");
                if *status == Incompatible {
                    assert!(entry.conflicts.iter().any(
                        |c| c.rule == AttachmentRule::NeuraVerb && c.morpheme_index == Some(0)
                    ));
                } else {
                    assert!(entry.conflicts.is_empty());
                }
            }
        }
        for (surface, lemmas) in [
            (format!("좋아하{form}"), vec!["좋다", "하다"]),
            (format!("좋아지{form}"), vec!["좋다", "지다"]),
        ] {
            let word = Lemmatizer::new().analyze_word(&surface).unwrap();
            let annotation = dictionary.annotate(&word).unwrap();
            let i = word
                .analyses
                .iter()
                .position(|a| {
                    a.lemmas
                        .iter()
                        .map(|l| l.text.as_str())
                        .eq(lemmas.iter().copied())
                        && a.morphemes.last().is_some_and(|m| m.form == form)
                })
                .unwrap();
            assert_ne!(annotation.readings[i].status, Incompatible);
            assert!(
                !annotation.readings[i]
                    .lemmas
                    .iter()
                    .flat_map(|l| &l.entries)
                    .flat_map(|e| &e.conflicts)
                    .any(|c| c.rule == AttachmentRule::NeuraVerb)
            );
        }
    }
    drop(dictionary);
    drop(db);
    fs::remove_file(path).unwrap();
}
