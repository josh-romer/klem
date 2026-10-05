//! Direct noun -하다 and independently licensed nested -화 retain whole heads.
#[path = "../tools/validity.rs"]
mod validity;
use klem::breakdown::Component;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, OriginRelation, SqliteDictionary,
    import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind, Session, WordAnalysis};
use serde_json::Value;
use std::{
    fs,
    path::PathBuf,
    sync::{Arc, OnceLock},
};
use unicode_normalization::UnicodeNormalization;
const RULE: &str = "suffix.verb.hada";
fn source() -> &'static Value {
    static DATA: OnceLock<Value> = OnceLock::new();
    DATA.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/nominal-hwa-hada-sources.json")).unwrap()
    })
}
fn derived(a: &Analysis) -> bool {
    a.rules.iter().any(|r| r == RULE)
}
struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-nominal-hwa-hada-{}-{}.db",
            std::process::id(),
            std::thread::current().name().unwrap()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-nominal-hwa-hada.json")],
            &path,
            "nominal-hwa-hada-test",
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
fn stable_cases_unicode_cache_components_and_recoveries() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("hwa-hada-"));
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (1136, 18));
    for budget in [0, 1, 1024, 4 * 1024 * 1024] {
        let mut session = Session::new(Arc::new(Lemmatizer::new()), budget);
        for case in &suite.cases {
            let word = session.analyze_word(&case.surface).unwrap();
            assert_eq!(
                word,
                session
                    .analyze_word(&case.surface.nfd().collect::<String>())
                    .unwrap()
            );
            for a in word.analyses.iter().filter(|a| derived(a)) {
                let order = a.breakdown().expect(&case.surface);
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
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
                assert!(
                    a.spelling_paths
                        .iter()
                        .flatten()
                        .all(|r| r.morpheme_index < a.morphemes.len())
                );
            }
        }
    }
}
#[test]
fn complete_native_sources_keep_all_hada_senses_and_homonyms() {
    let file = Fixture::new();
    let db = SqliteDictionary::open(&file.0).unwrap();
    let native = source()["complete_native_entries"].as_object().unwrap();
    assert_eq!(native.len(), 165);
    for (id, expected) in native {
        let mut projected = expected.clone();
        for sense in projected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            projected,
            "{id}"
        );
    }
    let suffix = db.entry("krdict:88475").unwrap().unwrap();
    assert_eq!(suffix.senses.len(), 6);
    assert!(
        suffix.senses[0]
            .notes
            .iter()
            .any(|n| n == "일부 명사 뒤에 붙는다.")
    );
    assert_eq!(
        source()["direct_nominal_heads"].as_array().unwrap().len(),
        28
    );
    assert_eq!(source()["nested_bases"].as_array().unwrap().len(), 22);
}
#[test]
fn original_word_order_and_all_thirty_annotated_rows_stay_intact() {
    let engine = Lemmatizer::new();
    let words = source()["before_analyses"].as_object().unwrap();
    assert_eq!(words.len(), 562);
    for (surface, before) in words {
        let before: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
        let after = engine.analyze_word(surface).unwrap();
        assert_eq!(
            after
                .analyses
                .iter()
                .filter(|a| !derived(a))
                .cloned()
                .collect::<Vec<_>>(),
            before.analyses,
            "{surface}"
        );
    }
    let mut rows = 0;
    for corpus in source()["corpora"].as_array().unwrap() {
        for row in corpus["rows"].as_array().unwrap() {
            let columns = row["original_row"].as_array().unwrap();
            assert_eq!(columns.len(), 10);
            assert!(row["original_lemma"].as_str().unwrap().contains("화+하"));
            assert!(row["complete_sentence"].as_str().unwrap().lines().any(|l| {
                l == columns
                    .iter()
                    .map(|v| v.as_str().unwrap())
                    .collect::<Vec<_>>()
                    .join("\t")
            }));
            rows += 1;
        }
    }
    assert_eq!(rows, 30);
}
#[test]
fn direct_and_nested_dictionary_identity_belongs_to_the_verbal_suffix() {
    let file = Fixture::new();
    let db = SqliteDictionary::open(&file.0).unwrap();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&db, 0);
    for family in source()["families"].as_array().unwrap() {
        let head = family["head"].as_str().unwrap();
        let base = family["base"].as_str().unwrap();
        for tail in [
            "하다",
            "했어요",
            "하는",
            "함은",
            "하기였다",
            "하고있다",
            "하지않는다",
        ] {
            let word = engine.analyze_word(&format!("{head}{tail}")).unwrap();
            let annotation = session.annotate(&word).unwrap();
            assert!(
                word.analyses
                    .iter()
                    .any(|a| !derived(a) && a.lemmas[0].text == format!("{head}하다"))
            );
            let mut direct = false;
            let mut nested = false;
            for (i, a) in word.analyses.iter().enumerate().filter(|(_, a)| derived(a)) {
                let is_nested = a.lemmas[0].text == base;
                assert_eq!(a.lemmas[0].kind, LemmaKind::Nominal);
                direct |= !is_nested;
                nested |= is_nested;
                let owner = &annotation.readings[i].lemmas[0];
                for entry in &owner.entries {
                    let native = &source()["complete_native_entries"][&entry.id];
                    if native["pos"] != "명사" {
                        continue;
                    }
                    let evidence = entry.derivational_identity.as_ref().unwrap();
                    assert_eq!(evidence.morpheme_index, usize::from(is_nested));
                    let expected = family["whole_hada_ids"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|v| v.as_str().unwrap())
                        .collect::<Vec<_>>();
                    assert_eq!(evidence.whole_entries, expected);
                    let matched = native["origins"].as_array().unwrap().iter().any(|o| {
                        evidence
                            .expected_origins
                            .contains(&o.as_str().unwrap().to_owned())
                    });
                    assert_eq!(
                        evidence.relation,
                        if matched {
                            OriginRelation::RecordedMatch
                        } else if native["origins"].as_array().unwrap().is_empty() {
                            OriginRelation::Unknown
                        } else {
                            OriginRelation::RecordedDifference
                        }
                    );
                }
                assert!(owner.entries.iter().any(|e| {
                    e.derivational_identity
                        .as_ref()
                        .is_some_and(|id| id.relation == OriginRelation::RecordedMatch)
                }));
            }
            for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = word.clone();
                let mut filtered_annotation = annotation.clone();
                filtered_annotation.filter(&mut filtered, filter);
                assert!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| derived(a) && a.lemmas[0].text == head),
                    "direct {head}{tail}: {filter:?}"
                );
                assert_eq!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| derived(a) && a.lemmas[0].text == base),
                    family["verbal_supported"] == true,
                    "nested {head}{tail}: {filter:?}"
                );
            }
            assert!(direct, "{head}{tail}");
            assert_eq!(nested, family["verbal_supported"] == true, "{head}{tail}");
        }
    }
}
#[test]
fn external_chains_cannot_borrow_class_or_origin_from_rule_flags() {
    let engine = Lemmatizer::new();
    let word = engine.analyze_word("상품화한다").unwrap();
    let path = word
        .analyses
        .into_iter()
        .find(|a| derived(a) && a.lemmas[0].text == "상품")
        .unwrap();
    assert_eq!(path.morphemes[1].form, "하다");
    for change in 0..4 {
        let mut a = path.clone();
        match change {
            0 => a.lemmas[0].text = "먹".into(),
            1 => a.lemmas[0].kind = LemmaKind::Root,
            2 => a.morphemes[1].kind = MorphemeKind::Prefinal,
            _ => a.rules.retain(|r| r != RULE),
        }
        assert!(a.breakdown().is_none());
    }
    let file = Fixture::new();
    let db = SqliteDictionary::open(&file.0).unwrap();
    let annotation = DictionarySession::new(&db, 0)
        .annotate(&engine.analyze_word("가시는").unwrap())
        .unwrap();
    assert!(
        annotation
            .readings
            .iter()
            .flat_map(|r| &r.lemmas)
            .flat_map(|l| &l.entries)
            .all(|e| e.derivational_identity.is_none())
    );
}
