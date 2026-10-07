use klem::{Analysis, WordAnalysis};
use serde_json::Value;
pub fn assert_report_parent(word: &str, actual: &Analysis) {
    let source: Value = serde_json::from_str(include_str!(
        "../fixtures/deoniman-cross-family-parents.json"
    ))
    .unwrap();
    let row = source["words"][word]
        .as_array()
        .expect(word)
        .iter()
        .find(|row| serde_json::from_value::<Analysis>(row["analysis"].clone()).unwrap() == *actual)
        .expect("uncaptured new report path");
    let mut inverse = actual.clone();
    inverse
        .rules
        .retain(|r| r != "ending.deoniman" && r != "ending.reported_deoni");
    let ending = inverse
        .morphemes
        .iter_mut()
        .find(|m| {
            matches!(
                m.form.as_str(),
                "더니만"
                    | "더니마는"
                    | "다더니"
                    | "는다더니"
                    | "다더니만"
                    | "다더니마는"
                    | "는다더니만"
                    | "는다더니마는"
            )
        })
        .unwrap();
    let plain = matches!(ending.form.as_str(), "더니만" | "더니마는");
    ending.form = if plain {
        "더니"
    } else if ending.form.starts_with("는다") {
        "는다던"
    } else {
        "다던"
    }
    .into();
    if !plain {
        inverse.rules.push("ending.reporting_retrospective".into());
    }
    inverse.rules.sort();
    inverse.rules.dedup();
    assert_eq!(
        inverse,
        serde_json::from_value::<Analysis>(row["inverse"].clone()).unwrap()
    );
    let parent: WordAnalysis = serde_json::from_value(
        source["actual_prior_companions"][row["companion"].as_str().unwrap()].clone(),
    )
    .unwrap();
    assert!(parent.analyses.contains(&inverse), "{word}: {actual:?}");
    assert!(actual.breakdown().is_some());
}
