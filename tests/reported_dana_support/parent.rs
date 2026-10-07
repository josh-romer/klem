use klem::{Analysis, MorphemeKind, WordAnalysis};
use serde_json::Value;
use std::sync::OnceLock;

pub fn assert_report_parent(family: &str, word: &str, actual: &Analysis) {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    let source = SOURCE.get_or_init(|| {
        serde_json::from_str(include_str!(
            "../fixtures/reported-dana-cross-family-parents.json"
        ))
        .unwrap()
    });
    let rows = source["individual_additions"].as_array().unwrap();
    let matching: Vec<_> = rows
        .iter()
        .filter(|row| {
            row["family"] == family
                && row["surface"] == word
                && serde_json::from_value::<Analysis>(row["analysis"].clone()).unwrap() == *actual
        })
        .collect();
    assert_eq!(
        matching.len(),
        1,
        "uncaptured {family} report path: {word}: {actual:?}"
    );
    let row = matching[0];
    assert_eq!(row["contextual_verdict"], "unjudged");
    assert_eq!(
        actual
            .rules
            .iter()
            .filter(|r| *r == "ending.reported_dana")
            .count(),
        1
    );
    assert!(actual.breakdown().is_some());
    assert!(
        actual
            .rules
            .iter()
            .all(|r| klem::rule_explanation(r).is_some())
    );
    let mut inverse = actual.clone();
    inverse.rules.retain(|r| r != "ending.reported_dana");
    let endings: Vec<_> = inverse
        .morphemes
        .iter_mut()
        .filter(|m| m.kind == MorphemeKind::Ending && matches!(m.form.as_str(), "다나" | "는다나"))
        .collect();
    assert_eq!(endings.len(), 1);
    let ending = endings.into_iter().next().unwrap();
    ending.form = if ending.form == "는다나" {
        "는다고"
    } else {
        "다고"
    }
    .into();
    assert_eq!(
        inverse,
        serde_json::from_value::<Analysis>(row["exact_parent"].clone()).unwrap()
    );
    let parent_surface = row["parent_surface"].as_str().unwrap();
    assert!(word.match_indices("다나").any(|(offset, _)| {
        format!("{}다고{}", &word[..offset], &word[offset + "다나".len()..]) == parent_surface
    }));
    let parent: WordAnalysis =
        serde_json::from_value(source["actual_prior_companions"][parent_surface].clone()).unwrap();
    assert!(parent.analyses.contains(&inverse), "{word}: {actual:?}");
}
