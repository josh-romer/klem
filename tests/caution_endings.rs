//! COV-017bs: caution finals, native ownership and immutable prior candidates.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, Session, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/caution-ending-sources.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-caution-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-caution-ending.json"),
                PathBuf::from("tests/fixtures/krdict-caution-ending-additional.json"),
            ],
            &path,
            "caution-test",
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
fn path(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == c["lemmas"]
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == c["lemma_kinds"]
        && serde_json::to_value(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()).unwrap()
            == c["morphemes"]
}

#[test]
fn native_entries_groups_and_authored_boundaries_are_preserved() {
    let file = Fixture::new("native");
    let db = file.open();
    let fixture = evidence();
    for e in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    let additional: Value = serde_json::from_str(include_str!(
        "fixtures/caution-ending-additional-native.json"
    ))
    .unwrap();
    for e in additional["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    assert_eq!(fixture["attestations"].as_array().unwrap().len(), 15);
    for row in fixture["attestations"].as_array().unwrap() {
        let e = db.entry(row["entry"].as_str().unwrap()).unwrap().unwrap();
        let s = e.senses.iter().find(|s| row["sense"] == s.id).unwrap();
        let group = &s.examples[row["example_group"].as_u64().unwrap() as usize];
        assert_eq!(serde_json::to_value(group).unwrap(), row["complete_group"]);
        assert!(
            group
                .iter()
                .any(|t| t.contains(row["excerpt"].as_str().unwrap()))
        );
    }
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("caution-ending-"));
    assert_eq!(
        suite.cases.len(),
        fixture["cases"].as_array().unwrap().len()
    );
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
}

#[test]
fn unicode_cache_filters_and_immediate_owner_assessments_agree_with_cli() {
    let file = Fixture::new("cases");
    let db = file.open();
    let engine = Arc::new(Lemmatizer::new());
    let fixture = evidence();
    for cache in [0, 1, 4096] {
        let mut words = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for case in fixture["cases"].as_array().unwrap() {
            for nfd in [false, true] {
                let surface = case["surface"].as_str().unwrap();
                let text = if nfd {
                    surface.nfd().collect()
                } else {
                    surface.to_owned()
                };
                let result = words.analyze_word(&text).unwrap();
                assert!(result.analyses.iter().any(|a| a.unchanged));
                let annotation = dictionary.annotate(&result).unwrap();
                let matches = result
                    .analyses
                    .iter()
                    .filter(|a| path(a, case))
                    .collect::<Vec<_>>();
                if case["verdict"] == "forbidden" {
                    assert!(matches.is_empty(), "{}: {matches:?}", case["id"]);
                } else {
                    assert!(!matches.is_empty(), "{}: {result:?}", case["id"]);
                    for a in matches {
                        assert!(a.breakdown().is_some());
                        assert!(a.rules.iter().any(|r| r == "ending.caution"));
                        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
                        let assessed = annotation.assess(a);
                        let status = if case["ending_owner_status"] == "unknown" {
                            Compatibility::Unknown
                        } else {
                            Compatibility::Compatible
                        };
                        assert!(
                            assessed
                                .lemmas
                                .last()
                                .unwrap()
                                .entries
                                .iter()
                                .any(|e| e.status == status),
                            "{}: {assessed:?}",
                            case["id"]
                        );
                    }
                }
                for (flag, policy) in [
                    (None, None),
                    (Some("--dict-only"), Some(DictionaryFilter::Headword)),
                    (
                        Some("--dict-compatible"),
                        Some(DictionaryFilter::Compatible),
                    ),
                ] {
                    let mut filtered = (*result).clone();
                    let mut assessed = annotation.clone();
                    if let Some(policy) = policy {
                        assessed.filter(&mut filtered, policy);
                    }
                    if case["verdict"] == "required" {
                        assert!(
                            filtered.analyses.iter().any(|a| path(a, case)),
                            "{}: {flag:?}",
                            case["id"]
                        );
                    }
                    if cache == 0 {
                        let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
                        command.args(["word", &text, "--dictionary"]).arg(&file.0);
                        if let Some(flag) = flag {
                            command.arg(flag);
                        }
                        let cli = command.output().unwrap();
                        assert!(cli.status.success());
                        let value: Value = serde_json::from_slice(&cli.stdout).unwrap();
                        assert_eq!(
                            serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                            filtered
                        );
                        assert_eq!(value["dictionary"], serde_json::to_value(assessed).unwrap());
                    }
                }
                assert!(dictionary.cache_bytes() <= cache);
            }
        }
    }
}

#[test]
fn all_frozen_prior_paths_assessments_and_order_survive_new_hypotheses() {
    let file = Fixture::new("before");
    let db = file.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let fixture = evidence();
    for (surface, before) in fixture["before_words"].as_object().unwrap() {
        let old: WordAnalysis = serde_json::from_value(before["analysis"].clone()).unwrap();
        let new = engine.analyze_word(surface).unwrap();
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
        for a in new.analyses.iter().filter(|a| !old.analyses.contains(a)) {
            assert!(
                a.rules.iter().any(|r| r == "ending.caution"),
                "{surface}: {a:?}"
            );
        }
    }
}

#[test]
fn native_accident_example_gains_independent_noun_and_main_verb_segments() {
    let file = Fixture::new("spacing");
    let db = file.open();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut words = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for original in ["사고날라", "학교에서사고날라"] {
            for text in [original.to_owned(), original.nfd().collect()] {
                let suggestions = klem::spacing::suggest(
                    &mut words,
                    &mut dictionary,
                    &text,
                    0,
                    klem::spacing::SpacingLimits::default(),
                )
                .unwrap();
                let expected = if original.starts_with("학교") {
                    vec!["학교에서", "사고", "날라"]
                } else {
                    vec!["사고", "날라"]
                };
                let option = suggestions
                    .alternatives
                    .iter()
                    .find(|h| {
                        h.rule == Some("spacing.bare_noun_main_nada")
                            && h.records
                                .iter()
                                .map(|s| s.record.analysis.as_ref().unwrap().normalized.as_str())
                                .eq(expected.iter().copied())
                    })
                    .unwrap_or_else(|| panic!("{text}: {suggestions:?}"));
                let right = option.records.last().unwrap();
                assert!(
                    right
                        .record
                        .analysis
                        .as_ref()
                        .unwrap()
                        .analyses
                        .iter()
                        .any(|a| a
                            .lemmas
                            .iter()
                            .any(|l| l.text == "나다" && l.kind == klem::LemmaKind::Predicate)
                            && a.morphemes.iter().any(|m| m.form == "을라"))
                );
                for segment in &option.records {
                    assert_eq!(
                        &text[segment.record.span.start..segment.record.span.end],
                        segment.record.surface
                    );
                }
            }
        }
    }
}
