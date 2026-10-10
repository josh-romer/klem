use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{LemmaKind, Lemmatizer, MorphemeKind};
use serde_json::Value;
use std::{collections::BTreeMap, path::PathBuf};
use unicode_normalization::UnicodeNormalization;
#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn original_novel_omitted_copula_and_constructed_written_boundaries_are_typed() {
    let source: Value = serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-copula-source.json"
    ))
    .unwrap();
    let mut suite: validity::Suite = serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-copula-validity.json"
    ))
    .unwrap();
    assert_eq!(source["typed_lemmas"], serde_json::json!(["장래", "이다"]));
    assert_eq!(suite.cases[0].surface, "장래려니와");
    assert_eq!(
        suite.cases[0].judgments[0].lemma_kinds,
        Some(vec![LemmaKind::Nominal, LemmaKind::Copula])
    );
    assert_eq!(
        suite.cases[0].judgments[0].morpheme_kinds,
        Some(vec![MorphemeKind::Ending])
    );
    for encoding in ["NFC", "NFD"] {
        if encoding == "NFD" {
            for case in &mut suite.cases {
                case.surface = case.surface.nfd().collect();
            }
        }
        let report = validity::evaluate(&suite).unwrap();
        assert!(report.passed(), "{:?}", report.violations);
        assert_eq!((report.required_present, report.forbidden_present), (4, 0));
    }
    let engine = Lemmatizer::new();
    let context = source["original_observation"]["complete_original_line"]
        .as_str()
        .unwrap();
    let offset = source["original_observation"]["after"]["span"]["start"]
        .as_u64()
        .unwrap() as usize
        - source["original_observation"]["line_byte_start"]
            .as_u64()
            .unwrap() as usize;
    let token = engine
        .analyze_text(context)
        .find(|token| token.span.start == offset)
        .unwrap();
    assert_eq!(&context[token.span.clone()], "장래려니와");
    let before: klem::WordAnalysis =
        serde_json::from_value(source["original_observation"]["after"]["analysis"].clone())
            .unwrap();
    let after = token.analysis.unwrap();
    assert!(
        before
            .analyses
            .iter()
            .all(|path| after.analyses.contains(path))
    );
    assert!(after.analyses.iter().any(|path| {
        path.lemmas
            .iter()
            .map(|lemma| lemma.text.as_str())
            .eq(["장래", "이다"])
            && path
                .lemmas
                .iter()
                .map(|lemma| lemma.kind)
                .eq([LemmaKind::Nominal, LemmaKind::Copula])
            && path
                .rules
                .iter()
                .any(|rule| rule == "copula.omitted_ending")
            && path
                .morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["으려니와"])
    }));
}

struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn original_noun_copula_native_fields_and_compatible_filter_preserve_the_novel_reading() {
    let expected: BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-copula-native-entries.json"
    ))
    .unwrap();
    assert_eq!(expected.len(), 8);
    assert_eq!(expected["krdict:70089"]["headword"], "장래");
    assert_eq!(expected["krdict:70089"]["pos"], "명사");
    let path = std::env::temp_dir().join(format!(
        "klem-conjectural-additive-copula-{}.db",
        std::process::id()
    ));
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/conjectural-additive-copula-native.json",
        )],
        &path,
        "original-conjectural-copula",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&cleanup.0).unwrap();
    for (id, owner) in expected {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            owner,
            "{id}"
        );
    }
    let suite: validity::Suite = serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-copula-validity.json"
    ))
    .unwrap();
    let engine = Lemmatizer::new();
    for cache in [0, 4096] {
        let mut session = DictionarySession::new(&dictionary, cache);
        let report = validity::evaluate_with(&suite, |surface| {
            let mut word = engine.analyze_word(surface).map_err(|e| e.to_string())?;
            let mut annotation = session.annotate(&word).map_err(|e| e.to_string())?;
            annotation.filter(&mut word, DictionaryFilter::Compatible);
            Ok(word)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
        assert_eq!((report.required_present, report.forbidden_present), (4, 0));
        let word = engine.analyze_word("장래려니와").unwrap();
        let annotation = session.annotate(&word).unwrap();
        assert!(word.analyses.iter().any(|path| {
            path.lemmas
                .iter()
                .map(|lemma| lemma.text.as_str())
                .eq(["장래", "이다"])
                && annotation.assess(path).status == Compatibility::Compatible
        }));
    }
}
