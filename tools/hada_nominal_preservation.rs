//! Prove sourced -하다 paths against unchanged historical whole-head parents.
use klem::{LemmaKind, MorphemeKind, WordAnalysis, breakdown::Component};
use serde_json::Value;
use std::sync::OnceLock;
fn owners() -> &'static Vec<Value> {
    static OWNERS: OnceLock<Vec<Value>> = OnceLock::new();
    OWNERS.get_or_init(|| {
        let fixture: Value =
            serde_json::from_str(include_str!("../tests/fixtures/hada-nominal-sources.json"))
                .unwrap();
        let remaining: Value = serde_json::from_str(include_str!(
            "../tests/fixtures/hada-remaining-sources.json"
        ))
        .unwrap();
        fixture["owners"]
            .as_array()
            .unwrap()
            .iter()
            .chain(remaining["owners"].as_array().unwrap())
            .cloned()
            .collect()
    })
}
fn kind(owner: &Value) -> LemmaKind {
    match owner["base_role"].as_str().unwrap() {
        "nominal" | "bound_noun" => LemmaKind::Nominal,
        "adverbial" => LemmaKind::Adverbial,
        "root" => LemmaKind::Root,
        _ => panic!("unsupported source base role"),
    }
}
/// Recognize a scoped nominal owner independently of the analysis-wide rule flags.
pub fn is_addition(a: &klem::Analysis) -> bool {
    a.breakdown().is_some_and(|order| {
        order.windows(2).any(|pair| {
            let [Component::Lemma(l), Component::Morpheme(m)] = pair else {
                return false;
            };
            a.morphemes[*m].kind == MorphemeKind::Suffix
                && a.morphemes[*m].form == "하다"
                && owners().iter().any(|o| {
                    o["base"].as_str() == Some(&a.lemmas[*l].text) && kind(o) == a.lemmas[*l].kind
                })
        })
    })
}
/// Strip only new senses 3–6 after proving their exact retained whole parents.
#[allow(dead_code)] // Shared test helper; not every importing target needs projection.
pub fn project_remaining(actual: &WordAnalysis) -> WordAnalysis {
    let mut frozen = actual.clone();
    frozen.analyses.retain(|a| {
        !a.breakdown().is_some_and(|order| {
            order.windows(2).any(|pair| {
                let [Component::Lemma(l), Component::Morpheme(m)] = pair else {
                    return false;
                };
                a.morphemes[*m].kind == MorphemeKind::Suffix
                    && a.morphemes[*m].form == "하다"
                    && owners().iter().any(|o| {
                        !matches!(o["sense_id"].as_str(), Some("1" | "2"))
                            && o["base"].as_str() == Some(&a.lemmas[*l].text)
                            && kind(o) == a.lemmas[*l].kind
                    })
            })
        })
    });
    assert_preserved(actual, &frozen);
    frozen
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
        // COV-017bx: the distinct friendly final preserves the exact old
        // adnominal parent. It can coexist with an earlier sourced 하다 split;
        // after restoring the final, keep proving that split below as well.
        let command_parent = if addition
            .rules
            .iter()
            .any(|r| r == "ending.friendly_command.n")
        {
            assert!(
                addition.breakdown().is_some(),
                "command needs owned components"
            );
            let mut parent = addition.clone();
            parent.rules.retain(|r| r != "ending.friendly_command.n");
            let ending = parent
                .morphemes
                .iter_mut()
                .rev()
                .find(|m| m.kind == MorphemeKind::Ending)
                .expect("command needs a final ending");
            assert_eq!(ending.form, "ㄴ");
            ending.form = "은".into();
            Some(parent)
        } else {
            None
        };
        let addition = command_parent.as_ref().unwrap_or(addition);
        if frozen.analyses.contains(addition) {
            continue;
        }
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
            if addition.morphemes[*m].kind != MorphemeKind::Suffix
                || addition.morphemes[*m].form != "하다"
            {
                continue;
            }
            let Some(owner) = owners().iter().find(|o| {
                o["base"].as_str() == Some(&addition.lemmas[*l].text)
                    && kind(o) == addition.lemmas[*l].kind
            }) else {
                continue;
            };
            let rules: Vec<_> = owner["supported_predicate_classes"]
                .as_array()
                .unwrap()
                .iter()
                .map(|pos| match pos.as_str().unwrap() {
                    "동사" => "suffix.verb.hada",
                    "형용사" => "suffix.adjective.hada",
                    "보조 동사" => "suffix.auxiliary.verb.hada",
                    "보조 형용사" => "suffix.auxiliary.adjective.hada",
                    _ => panic!("unsupported source predicate class"),
                })
                .filter(|rule| addition.rules.iter().any(|r| r == rule))
                .collect();
            assert!(!rules.is_empty(), "owner cannot borrow an unsourced class");
            insertions.push((
                *l,
                *m,
                owner["whole_head"].as_str().unwrap().to_owned(),
                owner["sense_id"] == "6",
            ));
            added_rules.extend(rules);
        }
        assert!(
            !insertions.is_empty(),
            "unattributed addition {}: {addition:?}",
            actual.normalized
        );
        insertions.sort_by_key(|(_, m, _, _)| *m);
        for (l, m, head, _) in insertions.iter().rev() {
            restored.lemmas[*l].text = head.clone();
            restored.morphemes.remove(*m);
            for path in &mut restored.spelling_paths {
                for recovery in path {
                    assert_ne!(
                        recovery.morpheme_index, *m,
                        "inserted suffix cannot borrow recovery evidence"
                    );
                    if recovery.morpheme_index > *m {
                        recovery.morpheme_index -= 1;
                    }
                }
            }
        }
        let mut found = false;
        for parent in &frozen.analyses {
            if insertions.iter().any(|(l, _, head, auxiliary)| {
                parent.lemmas.get(*l).is_none_or(|p| {
                    p.text != *head
                        || !(p.kind == LemmaKind::Predicate
                            || (*auxiliary && p.kind == LemmaKind::Auxiliary))
                })
            }) {
                continue;
            }
            for (l, _, _, _) in &insertions {
                restored.lemmas[*l].kind = parent.lemmas[*l].kind;
            }
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
