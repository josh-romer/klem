//! COV-021i: finite deictic verb vowel paradigms and adjective ambiguity.
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
            "klem-deictic-vowel-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-deictic-vowel.json")],
            &path,
            "deictic-vowel",
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
    serde_json::from_str(include_str!("fixtures/deictic-vowel-sources.json")).unwrap()
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn deictic_written_paradigms_keep_complete_native_forms_and_example_groups() {
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
    for (head, written) in [("그러다", "그래"), ("이러다", "이래"), ("저러다", "저래")]
    {
        let entry = source["verb_entries"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["headword"] == head)
            .unwrap();
        assert_eq!(entry["pos"], "동사");
        assert!(
            entry["forms"]
                .as_array()
                .unwrap()
                .iter()
                .any(|f| f["kind"] == "활용" && f["written"] == written)
        );
    }
    for observation in source["native_observations"].as_array().unwrap() {
        let entry = source["verb_entries"]
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
    assert_eq!(source["native_observations"].as_array().unwrap().len(), 2);
    assert_eq!(source["primary_publication"]["pdf_page"], 159);
}

#[test]
fn finite_vowel_recovery_preserves_ambiguity_unicode_prefinal_and_auxiliary_owners() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("deictic-vowel-"));
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (56, 13));
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
                .filter(|a| before.analyses.contains(a))
                .collect::<Vec<_>>(),
            before.analyses.iter().collect::<Vec<_>>(),
            "{surface}"
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        let a = word.analyses.iter().find(|a| matches(a, c)).unwrap();
        assert_eq!(
            a.rules.iter().any(|r| r == "contraction.deictic_verb"),
            c["new_verb"] == true,
            "{surface}"
        );
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        let order = a.breakdown().unwrap();
        assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len());
        use klem::breakdown::Component::{Lemma as L, Morpheme as M};
        if surface.ends_with("버렸다") || surface.ends_with("봤다") {
            assert_eq!(order, vec![L(0), M(0), L(1), M(1), M(2)]);
        }
        if c["new_verb"] == true {
            // Verb recovery does not inherit the homonymous adjective's ㅎ path.
            assert!(
                !a.spelling_paths
                    .iter()
                    .flatten()
                    .any(|p| matches!(p.class, klem::SpellingClass::HieutIrregular))
            );
        }
    }
}

#[test]
fn deictic_dictionary_source_cache_filters_and_cli_preserve_both_lexical_classes() {
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
            let entry = annotation.assess(a).lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == j["id"].as_str().unwrap())
                .unwrap()
                .clone();
            assert_eq!(serde_json::to_value(entry.status).unwrap(), j["status"]);
            assert_eq!(
                serde_json::to_value(entry.conflicts).unwrap(),
                j["conflicts"]
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
            assert!(expected.analyses.iter().any(|a| matches(a, c)), "{surface}");
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
fn unlisted_prefixed_stems_and_original_corpus_conflict_do_not_gain_the_finite_rule() {
    let engine = Lemmatizer::new();
    for c in sources()["unjudged_controls"].as_array().unwrap() {
        let before: WordAnalysis = serde_json::from_value(c["before_word"].clone()).unwrap();
        assert_eq!(
            engine.analyze_word(c["surface"].as_str().unwrap()).unwrap(),
            before
        );
    }
    let word = engine.analyze_word("그러지말고").unwrap();
    assert!(word.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["그러다", "말다"])
    }));
    let conflict = &sources()["separate_corpus_conflicts"][0];
    assert_eq!(conflict["original"]["source_row"][2], "그러하+지+말+고");
    assert_eq!(
        conflict["original"]["expected"],
        serde_json::json!(["그러하다", "말다"])
    );
    for n in [32, 128, 1024] {
        let surface = "그래".repeat(n);
        assert!(
            !engine
                .analyze_word(&surface)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "contraction.deictic_verb"))
        );
    }
}
