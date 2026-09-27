//! COV-017ab: short quotations and change/conditional homonyms.
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
fn short_clauses_preserve_roles_normalization_and_explainable_breakdowns() {
    let ledger: Value = serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    let engine = Lemmatizer::new();
    let mut checked = 0;
    for case in ledger["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["id"].as_str().unwrap().starts_with("short-clause-"))
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
                assert!(a.rules.iter().any(|r| r == "ending.short_clause"), "{word}");
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
    assert_eq!(checked, 142);
}

#[test]
fn short_clauses_preserve_unknown_heads_without_inventing_reporting_verbs() {
    let engine = Lemmatizer::new();
    for word in ["먹는단", "학생이냔", "먹단", "먹잔", "먹었느냔"] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .filter(|a| a.rules.iter().any(|r| r == "ending.short_clause"))
                .all(|a| a.lemmas.iter().all(|l| l.text != "하다"))
        );
    }
    let result = engine.analyze_word("먹었는단").unwrap();
    assert!(result.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "먹었다"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "는단"));
}
