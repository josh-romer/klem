//! Primary KRDict noun + -하다 examples retain separate verb/adjective classes.
#[path = "../tools/hada_nominal_preservation.rs"]
mod preservation;
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionarySession, OriginRelation, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use serde_json::Value;
use std::{fs, path::PathBuf, sync::OnceLock};
use unicode_normalization::UnicodeNormalization;
const VERB: &str = "suffix.verb.hada";
const ADJECTIVE: &str = "suffix.adjective.hada";
fn source() -> &'static Value {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    SOURCE.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/hada-nominal-sources.json")).unwrap()
    })
}
fn listed(a: &Analysis) -> bool {
    let Some(l) = a.lemmas.first() else {
        return false;
    };
    [
        "공부", "밥", "빨래", "사랑", "생각", "절", "건강", "순수", "정직", "진실", "행복",
    ]
    .contains(&l.text.as_str())
        && a.rules.iter().any(|r| r == VERB || r == ADJECTIVE)
}
struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        let p = std::env::temp_dir().join(format!(
            "klem-hada-nominal-{}-{}.db",
            std::process::id(),
            std::thread::current().name().unwrap()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-hada-six-sense.json")],
            &p,
            "hada-nominal-test",
        )
        .unwrap();
        Self(p)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
#[test]
fn eleven_sources_keep_whole_heads_unicode_and_class_boundaries() {
    let engine = Lemmatizer::new();
    for (base, rule, suffixes) in [
        (
            "공부",
            VERB,
            vec![
                "하다",
                "해요",
                "했어요",
                "하는",
                "한다",
                "하시다",
                "하고있다",
                "함은",
            ],
        ),
        ("밥", VERB, vec!["하다", "해요", "하는"]),
        ("빨래", VERB, vec!["하다", "했어요", "한다"]),
        ("사랑", VERB, vec!["하다", "하는", "하고있다"]),
        ("생각", VERB, vec!["하다", "한다", "함은"]),
        ("절", VERB, vec!["하다", "해요", "하시다"]),
        (
            "건강",
            ADJECTIVE,
            vec!["하다", "해요", "한", "했어요", "하지않다"],
        ),
        ("순수", ADJECTIVE, vec!["하다", "한", "해요"]),
        ("정직", ADJECTIVE, vec!["하다", "한", "했어요"]),
        ("진실", ADJECTIVE, vec!["하다", "한", "해요"]),
        ("행복", ADJECTIVE, vec!["하다", "한", "했어요"]),
    ] {
        for ending in suffixes {
            let surface = format!("{base}{ending}");
            let word = engine.analyze_word(&surface).unwrap();
            assert_eq!(
                word,
                engine
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            assert!(
                word.analyses.iter().any(|a| a
                    .lemmas
                    .first()
                    .is_some_and(|l| l.text == format!("{base}하다"))),
                "whole {surface}"
            );
            let paths: Vec<_> = word
                .analyses
                .iter()
                .filter(|a| {
                    listed(a) && a.lemmas[0].text == base && a.rules.iter().any(|r| r == rule)
                })
                .collect();
            assert!(!paths.is_empty(), "split {surface}");
            for a in paths {
                assert!(a.breakdown().is_some(), "{surface}");
                assert_eq!(a.morphemes[0].form, "하다");
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            }
        }
    }
    for word in [
        "건강하는",
        "건강한다",
        "건강하고있다",
        "순수해대다",
        "행복하는",
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(listed),
            "adjective boundary {word}"
        );
    }
    for word in ["공부해하다", "밥해하다"] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(listed),
            "verb boundary {word}"
        );
    }
}
#[test]
fn every_frozen_word_and_original_row_remains_preserved() {
    let engine = Lemmatizer::new();
    let before = source()["before_analyses"].as_object().unwrap();
    let mut words = 0;
    for old in before.values() {
        let original: klem::WordAnalysis = serde_json::from_value(old.clone()).unwrap();
        let after = engine.analyze_word(&original.normalized).unwrap();
        let retained: Vec<_> = after
            .analyses
            .iter()
            .filter(|a| original.analyses.contains(a))
            .cloned()
            .collect();
        assert_eq!(retained, original.analyses, "{}", original.normalized);
        words += 1;
    }
    assert_eq!(words, 649);
    let corpora = source()["corpora"].as_array().unwrap();
    assert_eq!(corpora.len(), 6);
    assert_eq!(
        corpora
            .iter()
            .map(|c| c["rows"].as_array().unwrap().len())
            .sum::<usize>(),
        1048
    );
    for row in corpora.iter().flat_map(|c| c["rows"].as_array().unwrap()) {
        assert_eq!(row["original_row"].as_array().unwrap().len(), 10);
        assert!(!row["complete_sentence"].as_str().unwrap().is_empty());
    }
}
#[test]
fn complete_native_closure_and_origin_homonyms_remain_separate() {
    let fixture = Fixture::new();
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let native = source()["complete_native_entries"].as_object().unwrap();
    assert_eq!(native.len(), 138);
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
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    let word = engine.analyze_word("정직하다").unwrap();
    let annotated = session.annotate(&word).unwrap();
    let index = word
        .analyses
        .iter()
        .position(|a| a.lemmas[0].text == "정직" && a.rules.iter().any(|r| r == ADJECTIVE))
        .unwrap();
    let reading = &annotated.readings[index];
    let identities: Vec<_> = reading.lemmas[0]
        .entries
        .iter()
        .filter_map(|e| e.derivational_identity.as_ref())
        .collect();
    assert!(
        identities
            .iter()
            .any(|i| i.relation == OriginRelation::RecordedMatch)
    );
    assert!(
        identities
            .iter()
            .any(|i| i.relation == OriginRelation::RecordedDifference)
    );
    for i in identities {
        assert_eq!(i.morpheme_index, 0);
        assert_eq!(i.whole_entries, vec!["krdict:31765"]);
    }
}
#[test]
fn missing_whole_origins_cannot_certify_a_homonym_difference() {
    let fixture = Fixture::new();
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for base in ["밥", "빨래", "사랑", "생각", "절"] {
        let word = engine.analyze_word(&format!("{base}하다")).unwrap();
        let annotated = session.annotate(&word).unwrap();
        let index = word
            .analyses
            .iter()
            .position(|a| a.lemmas[0].text == base && a.rules.iter().any(|r| r == VERB))
            .unwrap();
        let entries = &annotated.readings[index].lemmas[0].entries;
        assert!(!entries.is_empty());
        for entry in entries {
            if db.entry(&entry.id).unwrap().unwrap().summary.pos != "명사" {
                assert!(entry.derivational_identity.is_none());
                continue;
            }
            let identity = entry.derivational_identity.as_ref().unwrap();
            assert_eq!(
                identity.relation,
                OriginRelation::Unknown,
                "{base}: {entry:?}"
            );
            assert!(identity.expected_origins.is_empty());
            assert!(!identity.whole_origins_complete);
        }
    }
}

