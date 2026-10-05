//! Recorded whole-head origins must not fill absent noun-origin fields.
use klem::breakdown::Component;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, OriginRelation,
    SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemma, LemmaKind, Lemmatizer, Morpheme, Session};
use serde_json::Value;
use std::{
    fs,
    path::PathBuf,
    sync::{Arc, OnceLock},
};
use unicode_normalization::UnicodeNormalization;

fn source() -> &'static Value {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    SOURCE.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/doeda-partial-origin-sources.json")).unwrap()
    })
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-doeda-partial-origin-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-doeda-partial-origin.json",
            )],
            &path,
            "doeda-partial-origin-source-test",
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

fn matches(a: &Analysis, case: &Value) -> bool {
    a.lemmas == serde_json::from_value::<Vec<Lemma>>(case["lemmas"].clone()).unwrap()
        && a.morphemes
            == serde_json::from_value::<Vec<Morpheme>>(case["morphemes"].clone()).unwrap()
        && a.rules
            .iter()
            .any(|r| r == case["required_rule"].as_str().unwrap())
}

#[test]
fn native_semantic_links_retain_recorded_and_missing_origins_separately() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    assert_eq!(source()["formations"].as_array().unwrap().len(), 2);
    assert!(
        source()["corpus_occurrences"]
            .as_array()
            .unwrap()
            .is_empty()
    );
    for f in source()["formations"].as_array().unwrap() {
        let noun = db
            .entry(f["noun_entries"][0].as_str().unwrap())
            .unwrap()
            .unwrap();
        assert_eq!(noun.summary.pos, "명사");
        assert_eq!(noun.summary.headword, f["base"].as_str().unwrap());
        assert!(noun.origins.is_empty());
        let origin = f["expected_origins"][0].as_str().unwrap();
        for (field, head, ending) in [
            ("whole_entries", f["head"].as_str().unwrap(), "되다"),
            ("paired_hada_entries", "", "하다"),
        ] {
            let entry = db.entry(f[field][0].as_str().unwrap()).unwrap().unwrap();
            assert_eq!(entry.summary.pos, "동사");
            assert_eq!(
                entry.summary.headword,
                if head.is_empty() {
                    format!("{}{ending}", noun.summary.headword)
                } else {
                    head.into()
                }
            );
            assert_eq!(entry.origins, vec![format!("{origin}{ending}")]);
        }
        for evidence in f["semantic_evidence"].as_array().unwrap() {
            let entry = db
                .entry(evidence["entry"].as_str().unwrap())
                .unwrap()
                .unwrap();
            let sense = entry
                .senses
                .iter()
                .find(|s| s.id == evidence["sense"].as_str().unwrap())
                .unwrap();
            assert_eq!(sense.definition, evidence["definition"].as_str().unwrap());
        }
    }
}

