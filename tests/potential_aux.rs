//! COV-013/017bo/019aa: complete potential auxiliary sources and source-owned present inflections.
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
        let path =
            std::env::temp_dir().join(format!("klem-potential-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-potential-aux.json")],
            &path,
            "potential-aux",
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
    serde_json::from_str(include_str!("fixtures/potential-aux-sources.json")).unwrap()
}
fn cases() -> Value {
    serde_json::from_str(include_str!("fixtures/potential-aux-entry-judgments.json")).unwrap()
}
fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("potential-aux-"));
    suite
}
fn path(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn potential_sources_keep_four_complete_entries_and_all_29_native_groups() {
    let m = sources();
    let f = Fixture::new("sources");
    let db = f.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let s = suite();
    assert_eq!(m["source_entries"].as_array().unwrap().len(), 4);
    assert_eq!(s.cases.len(), 133);
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
    assert_eq!((senses, covered.len()), (5, 29));
    assert_eq!(m["native_entries"], 110);
    for e in m["grammar_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    assert_eq!(m["grammar_entries"].as_array().unwrap().len(), 5);
    let present = m["grammar_entries"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["id"] == "krdict:85853")
        .unwrap();
    assert_eq!(m["present_attestations"].as_array().unwrap().len(), 5);
    for (i, group) in present["senses"][0]["examples"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
    {
        let row = m["present_attestations"]
            .as_array()
            .unwrap()
            .iter()
            .find(|a| a["example_group"] == i)
            .unwrap();
        assert_eq!(row["examples"], *group);
        assert!(group.as_array().unwrap().iter().any(|line| {
            line.as_str()
                .unwrap()
                .contains(row["excerpt"].as_str().unwrap())
        }));
        assert!(
            s.cases
                .iter()
                .any(|c| c.id == row["case"].as_str().unwrap())
        );
    }
}

#[test]
fn potential_raw_paths_keep_unicode_components_and_original_word_hypotheses() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (128, 5));
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
fn potential_entry_policy_checks_standalone_classes_exceptions_and_exact_owners() {
    let f = Fixture::new("policy");
    let db = f.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let doc = cases();
    let all = doc["cases"].as_array().unwrap();
    assert_eq!(all.len(), 128);
    assert_eq!(
        all.iter()
            .map(|c| c["judgments"].as_array().unwrap().len())
            .sum::<usize>(),
        286
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
    // Both the lexical and auxiliary adjective entries of 뻔하다 own
    // their own bare -는 conflict. A missing left context cannot supply a
    // different POS. The original verb/auxiliary hypotheses remain raw.
    let word = engine.analyze_word("뻔하는").unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "뻔하다"
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["는"])
        })
        .unwrap();
    let assessment = dictionary.annotate(&word).unwrap().assess(a);
    assert_eq!(assessment.status, Compatibility::Incompatible);
    for id in ["krdict:15651", "krdict:66639"] {
        assert_eq!(
            assessment.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == id)
                .unwrap()
                .status,
            Compatibility::Incompatible
        );
    }
}

#[test]
fn potential_dictionary_cache_library_and_cli_keep_each_filter_identity() {
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
