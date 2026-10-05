//! COV-017br: vowel-final omitted-copula hypotheses, distinct from certified paths.
#[path = "../tools/hada_nominal_preservation.rs"]
mod hada_preservation;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, Session, WordAnalysis};
use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;

fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/rya-copula-regressions.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-rya-copula-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-rya-copula.json"),
                PathBuf::from("tests/fixtures/krdict-rya-copula-additional.json"),
            ],
            &path,
            "rya-copula-test",
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
fn path(a: &Analysis, case: &Value) -> bool {
    serde_json::to_value(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == case["lemmas"]
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == case["lemma_kinds"]
        && serde_json::to_value(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()).unwrap()
            == case["morphemes"]
}

#[test]
fn complete_native_owners_survive_import_without_fixture_rewriting() {
    let file = Fixture::new("native");
    let db = file.open();
    let fixture = evidence();
    assert_eq!(fixture["source_entries"].as_array().unwrap().len(), 143);
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
}

#[test]
fn additional_owners_exposed_by_new_hypotheses_preserve_all_native_fields() {
    let file = Fixture::new("additional");
    let db = file.open();
    let fixture: Value =
        serde_json::from_str(include_str!("fixtures/rya-copula-additional-native.json")).unwrap();
    assert_eq!(fixture["source_entries"].as_array().unwrap().len(), 18);
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
}

#[test]
fn omitted_copulas_preserve_boundaries_roles_provenance_and_owner_uncertainty() {
    let file = Fixture::new("cases");
    let db = file.open();
    let engine = Lemmatizer::new();
    let fixture = evidence();
    for case in fixture["cases"].as_array().unwrap() {
        for nfd in [false, true] {
            let word = case["surface"].as_str().unwrap();
            let surface = if nfd {
                word.nfd().collect()
            } else {
                word.to_owned()
            };
            let result = engine.analyze_word(&surface).unwrap();
            assert!(
                result.analyses.iter().any(|a| a.unchanged),
                "{}",
                case["id"]
            );
            if case["verdict"] == "forbidden" {
                assert!(
                    !result.analyses.iter().any(|a| path(a, case)),
                    "{}",
                    case["id"]
                );
                continue;
            }
            let a = result
                .analyses
                .iter()
                .find(|a| path(a, case))
                .unwrap_or_else(|| panic!("{}: {result:?}", case["id"]));
            assert!(a.breakdown().is_some());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            let mut dictionary = DictionarySession::new(&db, 0);
            let annotation = dictionary.annotate(&result).unwrap();
            let assessed = annotation.assess(a);
            if case["verdict"] == "required_hypothesis" {
                assert!(a.rules.iter().any(|r| r == "copula.omitted_ending"));
                assert!(a.rules.iter().any(|r| r == "copula.omitted_rya"));
                let owner = a.lemmas.iter().position(|l| l.text == "이다").unwrap();
                assert!(!assessed.lemmas[owner].entries.is_empty());
                assert_eq!(assessed.lemmas[owner].status, Compatibility::Unknown);
                assert!(
                    assessed.lemmas[owner]
                        .entries
                        .iter()
                        .any(|e| e.status == Compatibility::Unknown)
                );
                assert!(
                    assessed.lemmas[owner]
                        .entries
                        .iter()
                        .all(|e| e.status != Compatibility::Compatible)
                );
                // Uncertainty belongs to the omitted copula, never to earlier
                // nominalization/auxiliary owners merely sharing its rule tag.
                assert!(
                    assessed.lemmas[..owner].iter().all(|s| s
                        .entries
                        .iter()
                        .any(|e| e.status == Compatibility::Compatible)),
                    "{}: {assessed:?}",
                    case["id"]
                );
            } else {
                assert!(!a.rules.iter().any(|r| r == "copula.omitted_rya"));
                assert!(
                    assessed
                        .lemmas
                        .last()
                        .unwrap()
                        .entries
                        .iter()
                        .any(|e| e.status == Compatibility::Compatible)
                );
            }
        }
    }
}

#[test]
fn every_original_path_native_assessment_and_order_is_preserved() {
    let file = Fixture::new("before");
    let db = file.open();
    let fixture = evidence();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut words = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for (surface, before) in fixture["before_words"].as_object().unwrap() {
            let old: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
            for text in [surface.clone(), surface.nfd().collect()] {
                let new = words.analyze_word(&text).unwrap();
                assert_eq!(new.normalized, old.normalized);
                assert_eq!(
                    new.analyses
                        .iter()
                        .filter(|a| old.analyses.contains(a))
                        .collect::<Vec<_>>(),
                    old.analyses.iter().collect::<Vec<_>>(),
                    "{surface}"
                );
                let annotation = dictionary.annotate(&new).unwrap();
                for (i, a) in old.analyses.iter().enumerate() {
                    assert_eq!(
                        serde_json::to_value(annotation.assess(a)).unwrap(),
                        before["dictionary"]["readings"][i],
                        "{surface}"
                    );
                }
                for a in new
                    .analyses
                    .iter()
                    .filter(|a| !old.analyses.contains(a) && !hada_preservation::is_addition(a))
                {
                    assert!(
                        a.rules.iter().any(|r| r == "ending.rya")
                            && a.rules.iter().any(|r| r == "copula.omitted_rya"),
                        "{surface}: {a:?}"
                    );
                }
                let mut reviewed = (*new).clone();
                reviewed
                    .analyses
                    .retain(|a| old.analyses.contains(a) || !hada_preservation::is_addition(a));
                hada_preservation::assert_preserved(&new, &reviewed);
            }
        }
    }
}

