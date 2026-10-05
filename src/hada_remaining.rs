//! All seventeen retained KRDict -하다 examples in senses 3–6.
use crate::{
    Lemma, LemmaKind, Morpheme, MorphemeKind, doeda_identity::OriginSource, engine::PredicateClass,
};
pub(crate) const AUX_VERB_RULE: &str = "suffix.auxiliary.verb.hada";
pub(crate) const AUX_ADJECTIVE_RULE: &str = "suffix.auxiliary.adjective.hada";
struct Source {
    identity: OriginSource,
    kind: LemmaKind,
    verbal: bool,
    adjectival: bool,
    auxiliary: bool,
}
const SOURCES: &[Source] = &[
    Source {
        identity: OriginSource {
            base: "반짝반짝",
            expected_origins: &[],
            whole_entries: &["krdict:57643", "krdict:57644"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Adverbial,
        verbal: true,
        adjectival: true,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "소곤소곤",
            expected_origins: &[],
            whole_entries: &["krdict:88623"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Adverbial,
        verbal: true,
        adjectival: false,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "덜컹덜컹",
            expected_origins: &[],
            whole_entries: &["krdict:90273"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Adverbial,
        verbal: true,
        adjectival: false,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "달리",
            expected_origins: &[],
            whole_entries: &["krdict:28389"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Adverbial,
        verbal: true,
        adjectival: false,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "돌연",
            expected_origins: &["突然"],
            whole_entries: &["krdict:48636"],
            whole_origins_complete: true,
        },
        kind: LemmaKind::Adverbial,
        verbal: false,
        adjectival: true,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "빨리",
            expected_origins: &[],
            whole_entries: &["krdict:61185"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Adverbial,
        verbal: true,
        adjectival: false,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "잘",
            expected_origins: &[],
            whole_entries: &["krdict:70073"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Adverbial,
        verbal: true,
        adjectival: false,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "따뜻",
            expected_origins: &[],
            whole_entries: &["krdict:57297"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Root,
        verbal: false,
        adjectival: true,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "망",
            expected_origins: &["亡"],
            whole_entries: &["krdict:15942"],
            whole_origins_complete: true,
        },
        kind: LemmaKind::Root,
        verbal: true,
        adjectival: false,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "착",
            expected_origins: &[],
            whole_entries: &["krdict:71732"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Root,
        verbal: false,
        adjectival: true,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "흥",
            expected_origins: &["興"],
            whole_entries: &["krdict:88450"],
            whole_origins_complete: true,
        },
        kind: LemmaKind::Root,
        verbal: true,
        adjectival: false,
        auxiliary: false,
    },
    Source {
        identity: OriginSource {
            base: "듯",
            expected_origins: &[],
            whole_entries: &["krdict:49988"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Nominal,
        verbal: false,
        adjectival: true,
        auxiliary: true,
    },
    Source {
        identity: OriginSource {
            base: "법",
            expected_origins: &["法"],
            whole_entries: &["krdict:58484"],
            whole_origins_complete: true,
        },
        kind: LemmaKind::Nominal,
        verbal: false,
        adjectival: true,
        auxiliary: true,
    },
    Source {
        identity: OriginSource {
            base: "뻔",
            expected_origins: &[],
            whole_entries: &["krdict:66639"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Nominal,
        verbal: false,
        adjectival: true,
        auxiliary: true,
    },
    Source {
        identity: OriginSource {
            base: "양",
            expected_origins: &[],
            whole_entries: &["krdict:67248", "krdict:67249"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Nominal,
        verbal: true,
        adjectival: true,
        auxiliary: true,
    },
    Source {
        identity: OriginSource {
            base: "척",
            expected_origins: &[],
            whole_entries: &["krdict:72226"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Nominal,
        verbal: true,
        adjectival: false,
        auxiliary: true,
    },
    Source {
        identity: OriginSource {
            base: "체",
            expected_origins: &[],
            whole_entries: &["krdict:72227"],
            whole_origins_complete: false,
        },
        kind: LemmaKind::Nominal,
        verbal: true,
        adjectival: false,
        auxiliary: true,
    },
];
fn source(base: &str) -> Option<&'static Source> {
    SOURCES.iter().find(|s| s.identity.base == base)
}
fn formation(
    head: &str,
    auxiliary: bool,
    adjective: bool,
) -> Option<(&'static str, LemmaKind, PredicateClass)> {
    let s = source(head.strip_suffix("하다")?)?;
    if s.auxiliary != auxiliary || !(if adjective { s.adjectival } else { s.verbal }) {
        return None;
    }
    Some((
        s.identity.base,
        s.kind,
        if adjective {
            PredicateClass::Adjective
        } else {
            PredicateClass::Verb
        },
    ))
}
pub(crate) fn verbal(head: &str) -> Option<(&'static str, LemmaKind, PredicateClass)> {
    formation(head, false, false)
}
pub(crate) fn adjectival(head: &str) -> Option<(&'static str, LemmaKind, PredicateClass)> {
    formation(head, false, true)
}
pub(crate) fn auxiliary_verbal(head: &str) -> Option<(&'static str, LemmaKind, PredicateClass)> {
    formation(head, true, false)
}
pub(crate) fn auxiliary_adjectival(
    head: &str,
) -> Option<(&'static str, LemmaKind, PredicateClass)> {
    formation(head, true, true)
}
fn licensed_classes(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<(&'static Source, bool, bool)> {
    let s = source(&lemma.text)?;
    if lemma.kind != s.kind
        || !morphs
            .first()
            .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "하다")
    {
        return None;
    }
    let (verb, adjective) = if s.auxiliary {
        (AUX_VERB_RULE, AUX_ADJECTIVE_RULE)
    } else {
        (crate::hada_suffix::RULE, crate::hada_suffix::ADJECTIVE_RULE)
    };
    let v = s.verbal && rules.iter().any(|r| r == verb);
    let a = s.adjectival && rules.iter().any(|r| r == adjective);
    (v || a).then_some((s, v, a))
}
pub(crate) fn owned_source(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<&'static OriginSource> {
    licensed_classes(lemma, rules, morphs).map(|(s, _, _)| &s.identity)
}
pub(crate) fn owner_class(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<PredicateClass> {
    licensed_classes(lemma, rules, morphs).map(|(_, v, a)| match (v, a) {
        (true, true) => PredicateClass::VerbOrAdjective,
        (true, false) => PredicateClass::Verb,
        (false, true) => PredicateClass::Adjective,
        _ => unreachable!(),
    })
}

/// Native auxiliary notes constrain this new suffix owner, independently of
/// the preserved unsplit lexical hypotheses. Unknown left classes stay open.
pub(crate) fn auxiliary_attachment_allowed(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
    connector: Option<&str>,
    previous: Option<PredicateClass>,
    forced_class: Option<PredicateClass>,
) -> bool {
    let Some((s, verbal, adjectival)) = licensed_classes(lemma, rules, morphs) else {
        return true;
    };
    if !s.auxiliary || connector.is_none() {
        return true;
    }
    let connector = connector.unwrap();
    let verbal = verbal && !matches!(forced_class, Some(PredicateClass::Adjective));
    let adjectival = adjectival && !matches!(forced_class, Some(PredicateClass::Verb));
    match s.identity.base {
        "듯" => matches!(connector, "은" | "는" | "을"),
        "법" => connector == "을" && !matches!(previous, Some(PredicateClass::Copula)),
        "뻔" => {
            connector == "을"
                && !matches!(
                    previous,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
        }
        "양" => {
            matches!(connector, "은" | "는")
                && (!matches!(previous, Some(PredicateClass::Copula)) || adjectival)
                && (verbal || adjectival)
        }
        "척" | "체" => {
            matches!(connector, "은" | "는") && !matches!(previous, Some(PredicateClass::Copula))
        }
        _ => unreachable!(),
    }
}

pub(crate) fn auxiliary_base(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<&'static str> {
    licensed_classes(lemma, rules, morphs)
        .and_then(|(s, _, _)| s.auxiliary.then_some(s.identity.base))
}
