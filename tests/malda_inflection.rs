//! COV-019ac: paired lexical 말다 keeps inflection and auxiliary owners.
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
            "klem-malda-inflection-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-malda-inflection.json")],
            &path,
            "malda-inflection",
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
    serde_json::from_str(include_str!("fixtures/malda-inflection-sources.json")).unwrap()
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn malda_inflection_complete_sources_and_unjudged_probes_are_retained() {
    let source = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    assert_eq!(source["complete_entries"].as_array().unwrap().len(), 48);
    for entry in source["complete_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    let publication = &source["published_attestations"][0];
    assert_eq!(publication["pdf_page"], 5);
    assert_eq!(publication["surface"], "했건말았건");
    assert!(
        publication["verbatim_excerpt"]
            .as_str()
            .unwrap()
            .contains("했건 말았건")
    );
    // A targeted source attestation is separate from a blind precision sample.
    assert_eq!(
        source["unjudged_probe_dispositions"]
            .as_array()
            .unwrap()
            .len(),
        16
    );
    assert_eq!(
        source["native_scan_dispositions"].as_array().unwrap().len(),
        4
    );
    for corpus in source["corpus_search"].as_array().unwrap() {
        assert!(corpus["targets"].as_array().unwrap().is_empty());
    }
}

#[test]
fn malda_inflection_paths_keep_prefinals_and_auxiliaries_with_their_owners() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("malda-inflection-"));
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (82, 16));
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
        // Identity and all previous hypotheses remain, in their original order.
        let retained: Vec<_> = word
            .analyses
            .iter()
            .filter(|a| before.analyses.contains(a))
            .collect();
        assert_eq!(
            retained,
            before.analyses.iter().collect::<Vec<_>>(),
            "{surface}"
        );
        let a = word.analyses.iter().find(|a| matches(a, c)).unwrap();
        let order = a.breakdown().unwrap();
        assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len(), "{surface}");
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        use klem::breakdown::Component::{Lemma as L, Morpheme as M};
        let expected = match surface {
            "했건말았건" | "먹으시거나마시거나" => {
                Some(vec![L(0), M(0), M(1), L(1), M(2), M(3)])
            }
            "먹거나말아버렸거나" | "먹거나말지않았거나" => {
                Some(vec![L(0), M(0), L(1), M(1), L(2), M(2), M(3)])
            }
            "먹거나말아버리거나" | "먹거나말지않거나" | "할지말지않을지" | "할까말까싶다" => {
                Some(vec![L(0), M(0), L(1), M(1), L(2), M(2)])
            }
            _ => None,
        };
        if let Some(expected) = expected {
            assert_eq!(order, expected, "{surface}");
        }
        if matches!(surface, "먹거나말아버리거나" | "먹거나말지않거나") {
            assert!(a.rules.iter().any(|r| r == "lexical.mal.paired_branch"));
        }
        if surface == "할까말까싶다" {
            assert!(!a.rules.iter().any(|r| r == "lexical.mal.paired_branch"));
        }
    }
}

#[test]
fn repeated_short_mal_boundaries_preserve_exact_output_without_a_cutoff() {
    let engine = Lemmatizer::new();
    for c in sources()["stress"].as_array().unwrap() {
        let before: WordAnalysis = serde_json::from_value(c["before_word"].clone()).unwrap();
        assert_eq!(
            engine.analyze_word(c["surface"].as_str().unwrap()).unwrap(),
            before
        );
    }
    let word = engine
        .analyze_word(&format!("먹거나{}말았거나", "말다".repeat(6)))
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
fn malda_inflection_dictionary_homonyms_filters_cache_and_cli_preserve_verb_roles() {
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
