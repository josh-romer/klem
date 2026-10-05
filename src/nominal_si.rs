//! KRDict 71567: finite noun + -시 formations, with separately sourced passives.
use crate::{Lemma, LemmaKind, Morpheme, MorphemeKind, doeda_identity::OriginSource};

pub(crate) const RULE: &str = "suffix.nominal.si";

// Each full form is an explicit -시 example and has an independently recorded noun base.
pub(crate) fn nominal(head: &str) -> Option<&'static str> {
    match head {
        "동일시" => Some("동일"),
        "문제시" => Some("문제"),
        "야만시" => Some("야만"),
        "의문시" => Some("의문"),
        "적대시" => Some("적대"),
        "죄악시" => Some("죄악"),
        "중요시" => Some("중요"),
        _ => None,
    }
}

// A listed nominal is not sufficient to license -되다. These five complete native
// verb entries record both 視 and 되다 in their whole-head origin and passive senses.
pub(crate) fn passive(head: &str) -> Option<&'static str> {
    match head {
        "동일시되다" => Some("동일"),
        "문제시되다" => Some("문제"),
        "의문시되다" => Some("의문"),
        "죄악시되다" => Some("죄악"),
        "중요시되다" => Some("중요"),
        _ => None,
    }
}

pub(crate) fn owner(lemma: &Lemma, rules: &[String], morphs: &[Morpheme]) -> bool {
    morphs
        .first()
        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "시")
        && lemma.kind == LemmaKind::Nominal
        && matches!(
            lemma.text.as_str(),
            "동일" | "문제" | "야만" | "의문" | "적대" | "죄악" | "중요"
        )
        && rules.iter().any(|r| r == RULE)
}

pub(crate) fn passive_owner(lemma: &Lemma, rules: &[String], morphs: &[Morpheme]) -> bool {
    owner(lemma, rules, morphs)
        && matches!(
            lemma.text.as_str(),
            "동일" | "문제" | "의문" | "죄악" | "중요"
        )
        && rules.iter().any(|r| r == "suffix.verb.doeda")
        && morphs
            .get(1)
            .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "되다")
}

pub(crate) fn identity(base: &str) -> Option<&'static OriginSource> {
    SOURCES.iter().find(|source| source.base == base)
}

const SOURCES: &[OriginSource] = &[
    OriginSource {
        base: "동일",
        expected_origins: &["同一"],
        whole_entries: &["krdict:48642"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "문제",
        expected_origins: &["問題"],
        whole_entries: &["krdict:56919"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "의문",
        expected_origins: &["疑問"],
        whole_entries: &["krdict:71413"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "죄악",
        expected_origins: &["罪惡"],
        whole_entries: &["krdict:90804"],
        whole_origins_complete: true,
    },
    OriginSource {
        base: "중요",
        expected_origins: &["重要"],
        whole_entries: &["krdict:77024"],
        whole_origins_complete: true,
    },
];
