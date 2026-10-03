//! COV-018ad: a closed question can carry additive 도 without an overt nominalizer.
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
    serde_json::from_str(include_str!("fixtures/question-additive-sources.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-question-additive-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-question-additive.json",
            )],
            &path,
            "question-additive",
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
fn named<'a>(word: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(heads.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        })
        .unwrap_or_else(|| panic!("{}: {heads:?} {forms:?}", word.normalized))
}

#[test]
fn attestation_layout_native_entries_and_append_only_judgments() {
    let source = sources();
    let preflight: Value = serde_json::from_str(include_str!(
        "../docs/question-clause-additive-preflight.json"
    ))
    .unwrap();
    assert_eq!(
        preflight["before_word"],
        source["before_words"]["내느냐도"]["all"]
    );
    assert_eq!(preflight["target_path"], source["attested_target"]);
    assert_eq!(preflight["target_path_present_before"], false);
    assert!(
        preflight["complete_attested_sentence"]
            .as_str()
            .unwrap()
            .contains("내\n느냐도")
    );
    assert_eq!(source["native_scan"]["entries_scanned"], 56555);
    assert!(source["native_scan"]["hits"].as_array().unwrap().is_empty());
    let f = Fixture::new("source");
    let db = SqliteDictionary::open(&f.0).unwrap();
    assert_eq!(source["source_entries"].as_array().unwrap().len(), 19);
    for entry in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
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
    let suite: validity::Suite=serde_json::from_value(serde_json::json!({
        "schema_version":1,"review_status":"Source-backed agent review; independent review pending.",
        "sources":source["sources"],"cases":source["cases"]
    })).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (13, 1));
    assert!(!report.review_queue.is_empty());
    // A layout diagnostic is an author input; the engine cannot join a printed
    // word across a newline on behalf of the user.
    let engine = Lemmatizer::new();
    assert!(engine.analyze_word("내\n느냐도").is_err());
    let literal = engine.analyze_word("내느냐도").unwrap();
    let a = named(&literal, &["내다"], &["느냐", "도"]);
    assert!(a.rules.contains(&"particle.quoted_question".to_owned()));
    assert!(a.rules.iter().all(|r| !r.starts_with("nominalization")));
}

#[test]
fn additive_paths_preserve_prior_order_unicode_components_and_future_probes() {
    let source = sources();
    let engine = Lemmatizer::new();
    assert_eq!(source["before_words"].as_object().unwrap().len(), 26);
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
            assert_eq!(
                a.breakdown().unwrap().len(),
                a.lemmas.len() + a.morphemes.len()
            );
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            if !frozen.analyses.contains(a) {
                assert!(
                    a.rules.contains(&"particle.quoted_question".to_owned()),
                    "{surface}: {a:?}"
                );
                assert!(
                    a.morphemes
                        .iter()
                        .any(|m| m.form == "도" && m.kind == klem::MorphemeKind::Particle)
                );
            }
        }
        if [
            "내느냐부터",
            "내느냐조차",
            "내느냐마저",
            "먹느냐는도",
            "먹느냐는데도",
        ]
        .contains(&surface.as_str())
        {
            assert_eq!(actual, frozen, "Future-particle probe changed: {surface}");
        }
    }
    for c in source["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["judgments"][0]["verdict"] == "required")
    {
        let word = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        assert!(word.analyses.iter().any(|a| matches(a, &c["judgments"][0])));
    }
    // Bare-question licenses do not license every quoted-ending follower.
    // Their existing paths were checked against the actual frozen output above.
}

