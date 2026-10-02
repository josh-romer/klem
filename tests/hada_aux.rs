//! COV-013/019z: complete 하다 sources and separate verb/adjective inflection owners.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!("klem-hada-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-hada-aux.json")],
            &path,
            "hada-aux",
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
    serde_json::from_str(include_str!("fixtures/hada-aux-sources.json")).unwrap()
}
fn cases() -> Value {
    serde_json::from_str(include_str!("fixtures/hada-aux-entry-judgments.json")).unwrap()
}
fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("hada-aux-"));
    suite
}
fn path(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn hada_sources_keep_both_complete_entries_and_all_48_native_groups() {
    let m = sources();
    let f = Fixture::new("sources");
    let db = f.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let s = suite();
    assert_eq!(m["source_entries"].as_array().unwrap().len(), 2);
    assert_eq!(s.cases.len(), 72);
    let mut covered = std::collections::BTreeSet::new();
    let mut senses = 0;
    for entry in m["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
        for sense in entry["senses"].as_array().unwrap() {
            senses += 1;
            for (index, group) in sense["examples"].as_array().unwrap().iter().enumerate() {
                let rows: Vec<_> = m["attestations"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .filter(|r| {
                        r["entry"] == entry["id"]
                            && r["sense"] == sense["id"]
                            && r["example_group"] == index
                    })
                    .collect();
                assert_eq!(rows.len(), 1);
                let r = rows[0];
                assert_eq!(r["examples"], *group);
                let excerpt = r["excerpt"].as_str().unwrap();
                assert!(
                    group
                        .as_array()
                        .unwrap()
                        .iter()
                        .any(|line| line.as_str().unwrap().contains(excerpt))
                );
                let c = s.cases.iter().find(|c| c.id == r["case"]).unwrap();
                assert!(covered.insert(c.id.clone()));
                assert_eq!(c.surface, excerpt.replace(' ', ""));
                let j = &c.judgments[0];
                let word = Lemmatizer::new().analyze_word(&c.surface).unwrap();
                let a = word
                    .analyses
                    .iter()
                    .find(|a| {
                        a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
                            && a.morphemes.iter().map(|m| &m.form).eq(j
                                .morphemes
                                .as_ref()
                                .unwrap()
                                .iter())
                    })
                    .unwrap();
                let assessment = dictionary.annotate(&word).unwrap().assess(a);
                let slot = r["source_slot"].as_u64().unwrap() as usize;
                let aux = assessment
                    .lemmas
                    .iter()
                    .find(|s| s.lemma_index == slot)
                    .unwrap();
                let expected = entry["id"].as_str().unwrap();
                let selected = aux.entries.iter().find(|e| e.id == expected).unwrap();
                assert_eq!(selected.status, Compatibility::Compatible, "{}", c.id);
                assert!(selected.conflicts.is_empty());
            }
        }
    }
    assert_eq!((senses, covered.len()), (11, 48));
    assert_eq!(m["native_entries"], 67);
    for e in m["grammar_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    assert_eq!(m["grammar_entries"].as_array().unwrap().len(), 3);
}

#[test]
fn hada_raw_paths_keep_unicode_components_and_original_word_hypotheses() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (72, 0));
    let engine = Lemmatizer::new();
    for c in cases()["cases"].as_array().unwrap() {
        let surface = c["surface"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        assert!(word.analyses.iter().any(|a| path(a, c)), "{}", c["id"]);
        for a in &word.analyses {
            let order = a.breakdown().unwrap();
            assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn hada_entry_policy_preserves_both_pos_homonyms_and_immediate_owners() {
    let f = Fixture::new("policy");
    let db = f.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let doc = cases();
    let all = doc["cases"].as_array().unwrap();
    assert_eq!(all.len(), 94);
    assert_eq!(
        all.iter()
            .map(|c| c["judgments"].as_array().unwrap().len())
            .sum::<usize>(),
        437
    );
    for c in all {
        let word = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        let a = word.analyses.iter().find(|a| path(a, c)).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let assessment = annotation.assess(a);
        for j in c["judgments"].as_array().unwrap() {
            let index = j["lemma_index"].as_u64().unwrap() as usize;
            let slot = assessment
                .lemmas
                .iter()
                .find(|s| s.lemma_index == index)
                .unwrap();
            let e = slot
                .entries
                .iter()
                .find(|e| e.id == j["entry_id"].as_str().unwrap())
                .unwrap();
            assert_eq!(
                serde_json::to_value(e.status).unwrap(),
                j["status"],
                "{} {}",
                c["id"],
                j["id"]
            );
            assert_eq!(
                serde_json::to_value(&e.conflicts).unwrap(),
                j["conflicts"],
                "{} {}",
                c["id"],
                j["id"]
            );
        }
        if c["missing_owner_entries"] == true {
            assert!(assessment.lemmas[0].entries.is_empty());
            assert_eq!(assessment.status, Compatibility::Unknown);
        }
        for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut filtered = word.clone();
            let mut annotated = dictionary.annotate(&filtered).unwrap();
            annotated.filter(&mut filtered, filter);
            let expected = if c["missing_owner_entries"] == true {
                false
            } else if filter == DictionaryFilter::Compatible {
                c["filter_retained"].as_bool().unwrap_or(true)
            } else {
                true
            };
            assert_eq!(
                filtered.analyses.iter().any(|a| path(a, c)),
                expected,
                "{} {filter:?}",
                c["id"]
            );
        }
    }
    // The standalone lexical verb remains compatible. Missing sentence
    // context keeps its auxiliary verb unknown; only the sourced adjective
    // inflection is rejected, independently of the aggregate reading status.
    for surface in ["한다", "하는"] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| a.lemmas.len() == 1 && a.lemmas[0].text == "하다" && !a.unchanged)
            .unwrap();
        let assessment = dictionary.annotate(&word).unwrap().assess(a);
        assert_eq!(assessment.status, Compatibility::Compatible);
        let slot = &assessment.lemmas[0];
        assert_eq!(
            slot.entries
                .iter()
                .find(|e| e.id == "krdict:73277")
                .unwrap()
                .status,
            Compatibility::Compatible
        );
        assert_eq!(
            slot.entries
                .iter()
                .find(|e| e.id == "krdict:62888")
                .unwrap()
                .status,
            Compatibility::Unknown
        );
        assert_eq!(
            slot.entries
                .iter()
                .find(|e| e.id == "krdict:62899")
                .unwrap()
                .status,
            Compatibility::Incompatible
        );
    }
}

#[test]
fn hada_dictionary_cache_library_and_cli_keep_each_filter_identity() {
    let f = Fixture::new("cli");
    let db = f.open();
    let engine = Lemmatizer::new();
    let mut uncached = DictionarySession::new(&db, 0);
    let mut cached = DictionarySession::new(&db, 1 << 20);
    for c in cases()["cases"].as_array().unwrap() {
        let surface = c["surface"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(
            uncached.annotate(&word).unwrap(),
            cached.annotate(&word).unwrap()
        );
        for (flag, filter) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut filtered = word.clone();
            let mut annotation = cached.annotate(&filtered).unwrap();
            if let Some(f) = filter {
                annotation.filter(&mut filtered, f);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", surface, "--dictionary"]).arg(&f.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let out = command.output().unwrap();
            assert!(
                out.status.success(),
                "{} {}",
                c["id"],
                String::from_utf8_lossy(&out.stderr)
            );
            let cli: Value = serde_json::from_slice(&out.stdout).unwrap();
            let mut bare = cli.clone();
            bare.as_object_mut().unwrap().remove("dictionary");
            let actual: WordAnalysis = serde_json::from_value(bare).unwrap();
            assert_eq!(actual, filtered, "{} {flag:?}", c["id"]);
            assert_eq!(cli["dictionary"], serde_json::to_value(annotation).unwrap());
        }
    }
}
