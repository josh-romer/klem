//! Source-backed -씩 hypotheses; quantity and contextual senses remain open.
#[path = "../tools/validity.rs"]
mod validity;
use klem::{LemmaKind, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::{Value, json};
use std::sync::OnceLock;
use unicode_normalization::UnicodeNormalization;

fn fixture() -> &'static Value {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    SOURCE.get_or_init(|| serde_json::from_str(include_str!("fixtures/ssik-sources.json")).unwrap())
}

#[test]
fn source_structures_cover_quantity_units_emphasis_and_outer_boundaries() {
    let suite: validity::Suite = serde_json::from_value(json!({
        "schema_version":1,
        "review_status":"Conditional source-backed structure; contextual and independent review pending",
        "sources":{"ssik-krdict":"https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=72043"},
        "cases":fixture()["cases"],
    })).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (148, 11));
    assert_eq!(
        fixture()["all_original_groups"].as_array().unwrap().len(),
        11
    );
    let engine = Lemmatizer::new();
    for case in fixture()["cases"].as_array().unwrap() {
        let text = case["surface"].as_str().unwrap();
        let actual = engine.analyze_word(text).unwrap();
        assert_eq!(
            actual,
            engine
                .analyze_word(&text.nfd().collect::<String>())
                .unwrap()
        );
        for analysis in &actual.analyses {
            assert!(analysis.breakdown().is_some(), "{text}: {analysis:?}");
            assert!(
                analysis
                    .rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
        }
    }
}

#[test]
fn all_frozen_candidates_remain_in_their_original_order() {
    let engine = Lemmatizer::new();
    let before = fixture()["before_analyses"].as_object().unwrap();
    assert_eq!(before.len(), 193);
    for (text, value) in before {
        let old: WordAnalysis = serde_json::from_value(value.clone()).unwrap();
        let actual = engine.analyze_word(text).unwrap();
        let retained: Vec<_> = actual
            .analyses
            .iter()
            .filter(|a| old.analyses.contains(a))
            .cloned()
            .collect();
        assert_eq!(retained, old.analyses, "{text}");
    }
}

#[test]
fn lexical_adverb_empty_base_and_forged_suffix_orders_stay_distinct() {
    let engine = Lemmatizer::new();
    for text in ["씩", "씩이나"] {
        let actual = engine.analyze_word(text).unwrap();
        assert!(actual.analyses.iter().any(|a| a.unchanged));
        assert!(actual.analyses.iter().all(|a| {
            !a.morphemes
                .iter()
                .any(|m| m.kind == MorphemeKind::Suffix && m.form == "씩")
        }));
    }
    let actual = engine.analyze_word("잔씩").unwrap();
    let path = actual
        .analyses
        .iter()
        .find(|a| {
            a.lemmas[0].text == "잔"
                && a.lemmas[0].kind == LemmaKind::Nominal
                && a.morphemes.len() == 1
        })
        .unwrap();
    let mut forged = path.clone();
    forged.rules.retain(|r| r != "suffix.distributive.ssik");
    assert!(forged.breakdown().is_none());
    forged = path.clone();
    forged.morphemes.push(forged.morphemes[0].clone());
    assert!(forged.breakdown().is_none());
    forged = path.clone();
    forged.lemmas[0].kind = LemmaKind::Predicate;
    assert!(forged.breakdown().is_none());
}

#[test]
fn native_sources_dictionary_filters_and_adverb_homonym_are_preserved() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    use std::{fs, path::PathBuf};
    let path = std::env::temp_dir().join(format!("klem-ssik-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-ssik-english.json")],
        &path,
        "ssik-offline-source-test",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let native = fixture()["complete_native_entries"].as_object().unwrap();
    assert_eq!(native.len(), 17);
    for (id, original) in native {
        let mut expected = original.clone();
        for sense in expected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let mut session = DictionarySession::new(&db, 1048576);
    let engine = Lemmatizer::new();
    for text in [
        "잔씩",
        "마리씩",
        "하나씩",
        "조금씩",
        "고기씩이나",
        "선물씩이나",
        "용돈씩이나",
    ] {
        let actual = engine.analyze_word(text).unwrap();
        let annotation = session.annotate(&actual).unwrap();
        let index = actual
            .analyses
            .iter()
            .position(|a| a.rules.iter().any(|r| r == "suffix.distributive.ssik"))
            .unwrap();
        assert_eq!(
            annotation.readings[index].status,
            Compatibility::Compatible,
            "{text}"
        );
        assert!(!annotation.readings[index].lemmas[0].entries.is_empty());
    }
    let actual = engine.analyze_word("씩").unwrap();
    let annotation = session.annotate(&actual).unwrap();
    assert!(
        annotation
            .lemmas
            .iter()
            .any(|l| l.entries.iter().any(|e| e.entry.id == "krdict:66460"))
    );
}

#[test]
fn repeated_suffix_text_has_a_bounded_number_of_paths() {
    let engine = Lemmatizer::new();
    for repeats in [16, 256, 1024] {
        let text = format!("잔{}", "씩".repeat(repeats));
        let actual = engine.analyze_word(&text).unwrap();
        assert!(
            actual.analyses.len() < 32,
            "{repeats}: {}",
            actual.analyses.len()
        );
        assert!(actual.analyses.iter().all(|a| {
            a.morphemes
                .iter()
                .filter(|m| m.kind == MorphemeKind::Suffix && m.form == "씩")
                .count()
                <= 1
        }));
        assert!(actual.analyses.iter().any(|a| a.unchanged));
    }
}
