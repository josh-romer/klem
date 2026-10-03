//! COV-018ab: question clauses have a separate topic-particle interpretation.
#[path = "../tools/validity.rs"]
mod validity;

use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/question-topic-sources.json")).unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-question-topic-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-question-topic.json")],
            &path,
            "question-topic",
        )
        .unwrap();
        Self(path)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn matches(a: &Analysis, j: &Value) -> bool {
    serde_json::to_value(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == j["lemmas"]
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == j["lemma_kinds"]
        && serde_json::to_value(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()).unwrap()
            == j["morphemes"]
        && serde_json::to_value(a.morphemes.iter().map(|m| m.kind).collect::<Vec<_>>()).unwrap()
            == j["morpheme_kinds"]
}

#[test]
fn two_native_contexts_preserve_full_sources_and_individual_judgments() {
    let source = sources();
    let f = Fixture::new("sources");
    let db = SqliteDictionary::open(&f.0).unwrap();
    assert_eq!(source["source_entries"].as_array().unwrap().len(), 15);
    for entry in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    let original: Value =
        serde_json::from_str(include_str!("../docs/question-case-source-preflight.json")).unwrap();
    let selected = source["topic_attestations"].as_array().unwrap();
    assert_eq!(selected.len(), 2);
    for hit in selected {
        assert!(original["hits"].as_array().unwrap().contains(hit));
        let entry = &source["complete_native_entries"][hit["entry_id"].as_str().unwrap()];
        let sense = entry["senses"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["id"] == hit["sense"])
            .unwrap();
        assert_eq!(
            sense["examples"][hit["example_group"].as_u64().unwrap() as usize],
            hit["complete_example_group"]
        );
        let line = hit["complete_example_group"][hit["line_index"].as_u64().unwrap() as usize]
            .as_str()
            .unwrap();
        let span = hit["character_span"].as_array().unwrap();
        let start = span[0].as_u64().unwrap() as usize;
        let end = span[1].as_u64().unwrap() as usize;
        assert_eq!(
            line.chars()
                .skip(start)
                .take(end - start)
                .collect::<String>(),
            hit["surface"].as_str().unwrap()
        );
    }
    let ledger: Value = serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    for c in source["cases"].as_array().unwrap() {
        assert_eq!(
            ledger["cases"]
                .as_array()
                .unwrap()
                .iter()
                .find(|r| r["id"] == c["id"])
                .unwrap(),
            c
        );
    }
    let suite: validity::Suite = serde_json::from_value(serde_json::json!({
        "schema_version": 1, "review_status": "Source-backed agent review; independent review pending.",
        "sources": source["sources"], "cases": source["cases"]
    })).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (11, 2));
    assert!(!report.review_queue.is_empty());
}

