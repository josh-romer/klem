//! Prove additive noun-hada paths against unchanged historical whole-head parents.
use klem::{LemmaKind, MorphemeKind, WordAnalysis, breakdown::Component};
use serde_json::Value;
use std::sync::OnceLock;
fn owners() -> &'static Vec<Value> {
    static OWNERS: OnceLock<Vec<Value>> = OnceLock::new();
    OWNERS.get_or_init(|| {
        let fixture: Value =
            serde_json::from_str(include_str!("../tests/fixtures/hada-nominal-sources.json"))
                .unwrap();
        fixture["owners"].as_array().unwrap().clone()
    })
}
/// Recognize a scoped nominal owner independently of the analysis-wide rule flags.
pub fn is_addition(a: &klem::Analysis) -> bool {
    a.breakdown().is_some_and(|order| {
        order.windows(2).any(|pair| {
            let [Component::Lemma(l), Component::Morpheme(m)] = pair else {
                return false;
            };
            a.lemmas[*l].kind == LemmaKind::Nominal
                && a.morphemes[*m].kind == MorphemeKind::Suffix
                && a.morphemes[*m].form == "하다"
                && owners()
                    .iter()
                    .any(|o| o["base"].as_str() == Some(&a.lemmas[*l].text))
        })
    })
}
/// Preserve every prior path in order; each addition must invert exactly to a prior parent.
pub fn assert_preserved(actual: &WordAnalysis, frozen: &WordAnalysis) {
    assert_eq!(actual.normalized, frozen.normalized);
    let retained: Vec<_> = actual
        .analyses
        .iter()
        .filter(|a| frozen.analyses.contains(a))
        .cloned()
        .collect();
    assert_eq!(retained, frozen.analyses, "{}", actual.normalized);
    for addition in actual
        .analyses
        .iter()
        .filter(|a| !frozen.analyses.contains(a))
    {
        assert!(
            is_addition(addition),
            "unattributed addition {}",
            actual.normalized
        );
        let order = addition
            .breakdown()
            .expect("new path needs ordered ownership");
        let mut restored = addition.clone();
        let mut insertions = Vec::new();
        let mut added_rules = Vec::new();
        for pair in order.windows(2) {
            let [Component::Lemma(l), Component::Morpheme(m)] = pair else {
                continue;
            };
            if addition.lemmas[*l].kind != LemmaKind::Nominal
                || addition.morphemes[*m].kind != MorphemeKind::Suffix
                || addition.morphemes[*m].form != "하다"
            {
                continue;
            }
            let Some(owner) = owners()
                .iter()
                .find(|o| o["base"].as_str() == Some(&addition.lemmas[*l].text))
            else {
                continue;
            };
            let rule = if owner["sense_id"] == "1" {
                "suffix.verb.hada"
            } else {
                "suffix.adjective.hada"
            };
            assert!(addition.rules.iter().any(|r| r == rule));
            insertions.push((*l, *m, owner["whole_head"].as_str().unwrap().to_owned()));
            added_rules.push(rule);
        }
        assert!(
            !insertions.is_empty(),
            "unattributed addition {}: {addition:?}",
            actual.normalized
        );
        insertions.sort_by_key(|(_, m, _)| *m);
        for (l, m, head) in insertions.into_iter().rev() {
            restored.lemmas[l].text = head;
            restored.lemmas[l].kind = LemmaKind::Predicate;
            restored.morphemes.remove(m);
            for path in &mut restored.spelling_paths {
                for recovery in path {
                    assert_ne!(
                        recovery.morpheme_index, m,
                        "inserted suffix cannot borrow recovery evidence"
                    );
                    if recovery.morpheme_index > m {
                        recovery.morpheme_index -= 1;
                    }
                }
            }
        }
        let mut found = false;
        for parent in &frozen.analyses {
            let mut rules = parent.rules.clone();
            rules.extend(added_rules.iter().map(|r| (*r).to_owned()));
            rules.sort();
            rules.dedup();
            if rules != addition.rules {
                continue;
            }
            restored.rules = parent.rules.clone();
            if restored == *parent {
                found = true;
                break;
            }
        }
        assert!(
            found,
            "new path has no unchanged whole-head parent {}: {addition:?}",
            actual.normalized
        );
    }
}
