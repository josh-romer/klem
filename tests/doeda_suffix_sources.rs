//! COV-022m: suffix-owned inflections alongside immutable whole-head readings.
use klem::dictionary::{
    Annotation, AttachmentRule, Compatibility, Dictionary, DictionaryFilter, DictionarySession,
    SqliteDictionary, import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind, Session, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::PathBuf,
    process::Command,
    sync::{Arc, OnceLock},
};
use unicode_normalization::UnicodeNormalization;

fn source() -> &'static Value {
    static DATA: OnceLock<Value> = OnceLock::new();
    DATA.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/doeda-suffix-sources.json")).unwrap()
    })
}

fn effective_cases() -> Vec<Value> {
    let corrections: Value =
        serde_json::from_str(include_str!("fixtures/doeda-suffix-corrections.json")).unwrap();
    assert_eq!(
        corrections["source_fixture_sha256"],
        format!(
            "{:x}",
            Sha256::digest(include_bytes!("fixtures/doeda-suffix-sources.json"))
        )
    );
    for entry in corrections["source_entries"].as_array().unwrap() {
        assert!(
            source()["source_entries"]
                .as_array()
                .unwrap()
                .contains(entry)
        );
    }
    let mut cases = source()["cases"].as_array().unwrap().clone();
    assert_eq!(corrections["corrections"].as_array().unwrap().len(), 10);
    for c in corrections["corrections"].as_array().unwrap() {
        let i = cases.iter().position(|old| old == &c["original"]).unwrap();
        cases[i] = c["replacement_control"].clone();
        cases.push(c["replacement_positive"].clone());
    }
    cases
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-doeda-suffix-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-suffix.json")],
            &path,
            "doeda-suffix-source-test",
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

fn matches(a: &Analysis, c: &Value) -> bool {
    a.lemmas.iter().map(|l| l.text.as_str()).eq(c["lemmas"]
        .as_array()
        .unwrap()
        .iter()
        .map(|v| v.as_str().unwrap()))
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == c["lemma_kinds"]
        && a.morphemes
            .iter()
            .map(|m| m.form.as_str())
            .eq(c["morphemes"]
                .as_array()
                .unwrap()
                .iter()
                .map(|v| v.as_str().unwrap()))
        && serde_json::to_value(a.morphemes.iter().map(|m| m.kind).collect::<Vec<_>>()).unwrap()
            == c["morpheme_kinds"]
        && c["required_rules"]
            .as_array()
            .unwrap()
            .iter()
            .all(|r| a.rules.iter().any(|s| s == r.as_str().unwrap()))
}

fn order_is_complete(a: &Analysis) {
    use klem::breakdown::Component;
    let order = a.breakdown().expect("ordered suffix candidate");
    assert_eq!(
        order
            .iter()
            .filter_map(|c| match c {
                Component::Lemma(i) => Some(*i),
                _ => None,
            })
            .collect::<Vec<_>>(),
        (0..a.lemmas.len()).collect::<Vec<_>>()
    );
    assert_eq!(
        order
            .iter()
            .filter_map(|c| match c {
                Component::Morpheme(i) => Some(*i),
                _ => None,
            })
            .collect::<Vec<_>>(),
        (0..a.morphemes.len()).collect::<Vec<_>>()
    );
    for path in &a.spelling_paths {
        assert!(path.iter().all(|r| r.morpheme_index < a.morphemes.len()));
    }
}

#[test]
fn native_suffix_senses_examples_and_all_proposed_base_homonyms_survive_import() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    for expected in source()["source_entries"].as_array().unwrap() {
        let actual = db.entry(expected["id"].as_str().unwrap()).unwrap().unwrap();
        // This importer fixture is the explicit English translation projection;
        // the immutable source archive keeps every original language.
        let mut projected = expected.clone();
        for sense in projected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(serde_json::to_value(actual).unwrap(), projected);
    }
    let suffix = db.entry("krdict:74902").unwrap().unwrap();
    assert_eq!(suffix.summary.headword, "-되다");
    assert_eq!(suffix.summary.pos, "접사");
    assert_eq!(suffix.senses.len(), 2);
    assert_eq!(
        suffix
            .senses
            .iter()
            .map(|s| s.examples.len())
            .sum::<usize>(),
        157
    );
    assert!(db.lookup("타도되다").unwrap().is_empty());
    assert_eq!(
        db.entry("krdict:79461").unwrap().unwrap().summary.pos,
        "명사"
    );
}

