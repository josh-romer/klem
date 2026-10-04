//! COV-021j: written vowel exceptions and open-ㅕ absorption.
#[path = "support/written_vowel_history.rs"]
mod history;
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-written-vowel-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-written-vowel.json")],
            &path,
            "written-vowel",
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
fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/written-vowel-sources.json")).unwrap()
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn written_vowel_written_paradigms_keep_complete_native_forms_and_example_groups() {
    let source = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    for entry in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    for paradigm in source["paradigms"].as_array().unwrap() {
        let entries = source["owner_entries"].as_array().unwrap();
        let owners: Vec<_> = entries
            .iter()
            .filter(|e| e["headword"] == paradigm["headword"])
            .collect();
        assert!(!owners.is_empty());
        for entry in owners {
            assert!(
                entry["forms"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|f| f["kind"] == "활용" && f["written"] == paradigm["written"])
            );
        }
    }
    for observation in source["native_observations"].as_array().unwrap() {
        let entry = source["owner_entries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["id"] == observation["source_entry"])
            .unwrap();
        let sense = entry["senses"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["id"] == observation["sense"])
            .unwrap();
        assert_eq!(
            sense["examples"][observation["example_group"].as_u64().unwrap() as usize],
            observation["complete_example_group"]
        );
        assert!(
            observation["complete_example_group"]
                .as_array()
                .unwrap()
                .iter()
                .any(|l| l
                    .as_str()
                    .unwrap()
                    .contains(observation["surface"].as_str().unwrap()))
        );
    }
    assert_eq!(source["native_observations"].as_array().unwrap().len(), 131);
    assert_eq!(
        source["original_discovery_pairs"].as_array().unwrap().len(),
        18
    );
}

#[test]
fn finite_vowel_recovery_preserves_ambiguity_unicode_prefinal_and_auxiliary_owners() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("written-vowel-"));
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (252, 22));
    let engine = Lemmatizer::new();
    for c in sources()["cases"].as_array().unwrap() {
        let surface = c["surface"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        let before: WordAnalysis = serde_json::from_value(c["before_word"].clone()).unwrap();
        assert_eq!(
            word.analyses
                .iter()
                .filter(|a| before.analyses.contains(&history::project_analysis(a)))
                .map(history::project_analysis)
                .collect::<Vec<_>>(),
            before
                .analyses
                .iter()
                .map(history::project_analysis)
                .collect::<Vec<_>>(),
            "{surface}"
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        let a = word.analyses.iter().find(|a| matches(a, c)).unwrap();
        assert!(
            a.rules
                .iter()
                .any(|r| r == c["required_rule"].as_str().unwrap()),
            "{surface}"
        );
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        let order = a.breakdown().unwrap();
        assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len());
        use klem::breakdown::Component::{Lemma as L, Morpheme as M};
        if surface.ends_with("버렸다") || surface.ends_with("봤다") {
            assert_eq!(order, vec![L(0), M(0), L(1), M(1), M(2)]);
        }
    }
}

#[test]
fn written_vowel_dictionary_source_cache_filters_and_cli_preserve_both_lexical_classes() {
    // Preserve the original vowel-recovery fixture. COV-019ad separately
    // records the five source-backed adjective/버리다 policy changes.
    let updates: Value = serde_json::from_str(include_str!(
        "fixtures/continuation-left-written-vowel-judgments.json"
    ))
    .unwrap();
    assert_eq!(updates["cases"].as_array().unwrap().len(), 5);
    let fixture = Fixture::new("policies");
    let db = fixture.open();
    let mut cached = DictionarySession::new(&db, 1 << 20);
    let mut uncached = DictionarySession::new(&db, 0);
    for c in sources()["cases"].as_array().unwrap() {
        let surface = c["surface"].as_str().unwrap();
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        assert_eq!(
            cached.annotate(&word).unwrap(),
            uncached.annotate(&word).unwrap()
        );
        let a = word.analyses.iter().find(|a| matches(a, c)).unwrap();
        let annotation = cached.annotate(&word).unwrap();
        for j in c["entry_judgments"].as_array().unwrap() {
            let update = updates["cases"]
                .as_array()
                .unwrap()
                .iter()
                .find(|u| u["id"] == c["id"] && u["entry_id"] == j["id"]);
            let expected = if let Some(u) = update {
                assert_eq!(u["before"], *j);
                assert_eq!(u["lemmas"], c["lemmas"]);
                assert_eq!(u["morphemes"], c["morphemes"]);
                &u["after"]
            } else {
                j
            };
            let entry = annotation.assess(a).lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == j["id"].as_str().unwrap())
                .unwrap()
                .clone();
            assert_eq!(
                serde_json::to_value(entry.status).unwrap(),
                expected["status"]
            );
            assert_eq!(
                serde_json::to_value(entry.conflicts).unwrap(),
                expected["conflicts"]
            );
        }
        for (flag, filter) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut expected = word.clone();
            let mut annotated = cached.annotate(&expected).unwrap();
            if let Some(filter) = filter {
                annotated.filter(&mut expected, filter);
            }
            let changed = updates["cases"]
                .as_array()
                .unwrap()
                .iter()
                .any(|u| u["id"] == c["id"]);
            assert_eq!(
                expected.analyses.iter().any(|a| matches(a, c)),
                filter != Some(DictionaryFilter::Compatible) || !changed,
                "{surface}"
            );
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let out = command.output().unwrap();
            assert!(
                out.status.success(),
                "{}",
                String::from_utf8_lossy(&out.stderr)
            );
            let mut cli: Value = serde_json::from_slice(&out.stdout).unwrap();
            assert_eq!(
                cli.as_object_mut().unwrap().remove("dictionary").unwrap(),
                serde_json::to_value(annotated).unwrap()
            );
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(cli).unwrap(),
                expected
            );
        }
    }
}

#[test]
fn written_vowel_probes_preserve_old_candidates_and_finite_map_boundaries() {
    let engine = Lemmatizer::new();
    for c in sources()["unjudged_controls"].as_array().unwrap() {
        let before: WordAnalysis = serde_json::from_value(c["before_word"].clone()).unwrap();
        let after = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        assert_eq!(
            after
                .analyses
                .iter()
                .filter(|a| before.analyses.contains(&history::project_analysis(a)))
                .map(history::project_analysis)
                .collect::<Vec<_>>(),
            before
                .analyses
                .iter()
                .map(history::project_analysis)
                .collect::<Vec<_>>()
        );
        for a in after
            .analyses
            .iter()
            .filter(|a| !before.analyses.contains(&history::project_analysis(a)))
        {
            assert!(
                a.rules
                    .iter()
                    .any(|r| r == "contraction.yeo_absorption" || r == "inflection.written_vowel")
            );
        }
    }
    for n in [32, 128, 1024] {
        for surface in ["받아써".repeat(n), "늠므".repeat(n) + "약아"] {
            assert!(
                !engine
                    .analyze_word(&surface)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| a.rules.iter().any(|r| r == "inflection.written_vowel"))
            );
        }
    }
    let word = engine.analyze_word("켜").unwrap();
    assert!(
        word.analyses
            .iter()
            .any(|a| a.lemmas.iter().any(|l| l.text == "키다")
                && a.rules.iter().any(|r| r == "contraction.vowel"))
    );
    assert!(
        word.analyses
            .iter()
            .any(|a| a.lemmas.iter().any(|l| l.text == "켜다")
                && a.rules.iter().any(|r| r == "contraction.yeo_absorption"))
    );
}
