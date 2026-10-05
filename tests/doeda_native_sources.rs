//! Native whole/noun origin pairs license finite suffix-owned verb hypotheses.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemma, LemmaKind, Lemmatizer, Morpheme, MorphemeKind, Session};
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
        serde_json::from_str(include_str!("fixtures/doeda-native-formations.json")).unwrap()
    })
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-doeda-native-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-native.json")],
            &path,
            "doeda-native-source-test",
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

fn cases() -> impl Iterator<Item = (String, String, Vec<Lemma>, Vec<Morpheme>)> {
    source()["formations"]
        .as_array()
        .unwrap()
        .iter()
        .flat_map(|formation| {
            source()["variants"]
                .as_array()
                .unwrap()
                .iter()
                .map(move |variant| {
                    let id = format!(
                        "{}-{}",
                        formation["id"].as_str().unwrap(),
                        variant["id"].as_str().unwrap()
                    );
                    let surface = format!(
                        "{}{}",
                        formation["base"].as_str().unwrap(),
                        variant["tail"].as_str().unwrap()
                    );
                    let mut lemmas = vec![Lemma {
                        text: formation["base"].as_str().unwrap().into(),
                        kind: LemmaKind::Nominal,
                    }];
                    if let Some(later) = variant.get("later_lemmas") {
                        lemmas.extend(serde_json::from_value::<Vec<Lemma>>(later.clone()).unwrap());
                    }
                    let mut morphemes = vec![Morpheme {
                        form: "되다".into(),
                        kind: MorphemeKind::Suffix,
                    }];
                    for (form, kind) in variant["morphemes"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .zip(variant["morpheme_kinds"].as_array().unwrap())
                    {
                        morphemes.push(Morpheme {
                            form: form.as_str().unwrap().into(),
                            kind: serde_json::from_value(kind.clone()).unwrap(),
                        });
                    }
                    (id, surface, lemmas, morphemes)
                })
        })
}

fn matches(a: &Analysis, lemmas: &[Lemma], morphemes: &[Morpheme]) -> bool {
    a.lemmas == lemmas
        && a.morphemes == morphemes
        && a.rules.iter().any(|r| r == "suffix.verb.doeda")
}

#[test]
fn all_native_origin_pairs_survive_the_real_importer() {
    let file = Fixture::new("origins");
    let db = SqliteDictionary::open(&file.0).unwrap();
    assert_eq!(source()["formations"].as_array().unwrap().len(), 1570);
    for f in source()["formations"].as_array().unwrap() {
        assert_eq!(
            (f["base_kind"].as_str(), f["predicate_class"].as_str()),
            (Some("nominal"), Some("verb"))
        );
        for owner in f["whole_entries"].as_array().unwrap() {
            let whole = db.entry(owner.as_str().unwrap()).unwrap().unwrap();
            assert_eq!(whole.summary.headword, f["head"]);
            assert_eq!(whole.summary.pos, "동사");
            assert!(
                f["matching_noun_entries"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|id| {
                        let noun = db.entry(id.as_str().unwrap()).unwrap().unwrap();
                        noun.summary.headword == f["base"]
                            && noun.summary.pos == "명사"
                            && whole.origins.iter().any(|o| {
                                o.strip_suffix("되다")
                                    .is_some_and(|origin| noun.origins.iter().any(|n| n == origin))
                            })
                    }),
                "{}",
                f["id"]
            );
        }
    }
}

#[test]
fn every_native_case_has_complete_owned_components_in_nfc_and_nfd() {
    let mut session = Session::new(Arc::new(Lemmatizer::new()), 4 * 1024 * 1024);
    let mut count = 0;
    for (id, surface, lemmas, morphemes) in cases() {
        let expected = session.analyze_word(&surface).unwrap();
        assert!(
            expected
                .analyses
                .iter()
                .any(|a| matches(a, &lemmas, &morphemes)),
            "{id}: {surface}"
        );
        for a in expected
            .analyses
            .iter()
            .filter(|a| matches(a, &lemmas, &morphemes))
        {
            use klem::breakdown::Component;
            let order = a.breakdown().expect("suffix owns inflections");
            assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len(), "{id}");
            assert_eq!(order[0], Component::Lemma(0));
            assert_eq!(order[1], Component::Morpheme(0));
            assert!(
                a.spelling_paths
                    .iter()
                    .flatten()
                    .all(|r| r.morpheme_index < a.morphemes.len()),
                "{id}"
            );
        }
        assert_eq!(
            *expected,
            *session
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap(),
            "{id}: NFD"
        );
        count += 1;
    }
    assert_eq!(count, 15700);
}

#[test]
fn all_native_cases_survive_both_dictionary_filters_with_matching_noun_evidence() {
    let file = Fixture::new("filters");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4 * 1024 * 1024);
    let engine = Lemmatizer::new();
    let mut count = 0;
    for (id, surface, lemmas, morphemes) in cases() {
        let word = engine.analyze_word(&surface).unwrap();
        let native = dictionary.annotate(&word).unwrap();
        let index = word
            .analyses
            .iter()
            .position(|a| matches(a, &lemmas, &morphemes))
            .unwrap_or_else(|| panic!("{id}: {surface}"));
        assert_eq!(
            native.readings[index].status,
            Compatibility::Compatible,
            "{id}"
        );
        for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut result = word.clone();
            let mut annotation = native.clone();
            annotation.filter(&mut result, mode);
            assert!(
                result
                    .analyses
                    .iter()
                    .any(|a| matches(a, &lemmas, &morphemes)),
                "{id}: {mode:?}"
            );
        }
        count += 1;
    }
    assert_eq!(count, 15700);
}