#[test]
fn every_source_proposal_and_scoped_class_control_has_exact_owned_components() {
    let mut session = Session::new(Arc::new(Lemmatizer::new()), 4 * 1024 * 1024);
    let cases = effective_cases();
    assert_eq!(cases.len(), 1600);
    assert_eq!(
        cases.iter().filter(|c| c["verdict"] == "required").count(),
        1580
    );
    for c in &cases {
        for surface in [
            c["surface"].as_str().unwrap().to_owned(),
            c["surface"].as_str().unwrap().nfd().collect(),
        ] {
            let result = session.analyze_word(&surface).unwrap();
            assert_eq!(
                result.analyses.iter().any(|a| matches(a, c)),
                c["verdict"] == "required",
                "{}: {surface}",
                c["id"]
            );
            for a in &result.analyses {
                order_is_complete(a);
            }
        }
    }
}

#[test]
fn native_head_presence_and_reviewed_root_identity_control_each_source_path() {
    let file = Fixture::new("source-policy");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let mut missing = 0;
    let mut conflicts = 0;
    for case in effective_cases() {
        let raw = engine
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        let annotation = dictionary.annotate(&raw).unwrap();
        let Some(index) = raw.analyses.iter().position(|a| matches(a, &case)) else {
            assert_eq!(case["verdict"], "forbidden");
            continue;
        };
        assert_eq!(case["verdict"], "required");
        let path = &raw.analyses[index];
        let has_heads = path
            .lemmas
            .iter()
            .all(|l| !db.lookup(&l.text).unwrap().is_empty());
        let identity_conflict = path.lemmas[0].text == "속";
        if !has_heads {
            missing += 1;
        }
        if identity_conflict {
            conflicts += 1;
            assert_eq!(path.lemmas[0].kind, LemmaKind::Root);
            let reading = &annotation.readings[index];
            assert_eq!(reading.status, Compatibility::Incompatible);
            let entry = &reading.lemmas[0].entries[0];
            assert_eq!(entry.id, "krdict:71278");
            assert!(entry.conflicts.iter().any(|c| {
                c.rule == AttachmentRule::DerivationalRoot && c.morpheme_index == Some(0)
            }));
        }
        for (mode, expected) in [
            (DictionaryFilter::Headword, has_heads),
            (
                DictionaryFilter::Compatible,
                has_heads && !identity_conflict,
            ),
        ] {
            let mut filtered = raw.clone();
            let mut native = annotation.clone();
            native.filter(&mut filtered, mode);
            assert_eq!(
                filtered.analyses.iter().any(|a| matches(a, &case)),
                expected,
                "{}: {mode:?}",
                case["id"]
            );
        }
    }
    assert_eq!((missing, conflicts), (60, 10));
    // The individual derivational conflict must not affect ordinary noun use.
    let word = engine.analyze_word("속에는").unwrap();
    let native = dictionary.annotate(&word).unwrap();
    assert!(word.analyses.iter().zip(&native.readings).any(|(a, r)| {
        a.lemmas[0].text == "속"
            && a.lemmas[0].kind == LemmaKind::Nominal
            && r.status == Compatibility::Compatible
    }));
}

#[test]
fn all_prior_candidates_native_slots_assessments_and_order_survive_every_cache_budget() {
    let file = Fixture::new("retained");
    let db = SqliteDictionary::open(&file.0).unwrap();
    for budget in [0, 1, 4096] {
        let mut words = Session::new(Arc::new(Lemmatizer::new()), budget);
        let mut dictionary = DictionarySession::new(&db, 4 * 1024 * 1024);
        for (surface, value) in source()["before_case_words"].as_object().unwrap() {
            let old: WordAnalysis = serde_json::from_value(value.clone()).unwrap();
            let annotation: Annotation =
                serde_json::from_value(value["dictionary"].clone()).unwrap();
            let current = words.analyze_word(surface).unwrap();
            assert_eq!(
                current
                    .analyses
                    .iter()
                    .filter(|a| old.analyses.contains(a))
                    .cloned()
                    .collect::<Vec<_>>(),
                old.analyses,
                "{surface}, cache {budget}"
            );
            let native = dictionary.annotate(&current).unwrap();
            for (i, a) in old.analyses.iter().enumerate() {
                let j = current.analyses.iter().position(|b| b == a).unwrap();
                assert_eq!(
                    native.readings[j], annotation.readings[i],
                    "{surface}, cache {budget}"
                );
            }
            for slot in annotation.lemmas {
                assert!(native.lemmas.contains(&slot), "{surface}: old native slot");
            }
            assert_eq!(
                *words
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap(),
                *current,
                "{surface}, cache {budget}"
            );
        }
    }
}

