//! COV-019ah preflight: retain source identities and every prior reading.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, Session};
use serde_json::Value;
use std::{fs, path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn evidence() -> Value {
    let mut source: Value =
        serde_json::from_str(include_str!("fixtures/doeda-complement-sources.json")).unwrap();
    let corrections: Value =
        serde_json::from_str(include_str!("fixtures/doeda-complement-corrections.json")).unwrap();
    for correction in corrections["corrections"].as_array().unwrap() {
        let cases = source["cases"].as_array_mut().unwrap();
        let index = cases
            .iter()
            .position(|case| *case == correction["original"])
            .unwrap();
        cases[index] = correction["replacement_control"].clone();
        cases.push(correction["replacement_positive"].clone());
    }
    let boundaries: Value = serde_json::from_str(include_str!(
        "fixtures/doeda-complement-bridge-boundaries.json"
    ))
    .unwrap();
    source["cases"]
        .as_array_mut()
        .unwrap()
        .extend(boundaries["cases"].as_array().unwrap().iter().cloned());
    for (surface, before) in corrections["before_additional_words"].as_object().unwrap() {
        source["before_case_words"]
            .as_object_mut()
            .unwrap()
            .insert(surface.clone(), before.clone());
    }
    source
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-doeda-complement-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-complement.json")],
            &path,
            "doeda-complement-source-test",
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
fn complete_native_sources_keep_negation_compounds_and_classifications_distinct() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    assert_eq!(fixture["cases"].as_array().unwrap().len(), 415);
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    for (id, headword, pos) in [
        ("krdict:89858", "되다", "동사"),
        ("krdict:48214", "되다", "형용사"),
        ("krdict:71372", "안", "부사"),
        ("krdict:74890", "안", "명사"),
        ("krdict:14773", "안", "명사"),
        ("krdict:73915", "안되다", "동사"),
        ("krdict:16005", "안되다", "형용사"),
    ] {
        let entry = db.entry(id).unwrap().unwrap();
        assert_eq!(entry.summary.headword, headword);
        assert_eq!(entry.summary.pos, pos);
    }
    let verb = db.entry("krdict:89858").unwrap().unwrap();
    assert_eq!(verb.senses.len(), 22);
    for id in ["17", "18", "19", "21"] {
        assert!(verb.senses.iter().any(|sense| sense.id == id));
    }
    assert!(!verb.senses.iter().any(|sense| sense.id == "20"));
    assert!(fixture["cases"].as_array().unwrap().iter().all(|case| {
        case["family"] != "scheduled-ki-ro"
            || case["morphemes"]
                .as_array()
                .unwrap()
                .starts_with(&[Value::String("기".into()), Value::String("로".into())])
    }));
}

#[test]
fn every_prior_case_candidate_and_native_reading_retains_order_under_unicode_and_caching() {
    let file = Fixture::new("retention");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let fixture = evidence();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for (surface, before) in fixture["before_case_words"].as_object().unwrap() {
            let current = session.analyze_word(surface).unwrap();
            assert_eq!(
                current,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            let annotation = dictionary.annotate(&current).unwrap();
            let prior: Vec<Analysis> =
                serde_json::from_value(before["analysis"]["analyses"].clone()).unwrap();
            let mut cursor = 0;
            for (index, old) in prior.iter().enumerate() {
                let position = current.analyses[cursor..]
                    .iter()
                    .position(|analysis| analysis == old)
                    .unwrap_or_else(|| panic!("{surface}: prior path lost: {old:?}"))
                    + cursor;
                assert_eq!(
                    serde_json::to_value(&annotation.readings[position]).unwrap(),
                    before["dictionary"]["readings"][index],
                    "{surface}: prior native assessment changed"
                );
                cursor = position + 1;
            }
            for slot in before["dictionary"]["lemmas"].as_array().unwrap() {
                assert!(
                    annotation
                        .lemmas
                        .iter()
                        .any(|current| { serde_json::to_value(current).unwrap() == *slot }),
                    "{surface}: prior native slot changed"
                );
            }
            for analysis in &current.analyses {
                assert!(analysis.breakdown().is_some(), "{surface}: {analysis:?}");
                assert!(
                    analysis
                        .rules
                        .iter()
                        .all(|rule| klem::rule_explanation(rule).is_some())
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
fn every_source_listed_construction_keeps_roles_negation_and_native_owners() {
    let fixture = evidence();
    let file = Fixture::new("construction");
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
                "{}: {surface}: {word:?}",
                case["id"]
            );
            for i in indices {
                let path = &word.analyses[i];
                let right = path.lemmas.iter().position(|l| l.text == "되다").unwrap();
                let assessments = &native.readings[i].lemmas[right].entries;
                assert!(
                    assessments.iter().any(|e| e.id == "krdict:89858"
                        && e.status
                            == if path.lemmas[right].kind == LemmaKind::Predicate {
                                Compatibility::Compatible
                            } else {
                                // Native KRDict calls these senses verbs. Retain
                                // that role conflict on the separate NIKL reading.
                                Compatibility::Incompatible
                            }),
                    "{surface}: {assessments:?}"
                );
                if path.lemmas[right].kind == LemmaKind::Predicate {
                    assert_eq!(
                        assessments
                            .iter()
                            .find(|e| e.id == "krdict:48214")
                            .unwrap()
                            .status,
                        Compatibility::Incompatible,
                        "{surface}"
                    );
                }
                if let Some(negative) = path.lemmas.iter().position(|l| l.text == "안") {
                    assert_eq!(path.lemmas[negative].kind, LemmaKind::Adverbial);
                    assert!(
                        native.readings[i].lemmas[negative]
                            .entries
                            .iter()
                            .any(
                                |e| e.id == "krdict:71372" && e.status == Compatibility::Compatible
                            )
                    );
                }
                assert!(path.breakdown().is_some(), "{surface}: {path:?}");
                assert!(
                    path.rules
                        .iter()
                        .all(|r| klem::rule_explanation(r).is_some())
                );
            }
            for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = word.as_ref().clone();
                let mut annotation = native.clone();
                annotation.filter(&mut filtered, filter);
                assert_eq!(
                    filtered.analyses.iter().any(|a| matches(a, case)),
                    case["verdict"] == "required"
                        && (filter == DictionaryFilter::Headword
                            || !case["lemma_kinds"]
                                .as_array()
                                .unwrap()
                                .iter()
                                .zip(case["lemmas"].as_array().unwrap())
                                .any(|(kind, head)| *kind == "auxiliary" && *head == "되다")),
                    "{surface}: {filter:?}"
                );
            }
        }
    }
}

#[test]
fn mixed_connectors_keep_all_roles_and_each_links_own_provenance() {
    use std::collections::BTreeSet;
    let word = Lemmatizer::new()
        .analyze_word("먹게되어야되면안되게끔되었다")
        .unwrap();
    let mut roles = BTreeSet::new();
    for a in word.analyses.iter().filter(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["먹다", "되다", "되다", "안", "되다", "되다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["게", "어야", "으면", "게끔", "었", "다"])
    }) {
        let kinds: Vec<_> = [1, 2, 4, 5].map(|i| a.lemmas[i].kind).into();
        assert!(a.breakdown().is_some());
        assert_eq!(a.lemmas[3].kind, LemmaKind::Adverbial);
        assert_eq!(
            a.rules.iter().any(|r| r == "lexical.doeda.complement"),
            [1, 5]
                .iter()
                .any(|&i| a.lemmas[i].kind == LemmaKind::Predicate)
        );
        assert_eq!(
            a.rules.iter().any(|r| r == "lexical.doeda.extended"),
            [2, 4]
                .iter()
                .any(|&i| a.lemmas[i].kind == LemmaKind::Predicate)
        );
        assert_eq!(
            a.rules.iter().any(|r| r == "auxiliary.doeda.extended"),
            [2, 4]
                .iter()
                .any(|&i| a.lemmas[i].kind == LemmaKind::Auxiliary)
        );
        roles.insert(kinds);
    }
    assert_eq!(roles.len(), 16, "{roles:?}");
    // A negative adverb is a bridge only before a reviewed 되다 complement.
    // No stand-alone adverb prefix or arbitrary connective license is inferred.
    for surface in [
        "먹고안된다",
        "먹어안된다",
        "먹도록안본다",
        "먹기로안한다",
        "안된다",
        "안되다",
        "안되겠지만",
        "안되고",
        "안되면싶다",
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        assert!(
            word.analyses
                .iter()
                .all(|a| !a.rules.iter().any(|r| r == "doeda.negative_bridge")),
            "{surface}: {word:?}"
        );
    }
}

#[test]
fn cli_outputs_keep_complete_native_readings_and_filter_order() {
    let fixture = evidence();
    let file = Fixture::new("cli");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let surfaces: std::collections::BTreeSet<_> = fixture["cases"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["surface"].as_str().unwrap())
        .collect();
    for surface in surfaces {
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
            for input in [surface.to_owned(), surface.nfd().collect()] {
                let mut command = std::process::Command::new(env!("CARGO_BIN_EXE_klem"));
                command.args(["word", &input, "--dictionary"]).arg(&file.0);
                if let Some(f) = filter {
                    command.arg(if f == DictionaryFilter::Headword {
                        "--dict-only"
                    } else {
                        "--dict-compatible"
                    });
                }
                let output = command.output().unwrap();
                assert!(output.status.success(), "{surface}: {:?}", output.stderr);
                let mut actual: Value = serde_json::from_slice(&output.stdout).unwrap();
                assert_eq!(
                    actual
                        .as_object_mut()
                        .unwrap()
                        .remove("dictionary")
                        .unwrap(),
                    serde_json::to_value(&annotation).unwrap()
                );
                assert_eq!(actual, serde_json::to_value(&expected).unwrap());
            }
        }
    }
}
