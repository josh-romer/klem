//! Separate proof for additions after the immutable ending-family snapshots.
use klem::{Analysis, WordAnalysis};
use serde_json::Value;
use std::sync::OnceLock;

pub fn assert_omission_parent(word: &str, a: &Analysis) {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    let source = SOURCE.get_or_init(|| {
        serde_json::from_str(include_str!("../copula-expectation-full-source.json")).unwrap()
    });
    assert!(a.rules.iter().any(|r| r == "copula.omitted_ending"));
    assert!(a.breakdown().is_some());
    let rows = source["individual_additions"].as_array().unwrap();
    let row = rows
        .iter()
        .find(|r| {
            r["surface"] == word
                && serde_json::from_value::<Analysis>(r["after"].clone()).unwrap() == *a
        })
        .expect("missing separate omission attribution");
    let mut inverse = a.clone();
    inverse.rules.retain(|r| r != "copula.omitted_ending");
    inverse.rules.push("boundary.eu".into());
    inverse.rules.sort();
    inverse.rules.dedup();
    assert!(
        row["explicit_parents"].as_array().unwrap().iter().any(|p| {
            let parent: WordAnalysis =
                serde_json::from_value(source["explicit_parents"][p.as_str().unwrap()].clone())
                    .unwrap();
            parent.analyses.contains(&inverse)
        }),
        "missing exact explicit parent {word}: {a:?}"
    );
}