#[test]
fn suffix_class_survives_negation_and_does_not_borrow_an_unrelated_base_pos() {
    let engine = Lemmatizer::new();
    for (word, base, kind) in [
        ("타도되어있다", "타도", LemmaKind::Nominal),
        ("고되지않았다", "고", LemmaKind::Root),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| a.lemmas.len() == 2
                && a.lemmas[0].text == base
                && a.lemmas[0].kind == kind
                && a.morphemes
                    .first()
                    .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "되다")),
            "{word}"
        );
    }
    let result = engine.analyze_word("고되어있다").unwrap();
    assert!(!result.analyses.iter().any(|a| {
        a.lemmas
            .first()
            .is_some_and(|l| l.text == "고" && l.kind == LemmaKind::Root)
            && a.lemmas
                .iter()
                .any(|l| l.text == "있다" && l.kind == LemmaKind::Auxiliary)
            && a.rules.iter().any(|r| r == "suffix.adjective.doeda")
    }));
    let mut malformed = engine
        .analyze_word("고돼요")
        .unwrap()
        .analyses
        .into_iter()
        .find(|a| a.rules.iter().any(|r| r == "suffix.adjective.doeda"))
        .unwrap();
    malformed.lemmas[0].kind = LemmaKind::Nominal;
    assert!(malformed.breakdown().is_none());
}

#[test]
fn dictionary_bare_inflection_belongs_to_suffix_after_a_nominal_base() {
    let file = Fixture::new("bare-inflection");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut word = Lemmatizer::new().analyze_word("거짓되다").unwrap();
    word.analyses
        .retain(|a| a.rules.iter().any(|r| r == "suffix.adjective.doeda"));
    assert_eq!(word.analyses.len(), 1);
    // Externally supplied analyses can be displayable while violating an
    // attachment class. The noun entry cannot hide the derived owner's
    // bare verbal ending, and the conflict must point to that ending.
    word.analyses[0].morphemes[1].form = "는다".into();
    assert!(word.analyses[0].breakdown().is_some());
    let native = dictionary.annotate(&word).unwrap();
    assert_eq!(native.readings[0].status, Compatibility::Incompatible);
    assert!(
        native.readings[0].lemmas[0].entries[0]
            .conflicts
            .iter()
            .any(|c| {
                c.rule == AttachmentRule::PresentDeclarativeVerb && c.morpheme_index == Some(1)
            })
    );
}

#[test]
fn cli_library_filters_and_unicode_retain_the_observed_overthrow_reading() {
    let file = Fixture::new("cli");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4 * 1024 * 1024);
    for word in [
        "타도되었다",
        "고돼요",
        "가결됨이다",
        "거짓되는",
        "못돼요",
        "가공되어있다",
        "한갓된",
        "이룩되었다",
        "속된",
        "속에는",
    ] {
        for surface in [word.to_owned(), word.nfd().collect()] {
            let raw = Lemmatizer::new().analyze_word(&surface).unwrap();
            for (flag, policy) in [
                (None, None),
                (Some("--dict-only"), Some(DictionaryFilter::Headword)),
                (
                    Some("--dict-compatible"),
                    Some(DictionaryFilter::Compatible),
                ),
            ] {
                let mut expected = raw.clone();
                let mut annotation = dictionary.annotate(&expected).unwrap();
                if let Some(policy) = policy {
                    annotation.filter(&mut expected, policy);
                }
                let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
                command
                    .args(["word", &surface, "--dictionary"])
                    .arg(&file.0);
                if let Some(flag) = flag {
                    command.arg(flag);
                }
                let output = command.output().unwrap();
                assert!(output.status.success());
                let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
                assert_eq!(
                    serde_json::from_value::<WordAnalysis>(actual.clone()).unwrap(),
                    expected,
                    "{word}: {flag:?}"
                );
                assert_eq!(
                    actual["dictionary"],
                    serde_json::to_value(annotation).unwrap()
                );
                if word == "타도되었다" {
                    assert!(expected.analyses.iter().any(|a| a.lemmas[0].text == "타도"
                        && a.rules.iter().any(|r| r == "suffix.verb.doeda")));
                }
            }
        }
    }
}
