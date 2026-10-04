//! COV-017bu: source-correct canonical owners and individually tracked removals.
#[path = "../tools/adjectival_allomorph.rs"]
mod boundaries;
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Analysis, Lemmatizer, Session, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn fixture() -> Value {
    serde_json::from_str(include_str!("fixtures/adjectival-allomorph-preflight.json")).unwrap()
}
fn supplement() -> Value {
    serde_json::from_str(include_str!(
        "fixtures/adjectival-allomorph-derived-supplement.json"
    ))
    .unwrap()
}
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases
        .retain(|c| c.id.starts_with("adjectival-allomorph-"));
    s
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-adjectival-allomorph-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-adjectival-allomorph.json"),
                PathBuf::from("tests/fixtures/krdict-adjectival-allomorph-derived.json"),
            ],
            &path,
            "adjectival-allomorph-test",
        )
        .unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn prior_words() -> Vec<(String, Value)> {
    let core = fixture();
    let mut rows: Vec<_> = core["before_words"]
        .as_object()
        .unwrap()
        .iter()
        .map(|(s, v)| (s.clone(), v.clone()))
        .collect();
    for r in supplement()["before_streams"]["all"].as_array().unwrap() {
        if r["kind"] == "word" {
            rows.push((
                r["surface"].as_str().unwrap().to_owned(),
                serde_json::json!({"analysis": r["analysis"], "dictionary": r["dictionary"]}),
            ));
        }
    }
    rows
}

#[test]
fn matrix_preserves_irregular_general_auxiliary_and_derived_paths() {
    let s = suite();
    let report = validity::evaluate(&s).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (216, 180));
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        for case in &s.cases {
            let nfc = session.analyze_word(&case.surface).unwrap();
            assert_eq!(
                nfc,
                session
                    .analyze_word(&case.surface.nfd().collect::<String>())
                    .unwrap()
            );
            assert!(nfc.analyses.iter().any(|a| a.unchanged));
            for a in &nfc.analyses {
                assert!(a.breakdown().is_some(), "{}: {a:?}", case.surface);
                assert!(!boundaries::reviewed_removal(a), "{}: {a:?}", case.surface);
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            }
        }
    }
}

#[test]
fn every_prior_path_changes_only_for_its_ordered_open_or_rieul_owner() {
    let file = Fixture::new("prior");
    let db = file.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let mut removed = 0;
    for (surface, before) in prior_words() {
        let old: WordAnalysis = serde_json::from_value(before["analysis"].clone()).unwrap();
        let mut expected = old.clone();
        expected
            .analyses
            .retain(|a| !boundaries::reviewed_removal(a));
        removed += old.analyses.len() - expected.analyses.len();
        for text in [surface.clone(), surface.nfd().collect()] {
            let actual = engine.analyze_word(&text).unwrap();
            assert_eq!(actual, expected, "{surface}");
            let annotation = dictionary.annotate(&actual).unwrap();
            for (i, a) in old
                .analyses
                .iter()
                .enumerate()
                .filter(|(_, a)| !boundaries::reviewed_removal(a))
            {
                assert_eq!(
                    serde_json::to_value(annotation.assess(a)).unwrap(),
                    before["dictionary"]["readings"][i],
                    "{surface}: {a:?}"
                );
            }
        }
    }
    // Pin the immutable cohort's individually checked removals, including
    // unknown lexical aliases beyond the 53 known matrix paths.
    assert_eq!(removed, 703);
    println!("Individually reviewed candidate removals in the prior-word cohort: {removed}");
}

#[test]
fn dictionary_cli_filters_and_caches_keep_complete_groups_and_unicode() {
    let file = Fixture::new("cli");
    let db = file.open();
    let engine = Lemmatizer::new();
    let s = suite();
    let input = s
        .cases
        .iter()
        .map(|c| c.surface.clone())
        .collect::<std::collections::BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>()
        .join(" ");
    for text in [input.clone(), input.nfd().collect()] {
        for (flag, policy) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["text", "-", "--dictionary"]).arg(&file.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            use std::io::Write;
            use std::process::Stdio;
            let mut child = command
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .unwrap();
            child
                .stdin
                .take()
                .unwrap()
                .write_all(text.as_bytes())
                .unwrap();
            let output = child.wait_with_output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let records: Vec<Value> = String::from_utf8(output.stdout)
                .unwrap()
                .lines()
                .map(|l| serde_json::from_str(l).unwrap())
                .collect();
            assert_eq!(
                records
                    .iter()
                    .map(|r| r["surface"].as_str().unwrap())
                    .collect::<String>(),
                text
            );
            for cache in [0, 1, 4096] {
                let mut dictionary = DictionarySession::new(&db, cache);
                for record in records.iter().filter(|r| r["kind"] == "word") {
                    let mut word = engine
                        .analyze_word(record["surface"].as_str().unwrap())
                        .unwrap();
                    let mut annotation = dictionary.annotate(&word).unwrap();
                    if let Some(policy) = policy {
                        annotation.filter(&mut word, policy);
                    }
                    assert_eq!(serde_json::to_value(&word).unwrap(), record["analysis"]);
                    assert_eq!(
                        serde_json::to_value(&annotation).unwrap(),
                        record["dictionary"]
                    );
                    assert!(
                        word.analyses
                            .iter()
                            .all(|a| !boundaries::reviewed_removal(a))
                    );
                }
            }
        }
    }
}

#[test]
fn explicit_ledger_corrections_reject_the_archived_path_and_keep_general_readings() {
    let changes: Value = serde_json::from_str(include_str!(
        "fixtures/adjectival-allomorph-corrections.json"
    ))
    .unwrap();
    let mut ledger: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    let ids: Vec<_> = changes["superseded"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r["replacement"]["id"].as_str().unwrap())
        .collect();
    ledger.cases.retain(|c| ids.contains(&c.id.as_str()));
    let report = validity::evaluate(&ledger).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (0, 26));
    let engine = Lemmatizer::new();
    let prior = fixture();
    for change in changes["superseded"].as_array().unwrap() {
        let row = &change["original"];
        let surface = row["surface"].as_str().unwrap();
        let original = &row["judgments"][0];
        let old: WordAnalysis =
            serde_json::from_value(prior["before_words"][surface]["analysis"].clone()).unwrap();
        let legacy: Vec<_> = old
            .analyses
            .iter()
            .filter(|a| {
                a.lemmas
                    .iter()
                    .map(|l| Value::String(l.text.clone()))
                    .eq(original["lemmas"].as_array().unwrap().iter().cloned())
                    && a.morphemes
                        .iter()
                        .map(|m| Value::String(m.form.clone()))
                        .eq(original["morphemes"].as_array().unwrap().iter().cloned())
            })
            .collect();
        assert!(!legacy.is_empty());
        for a in legacy {
            assert!(boundaries::reviewed_removal(a));
            let actual = engine.analyze_word(surface).unwrap();
            assert!(!actual.analyses.contains(a));
            let mut general: Analysis = a.clone();
            let index = change["ordered_owner"]["canonical_morpheme_index"]
                .as_u64()
                .unwrap() as usize;
            general.morphemes[index].form.remove(0);
            assert!(
                actual
                    .analyses
                    .iter()
                    .any(|p| p.lemmas == general.lemmas && p.morphemes == general.morphemes),
                "{surface}: {actual:?}"
            );
        }
    }
}
