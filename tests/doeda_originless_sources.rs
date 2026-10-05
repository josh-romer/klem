//! Finite semantic links and original tagged contexts, with unknown origin identity.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, OriginRelation,
    SqliteDictionary, import_krdict,
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
        serde_json::from_str(include_str!("fixtures/doeda-originless-formations.json")).unwrap()
    })
}
fn before() -> &'static Value {
    static BEFORE: OnceLock<Value> = OnceLock::new();
    BEFORE.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/doeda-originless-before.json")).unwrap()
    })
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-doeda-originless-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-originless.json")],
            &path,
            "doeda-originless-source-test",
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

fn cases() -> Vec<(String, String, Vec<Lemma>, Vec<Morpheme>)> {
    let mut result = Vec::new();
    for f in source()["formations"].as_array().unwrap() {
        for v in source()["variants"].as_array().unwrap() {
            let id = format!(
                "{}-{}",
                f["id"].as_str().unwrap(),
                v["id"].as_str().unwrap()
            );
            let surface = format!(
                "{}{}",
                f["base"].as_str().unwrap(),
                v["tail"].as_str().unwrap()
            );
            let mut lemmas = vec![Lemma {
                text: f["base"].as_str().unwrap().into(),
                kind: LemmaKind::Nominal,
            }];
            if let Some(later) = v.get("later_lemmas") {
                lemmas.extend(serde_json::from_value::<Vec<Lemma>>(later.clone()).unwrap());
            }
            let mut morphs = vec![Morpheme {
                form: "되다".into(),
                kind: MorphemeKind::Suffix,
            }];
            for (form, kind) in v["morphemes"]
                .as_array()
                .unwrap()
                .iter()
                .zip(v["morpheme_kinds"].as_array().unwrap())
            {
                morphs.push(Morpheme {
                    form: form.as_str().unwrap().into(),
                    kind: serde_json::from_value(kind.clone()).unwrap(),
                });
            }
            result.push((id, surface, lemmas, morphs));
        }
    }
    result
}

fn matches(a: &Analysis, lemmas: &[Lemma], morphs: &[Morpheme]) -> bool {
    a.lemmas == lemmas && a.morphemes == morphs && a.rules.iter().any(|r| r == "suffix.verb.doeda")
}