#[test]
fn prior_candidates_and_whole_parent_component_order_survive() {
    let engine = Lemmatizer::new();
    for (surface, before) in source()["before_words"].as_object().unwrap() {
        let prior: Vec<Analysis> = serde_json::from_value(before["analyses"].clone()).unwrap();
        let current = engine.analyze_word(surface).unwrap();
        assert_eq!(
            current
                .analyses
                .iter()
                .filter(|a| prior.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            prior,
            "{surface}"
        );
    }
    assert_eq!(source()["cases"].as_array().unwrap().len(), 20);
    for case in source()["cases"].as_array().unwrap() {
        let surface = case["surface"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        let derived = word
            .analyses
            .iter()
            .find(|a| matches(a, case))
            .unwrap_or_else(|| panic!("{}", case["id"]));
        let whole_lemmas: Vec<Lemma> =
            serde_json::from_value(case["original_whole_lemmas"].clone()).unwrap();
        let whole = word
            .analyses
            .iter()
            .find(|a| a.lemmas == whole_lemmas && a.morphemes == derived.morphemes[1..])
            .unwrap();
        let original_order = whole.breakdown().unwrap();
        assert_eq!(original_order[0], Component::Lemma(0));
        let mut expected = vec![Component::Lemma(0), Component::Morpheme(0)];
        expected.extend(original_order.into_iter().skip(1).map(|c| match c {
            Component::Lemma(i) => Component::Lemma(i),
            Component::Morpheme(i) => Component::Morpheme(i + 1),
        }));
        assert_eq!(derived.breakdown().unwrap(), expected, "{}", case["id"]);
    }
}

#[test]
fn every_case_has_unknown_identity_and_unicode_cache_filter_parity() {
    let file = Fixture::new("filters");
    let db = SqliteDictionary::open(&file.0).unwrap();
    for budget in [0, 1, 1024, 4 * 1024 * 1024] {
        let mut session = Session::new(Arc::new(Lemmatizer::new()), budget);
        let mut dictionary = DictionarySession::new(&db, budget);
        for case in source()["cases"].as_array().unwrap() {
            let surface = case["surface"].as_str().unwrap();
            let nfc = session.analyze_word(surface).unwrap();
            let nfd = session
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap();
            assert_eq!(nfc, nfd, "{}: {budget}", case["id"]);
            let annotated = dictionary.annotate(&nfc).unwrap();
            assert_eq!(annotated, dictionary.annotate(&nfd).unwrap());
            let index = nfc.analyses.iter().position(|a| matches(a, case)).unwrap();
            let f = source()["formations"]
                .as_array()
                .unwrap()
                .iter()
                .find(|f| f["id"] == case["formation_id"])
                .unwrap();
            let reading = &annotated.readings[index];
            assert_eq!(reading.status, Compatibility::Compatible);
            let entry = reading.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == f["noun_entries"][0].as_str().unwrap())
                .unwrap();
            let noun_slot = annotated
                .lemmas
                .iter()
                .find(|l| l.lemma == nfc.analyses[index].lemmas[0])
                .unwrap();
            let native_entry = noun_slot
                .entries
                .iter()
                .find(|e| e.entry.id == entry.id)
                .unwrap();
            assert_eq!(native_entry.origins, Some(vec![]));
            let identity = entry.derivational_identity.as_ref().unwrap();
            assert_eq!(identity.relation, OriginRelation::Unknown);
            assert!(identity.whole_origins_complete);
            assert_eq!(
                serde_json::to_value(&identity.expected_origins).unwrap(),
                f["expected_origins"]
            );
            assert_eq!(
                serde_json::to_value(&identity.whole_entries).unwrap(),
                f["whole_entries"]
            );
            assert_eq!(identity.morpheme_index, 0);
            for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = (*nfc).clone();
                let mut annotations = annotated.clone();
                annotations.filter(&mut filtered, mode);
                assert!(
                    filtered.analyses.iter().any(|a| matches(a, case)),
                    "{}: {mode:?}",
                    case["id"]
                );
            }
        }
        // Cache warming with known whole origins must not invent noun origins
        // or derivational metadata on an ordinary noun.
        for f in source()["formations"].as_array().unwrap() {
            let word = session.analyze_word(f["base"].as_str().unwrap()).unwrap();
            let annotated = dictionary.annotate(&word).unwrap();
            assert!(
                annotated
                    .lemmas
                    .iter()
                    .filter(|l| l.lemma.kind == LemmaKind::Nominal)
                    .flat_map(|l| &l.entries)
                    .all(|e| e.origins.is_none())
            );
            assert!(
                annotated
                    .readings
                    .iter()
                    .flat_map(|r| &r.lemmas)
                    .flat_map(|l| &l.entries)
                    .all(|e| e.derivational_identity.is_none())
            );
        }
    }
}

#[test]
fn unrelated_nouns_keep_whole_readings_without_a_suffix_link() {
    let engine = Lemmatizer::new();
    assert_eq!(source()["controls"].as_array().unwrap().len(), 20);
    for case in source()["controls"].as_array().unwrap() {
        let surface = case["surface"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        let base = case["base"].as_str().unwrap();
        assert!(
            !word.analyses.iter().any(|a| a
                .lemmas
                .first()
                .is_some_and(|l| l.kind == LemmaKind::Nominal && l.text == base)
                && a.rules
                    .iter()
                    .any(|r| r == case["forbidden_rule"].as_str().unwrap())),
            "{}",
            case["id"]
        );
        assert!(
            word.analyses.iter().any(|a| {
                a.lemmas.first().is_some_and(|l| {
                    l.kind == LemmaKind::Predicate && l.text == format!("{base}되다")
                })
            }),
            "{}",
            case["id"]
        );
    }
}

#[test]
fn later_auxiliaries_preserve_the_parent_and_component_owners() {
    let engine = Lemmatizer::new();
    for f in source()["formations"].as_array().unwrap() {
        for (tail, auxiliary) in [
            ("되지않았다", "않다"),
            ("되어버렸다", "버리다"),
            ("되어있다", "있다"),
        ] {
            let surface = format!("{}{}", f["base"].as_str().unwrap(), tail);
            let word = engine.analyze_word(&surface).unwrap();
            let derived = word
                .analyses
                .iter()
                .find(|a| {
                    a.lemmas.len() == 2
                        && a.lemmas[0].text == f["base"].as_str().unwrap()
                        && a.lemmas[0].kind == LemmaKind::Nominal
                        && a.lemmas[1].text == auxiliary
                        && a.lemmas[1].kind == LemmaKind::Auxiliary
                        && a.rules.iter().any(|r| r == "suffix.verb.doeda")
                })
                .unwrap_or_else(|| panic!("{surface}"));
            assert!(
                word.analyses.iter().any(|a| a.lemmas.len() == 2
                    && a.lemmas[0].text == f["head"].as_str().unwrap()
                    && a.lemmas[0].kind == LemmaKind::Predicate
                    && a.lemmas[1] == derived.lemmas[1]
                    && a.morphemes == derived.morphemes[1..]),
                "{surface}"
            );
            assert_eq!(
                &derived.breakdown().unwrap()[..4],
                &[
                    Component::Lemma(0),
                    Component::Morpheme(0),
                    Component::Morpheme(1),
                    Component::Lemma(1)
                ],
                "{surface}"
            );
        }
    }
}
