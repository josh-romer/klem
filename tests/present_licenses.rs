//! COV-017y / COV-019h: present declaratives share prefinal and class licenses.
use klem::{Analysis, Lemmatizer};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

fn matches(a: &Analysis, judgment: &Value) -> bool {
    let value = serde_json::to_value(a).unwrap();
    [
        ("lemmas", "text", "lemmas"),
        ("lemmas", "kind", "lemma_kinds"),
        ("morphemes", "form", "morphemes"),
        ("morphemes", "kind", "morpheme_kinds"),
    ]
    .iter()
    .all(|(field, key, expected)| {
        value[field]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| &v[key])
            .eq(judgment[expected].as_array().unwrap())
    })
}

#[test]
fn present_declaratives_preserve_roles_normalization_and_explainable_breakdowns() {
    let ledger: Value = serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    let engine = Lemmatizer::new();
    let mut checked = 0;
    for case in ledger["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["id"].as_str().unwrap().starts_with("present-license-"))
    {
        let word = case["surface"].as_str().unwrap();
        let result = engine.analyze_word(word).unwrap();
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for judgment in case["judgments"].as_array().unwrap() {
            let matched = result.analyses.iter().find(|a| matches(a, judgment));
            assert_eq!(
                matched.is_some(),
                judgment["verdict"] == "required",
                "{word}: {judgment}"
            );
            if let Some(a) = matched {
                assert!(a.breakdown().is_some(), "{word}");
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
                if a.lemmas
                    .iter()
                    .any(|l| l.kind == klem::LemmaKind::Auxiliary)
                {
                    assert!(
                        a.rules.iter().any(|r| r.starts_with("auxiliary")),
                        "{word}: {:?}",
                        a.rules
                    );
                }
            }
        }
        checked += 1;
    }
    assert_eq!(checked, 338);
}

#[test]
fn present_licenses_do_not_guess_lexical_class_from_stem_spelling() {
    let engine = Lemmatizer::new();
    for (word, unknown, form) in [
        ("먹었는다", "먹었다", "는다"),
        ("먹겠는다고", "먹겠다", "는다고"),
        ("먹고싶으신다는", "먹고싶으시다", "는다는"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == unknown
                && a.morphemes.len() == 1
                && a.morphemes[0].form == form),
            "{word}"
        );
    }
}
