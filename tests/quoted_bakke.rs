//! COV-018z: reported clauses before 밖에 and explicit question allomorphs.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("quoted-bakke-"));
    suite
}

#[test]
fn quoted_bakke_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (47, 9));
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
fn quoted_bakke_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-quoted-bakke-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-quoted-bakke.json")],
        &path,
        "quoted_bakke",
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
fn quoted_question_assesses_lexical_entries_without_erasing_unknown_auxiliary() {
    use klem::dictionary::{AttachmentRule, Compatibility};
    let path = std::env::temp_dir().join(format!(
        "klem-quoted-bakke-homonyms-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-quoted-bakke.json")],
        &path,
        "quoted-bakke",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for surface in ["먹으냐고", "먹으냐고밖에"] {
        let raw = Lemmatizer::new().analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&raw).unwrap();
        let i = raw
            .analyses
            .iter()
            .position(|a| {
                a.lemmas.len() == 1 && a.lemmas[0].text == "먹다" && a.morphemes[0].form == "으냐고"
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
                    .any(|c| c.rule == AttachmentRule::BareAdjectivalQuestion
                        && c.morpheme_index == Some(0))
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