#[test]
fn cli_filters_keep_unknown_hypotheses_and_match_library_with_unicode_offsets() {
    let file = Fixture::new("cli");
    let db = file.open();
    let fixture = evidence();
    let words = fixture["before_words"]
        .as_object()
        .unwrap()
        .keys()
        .cloned()
        .collect::<Vec<_>>()
        .join(" ");
    for nfd in [false, true] {
        let text = format!(
            "前🙂「{}」",
            if nfd {
                words.nfd().collect::<String>()
            } else {
                words.clone()
            }
        );
        for cache in [0, 1, 4096] {
            for (flag, filter) in [
                (None, None),
                (Some("--dict-only"), Some(DictionaryFilter::Headword)),
                (
                    Some("--dict-compatible"),
                    Some(DictionaryFilter::Compatible),
                ),
            ] {
                let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
                command
                    .args(["text", "-", "--dictionary"])
                    .arg(&file.0)
                    .args(["--cache-bytes", &cache.to_string()]);
                if let Some(flag) = flag {
                    command.arg(flag);
                }
                let mut child = command
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .spawn()
                    .unwrap();
                child
                    .stdin
                    .take()
                    .unwrap()
                    .write_all(text.as_bytes())
                    .unwrap();
                let output = child.wait_with_output().unwrap();
                assert!(output.status.success());
                let cli: Vec<Value> = String::from_utf8(output.stdout)
                    .unwrap()
                    .lines()
                    .map(|l| serde_json::from_str(l).unwrap())
                    .collect();
                let mut session = Session::new(Arc::new(Lemmatizer::new()), cache);
                let mut dictionary = DictionarySession::new(&db, cache);
                for r in cli {
                    let start = r["span"]["start"].as_u64().unwrap() as usize;
                    let end = r["span"]["end"].as_u64().unwrap() as usize;
                    assert_eq!(&text[start..end], r["surface"].as_str().unwrap());
                    if r["kind"] != "word" {
                        continue;
                    }
                    let mut word = session
                        .analyze_word(r["surface"].as_str().unwrap())
                        .unwrap()
                        .as_ref()
                        .clone();
                    let mut annotation = dictionary.annotate(&word).unwrap();
                    if let Some(filter) = filter {
                        annotation.filter(&mut word, filter);
                    }
                    assert_eq!(r["analysis"], serde_json::to_value(&word).unwrap());
                    assert_eq!(r["dictionary"], serde_json::to_value(&annotation).unwrap());
                }
            }
        }
    }
}