#[test]
fn topic_paths_keep_every_prior_bundle_unicode_and_component_ownership() {
    let source = sources();
    let engine = Lemmatizer::new();
    assert_eq!(
        source["original_bundle_observations"]
            .as_array()
            .unwrap()
            .len(),
        165
    );
    for (surface, modes) in source["before_words"].as_object().unwrap() {
        let mut frozen = modes["all"].clone();
        frozen.as_object_mut().unwrap().remove("dictionary");
        let frozen: WordAnalysis = serde_json::from_value(frozen).unwrap();
        let actual = engine.analyze_word(surface).unwrap();
        let retained: Vec<_> = actual
            .analyses
            .iter()
            .filter(|a| frozen.analyses.contains(a))
            .collect();
        assert_eq!(
            retained,
            frozen.analyses.iter().collect::<Vec<_>>(),
            "{surface}"
        );
        assert_eq!(
            actual,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        for a in &actual.analyses {
            let components = a.breakdown().unwrap();
            assert_eq!(components.len(), a.lemmas.len() + a.morphemes.len());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            // This frozen topic cohort also contains future-particle probes.
            // Keep the topic-specific assertion scoped to topic surfaces;
            // later independently reviewed particles may add their own paths.
            if surface.ends_with("는") && !frozen.analyses.contains(a) {
                assert!(
                    a.rules.contains(&"particle.quoted_question".to_owned()),
                    "{surface}: {a:?}"
                );
                assert!(
                    a.morphemes
                        .iter()
                        .any(|m| m.form == "는" && m.kind == klem::MorphemeKind::Particle)
                );
            }
        }
    }
    for c in source["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["judgments"][0]["verdict"] == "required")
    {
        let word = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| matches(a, &c["judgments"][0]))
            .unwrap();
        assert!(a.rules.iter().all(|r| !r.starts_with("nominalization")));
    }
}

#[test]
fn topic_attachment_keeps_question_owner_pos_and_unknown_alternatives() {
    let f = Fixture::new("policy");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let mut session = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (surface, head, ending, id, status) in [
        (
            "넣느냐는",
            "넣다",
            "느냐",
            "krdict:64509",
            Compatibility::Compatible,
        ),
        (
            "붙느냐는",
            "붙다",
            "느냐",
            "krdict:74181",
            Compatibility::Compatible,
        ),
        (
            "먹느냐는",
            "먹다",
            "느냐",
            "krdict:15983",
            Compatibility::Compatible,
        ),
        (
            "크냐는",
            "크다",
            "냐",
            "krdict:66586",
            Compatibility::Compatible,
        ),
        (
            "크느냐는",
            "크다",
            "느냐",
            "krdict:66584",
            Compatibility::Compatible,
        ),
        (
            "크느냐는",
            "크다",
            "느냐",
            "krdict:66586",
            Compatibility::Incompatible,
        ),
        (
            "좋으냐는",
            "좋다",
            "으냐",
            "krdict:79033",
            Compatibility::Compatible,
        ),
        (
            "좋느냐는",
            "좋다",
            "느냐",
            "krdict:79033",
            Compatibility::Incompatible,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq([ending, "는"])
            })
            .unwrap();
        let assessment = session.annotate(&word).unwrap().assess(a);
        let selected = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == id)
            .unwrap();
        assert_eq!(selected.status, status, "{surface} {id}");
        if status == Compatibility::Incompatible {
            assert!(
                selected
                    .conflicts
                    .iter()
                    .all(|c| c.morpheme_index == Some(0))
            );
        }
    }
    // The following topic particle cannot borrow the nominal's class for the
    // copula's question ending. Keep the incompatible raw alternative visible.
    let word = engine.analyze_word("학생이냐는").unwrap();
    for (ending, status) in [
        ("냐", Compatibility::Compatible),
        ("으냐", Compatibility::Incompatible),
    ] {
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(["학생", "이다"])
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq([ending, "는"])
            })
            .unwrap();
        let assessment = session.annotate(&word).unwrap().assess(a);
        assert_eq!(assessment.lemmas[0].status, Compatibility::Compatible);
        assert_eq!(assessment.lemmas[1].status, status);
        if status == Compatibility::Incompatible {
            assert!(
                assessment.lemmas[1]
                    .entries
                    .iter()
                    .all(|e| e.conflicts.iter().all(|c| c.morpheme_index == Some(0)))
            );
        }
    }
    for (surface, prefinal) in [
        ("넣었느냐는", "었"),
        ("넣겠느냐는", "겠"),
        ("넣으시느냐는", "시"),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == "넣다"
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq([prefinal, "느냐", "는"])
            })
            .unwrap();
        let assessment = session.annotate(&word).unwrap().assess(a);
        assert_eq!(assessment.status, Compatibility::Compatible);
    }
    let word = engine.analyze_word("뮈느냐는").unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "뮈다"
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["느냐", "는"])
        })
        .unwrap();
    assert_eq!(
        session.annotate(&word).unwrap().assess(a).status,
        Compatibility::Unknown
    );
}

#[test]
fn topic_cli_library_cache_and_filters_retain_current_raw_identity() {
    let f = Fixture::new("cli");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let mut cached = DictionarySession::new(&db, 1 << 20);
    let mut uncached = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    let source = sources();
    let mut surfaces: Vec<_> = source["cases"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["surface"].as_str().unwrap())
        .collect();
    surfaces.extend(["크느냐는", "좋느냐는", "학생이느냐는", "뮈느냐는"]);
    for surface in surfaces {
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(
            cached.annotate(&word).unwrap(),
            uncached.annotate(&word).unwrap()
        );
        for (flag, filter) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut expected = word.clone();
            let mut dictionary = cached.annotate(&word).unwrap();
            if let Some(filter) = filter {
                dictionary.filter(&mut expected, filter);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", surface, "--dictionary"]).arg(&f.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let out = command.output().unwrap();
            assert!(
                out.status.success(),
                "{}",
                String::from_utf8_lossy(&out.stderr)
            );
            let mut actual: Value = serde_json::from_slice(&out.stdout).unwrap();
            let annotation = actual
                .as_object_mut()
                .unwrap()
                .remove("dictionary")
                .unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(actual).unwrap(),
                expected
            );
            assert_eq!(annotation, serde_json::to_value(dictionary).unwrap());
        }
    }
}
