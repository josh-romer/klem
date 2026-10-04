//! COV-019ae: native source tensions and immediate inflection owners.
use klem::dictionary::{
    AttachmentRule, Compatibility, Dictionary, DictionaryFilter, DictionarySession,
    SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!(
        "fixtures/continuation-inflection-sources.json"
    ))
    .unwrap()
}
fn judgments() -> Value {
    serde_json::from_str(include_str!(
        "fixtures/continuation-inflection-judgments.json"
    ))
    .unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-continuation-inflection-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-continuation-inflection.json"),
                PathBuf::from("tests/fixtures/krdict-continuation-inflection-additional.json"),
            ],
            &path,
            "continuation-inflection",
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
fn path(a: &Analysis, case: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == case["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == case["morphemes"]
}
fn new_rule(rule: AttachmentRule) -> bool {
    matches!(
        rule,
        AttachmentRule::ContinuationLeftTense
            | AttachmentRule::GoNadaHonorific
            | AttachmentRule::GoNadaFuture
            | AttachmentRule::GoNadaFinalEnding
    )
}

#[test]
fn complete_native_import_including_missing_idiom_pos_is_preserved() {
    let source = sources();
    let fixture = Fixture::new("source");
    let db = fixture.open();
    assert_eq!(source["source_entries"].as_array().unwrap().len(), 172);
    for e in source["source_entries"].as_array().unwrap() {
        let id = e["id"].as_str().unwrap();
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            *e
        );
        let mut projected = source["complete_native_entries"][id].clone();
        for sense in projected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(projected, *e);
    }
    let extra: Value = serde_json::from_str(include_str!(
        "fixtures/continuation-inflection-additional.json"
    ))
    .unwrap();
    for e in extra["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    let idiom = db.lookup("손에 붙다").unwrap();
    assert_eq!(idiom.len(), 1);
    assert_eq!(idiom[0].pos, "");
    assert!(idiom[0].id.starts_with("krdict:17608:"));
    assert_eq!(source["individual_reviews"].as_array().unwrap().len(), 52);
    for review in source["individual_reviews"].as_array().unwrap() {
        assert_eq!(review["contextual_verdict"], "unjudged");
        assert_eq!(review["independent_review"], "pending");
    }
}

#[test]
fn original_raw_paths_and_four_historical_tensions_remain_unchanged() {
    let source = sources();
    let preflight: Value = serde_json::from_str(include_str!(
        "../docs/continuation-inflection-source-preflight.json"
    ))
    .unwrap();
    for (surface, modes) in preflight["words"].as_object().unwrap() {
        assert_eq!(source["before_words"][surface], *modes);
    }
    let engine = Lemmatizer::new();
    let fixture = Fixture::new("raw");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    assert_eq!(source["before_words"].as_object().unwrap().len(), 352);
    let extra: Value = serde_json::from_str(include_str!(
        "fixtures/continuation-inflection-additional.json"
    ))
    .unwrap();
    assert_eq!(extra["before_words"].as_object().unwrap().len(), 15);
    for (surface, modes) in source["before_words"]
        .as_object()
        .unwrap()
        .iter()
        .chain(extra["before_words"].as_object().unwrap().iter())
    {
        let mut frozen = modes["all"].clone();
        frozen.as_object_mut().unwrap().remove("dictionary");
        let frozen: WordAnalysis = serde_json::from_value(frozen).unwrap();
        let actual = engine.analyze_word(surface).unwrap();
        assert_eq!(actual, frozen, "{surface}");
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
        }
        let mut filtered = actual.clone();
        dictionary
            .annotate(&filtered)
            .unwrap()
            .filter(&mut filtered, DictionaryFilter::Headword);
        let mut frozen_headword = modes["headword"].clone();
        frozen_headword
            .as_object_mut()
            .unwrap()
            .remove("dictionary");
        assert_eq!(
            filtered,
            serde_json::from_value::<WordAnalysis>(frozen_headword).unwrap(),
            "{surface}"
        );
    }
}