#[test]
fn forged_class_rule_cannot_borrow_another_owner() {
    let engine = Lemmatizer::new();
    for word in ["공부하다", "건강하다"] {
        let analysis = engine
            .analyze_word(word)
            .unwrap()
            .analyses
            .into_iter()
            .find(listed)
            .unwrap();
        let mut forged = analysis.clone();
        for r in &mut forged.rules {
            if r == VERB {
                *r = ADJECTIVE.into();
            } else if r == ADJECTIVE {
                *r = VERB.into();
            }
        }
        assert!(analysis.breakdown().is_some());
        assert!(forged.breakdown().is_none(), "{word}");
    }
}

#[test]
fn source_backed_stable_class_cases() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("hada-noun-"));
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (88, 26));
}

#[test]
fn historical_snapshot_guard_rejects_lost_parents_and_borrowed_recoveries() {
    let frozen: klem::WordAnalysis =
        serde_json::from_value(source()["before_analyses"]["공부하다"].clone()).unwrap();
    let actual = Lemmatizer::new().analyze_word("공부하다").unwrap();
    preservation::assert_preserved(&actual, &frozen);
    let mut lost = actual.clone();
    lost.analyses.retain(|a| a != &frozen.analyses[0]);
    assert!(std::panic::catch_unwind(|| preservation::assert_preserved(&lost, &frozen)).is_err());
    let mut borrowed = actual.clone();
    let added = borrowed
        .analyses
        .iter_mut()
        .find(|a| !frozen.analyses.contains(a))
        .unwrap();
    added.spelling_paths = vec![vec![klem::SpellingRecovery {
        morpheme_index: 0,
        class: klem::SpellingClass::HieutIrregular,
    }]];
    assert!(
        std::panic::catch_unwind(|| preservation::assert_preserved(&borrowed, &frozen)).is_err()
    );
}