#[test]
fn source_links_survive_the_production_importer_without_origins() {
    let file = Fixture::new("source");
    let db = SqliteDictionary::open(&file.0).unwrap();
    assert_eq!(source()["formations"].as_array().unwrap().len(), 17);
    for f in source()["formations"].as_array().unwrap() {
        for (field, pos, head) in [
            ("whole_entries", "동사", &f["head"]),
            ("noun_entries", "명사", &f["base"]),
        ] {
            for id in f[field].as_array().unwrap() {
                let entry = db.entry(id.as_str().unwrap()).unwrap().unwrap();
                assert_eq!(entry.summary.headword, head.as_str().unwrap());
                assert_eq!(entry.summary.pos, pos);
                assert!(entry.origins.is_empty());
                for evidence in f["semantic_evidence"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .filter(|e| e["entry"] == *id)
                {
                    let sense = entry
                        .senses
                        .iter()
                        .find(|s| s.id == evidence["sense"].as_str().unwrap())
                        .unwrap();
                    assert_eq!(sense.definition, evidence["definition"].as_str().unwrap());
                }
            }
        }
    }
}

#[test]
fn all_prior_candidates_and_whole_heads_keep_their_order() {
    let engine = Lemmatizer::new();
    for (surface, old) in before()["before_words"].as_object().unwrap() {
        let prior: Vec<Analysis> = serde_json::from_value(old["analyses"].clone()).unwrap();
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
    for (id, surface, lemmas, morphs) in cases() {
        let word = engine.analyze_word(&surface).unwrap();
        let added = word
            .analyses
            .iter()
            .find(|a| matches(a, &lemmas, &morphs))
            .unwrap_or_else(|| panic!("{id}"));
        let order = added.breakdown().expect("suffix-owned display");
        assert_eq!(
            order.len(),
            added.lemmas.len() + added.morphemes.len(),
            "{id}"
        );
        assert_eq!(order[0], klem::breakdown::Component::Lemma(0));
        assert_eq!(order[1], klem::breakdown::Component::Morpheme(0));
        assert!(
            added
                .spelling_paths
                .iter()
                .flatten()
                .all(|r| r.morpheme_index < added.morphemes.len()),
            "{id}"
        );
    }
}

#[test]
fn all_cases_keep_unicode_cache_filter_parity_and_unknown_identity() {
    let file = Fixture::new("filters");
    let db = SqliteDictionary::open(&file.0).unwrap();
    for budget in [0, 1, 1024, 4 * 1024 * 1024] {
        let mut session = Session::new(Arc::new(Lemmatizer::new()), budget);
        let mut dictionary = DictionarySession::new(&db, budget);
        for (id, surface, lemmas, morphs) in cases() {
            let nfc = session.analyze_word(&surface).unwrap();
            let nfd = session
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap();
            assert_eq!(nfc, nfd, "{id}: {budget}");
            let annotation = dictionary.annotate(&nfc).unwrap();
            assert_eq!(annotation, dictionary.annotate(&nfd).unwrap(), "{id}");
            let index = nfc
                .analyses
                .iter()
                .position(|a| matches(a, &lemmas, &morphs))
                .unwrap();
            let reading = &annotation.readings[index];
            assert_eq!(reading.status, Compatibility::Compatible, "{id}");
            let f = source()["formations"]
                .as_array()
                .unwrap()
                .iter()
                .find(|f| f["base"] == lemmas[0].text)
                .unwrap();
            let noun_id = f["noun_entries"][0].as_str().unwrap();
            let entry = reading.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == noun_id)
                .unwrap();
            let identity = entry
                .derivational_identity
                .as_ref()
                .expect("missing origin is explicitly unknown");
            assert_eq!(identity.relation, OriginRelation::Unknown, "{id}");
            assert!(identity.expected_origins.is_empty() && !identity.whole_origins_complete);
            assert_eq!(
                serde_json::to_value(&identity.whole_entries).unwrap(),
                f["whole_entries"]
            );
            assert_eq!(identity.morpheme_index, 0);
            for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = (*nfc).clone();
                let mut native = annotation.clone();
                native.filter(&mut filtered, mode);
                assert!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| matches(a, &lemmas, &morphs)),
                    "{id}: {mode:?}"
                );
            }
        }
        for f in source()["formations"].as_array().unwrap() {
            let noun = session.analyze_word(f["base"].as_str().unwrap()).unwrap();
            let annotation = dictionary.annotate(&noun).unwrap();
            for slot in &annotation.lemmas {
                if slot.lemma.kind == LemmaKind::Nominal {
                    assert!(slot.entries.iter().all(|e| e.origins.is_none()));
                }
            }
            assert!(
                annotation
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
fn later_auxiliaries_keep_their_components_and_suffix_ownership() {
    let engine = Lemmatizer::new();
    for f in source()["formations"].as_array().unwrap() {
        let base = f["base"].as_str().unwrap();
        for (tail, auxiliary, connector, past) in [
            ("되지않았다", "않다", "지", true),
            ("되어버렸다", "버리다", "어", true),
            ("되어있다", "있다", "어", false),
        ] {
            let surface = format!("{base}{tail}");
            let lemmas = vec![
                Lemma {
                    text: base.into(),
                    kind: LemmaKind::Nominal,
                },
                Lemma {
                    text: auxiliary.into(),
                    kind: LemmaKind::Auxiliary,
                },
            ];
            let mut morphs = vec![
                Morpheme {
                    form: "되다".into(),
                    kind: MorphemeKind::Suffix,
                },
                Morpheme {
                    form: connector.into(),
                    kind: MorphemeKind::Ending,
                },
            ];
            if past {
                morphs.push(Morpheme {
                    form: "었".into(),
                    kind: MorphemeKind::Prefinal,
                });
            }
            morphs.push(Morpheme {
                form: "다".into(),
                kind: MorphemeKind::Ending,
            });
            let word = engine.analyze_word(&surface).unwrap();
            let derived = word
                .analyses
                .iter()
                .find(|a| matches(a, &lemmas, &morphs))
                .unwrap_or_else(|| panic!("{surface}"));
            let mut whole = lemmas.clone();
            whole[0] = Lemma {
                text: f["head"].as_str().unwrap().into(),
                kind: LemmaKind::Predicate,
            };
            assert!(
                word.analyses
                    .iter()
                    .any(|a| a.lemmas == whole && a.morphemes == morphs[1..]),
                "{surface}"
            );
            let order = derived.breakdown().unwrap();
            assert_eq!(
                &order[..4],
                &[
                    klem::breakdown::Component::Lemma(0),
                    klem::breakdown::Component::Morpheme(0),
                    klem::breakdown::Component::Morpheme(1),
                    klem::breakdown::Component::Lemma(1)
                ],
                "{surface}"
            );
        }
    }
}

#[test]
fn homographic_nouns_do_not_gain_unreviewed_suffix_roles() {
    let engine = Lemmatizer::new();
    for control in source()["controls"].as_array().unwrap() {
        for v in source()["variants"].as_array().unwrap() {
            let base = control["base"].as_str().unwrap();
            let surface = format!("{base}{}", v["tail"].as_str().unwrap());
            let word = engine.analyze_word(&surface).unwrap();
            assert!(
                !word.analyses.iter().any(|a| a
                    .lemmas
                    .first()
                    .is_some_and(|l| l.text == base && l.kind == LemmaKind::Nominal)
                    && a.morphemes
                        .first()
                        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "되다")
                    && a.rules.iter().any(|r| r == "suffix.verb.doeda")),
                "{surface}"
            );
        }
    }
    // The separately implemented adjective/adverb source role remains intact.
    assert!(
        engine
            .analyze_word("안됐어요")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas[0].text == "안"
                && a.lemmas[0].kind == LemmaKind::Adverbial
                && a.rules.iter().any(|r| r == "suffix.adjective.doeda"))
    );
}

#[test]
fn original_tagged_tokens_add_splits_without_replacing_whole_gold() {
    let engine = Lemmatizer::new();
    let mut supported = 0;
    let tokens = before()["corpus_occurrences"].as_array().unwrap();
    assert_eq!(tokens.len(), 52);
    for row in tokens {
        let Some(f) = source()["formations"]
            .as_array()
            .unwrap()
            .iter()
            .find(|f| f["head"] == row["head"])
        else {
            continue;
        };
        let word = engine
            .analyze_word(row["original_row"][1].as_str().unwrap())
            .unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas.first().is_some_and(
                    |l| l.text == f["head"].as_str().unwrap() && l.kind == LemmaKind::Predicate
                )),
            "{}",
            row["id"]
        );
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas.first().is_some_and(
                    |l| l.text == f["base"].as_str().unwrap() && l.kind == LemmaKind::Nominal
                ) && a
                    .morphemes
                    .first()
                    .is_some_and(|m| m.form == "되다" && m.kind == MorphemeKind::Suffix)
                    && a.rules.iter().any(|r| r == "suffix.verb.doeda")),
            "{}",
            row["id"]
        );
        supported += 1;
    }
    assert_eq!(supported, 39);
}
