//! Source-listed noun -시 and nested passive owners retain original alternatives.
#[path = "../tools/hada_nominal_preservation.rs"]
mod hada_nominal_preservation;
#[path = "../tools/validity.rs"]
mod validity;
use klem::breakdown::Component;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, OriginRelation, SqliteDictionary,
    import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, Session, WordAnalysis};
use serde_json::Value;
use std::{
    fs,
    path::PathBuf,
    sync::{Arc, OnceLock},
};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "suffix.nominal.si";
fn source() -> &'static Value {
    static DATA: OnceLock<Value> = OnceLock::new();
    DATA.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/nominal-si-sources.json")).unwrap()
    })
}
fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("nominal-si-"));
    suite
}
fn derived(a: &Analysis) -> bool {
    a.rules.iter().any(|r| r == RULE)
}
struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-nominal-si-{}-{}.db",
            std::process::id(),
            std::thread::current().name().unwrap()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-nominal-si.json")],
            &path,
            "nominal-si-test",
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
fn all_individual_cases_unicode_and_owned_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (200, 10));
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
fn every_native_entry_and_all_ten_source_examples_survive_import() {
    let file = Fixture::new();
    let db = SqliteDictionary::open(&file.0).unwrap();
    let native = source()["complete_native_entries"].as_object().unwrap();
    assert_eq!(native.len(), 44);
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
    let suffix = db.entry("krdict:71567").unwrap().unwrap();
    assert_eq!(
        (
            suffix.summary.headword.as_str(),
            suffix.summary.pos.as_str()
        ),
        ("-시", "접사")
    );
    assert_eq!(
        suffix
            .senses
            .iter()
            .map(|s| s.examples.len())
            .sum::<usize>(),
        10
    );
    assert!(suffix.notes.iter().any(|n| n == "일부 명사 뒤에 붙는다."));
    let families = source()["families"].as_array().unwrap();
    assert_eq!(
        families
            .iter()
            .filter(|f| f["nominal_supported"] == true)
            .count(),
        7
    );
    assert_eq!(
        families
            .iter()
            .filter(|f| f["passive_supported"] == true)
            .count(),
        5
    );
}

#[test]
fn old_candidate_order_and_original_annotation_are_preserved() {
    let engine = Lemmatizer::new();
    let snapshots = source()["before_analyses"].as_object().unwrap();
    assert_eq!(snapshots.len(), 252);
    for (word, old) in snapshots {
        let old: WordAnalysis = serde_json::from_value(old.clone()).unwrap();
        let after =
            hada_nominal_preservation::project_remaining(&engine.analyze_word(word).unwrap());
        assert_eq!(
            after
                .analyses
                .iter()
                .filter(|a| !derived(a) && !a.rules.iter().any(|r| r == "suffix.verb.hada"))
                .cloned()
                .collect::<Vec<_>>(),
            old.analyses,
            "{word}"
        );
    }
    let mut rows = 0;
    let mut hada_context = false;
    for corpus in source()["corpora"].as_array().unwrap() {
        for row in corpus["rows"].as_array().unwrap() {
            let columns = row["original_row"].as_array().unwrap();
            assert_eq!(columns.len(), 10);
            assert!(
                row["complete_sentence"]
                    .as_str()
                    .unwrap()
                    .lines()
                    .any(|line| line
                        == columns
                            .iter()
                            .map(|v| v.as_str().unwrap())
                            .collect::<Vec<_>>()
                            .join("\t"))
            );
            hada_context |= row["original_lemma"] == "문제시+하+지+도";
            rows += 1;
        }
    }
    assert_eq!(rows, 34);
    assert!(
        hada_context,
        "The original 하다 context is distinct from passive 되다."
    );
}

#[test]
fn filters_keep_passives_with_identity_evidence_scoped_to_the_owned_suffix() {
    let file = Fixture::new();
    let db = SqliteDictionary::open(&file.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    for family in source()["families"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|f| f["passive_supported"] == true)
    {
        let head = family["head"].as_str().unwrap();
        let base = family["base"].as_str().unwrap();
        let whole = family["whole_passive_ids"].as_array().unwrap()[0]
            .as_str()
            .unwrap();
        for tail in [
            "되는",
            "됐어요",
            "됨은",
            "되기였다",
            "되지않는다",
            "되고있다",
        ] {
            let word = engine.analyze_word(&format!("{head}{tail}")).unwrap();
            let annotation = dictionary.annotate(&word).unwrap();
            let mut seen = 0;
            for (i, a) in word.analyses.iter().enumerate().filter(|(_, a)| derived(a)) {
                if !a.rules.iter().any(|r| r == "suffix.verb.doeda") {
                    continue;
                }
                assert_eq!(a.lemmas[0].text, base);
                assert_eq!(
                    &a.morphemes[..2]
                        .iter()
                        .map(|m| m.form.as_str())
                        .collect::<Vec<_>>(),
                    &["시", "되다"]
                );
                let owner = &annotation.readings[i].lemmas[0];
                for entry in owner
                    .entries
                    .iter()
                    .filter(|e| e.derivational_identity.is_some())
                {
                    let identity = entry.derivational_identity.as_ref().unwrap();
                    assert_eq!(identity.morpheme_index, 1);
                    assert_eq!(identity.whole_entries, [whole]);
                    assert_eq!(identity.relation, OriginRelation::RecordedMatch);
                }
                assert!(
                    owner
                        .entries
                        .iter()
                        .any(|e| e.derivational_identity.is_some())
                );
                seen += 1;
            }
            assert!(seen > 0, "{head}{tail}");
            for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = word.clone();
                let mut filtered_annotation = annotation.clone();
                filtered_annotation.filter(&mut filtered, filter);
                assert!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| derived(a) && a.rules.iter().any(|r| r == "suffix.verb.doeda")),
                    "{head}{tail}: {filter:?}"
                );
                assert!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| a.lemmas[0].text == format!("{head}되다")),
                    "whole alternative: {head}{tail}"
                );
            }
        }
    }
    // A nominal derivation has no passive source identity merely because its
    // spelling also occurs in one of the five recorded passive heads.
    let word = engine.analyze_word("의문시는").unwrap();
    let annotation = dictionary.annotate(&word).unwrap();
    for (i, _) in word.analyses.iter().enumerate().filter(|(_, a)| derived(a)) {
        assert!(
            annotation.readings[i]
                .lemmas
                .iter()
                .flat_map(|l| &l.entries)
                .all(|e| e.derivational_identity.is_none())
        );
    }
}

#[test]
fn external_invalid_suffix_chains_cannot_borrow_the_finite_owner() {
    let engine = Lemmatizer::new();
    let valid = engine
        .analyze_word("문제시되는")
        .unwrap()
        .analyses
        .into_iter()
        .find(|a| derived(a) && a.morphemes[1].form == "되다")
        .unwrap();
    for base in ["먹", "야만", "문제시"] {
        let mut invalid = valid.clone();
        invalid.lemmas[0].text = base.into();
        assert!(invalid.breakdown().is_none(), "{base}");
    }
    let mut invalid = valid.clone();
    invalid.morphemes[0].kind = klem::MorphemeKind::Prefinal;
    assert!(invalid.breakdown().is_none());
    let mut invalid = valid;
    invalid.lemmas[0].kind = LemmaKind::Root;
    assert!(invalid.breakdown().is_none());
}
