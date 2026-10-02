//! COV-013/019y: complete deul sources and finite ownership regressions.
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
        let path = std::env::temp_dir().join(format!("klem-deul-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-deul-aux.json")],
            &path,
            "deul-aux",
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
    serde_json::from_str(include_str!("fixtures/deul-aux-sources.json")).unwrap()
}
fn cases() -> Value {
    serde_json::from_str(include_str!("fixtures/deul-aux-entry-judgments.json")).unwrap()
}
fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("deul-aux-"));
    suite
}
fn path(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn deul_sources_keep_one_complete_entry_and_all_12_native_groups() {
    let m = sources();
    let f = Fixture::new("sources");
    let db = f.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let s = suite();
    assert_eq!(m["source_entries"].as_array().unwrap().len(), 1);
    assert_eq!(s.cases.len(), 22);
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
                let expected = r["target_entry"].as_str().unwrap();
                let selected = aux.entries.iter().find(|e| e.id == expected).unwrap();
                assert_eq!(selected.status, Compatibility::Compatible, "{}", c.id);
                assert!(selected.conflicts.is_empty());
            }
        }
    }
    assert_eq!((senses, covered.len()), (3, 12));
    assert_eq!(
        s.cases
            .iter()
            .filter(|c| c.id.contains("wrong-connector"))
            .count(),
        3
    );
    // Keep the native typo as a source conflict, with independent current
    // NIKL evidence recorded separately. Five examples were genuine misses.
    assert!(
        m["source_entries"][0]["senses"][2]["notes"][0]
            .as_str()
            .unwrap()
            .contains("-고 들다")
    );
    assert_eq!(
        m["attestations"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|a| a["raw_recovered_before"] == true)
            .count(),
        7
    );
    assert_eq!(
        m["attestations"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|a| a["sense"] == "3")
            .count(),
        5
    );
    assert!(
        m["runtime_policy"]
            .as_str()
            .unwrap()
            .starts_with("Add the independently confirmed 어 connector for 들다")
    );
}

#[test]
fn deul_raw_paths_keep_unicode_components_and_original_word_hypotheses() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (19, 3));
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
fn deul_entry_observations_preserve_homonyms_unknowns_and_immediate_owners() {
    let f = Fixture::new("policy");
    let db = f.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let doc = cases();
    let all = doc["cases"].as_array().unwrap();
    assert_eq!(all.len(), 26);
    assert_eq!(
        all.iter()
            .map(|c| c["judgments"].as_array().unwrap().len())
            .sum::<usize>(),
        151
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
            assert!(assessment.lemmas.iter().any(|s| s.entries.is_empty()));
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
    // A new auxiliary hypothesis must not erase the independently dictionary
    // listed compound or borrow its identity to classify the split reading.
    let mut word = engine.analyze_word("스며들었다").unwrap();
    let mut annotation = dictionary.annotate(&word).unwrap();
    annotation.filter(&mut word, DictionaryFilter::Compatible);
    assert!(
        word.analyses
            .iter()
            .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == "스며들다")
    );
    assert!(word.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["스미다", "들다"])
    }));
    // An initial lexical predicate and an auxiliary entry have different
    // evidence. An unrelated lexical homonym must not upgrade that auxiliary's
    // unknown preceding context, even when their aggregate is compatible.
    for c in all
        .iter()
        .filter(|c| c["id"].as_str().unwrap().contains("standalone"))
    {
        let word = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        let a = word.analyses.iter().find(|a| path(a, c)).unwrap();
        let assessment = dictionary.annotate(&word).unwrap().assess(a);
        let native = sources()["source_entries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["headword"] == a.lemmas[0].text && e["pos"] == "보조 동사")
            .unwrap()
            .clone();
        let auxiliary = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == native["id"].as_str().unwrap())
            .unwrap();
        assert_eq!(auxiliary.status, Compatibility::Unknown, "{}", c["id"]);
        assert!(auxiliary.conflicts.is_empty());
    }
}

#[test]
fn deul_dictionary_cache_library_and_cli_keep_each_filter_identity() {
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
