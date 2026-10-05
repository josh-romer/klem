use klem::{LemmaKind, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use std::{path::PathBuf, sync::OnceLock};
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

fn fixture() -> &'static Value {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    SOURCE.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/ssik-adverb-sources.json")).unwrap()
    })
}
const BASES: &[&str] = &[
    "가끔",
    "살짝",
    "이따금",
    "이만큼",
    "잠깐",
    "조금",
    "하나하나",
    "한바탕",
    "한발",
];
fn quantity(a: &klem::Analysis, base: &str) -> bool {
    a.lemmas[0].text == base
        && a.lemmas[0].kind == LemmaKind::Adverbial
        && a.rules
            .iter()
            .any(|r| r == "suffix.distributive.ssik.adverbial_base")
}
#[test]
fn all_nine_source_bases_focus_chains_and_unicode() {
    let engine = Lemmatizer::new();
    for base in BASES {
        for tail in ["", "은", "도", "만", "은요"] {
            let word = format!("{base}씩{tail}");
            let result = engine.analyze_word(&word).unwrap();
            assert!(
                result.analyses.iter().any(|a| quantity(a, base)),
                "missing {word}"
            );
            assert!(result.analyses.iter().any(|a| a.unchanged));
            assert_eq!(
                result,
                engine
                    .analyze_word(&word.nfd().collect::<String>())
                    .unwrap()
            );
            for a in result.analyses.iter().filter(|a| quantity(a, base)) {
                assert_eq!(a.morphemes[0].form, "씩");
                assert_eq!(a.morphemes[0].kind, MorphemeKind::Suffix);
                assert!(a.breakdown().is_some(), "unordered {word}: {a:?}");
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            }
        }
    }
}
#[test]
fn incompatible_homonyms_repeated_suffixes_and_unsupported_copulas() {
    let engine = Lemmatizer::new();
    for base in ["통", "정", "단", "씩", "먹다"] {
        assert!(
            !engine
                .analyze_word(&format!("{base}씩"))
                .unwrap()
                .analyses
                .iter()
                .any(|a| quantity(a, base)),
            "{base}"
        );
    }
    for base in BASES {
        for tail in [
            "는",
            "가",
            "를",
            "로",
            "나",
            "야",
            "예요",
            "씩",
            "을은",
            "은는",
            "이다",
            "이에요",
            "답다",
        ] {
            let word = format!("{base}씩{tail}");
            assert!(
                !engine
                    .analyze_word(&word)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| quantity(a, base)),
                "unexpected {word}"
            );
        }
    }
}
#[test]
fn frozen_nominal_package_candidates_are_preserved() {
    let engine = Lemmatizer::new();
    assert_eq!(
        fixture()["before_analyses"].as_object().unwrap().len(),
        2509
    );
    for (word, value) in fixture()["before_analyses"].as_object().unwrap() {
        let old: WordAnalysis = serde_json::from_value(value.clone()).unwrap();
        assert_eq!(&old.normalized, word);
        let new = engine.analyze_word(&old.normalized).unwrap();
        let retained: Vec<_> = new
            .analyses
            .into_iter()
            .filter(|a| old.analyses.contains(a))
            .collect();
        assert_eq!(retained, old.analyses, "{}", old.normalized);
    }
}
#[test]
fn source_base_and_full_native_dictionary_imports() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    let path = std::env::temp_dir().join(format!(
        "klem-ssik-adverb-preview-{}.db",
        std::process::id()
    ));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _guard = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-ssik-adverb-english.json",
        )],
        &path,
        "source-patch-preview",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    let source: Value = serde_json::from_reader(
        std::fs::File::open("tests/fixtures/krdict-ssik-adverb-english.json").unwrap(),
    )
    .unwrap();
    assert_eq!(
        source["LexicalResource"]["Lexicon"]["LexicalEntry"]
            .as_array()
            .unwrap()
            .len(),
        349
    );
    for id in [
        "krdict:61176",
        "krdict:61177",
        "krdict:65204",
        "krdict:91751",
        "krdict:66460",
        "krdict:72043",
    ] {
        assert!(dictionary.entry(id).unwrap().is_some());
    }
    let native = &fixture()["complete_native_entries"];
    for (id, original) in native.as_object().unwrap() {
        let mut expected = original.clone();
        for sense in expected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|translation| translation["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(dictionary.entry(id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 1048576);
    for base in BASES {
        let word = engine.analyze_word(&format!("{base}씩")).unwrap();
        let annotation = session.annotate(&word).unwrap();
        let index = word
            .analyses
            .iter()
            .position(|a| quantity(a, base))
            .unwrap();
        assert_eq!(
            annotation.readings[index].status,
            Compatibility::Compatible,
            "{base}"
        );
    }
}

#[test]
fn stable_cases_and_separate_original_typed_morphology() {
    let suite: validity::Suite = serde_json::from_value(serde_json::json!({
        "schema_version": 1,
        "review_status": "Conditional source-backed structures; contextual and independent review pending",
        "sources": fixture()["sources"],
        "cases": fixture()["cases"],
    })).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (45, 85));
    let projection: Value =
        serde_json::from_str(include_str!("../docs/ssik-morphology-projection.json")).unwrap();
    let engine = Lemmatizer::new();
    let mut count = 0;
    for row in projection["rows"].as_array().unwrap() {
        if row["expected"].is_null() {
            continue;
        }
        count += 1;
        let surface = row["original_row"][1].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        assert!(
            word.analyses.iter().any(|path| {
                let actual = serde_json::to_value(path).unwrap();
                actual["lemmas"] == row["expected"]["lemmas"]
                    && actual["morphemes"] == row["expected"]["morphemes"]
            }),
            "{}: {surface}",
            row["id"]
        );
    }
    assert_eq!(count, 9);
}

#[test]
fn forged_adverb_suffix_owners_do_not_produce_ordered_readings() {
    let engine = Lemmatizer::new();
    let word = engine.analyze_word("가끔씩").unwrap();
    let original = word
        .analyses
        .iter()
        .find(|path| quantity(path, "가끔"))
        .unwrap();
    for rule in [
        "suffix.distributive.ssik",
        "suffix.distributive.ssik.adverbial_base",
    ] {
        let mut forged = original.clone();
        forged.rules.retain(|r| r != rule);
        assert!(forged.breakdown().is_none());
    }
    let mut forged = original.clone();
    forged.lemmas[0].text = "통".into();
    assert!(forged.breakdown().is_none());
    forged = original.clone();
    forged.lemmas[0].kind = LemmaKind::Nominal;
    assert!(forged.breakdown().is_none());
    forged = original.clone();
    forged.morphemes.push(forged.morphemes[0].clone());
    assert!(forged.breakdown().is_none());
    forged = original.clone();
    forged.morphemes[0].kind = MorphemeKind::Particle;
    assert!(forged.breakdown().is_none());
    forged = original.clone();
    forged.lemmas.push(klem::Lemma {
        text: "이다".into(),
        kind: LemmaKind::Copula,
    });
    assert!(forged.breakdown().is_none());
}
