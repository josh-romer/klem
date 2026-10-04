//! Development-only source correction overlays for immutable prior fixtures.
//! Classify the ordered owner, never the last lemma of an arbitrary analysis.
use klem::{Analysis, LemmaKind, MorphemeKind, breakdown::Component};

pub fn reviewed_removal(a: &Analysis) -> bool {
    fn canonical(form: &str) -> bool {
        matches!(
            form,
            "으냐"
                | "으냐고"
                | "으냐는"
                | "으냐며"
                | "으냐면서"
                | "으냐니"
                | "으냔"
                | "으냔다"
                | "으냬"
                | "으냐지만"
                | "으냐니까"
                | "으냐느니"
                | "으냐면"
                | "으냐던데"
                | "으냐는구나"
                | "으냐는군"
                | "으냐더군"
                | "으냐더군요"
        )
    }
    if !a
        .morphemes
        .iter()
        .any(|m| m.kind == MorphemeKind::Ending && canonical(&m.form))
    {
        return false;
    }
    let mut owner = None;
    for component in a
        .breakdown()
        .expect("canonical question needs an ordered owner")
    {
        match component {
            Component::Lemma(i) => {
                owner = matches!(
                    a.lemmas[i].kind,
                    LemmaKind::Predicate | LemmaKind::Auxiliary | LemmaKind::Copula
                )
                .then(|| {
                    a.lemmas[i]
                        .text
                        .strip_suffix('다')
                        .expect("predicate dictionary form")
                });
            }
            Component::Morpheme(i) => {
                let m = &a.morphemes[i];
                if m.kind == MorphemeKind::Suffix && m.form == "답다" {
                    owner = Some("답");
                }
                if m.kind == MorphemeKind::Ending && canonical(&m.form) {
                    let stem =
                        owner.expect("question ending's immediate predicate or suffix owner");
                    let last = stem.chars().last().expect("nonempty owner") as u32;
                    if (0xAC00..=0xD7A3).contains(&last) && matches!((last - 0xAC00) % 28, 0 | 8) {
                        return true;
                    }
                }
            }
        }
    }
    false
}