#[test]
fn authored_entry_judgments_and_filter_memberships_hold_with_bounded_caches() {
    let fixture = Fixture::new("judgments");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let cases = judgments();
    assert_eq!(cases["cases"].as_array().unwrap().len(), 34);
    for budget in [0, 1, 4096] {
        let mut dictionary = DictionarySession::new(&db, budget);
        for case in cases["cases"].as_array().unwrap() {
            for surface in [
                case["surface"].as_str().unwrap().to_owned(),
                case["surface"].as_str().unwrap().nfd().collect(),
            ] {
                let word = engine.analyze_word(&surface).unwrap();
                let a = word.analyses.iter().find(|a| path(a, case)).unwrap();
                let annotation = dictionary.annotate(&word).unwrap();
                let reading = annotation.assess(a);
                for j in case["judgments"].as_array().unwrap() {
                    let slot = reading
                        .lemmas
                        .iter()
                        .find(|s| s.lemma_index == j["lemma_index"].as_u64().unwrap() as usize)
                        .unwrap();
                    let entry = slot
                        .entries
                        .iter()
                        .find(|e| e.id == j["entry_id"].as_str().unwrap())
                        .unwrap();
                    assert_eq!(
                        serde_json::to_value(entry.status).unwrap(),
                        j["status"],
                        "{} {}",
                        case["id"],
                        entry.id
                    );
                    assert_eq!(
                        serde_json::to_value(&entry.conflicts).unwrap(),
                        j["conflicts"],
                        "{} {}",
                        case["id"],
                        entry.id
                    );
                }
                for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                    let mut filtered = word.clone();
                    let mut ann = annotation.clone();
                    ann.filter(&mut filtered, policy);
                    assert_eq!(
                        filtered.analyses.iter().any(|a| path(a, case)),
                        policy == DictionaryFilter::Headword || case["filter_retained"] == true,
                        "{}",
                        case["id"]
                    );
                    assert_eq!(ann.readings.len(), filtered.analyses.len());
                }
                assert!(dictionary.cache_bytes() <= budget);
            }
        }
    }
}

#[test]
fn restrictions_require_native_identity_and_do_not_cross_negatives_or_connectors() {
    let fixture = Fixture::new("providers");
    let db = fixture.open();
    let mut dict = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    let cases = judgments();
    for name in [
        "beorida-left-past",
        "nada-right-honorific",
        "nada-right-future",
        "nada-finite-present",
    ] {
        let case = cases["cases"]
            .as_array()
            .unwrap()
            .iter()
            .find(|c| c["id"] == format!("continuation-inflection-{name}"))
            .unwrap();
        let word = engine
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        let a = word.analyses.iter().find(|a| path(a, case)).unwrap();
        let original = dict.annotate(&word).unwrap();
        for mutation in 0..4 {
            let mut annotation = original.clone();
            for matched in annotation
                .lemmas
                .iter_mut()
                .filter(|m| m.lemma == *a.lemmas.last().unwrap())
            {
                for entry in &mut matched.entries {
                    match mutation {
                        0 => entry.entry.id = "other-provider:auxiliary".into(),
                        1 => entry.entry.headword = "wrong headword".into(),
                        2 => entry.entry.homonym = "1".into(),
                        _ => {
                            entry.entry.pos.clear();
                            entry.pos_compatibility = Compatibility::Unknown;
                        }
                    }
                }
            }
            assert!(
                annotation
                    .assess(a)
                    .lemmas
                    .iter()
                    .flat_map(|s| &s.entries)
                    .flat_map(|e| &e.conflicts)
                    .all(|c| !new_rule(c.rule)),
                "{name} mutation {mutation}"
            );
        }
    }
    // The native adjective counterexample is immediate, not an inherited
    // permission for adjective negatives or other continuation auxiliaries.
    for surface in ["아프지않고나서", "아파버리다", "아파내다"] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| a.lemmas.first().is_some_and(|l| l.text == "아프다") && a.lemmas.len() > 1)
            .unwrap();
        let reading = dict.annotate(&word).unwrap().assess(a);
        let entry = reading.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == "krdict:62239")
            .unwrap();
        assert_eq!(entry.status, Compatibility::Incompatible, "{surface}");
        assert!(
            entry
                .conflicts
                .iter()
                .any(|c| c.rule == AttachmentRule::ContinuationVerb)
        );
    }
    for surface in [
        "많아온다",
        "커왔다",
        "나빠올",
        "밝아올것이다",
        "타고나셨다",
        "들고났다",
        "나다",
        "버렸다",
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let ann = dict.annotate(&word).unwrap();
        // These source/lexical alternatives are not inferred from spelling.
        for a in word
            .analyses
            .iter()
            .filter(|a| a.lemmas.len() == 1 || a.lemmas.last().is_some_and(|l| l.text == "오다"))
        {
            assert!(
                ann.assess(a)
                    .lemmas
                    .iter()
                    .flat_map(|s| &s.entries)
                    .flat_map(|e| &e.conflicts)
                    .all(|c| !new_rule(c.rule)),
                "{surface}"
            );
        }
    }
}

#[test]
fn cli_modes_match_library_entry_assessments_and_preserve_whole_lexical_alternatives() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let mut dict = DictionarySession::new(&db, 4096);
    let cases = judgments();
    for surface in cases["cases"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["surface"].as_str().unwrap())
        .chain(["타고나셨다", "들고났다", "아프고난"])
    {
        let raw = engine.analyze_word(surface).unwrap();
        for (flag, policy) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut word = raw.clone();
            let mut annotation = dict.annotate(&word).unwrap();
            if let Some(policy) = policy {
                annotation.filter(&mut word, policy);
            }
            let mut expected = serde_json::to_value(&word).unwrap();
            expected["dictionary"] = serde_json::to_value(&annotation).unwrap();
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let output = command.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            assert_eq!(
                serde_json::from_slice::<Value>(&output.stdout).unwrap(),
                expected,
                "{surface} {flag:?}"
            );
        }
    }
}