#[test]
fn additive_keeps_question_owner_pos_copula_and_exact_negative_exception() {
    let f = Fixture::new("policy");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let mut session = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (surface, head, forms, id, status, slot) in [
        (
            "내느냐도",
            "내다",
            vec!["느냐", "도"],
            "krdict:89906",
            Compatibility::Compatible,
            0,
        ),
        (
            "크느냐도",
            "크다",
            vec!["느냐", "도"],
            "krdict:66584",
            Compatibility::Compatible,
            0,
        ),
        (
            "크느냐도",
            "크다",
            vec!["느냐", "도"],
            "krdict:66586",
            Compatibility::Incompatible,
            0,
        ),
        (
            "좋느냐도",
            "좋다",
            vec!["느냐", "도"],
            "krdict:79033",
            Compatibility::Incompatible,
            0,
        ),
        (
            "좋으냐도",
            "좋다",
            vec!["으냐", "도"],
            "krdict:79033",
            Compatibility::Compatible,
            0,
        ),
        (
            "냈느냐도",
            "내다",
            vec!["었", "느냐", "도"],
            "krdict:89906",
            Compatibility::Compatible,
            1,
        ),
        (
            "내겠느냐도",
            "내다",
            vec!["겠", "느냐", "도"],
            "krdict:89906",
            Compatibility::Compatible,
            1,
        ),
        (
            "내시느냐도",
            "내다",
            vec!["시", "느냐", "도"],
            "krdict:89906",
            Compatibility::Compatible,
            1,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = named(&word, &[head], &forms);
        let assessment = session.annotate(&word).unwrap().assess(a);
        let entry = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == id)
            .unwrap();
        assert_eq!(entry.status, status, "{surface} {id}");
        if status == Compatibility::Incompatible {
            assert!(
                entry
                    .conflicts
                    .iter()
                    .all(|c| c.morpheme_index == Some(slot))
            );
        }
    }
    let word = engine.analyze_word("학생이냐도").unwrap();
    for (ending, status) in [
        ("냐", Compatibility::Compatible),
        ("으냐", Compatibility::Incompatible),
    ] {
        let a = named(&word, &["학생", "이다"], &[ending, "도"]);
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
    for (surface, left, aggregate, adj_status) in [
        (
            "없지않느냐도",
            "없다",
            Compatibility::Compatible,
            Compatibility::Compatible,
        ),
        (
            "좋지않느냐도",
            "좋다",
            Compatibility::Incompatible,
            Compatibility::Incompatible,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = named(&word, &[left, "않다"], &["지", "느냐", "도"]);
        let assessment = session.annotate(&word).unwrap().assess(a);
        assert_eq!(assessment.status, aggregate);
        assert_eq!(assessment.lemmas[0].status, Compatibility::Compatible);
        let adj = assessment.lemmas[1]
            .entries
            .iter()
            .find(|e| e.id == "krdict:71583")
            .unwrap();
        assert_eq!(adj.status, adj_status);
        if adj_status == Compatibility::Incompatible {
            assert!(adj.conflicts.iter().all(|c| c.morpheme_index == Some(1)));
        }
    }
    let word = engine.analyze_word("먹어내느냐도").unwrap();
    let assessment = session.annotate(&word).unwrap().assess(named(
        &word,
        &["먹다", "내다"],
        &["어", "느냐", "도"],
    ));
    assert_eq!(assessment.status, Compatibility::Compatible);
    assert_eq!(
        assessment.lemmas[1]
            .entries
            .iter()
            .find(|e| e.id == "krdict:60625")
            .unwrap()
            .status,
        Compatibility::Compatible
    );
    assert_eq!(
        assessment.lemmas[1]
            .entries
            .iter()
            .find(|e| e.id == "krdict:89906")
            .unwrap()
            .status,
        Compatibility::Incompatible
    );
    let word = engine.analyze_word("뮈느냐도").unwrap();
    assert_eq!(
        session
            .annotate(&word)
            .unwrap()
            .assess(named(&word, &["뮈다"], &["느냐", "도"]))
            .status,
        Compatibility::Unknown
    );
    // 좋아 내다 is deliberately a diagnostic, not a new required grammar
    // judgment: the continuation auxiliary's left-class audit remains COV-019ad.
}

#[test]
fn additive_cli_library_cache_and_filters_use_actual_current_candidates() {
    let f = Fixture::new("cli");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let mut cached = DictionarySession::new(&db, 1 << 20);
    let mut uncached = DictionarySession::new(&db, 0);
    let source = sources();
    let engine = Lemmatizer::new();
    for surface in source["before_words"].as_object().unwrap().keys() {
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
