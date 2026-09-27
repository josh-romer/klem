//! COV-017at: short reports, source conflicts and component ownership.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("short-report-"));
    suite
}

#[test]
fn short_reports_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (115, 53));
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
                    "대" | "는대" | "래" | "으래" | "냬" | "느냬" | "으냬" | "재" | "더래"
                )
            }) {
                assert!(
                    a.rules.iter().any(|r| r == "ending.reporting_short"),
                    "{}: {a:?}",
                    case.surface
                );
            }
        }
    }
}

#[test]
fn short_reports_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-short_reports-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-short-reports.json")],
        &path,
        "short_reports",
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
fn short_report_sources_preserve_all_entries_senses_and_example_excerpts() {
    use klem::dictionary::Dictionary;
    let path = std::env::temp_dir().join(format!(
        "klem-short-report-sources-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-short-reports.json")],
        &path,
        "short-reports",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let review: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/short-reports-sources.json")).unwrap();
    let entries = review["source_entries"].as_array().unwrap();
    let attestations = review["attestations"].as_array().unwrap();
    assert_eq!(entries.len(), 28);
    assert_eq!(attestations.len(), 59);
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
    assert_eq!(senses, 51);
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
fn clothing_question_source_conflict_is_scoped_to_attested_polite_head() {
    use klem::dictionary::{AttachmentRule, Compatibility};
    let path = std::env::temp_dir().join(format!(
        "klem-short-report-conflict-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-short-reports.json")],
        &path,
        "short-reports",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, head, expected) in [
        ("입으냬요", "입다", Compatibility::Unknown),
        ("입으냬", "입다", Compatibility::Incompatible),
        ("읽으냬요", "읽다", Compatibility::Incompatible),
        ("좋으냬요", "좋다", Compatibility::Compatible),
    ] {
        let raw = Lemmatizer::new().analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&raw).unwrap();
        let i = raw
            .analyses
            .iter()
            .position(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes.first().is_some_and(|m| m.form == "으냬")
            })
            .unwrap();
        let reading = &annotation.readings[i];
        assert_eq!(reading.status, expected, "{surface}");
        assert!(!reading.lemmas[0].entries.is_empty());
        for e in &reading.lemmas[0].entries {
            assert_eq!(e.status, expected, "{surface}: {}", e.id);
            if expected == Compatibility::Incompatible {
                assert!(
                    e.conflicts
                        .iter()
                        .any(|c| c.rule == AttachmentRule::BareAdjectivalQuestion
                            && c.morpheme_index == Some(0))
                );
            } else {
                assert!(e.conflicts.is_empty());
            }
        }
        let mut filtered = raw.clone();
        annotation
            .clone()
            .filter(&mut filtered, DictionaryFilter::Compatible);
        assert_eq!(
            filtered.analyses.contains(&raw.analyses[i]),
            expected != Compatibility::Incompatible
        );
    }
    drop(dictionary);
    drop(db);
    fs::remove_file(path).unwrap();
}

#[test]
fn short_report_questions_preserve_existential_entries_and_assess_homonyms() {
    use Compatibility::{Compatible, Incompatible, Unknown};
    use klem::dictionary::{AttachmentRule, Compatibility};
    let path = std::env::temp_dir().join(format!(
        "klem-short-reports-questions-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-short-reports.json")],
        &path,
        "short-reports",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, head, expected) in [
        (
            "늦느냬",
            "늦다",
            &[("krdict:61181", Compatible), ("krdict:64526", Incompatible)][..],
        ),
        ("좋느냬", "좋다", &[("krdict:79033", Incompatible)][..]),
        (
            "있느냬",
            "있다",
            &[
                ("krdict:68796", Compatible),
                ("krdict:68797", Compatible),
                ("krdict:62595", Unknown),
            ][..],
        ),
        ("없느냬", "없다", &[("krdict:89917", Compatible)][..]),
        (
            "계시느냬",
            "계시다",
            &[("krdict:17749", Compatible), ("krdict:61346", Unknown)][..],
        ),
        (
            "재미있느냬",
            "재미있다",
            &[("krdict:71212", Compatible)][..],
        ),
        (
            "재미없느냬",
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
                        && a.morphemes.first().is_some_and(|m| m.form == "느냬")
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
