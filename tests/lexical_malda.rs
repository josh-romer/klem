//! COV-019ac: lexical 말다 retains its verb role and its own endings.
#[path = "../tools/validity.rs"]
mod validity;
use klem::breakdown::Component;
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
            "klem-lexical-malda-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-lexical-malda.json")],
            &path,
            "lexical-malda",
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
    serde_json::from_str(include_str!("fixtures/lexical-malda-sources.json")).unwrap()
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn lexical_malda_sources_retain_every_native_group_and_complete_verb_entry() {
    let source = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    for key in ["source_entries", "grammar_entries", "object_entries"] {
        for entry in source[key].as_array().unwrap() {
            assert_eq!(
                serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                    .unwrap(),
                *entry
            );
        }
    }
    let entry = &source["source_entries"][0];
    assert_eq!(
        (entry["id"].as_str(), entry["pos"].as_str()),
        (Some("krdict:69296"), Some("동사"))
    );
    assert_eq!(entry["senses"].as_array().unwrap().len(), 3);
    let mut groups = 0;
    for sense in entry["senses"].as_array().unwrap() {
        for (index, group) in sense["examples"].as_array().unwrap().iter().enumerate() {
            let observations: Vec<_> = source["attestations"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|o| o["sense"] == sense["id"] && o["example_group"] == index)
                .collect();
            assert_eq!(observations.len(), 1);
            let observation = observations[0];
            assert_eq!(observation["examples"], *group);
            let excerpt = observation["excerpt"].as_str().unwrap();
            assert!(
                group
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|line| line.as_str().unwrap().contains(excerpt))
            );
            assert_eq!(observation["surface"], excerpt.replace(' ', ""));
            let c = source["cases"]
                .as_array()
                .unwrap()
                .iter()
                .find(|c| c["id"] == observation["id"])
                .unwrap();
            let word = Lemmatizer::new()
                .analyze_word(c["surface"].as_str().unwrap())
                .unwrap();
            assert!(word.analyses.iter().any(|a| matches(a, c)), "{}", c["id"]);
            groups += 1;
        }
    }
    assert_eq!(groups, 27);
    for observation in source["object_attestations"].as_array().unwrap() {
        let e = source["object_entries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["id"] == observation["entry"])
            .unwrap();
        let sense = e["senses"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["id"] == observation["sense"])
            .unwrap();
        assert_eq!(
            sense["examples"][observation["example_group"].as_u64().unwrap() as usize],
            observation["examples"]
        );
    }
}

#[test]
fn lexical_malda_raw_judgments_preserve_roles_unicode_and_mixed_owner_order() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("lexical-malda-"));
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (72, 16));
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
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in &word.analyses {
            let order = a.breakdown().unwrap();
            assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len(), "{surface}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
        let a = word.analyses.iter().find(|a| matches(a, c)).unwrap();
        use Component::{Lemma as L, Morpheme as M};
        let expected = match surface {
            "먹어보다말았다" | "먹다말아버렸다" | "먹다말지않았다" => {
                Some(vec![L(0), M(0), L(1), M(1), L(2), M(2), M(3)])
            }
            "선생님들말고" => Some(vec![L(0), M(0), M(1), L(1), M(2)]),
            "걱정을말다" => Some(vec![L(0), M(0), L(1), M(1)]),
            _ => None,
        };
        if let Some(expected) = expected {
            assert_eq!(a.breakdown().unwrap(), expected, "{surface}");
        }
    }
    // Several lexical members remain enumerable without a chain-depth cutoff.
    let word = engine
        .analyze_word(&format!("먹다{}말았다", "말다".repeat(6)))
        .unwrap();
    assert!(word.analyses.iter().any(|a| {
        a.lemmas.len() == 8
            && a.lemmas[0].text == "먹다"
            && a.lemmas
                .iter()
                .skip(1)
                .all(|l| l.text == "말다" && l.kind == klem::LemmaKind::Predicate)
    }));
}

#[test]
fn lexical_malda_dictionary_homonyms_filters_cache_and_cli_preserve_verb_roles() {
    let fixture = Fixture::new("policy");
    let db = fixture.open();
    let mut uncached = DictionarySession::new(&db, 0);
    let mut cached = DictionarySession::new(&db, 1 << 20);
    for c in sources()["cases"].as_array().unwrap() {
        let surface = c["surface"].as_str().unwrap();
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        assert_eq!(
            uncached.annotate(&word).unwrap(),
            cached.annotate(&word).unwrap()
        );
        let a = word.analyses.iter().find(|a| matches(a, c)).unwrap();
        let annotated = cached.annotate(&word).unwrap();
        let assessment = annotated.assess(a);
        let slot = c["lexical_mal_slot"].as_u64().unwrap() as usize;
        let mal = assessment
            .lemmas
            .iter()
            .find(|l| l.lemma_index == slot)
            .unwrap();
        for j in c["entry_judgments"].as_array().unwrap() {
            let e = mal
                .entries
                .iter()
                .find(|e| e.id == j["id"].as_str().unwrap())
                .unwrap();
            assert_eq!(
                serde_json::to_value(e.status).unwrap(),
                j["status"],
                "{surface} {}",
                j["id"]
            );
            assert_eq!(serde_json::to_value(&e.conflicts).unwrap(), j["conflicts"]);
        }
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
                assert_eq!(
                    filtered.analyses.iter().any(|a| matches(a, c)),
                    c["missing_owner_entries"] != true,
                    "{surface} {f:?}"
                );
            }
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
                serde_json::to_value(annotation).unwrap()
            );
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(cli).unwrap(),
                filtered
            );
        }
    }
}
