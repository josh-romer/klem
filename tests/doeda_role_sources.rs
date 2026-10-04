//! COV-019ag: attributed lexical alternatives and historical role retention.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, Session};
use serde_json::Value;
use std::{collections::BTreeSet, fs, path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/doeda-role-sources.json")).unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-doeda-role-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-role.json")],
            &path,
            "doeda-role-source-test",
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

#[test]
fn complete_case_native_entries_preserve_distinct_verb_and_adjective() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    assert_eq!(fixture["cases"].as_array().unwrap().len(), 81);
    assert_eq!(fixture["source_entries"].as_array().unwrap().len(), 35);
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    let verb = db.entry("krdict:89858").unwrap().unwrap();
    let adjective = db.entry("krdict:48214").unwrap().unwrap();
    assert_eq!(verb.summary.pos, "동사");
    assert_eq!(adjective.summary.pos, "형용사");
    assert_eq!(verb.senses.len(), 22);
    assert!(verb.senses.iter().any(|s| s.id == "23"));
    assert!(!verb.senses.iter().any(|s| s.id == "20"));
}

#[test]
fn prior_paths_readings_and_order_survive_unicode_and_cache_variants() {
    let file = Fixture::new("retention");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for (surface, before) in fixture["before_case_words"].as_object().unwrap() {
            let word = session.analyze_word(surface).unwrap();
            assert_eq!(
                word,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            let annotation = dictionary.annotate(&word).unwrap();
            let original: Vec<Analysis> =
                serde_json::from_value(before["analysis"]["analyses"].clone()).unwrap();
            let readings = before["dictionary"]["readings"].as_array().unwrap();
            let mut cursor = 0;
            for (index, prior) in original.iter().enumerate() {
                let position = word.analyses[cursor..]
                    .iter()
                    .position(|a| a == prior)
                    .unwrap_or_else(|| panic!("{surface}: historical path lost: {prior:?}"))
                    + cursor;
                assert_eq!(
                    serde_json::to_value(&annotation.readings[position]).unwrap(),
                    readings[index],
                    "{surface}: historical native reading changed"
                );
                cursor = position + 1;
            }
            for analysis in &word.analyses {
                assert!(analysis.breakdown().is_some(), "{surface}: {analysis:?}");
                assert!(
                    analysis
                        .rules
                        .iter()
                        .all(|r| klem::rule_explanation(r).is_some())
                );
            }
        }
    }
}

