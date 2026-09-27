//! COV-017aq: contrasting reported clauses and attachment ownership.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("dajiman-"));
    suite
}

#[test]
fn dajiman_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (126, 34));
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
fn dajiman_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-dajiman-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-dajiman.json")],
        &path,
        "dajiman",
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
fn contrasting_reports_assess_lexical_entries_without_erasing_unknown_auxiliary() {
    use klem::dictionary::{AttachmentRule, Compatibility};
    let path =
        std::env::temp_dir().join(format!("klem-dajiman-homonyms-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-dajiman.json")],
        &path,
        "dajiman",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, ending, conflict) in [
        ("먹다지만", "다지만", AttachmentRule::BareAdjectivalReport),
        (
            "먹으냐지만",
            "으냐지만",
            AttachmentRule::BareAdjectivalQuestion,
        ),
    ] {
        let raw = Lemmatizer::new().analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&raw).unwrap();
        let i = raw
            .analyses
            .iter()
            .position(|a| {
                a.lemmas.len() == 1 && a.lemmas[0].text == "먹다" && a.morphemes[0].form == ending
            })
            .unwrap();
        let reading = &annotation.readings[i];
        assert_eq!(reading.status, Compatibility::Unknown);
        for id in ["krdict:15983", "krdict:58272"] {
            let evidence = reading.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == id)
                .unwrap();
            assert_eq!(evidence.status, Compatibility::Incompatible);
            assert!(
                evidence
                    .conflicts
                    .iter()
                    .any(|c| c.rule == conflict && c.morpheme_index == Some(0))
            );
        }
        assert_eq!(
            reading.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == "krdict:77243")
                .unwrap()
                .status,
            Compatibility::Unknown
        );
        let mut filtered = raw.clone();
        let mut evidence = annotation.clone();
        evidence.filter(&mut filtered, DictionaryFilter::Compatible);
        assert!(filtered.analyses.contains(&raw.analyses[i]));
    }
    drop(dictionary);
    drop(db);
    fs::remove_file(path).unwrap();
}

#[test]
fn contrasting_questions_preserve_existential_entries_and_assess_homonyms() {
    use Compatibility::{Compatible, Incompatible, Unknown};
    use klem::dictionary::{AttachmentRule, Compatibility};
    let path =
        std::env::temp_dir().join(format!("klem-dajiman-questions-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-dajiman.json")],
        &path,
        "dajiman",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, head, expected) in [
        (
            "늦느냐지만",
            "늦다",
            &[("krdict:61181", Compatible), ("krdict:64526", Incompatible)][..],
        ),
        ("좋느냐지만", "좋다", &[("krdict:79033", Incompatible)][..]),
        (
            "있느냐지만",
            "있다",
            &[
                ("krdict:68796", Compatible),
                ("krdict:68797", Compatible),
                ("krdict:62595", Unknown),
            ][..],
        ),
        ("없느냐지만", "없다", &[("krdict:89917", Compatible)][..]),
        (
            "계시느냐지만",
            "계시다",
            &[("krdict:17749", Compatible), ("krdict:61346", Unknown)][..],
        ),
        (
            "재미있느냐지만",
            "재미있다",
            &[("krdict:71212", Compatible)][..],
        ),
        (
            "재미없느냐지만",
            "재미없다",
            &[("krdict:57315", Compatible)][..],
        ),
    ] {
        for polite in [false, true] {
            let word = format!("{surface}{}", if polite { "요" } else { "" });
            let raw = Lemmatizer::new().analyze_word(&word).unwrap();
            let annotation = dictionary.annotate(&raw).unwrap();
            let index = raw
                .analyses
                .iter()
                .position(|a| {
                    a.lemmas.len() == 1
                        && a.lemmas[0].text == head
                        && a.morphemes.first().is_some_and(|m| m.form == "느냐지만")
                })
                .unwrap();
            let entries = &annotation.readings[index].lemmas[0].entries;
            for (id, status) in expected {
                let entry = entries.iter().find(|e| e.id == *id).unwrap();
                assert_eq!(entry.status, *status, "{word}: {id}");
                if *status == Incompatible {
                    assert!(
                        entry
                            .conflicts
                            .iter()
                            .any(|c| c.rule == AttachmentRule::BareVerbalQuestion
                                && c.morpheme_index == Some(0))
                    );
                } else {
                    assert!(entry.conflicts.is_empty(), "{word}: {id}");
                }
            }
        }
    }
    drop(dictionary);
    drop(db);
    fs::remove_file(path).unwrap();
}