fn matches(analysis: &Analysis, case: &Value) -> bool {
    serde_json::to_value(analysis.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == case["lemmas"]
        && serde_json::to_value(analysis.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == case["lemma_kinds"]
        && serde_json::to_value(
            analysis
                .morphemes
                .iter()
                .map(|m| &m.form)
                .collect::<Vec<_>>(),
        )
        .unwrap()
            == case["morphemes"]
        && serde_json::to_value(
            analysis
                .morphemes
                .iter()
                .map(|m| m.kind)
                .collect::<Vec<_>>(),
        )
        .unwrap()
            == case["morpheme_kinds"]
        && case["required_rules"].as_array().unwrap().iter().all(|r| {
            analysis
                .rules
                .iter()
                .any(|actual| actual == r.as_str().unwrap())
        })
}

#[test]
fn attributed_lexical_paths_pass_filters_without_borrowing_adjective_senses() {
    let fixture = evidence();
    let file = Fixture::new("alternatives");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for case in fixture["cases"].as_array().unwrap() {
            let surface = case["surface"].as_str().unwrap();
            let word = session.analyze_word(surface).unwrap();
            assert_eq!(
                word,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            let native = dictionary.annotate(&word).unwrap();
            let indices: Vec<_> = word
                .analyses
                .iter()
                .enumerate()
                .filter(|(_, a)| matches(a, case))
                .map(|(i, _)| i)
                .collect();
            assert_eq!(
                !indices.is_empty(),
                case["verdict"] == "required",
                "{surface}: {word:?}"
            );
            for i in indices {
                let path = &word.analyses[i];
                let right = path
                    .lemmas
                    .iter()
                    .position(|l| l.kind == LemmaKind::Predicate && l.text == "되다")
                    .unwrap();
                let assessments = &native.readings[i].lemmas[right].entries;
                assert!(
                    assessments
                        .iter()
                        .any(|e| e.id == "krdict:89858" && e.status == Compatibility::Compatible),
                    "{surface}: {assessments:?}"
                );
                let adjective = assessments.iter().find(|e| e.id == "krdict:48214").unwrap();
                assert_eq!(adjective.status, Compatibility::Incompatible, "{surface}");
                assert!(!adjective.conflicts.is_empty());
            }
            for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = word.as_ref().clone();
                let mut annotation = native.clone();
                annotation.filter(&mut filtered, filter);
                assert_eq!(
                    filtered.analyses.iter().any(|a| matches(a, case)),
                    case["verdict"] == "required",
                    "{surface}: {filter:?}"
                );
            }
        }
        // Scope is the joined lexical construction. The standalone adjective
        // homonym remains a possible dictionary interpretation of 되다.
        let word = session.analyze_word("되다").unwrap();
        let native = dictionary.annotate(&word).unwrap();
        assert!(word.analyses.iter().zip(&native.readings).any(|(a, r)| {
            a.lemmas.len() == 1
                && a.lemmas[0].kind == LemmaKind::Predicate
                && r.lemmas[0]
                    .entries
                    .iter()
                    .any(|e| e.id == "krdict:48214" && e.status == Compatibility::Compatible)
        }));
    }
}

#[test]
fn repeated_doeda_owners_offer_every_independent_role_combination() {
    let word = Lemmatizer::new()
        .analyze_word("먹게되게끔되게되었다")
        .unwrap();
    let roles: BTreeSet<_> = word
        .analyses
        .iter()
        .filter(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["먹다", "되다", "되다", "되다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["게", "게끔", "게", "었", "다"])
        })
        .map(|a| a.lemmas.iter().skip(1).map(|l| l.kind).collect::<Vec<_>>())
        .collect();
    let expected: BTreeSet<_> = [LemmaKind::Predicate, LemmaKind::Auxiliary]
        .into_iter()
        .flat_map(|a| {
            [LemmaKind::Predicate, LemmaKind::Auxiliary]
                .into_iter()
                .flat_map(move |b| {
                    [LemmaKind::Predicate, LemmaKind::Auxiliary]
                        .into_iter()
                        .map(move |c| vec![a, b, c])
                })
        })
        .collect();
    assert_eq!(roles, expected);
}

#[test]
fn central_judgments_and_cli_filters_agree_with_library_roles() {
    let file = Fixture::new("central");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let fixture = evidence();
    for (path, policy) in [
        ("tests/fixtures/validity.json", false),
        ("tests/fixtures/dictionary-attachments.json", true),
    ] {
        let mut suite: validity::Suite =
            serde_json::from_str(&fs::read_to_string(path).unwrap()).unwrap();
        suite.cases.retain(|c| c.id.starts_with("doeda-role-"));
        if policy {
            for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let report = validity::evaluate_with(&suite, |surface| {
                    let mut word = engine.analyze_word(surface).unwrap();
                    let mut native = dictionary.annotate(&word).unwrap();
                    native.filter(&mut word, filter);
                    Ok(word)
                })
                .unwrap();
                assert_eq!((report.required_total, report.forbidden_total), (78, 3));
                assert!(report.passed(), "{filter:?}: {:?}", report.violations);
            }
        } else {
            let report = validity::evaluate(&suite).unwrap();
            assert_eq!((report.required_total, report.forbidden_total), (78, 3));
            assert!(report.passed(), "{:?}", report.violations);
        }
    }
    for case in fixture["cases"].as_array().unwrap() {
        let surface = case["surface"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        let native = dictionary.annotate(&word).unwrap();
        for filter in [
            None,
            Some(DictionaryFilter::Headword),
            Some(DictionaryFilter::Compatible),
        ] {
            let mut expected = word.clone();
            let mut annotation = native.clone();
            if let Some(f) = filter {
                annotation.filter(&mut expected, f);
            }
            let mut command = std::process::Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", surface, "--dictionary"]).arg(&file.0);
            if let Some(f) = filter {
                command.arg(if f == DictionaryFilter::Headword {
                    "--dict-only"
                } else {
                    "--dict-compatible"
                });
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let mut actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(annotation).unwrap()
            );
            assert_eq!(actual, serde_json::to_value(expected).unwrap());
        }
    }
}
