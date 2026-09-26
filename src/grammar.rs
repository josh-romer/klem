//! Explicit morphotactics and reverse spelling rules. No statistical weights.
use crate::hangul::*;
use std::{collections::HashMap, sync::OnceLock};

// Source-listed adverb roots, not a general 이/히 spelling heuristic. The
// related 하다 lemma is a lookup normalization; the suffix attaches to the root.
// KRDict 88504 and NIKL's 1999 spelling discussion; see docs/adverb-inventory.json.
pub(crate) const ADVERB_HADA_ROOTS: &[(&str, &str)] = &[
    ("익숙", "히"),
    ("특별", "히"),
    ("기웃", "이"),
    ("버젓", "이"),
    ("번듯", "이"),
    ("반듯", "이"),
    ("지긋", "이"),
    ("산뜻", "이"),
    ("깨끗", "이"),
    ("깊숙", "이"),
    ("가득", "히"),
    ("가뿐", "히"),
    ("가지런", "히"),
    ("나란", "히"),
    ("날렵", "히"),
    ("냉랭", "히"),
    ("냉정", "히"),
    ("냉철", "히"),
    ("냉혹", "히"),
    ("너끈", "히"),
    ("넉넉", "히"),
    ("느슨", "히"),
    ("능", "히"),
    ("다급", "히"),
    ("다분", "히"),
    ("다정", "히"),
    ("다행", "히"),
    ("단단", "히"),
    ("단순", "히"),
    ("단정", "히"),
    ("단호", "히"),
    ("담담", "히"),
    ("마땅", "히"),
    ("막연", "히"),
    ("만만", "히"),
    ("말끔", "히"),
    ("망연", "히"),
    ("맹렬", "히"),
    ("멀뚱", "히"),
    ("멀쩡", "히"),
    ("멍청", "히"),
    ("멍", "히"),
    ("무사", "히"),
    ("부단", "히"),
    ("부지런", "히"),
    ("분명", "히"),
    ("분분", "히"),
    ("분주", "히"),
    ("안녕", "히"),
    ("영원", "히"),
    ("조용", "히"),
    ("엄격", "히"),
    ("과감", "히"),
    ("급급", "히"),
    ("꼼꼼", "히"),
    ("도저", "히"),
    ("무단", "히"),
    ("열심", "히"),
    ("상당", "히"),
];

// Source-listed adverbs formed from adverbs and repeated nominal bases.
// Repeated bases remain one component; this is not arbitrary compound splitting.
pub(crate) const ADVERB_ADVERB_ROOTS: &[(&str, &str)] = &[
    ("곰곰", "이"),
    ("더욱", "이"),
    ("일찍", "이"),
    ("오뚝", "이"),
    ("히죽", "이"),
    ("생긋", "이"),
    ("가만", "히"),
    ("단연", "히"),
];
pub(crate) const ADVERB_NOMINAL_ROOTS: &[&str] = &[
    "겹겹", "곳곳", "낱낱", "몫몫", "샅샅", "앞앞", "집집", "누누", "다달", "번번", "올올", "일일",
    "점점", "줄줄", "짬짬", "첩첩", "층층", "켜켜", "칸칸", "틈틈", "푼푼",
];

#[derive(Debug, Clone)]
pub(crate) struct Recovery {
    pub stem: String,
    pub rules: Vec<String>,
}
fn push(out: &mut Vec<Recovery>, stem: String, rule: &str) {
    if !stem.is_empty() && has_hangul(&stem) {
        out.push(Recovery {
            stem,
            rules: vec![rule.into()],
        });
    }
}

/// Invert stem + 아/어, including contractions. Lexical classes are hypotheses.
pub(crate) fn aeo(surface: &str) -> Vec<Recovery> {
    let mut out = Vec::new();
    for ending in ["아", "어", "여"] {
        if let Some(stem) = surface.strip_suffix(ending).filter(|s| !s.is_empty()) {
            if (ending == "아" && bright(stem) && coda(stem) != Some(20) && !stem.ends_with('하'))
                || (ending == "어"
                    && (!bright(stem) || coda(stem) == Some(20))
                    && !stem.ends_with('하'))
            {
                push(&mut out, stem.into(), "boundary.regular");
            }
            if ending == "여" && stem.ends_with('하') {
                push(&mut out, stem.into(), "irregular.ha");
            }
            if let Some((_, v, t)) = last(stem) {
                if t == 8 && ((ending == "아") == bright(stem)) && ending != "여" {
                    push(
                        &mut out,
                        replace_last(stem, v, 7).unwrap(),
                        "irregular.digeut",
                    );
                }
                if t == 0 && ending != "여" && ((ending == "아") == bright(stem)) {
                    push(
                        &mut out,
                        replace_last(stem, v, 19).unwrap(),
                        "irregular.siot",
                    );
                }
            }
        }
    }
    if let Some((_, v, 0)) = last(surface) {
        // Contraction of an identical vowel, or 어 after 애/에.
        if matches!(v, 0 | 4 | 1 | 5) && !surface.ends_with('하') {
            push(&mut out, surface.into(), "contraction.identical");
        }
        for (from, to) in [(9, 8), (14, 13), (10, 11), (6, 20)] {
            if v == from {
                push(
                    &mut out,
                    replace_last(surface, to, 0).unwrap(),
                    "contraction.vowel",
                );
            }
        }
        if v == V_A || v == V_EO {
            let prefix = &surface[..surface.len() - 3];
            if (v == V_A) == bright(prefix) {
                push(
                    &mut out,
                    replace_last(surface, 18, 0).unwrap(),
                    "deletion.eu",
                );
            }
        }
        if let Some(prefix) = surface.strip_suffix('해') {
            push(&mut out, format!("{prefix}하"), "irregular.ha");
        }
        // Article 35, supplement 1: 놓아 -> 놔, including compounds.
        // This is lexical, not a general ㅎ-deletion rule (좋아 != 좌).
        if let Some(prefix) = surface.strip_suffix('놔') {
            push(&mut out, format!("{prefix}놓"), "contraction.noh");
        }
        if surface == "퍼" {
            push(&mut out, "푸".into(), "irregular.pu");
        }
        // 르 doubling: 몰라 -> 모르; 불러 -> 부르.
        if surface.ends_with('라') || surface.ends_with('러') {
            let prefix = &surface[..surface.len() - 3];
            if let Some((_, pv, 8)) = last(prefix)
                && surface.ends_with('라') == bright(prefix)
            {
                push(
                    &mut out,
                    format!("{}르", replace_last(prefix, pv, 0).unwrap()),
                    "irregular.reu",
                );
            }
            if surface.ends_with("르러") {
                push(
                    &mut out,
                    surface[..surface.len() - 3].into(),
                    "irregular.reo",
                );
            }
        }
        // ㅎ contraction (class membership remains unverified).
        for (from, to) in [(1, 0), (3, 2), (5, 4), (7, 6)] {
            if v == from {
                push(
                    &mut out,
                    replace_last(surface, to, 27).unwrap(),
                    "irregular.hieut",
                );
            }
        }
        for (form, stem) in [
            ("그래", "그렇"),
            ("이래", "이렇"),
            ("저래", "저렇"),
            ("어때", "어떻"),
        ] {
            if surface == form {
                push(&mut out, stem.into(), "irregular.hieut");
            }
        }
    }
    // ㅂ -> 우/오 + 아/어. Recover from both contracted and expanded spellings.
    let intermediates = out.clone();
    for r in intermediates {
        for vowel in ['우', '오'] {
            if let Some(prefix) = r.stem.strip_suffix(vowel)
                && let Some((_, v, 0)) = last(prefix)
            {
                // Before 아/어, 돕/곱 require 오; other stems require 우.
                // Before (으) endings both classes use 우 (recover_eu_open).
                if (vowel == '오') == matches!(prefix, "도" | "고") {
                    push(
                        &mut out,
                        replace_last(prefix, v, 17).unwrap(),
                        "irregular.bieup",
                    );
                }
            }
        }
    }
    out.sort_by(|a, b| (&a.stem, &a.rules).cmp(&(&b.stem, &b.rules)));
    out.dedup_by(|a, b| a.stem == b.stem && a.rules == b.rules);
    out
}

#[derive(Debug, Clone, Copy)]
pub(crate) enum Boundary {
    Literal,
    Consonant,
    EuFull,
    EuZero,
    Attached(u32),
    Aeo,
    Copular,
    ZeroCopula,
    // Omitted 이 before a reviewed ending; 0 = separate suffix, otherwise
    // the ending's initial consonant is attached to the nominal syllable.
    OmittedCopula(u32),
    HaDeletion,
    HaAspiration,
}

#[derive(Debug)]
pub(crate) struct Ending {
    pub suffix: &'static str,
    pub form: &'static str,
    pub boundary: Boundary,
    pub connector: bool,
}

pub(crate) const AUXILIARY_CONNECTORS: &[&str] = &[
    "어",
    "고",
    "지",
    "게",
    "어야",
    "은",
    "는",
    "을",
    "음",
    "으려",
    "으려고",
    "기로",
    "자고",
    "다",
    "다가",
    "는가",
    "은가",
    "던가",
    "나",
    "을까",
    "으면",
    "기",
    "기도",
    "기는",
    "기만",
    "고자",
];

pub(crate) fn recover(surface: &str, suffix: &str, boundary: Boundary) -> Vec<Recovery> {
    let Some(base) = surface.strip_suffix(suffix) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    match boundary {
        Boundary::HaDeletion | Boundary::HaAspiration => {
            // Article 40: stop-final bases lose all of 하; vowels/sonorants
            // retain ㅎ, which aspirates the following onset. Complex codas
            // need a separate pronunciation audit, so are not guessed here.
            let allowed = match boundary {
                Boundary::HaDeletion => matches!(
                    coda(base),
                    Some(1 | 2 | 7 | 17 | 19 | 20 | 22 | 23 | 24 | 25 | 26)
                ),
                _ => matches!(coda(base), Some(0 | 4 | 8 | 16 | 21)),
            };
            if allowed {
                push(
                    &mut out,
                    format!("{base}하"),
                    match boundary {
                        Boundary::HaDeletion => "deletion.ha",
                        _ => "contraction.ha_aspiration",
                    },
                );
            }
        }
        Boundary::Aeo => return aeo(base),
        Boundary::OmittedCopula(t) => {
            let nominal = if t == 0 {
                Some(base.to_owned())
            } else {
                last(base).and_then(|(_, v, actual)| {
                    (actual == t).then(|| replace_last(base, v, 0).unwrap())
                })
            };
            if let Some(nominal) = nominal {
                if coda(&nominal) == Some(0) {
                    push(&mut out, format!("{nominal}이"), "copula.omitted_ending");
                } else if let Some(rule) = crate::pronunciation::assumption(&nominal, 2) {
                    out.push(Recovery {
                        stem: format!("{nominal}이"),
                        rules: vec!["copula.omitted_ending".into(), rule.into()],
                    });
                }
            }
        }
        Boundary::Copular => {
            if base.ends_with('이') || base == "아니" {
                push(&mut out, base.into(), "boundary.copular");
            }
        }
        Boundary::ZeroCopula => {
            if coda(base) == Some(0) {
                push(&mut out, format!("{base}이"), "copula.zero");
            } else if let Some(rule) = crate::pronunciation::assumption(base, 2) {
                out.push(Recovery {
                    stem: format!("{base}이"),
                    rules: vec!["copula.zero".into(), rule.into()],
                });
            }
        }
        Boundary::Literal => {
            let loses_l = drops_rieul(suffix);
            if !loses_l || coda(base) != Some(8) {
                push(&mut out, base.into(), "boundary.regular");
            }
            if loses_l && coda(base) == Some(0) {
                let (_, v, _) = last(base).unwrap();
                push(
                    &mut out,
                    replace_last(base, v, 8).unwrap(),
                    "deletion.rieul",
                );
            }
        }
        Boundary::Consonant => {
            if coda(base).is_some_and(|t| t != 0 && t != 8) {
                push(&mut out, base.into(), "boundary.consonant");
            }
        }
        Boundary::EuFull => {
            if let Some((_, v, t)) = last(base) {
                if t != 0 && t != 8 {
                    push(&mut out, base.into(), "boundary.eu");
                }
                if t == 8 {
                    push(
                        &mut out,
                        replace_last(base, v, 7).unwrap(),
                        "irregular.digeut",
                    );
                }
                if t == 0 {
                    push(
                        &mut out,
                        replace_last(base, v, 19).unwrap(),
                        "irregular.siot",
                    );
                }
            }
        }
        Boundary::EuZero => {
            let loses_l = drops_rieul(suffix);
            if coda(base) == Some(0) || (!loses_l && coda(base) == Some(8)) {
                push(&mut out, base.into(), "boundary.eu");
            }
            if loses_l && coda(base) == Some(0) {
                let (_, v, _) = last(base).unwrap();
                push(
                    &mut out,
                    replace_last(base, v, 8).unwrap(),
                    "deletion.rieul",
                );
            }
            recover_eu_open(base, &mut out, true);
        }
        Boundary::Attached(t) => {
            if t == 16
                && let Some((_, v, 10)) = last(base)
            {
                push(
                    &mut out,
                    replace_last(base, v, 8).unwrap(),
                    "boundary.attached",
                );
            }
            if let Some((_, v, final_t)) = last(base)
                && final_t == t
            {
                let stem = replace_last(base, v, 0).unwrap();
                push(&mut out, stem.clone(), "boundary.attached");
                if t != 16 {
                    push(
                        &mut out,
                        replace_last(base, v, 8).unwrap(),
                        "deletion.rieul",
                    );
                }
                if (t != 17 || suffix == "시다")
                    && !matches!(
                        suffix,
                        "다" | "다고" | "다는" | "다면" | "답니다" | "다거나" | "다든가"
                    )
                {
                    recover_eu_open(&stem, &mut out, true);
                }
            }
        }
    }
    out
}

// Stem-final ㄹ drops before ㄴ/ㅂ/ㅅ-initial endings and -오.
// Attached consonants are handled separately by Boundary::Attached.
fn drops_rieul(suffix: &str) -> bool {
    suffix.starts_with('오')
        || suffix
            .chars()
            .next()
            .and_then(split)
            .is_some_and(|(initial, _, _)| matches!(initial, 2 | 7 | 9))
}

fn recover_eu_open(base: &str, out: &mut Vec<Recovery>, allow_h: bool) {
    if let Some(prefix) = base.strip_suffix('우')
        && let Some((_, v, 0)) = last(prefix)
    {
        push(out, replace_last(prefix, v, 17).unwrap(), "irregular.bieup");
    }
    if allow_h && let Some((_, v, 0)) = last(base) {
        push(out, replace_last(base, v, 27).unwrap(), "irregular.hieut");
    }
}

pub(crate) fn endings() -> &'static [Ending] {
    static RULES: OnceLock<Vec<Ending>> = OnceLock::new();
    RULES.get_or_init(|| {
        use Boundary::*;
        let mut out = Vec::new();
        for suffix in [
            "다",
            "답니다",
            "다거나",
            "다든가",
            "다가",
            "고자",
            "건대",
            "구나",
            "군",
            "군요",
            "는가",
            "는가요",
            "는데도",
            "는데다가",
            "느냐",
            "느라고",
            "고",
            "고서",
            "고요",
            "지만",
            "지만요",
            "지",
            "지요",
            "죠",
            "게",
            "게요",
            "도록",
            "듯",
            "듯이",
            "기에",
            "길래",
            "든지",
            "든가",
            "든",
            "더라도",
            "더니",
            "더라",
            "더라고",
            "더라는",
            "더군요",
            "더군",
            "던",
            "던데",
            "던데요",
            "던가",
            "던지",
            "나",
            "나요",
            "네",
            "네요",
            "는",
            "는데",
            "는데요",
            "는지",
            "냐",
            "냐고",
            "냐는",
            "느냐는",
            "니",
            "기",
            "기로",
            "기가",
            "기는",
            "기도",
            "기만",
            "기를",
            "기보다",
            "자",
            "자고",
            "자는",
            "자거나",
            "자면",
            "자마자",
            "거든",
            "거든요",
            "건",
            "거나",
            "거니",
            "거니와",
            "소",
            "오",
        ] {
            out.push(Ending {
                suffix,
                form: suffix,
                boundary: Literal,
                connector: matches!(suffix, "고" | "지" | "게"),
            });
        }
        // Reviewed omitted-copula families. Do not apply predicate irregular
        // recovery to the nominal or restore 이 before arbitrary endings.
        for (suffix, form, attached) in [
            ("지", "지", 0),
            ("지요", "지요", 0),
            ("죠", "죠", 0),
            ("면", "으면", 0),
            ("데", "은데", 4),
            ("지", "은지", 4),
            ("가", "은가", 4),
            ("가요", "은가요", 4),
            ("까", "을까", 8),
            ("까요", "을까요", 8),
            ("지", "을지", 8),
            ("니다", "습니다", 17),
            ("니까", "습니까", 17),
            ("니", "니", 0),
            ("니", "으니", 0),
            ("니까", "으니까", 0),
            ("고", "고", 0),
            ("지만", "지만", 0),
            ("지만요", "지만요", 0),
            ("거든", "거든", 0),
            ("거든요", "거든요", 0),
            ("네", "네", 0),
            ("네요", "네요", 0),
            ("세요", "으세요", 0),
            ("더라", "더라", 0),
            ("더라고", "더라고", 0),
            ("더군", "더군", 0),
            ("더군요", "더군요", 0),
            ("더니", "더니", 0),
            ("더라도", "더라도", 0),
            ("던데", "던데", 0),
            ("던데요", "던데요", 0),
            ("던가", "던가", 0),
            ("던지", "던지", 0),
        ] {
            out.push(Ending {
                suffix,
                form,
                boundary: OmittedCopula(attached),
                connector: matches!(suffix, "지" | "고"),
            });
        }
        // Enumerative -요 is a copula/아니다 ending, distinct from polite 요.
        for boundary in [Copular, OmittedCopula(0)] {
            out.push(Ending {
                suffix: "요",
                form: "요",
                boundary,
                connector: false,
            });
        }
        // Productive 아/어 family; the last stem vowel may absorb the ending.
        for (suffix, form) in [
            ("", "어"),
            ("요", "어요"),
            ("서", "어서"),
            ("서야", "어서야"),
            ("도", "어도"),
            ("야", "어야"),
            ("야지", "어야지"),
            ("야죠", "어야죠"),
            ("라", "어라"),
            ("다가", "어다가"),
            ("서는", "어서는"),
            ("서도", "어서도"),
        ] {
            out.push(Ending {
                suffix,
                form,
                boundary: Aeo,
                connector: matches!(suffix, "" | "야"),
            });
        }
        for (full, short, form) in [
            ("으면", "면", "으면"),
            ("으니까", "니까", "으니까"),
            ("으니", "니", "으니"),
            ("으며", "며", "으며"),
            ("으면서", "면서", "으면서"),
            ("으므로", "므로", "으므로"),
            ("으러", "러", "으러"),
            ("으려고", "려고", "으려고"),
            ("으려면", "려면", "으려면"),
            ("으려", "려", "으려"),
            ("으려는", "려는", "으려는"),
            ("으라", "라", "으라"),
            ("으라고", "라고", "으라고"),
            ("으라는", "라는", "으라는"),
            ("으란", "란", "으란"),
            ("으라면", "라면", "으라면"),
            ("으랍니다", "랍니다", "으랍니다"),
            ("으라거나", "라거나", "으라거나"),
            ("으세요", "세요", "으세요"),
            ("으십시오", "십시오", "으십시오"),
            ("으냐", "냐", "으냐"),
            ("으냐는", "냐는", "으냐는"),
            ("으나", "나", "으나"),
            ("으나마", "나마", "으나마"),
            ("으리라", "리라", "으리라"),
            ("으리라고", "리라고", "으리라고"),
        ] {
            out.push(Ending {
                suffix: full,
                form,
                boundary: EuFull,
                connector: false,
            });
            out.push(Ending {
                suffix: short,
                form,
                boundary: EuZero,
                connector: false,
            });
        }
        for (full, short, form, t) in [
            ("은", "", "은", 4),
            ("은데", "데", "은데", 4),
            ("은지", "지", "은지", 4),
            ("은가", "가", "은가", 4),
            ("은가요", "가요", "은가요", 4),
            ("은데도", "데도", "은데도", 4),
            ("은데다가", "데다가", "은데다가", 4),
            ("을", "", "을", 8),
            ("을까", "까", "을까", 8),
            ("을까요", "까요", "을까요", 8),
            ("을게", "게", "을게", 8),
            ("을게요", "게요", "을게요", 8),
            ("을래", "래", "을래", 8),
            ("을래요", "래요", "을래요", 8),
            ("을지", "지", "을지", 8),
            ("을지라도", "지라도", "을지라도", 8),
            ("을수록", "수록", "을수록", 8),
            ("음", "", "음", 16),
            // Unlike -습니다/-습니까, -(으)ㅂ시다 has a vowel boundary:
            // 들읍시다, 부읍시다, 도웁시다. The attached variant drops ㄹ.
            ("읍시다", "시다", "읍시다", 17),
        ] {
            out.push(Ending {
                suffix: full,
                form,
                boundary: EuFull,
                connector: false,
            });
            out.push(Ending {
                suffix: short,
                form,
                boundary: Attached(t),
                connector: false,
            });
        }
        for (full, short, form, t) in [
            ("습니다", "니다", "습니다", 17),
            ("습니까", "니까", "습니까", 17),
            ("는다", "다", "는다", 4),
            ("는다고", "다고", "는다고", 4),
            ("는다는", "다는", "는다는", 4),
            ("는다면", "다면", "는다면", 4),
            ("는답니다", "답니다", "는답니다", 4),
            ("는다거나", "다거나", "는다거나", 4),
            ("는다든가", "다든가", "는다든가", 4),
        ] {
            out.push(Ending {
                suffix: full,
                form,
                boundary: Consonant,
                connector: false,
            });
            out.push(Ending {
                suffix: short,
                form,
                boundary: Attached(t),
                connector: false,
            });
        }
        for suffix in ["다고", "다는", "다니", "다면", "잖아", "잖아요"] {
            out.push(Ending {
                suffix,
                form: suffix,
                boundary: Literal,
                connector: false,
            });
        }
        // Explicit ㄱ/ㄷ/ㅈ ending families for Article 40. Ordinary endings
        // remain alongside their shortened variants; no global text rewriting.
        for (form, aspirated) in [
            ("기", "키"),
            ("기로", "키로"),
            ("기가", "키가"),
            ("기는", "키는"),
            ("기도", "키도"),
            ("기만", "키만"),
            ("기를", "키를"),
            ("기보다", "키보다"),
            ("게", "케"),
            ("게요", "케요"),
            ("지", "치"),
            ("지요", "치요"),
            ("지만", "치만"),
            ("지만요", "치만요"),
            ("다", "타"),
            ("다고", "타고"),
            ("다는", "타는"),
            ("다니", "타니"),
            ("다면", "타면"),
            ("도록", "토록"),
            ("고자", "코자"),
            ("건대", "컨대"),
        ] {
            for (suffix, boundary) in [(form, HaDeletion), (aspirated, HaAspiration)] {
                out.push(Ending {
                    suffix,
                    form,
                    boundary,
                    connector: matches!(form, "게" | "지"),
                });
            }
        }
        // 이 is part of the copular stem, never an arbitrary removable ending.
        for suffix in ["라", "라서", "라고", "라는", "라면", "랍니다", "라든가"] {
            for boundary in [Copular, ZeroCopula] {
                out.push(Ending {
                    suffix,
                    form: suffix,
                    boundary,
                    connector: false,
                });
            }
            // These homonyms also follow reviewed prefinals. A literal
            // boundary alone is insufficient; predicates() checks the last
            // recovered prefinal rather than treating any vowel stem as copular.
            out.push(Ending {
                suffix,
                form: suffix,
                boundary: Literal,
                connector: false,
            });
        }
        // Copular -라거나 shares its spelling with quoted-command -(으)라거나.
        for boundary in [Copular, ZeroCopula] {
            out.push(Ending {
                suffix: "라거나",
                form: "라거나",
                boundary,
                connector: false,
            });
        }
        // Short quoted -란 also follows retrospective 더. Its recovered
        // copular/prefinal licenses are checked in predicates().
        for boundary in [Literal, ZeroCopula] {
            out.push(Ending {
                suffix: "란",
                form: "란",
                boundary,
                connector: false,
            });
        }
        for ending in &mut out {
            ending.connector = AUXILIARY_CONNECTORS.contains(&ending.form);
        }
        out
    })
}

/// A reverse trie prunes suffix rules before any Hangul reconstruction.
#[derive(Default)]
struct Trie {
    next: HashMap<char, Trie>,
    rules: Vec<usize>,
}
pub(crate) fn matching_endings(word: &str) -> Vec<&'static Ending> {
    static INDEX: OnceLock<Trie> = OnceLock::new();
    let root = INDEX.get_or_init(|| {
        let mut root = Trie::default();
        for (i, ending) in endings().iter().enumerate() {
            let mut node = &mut root;
            for c in ending.suffix.chars().rev() {
                node = node.next.entry(c).or_default();
            }
            node.rules.push(i);
        }
        root
    });
    let mut out: Vec<_> = root.rules.iter().map(|&i| &endings()[i]).collect();
    let mut node = root;
    for c in word.chars().rev() {
        let Some(next) = node.next.get(&c) else { break };
        node = next;
        out.extend(node.rules.iter().map(|&i| &endings()[i]));
    }
    out
}

// Particle order is finite: case -> restrictive -> additive/topic. The second
// case slot supports 만으로도, 에서의, etc.; arbitrary repetition is disallowed.
pub(crate) struct Particle {
    pub form: &'static str,
    pub class: u8,
    pub condition: u8,
}
pub(crate) fn particles() -> &'static [Particle] {
    static RULES: OnceLock<Vec<Particle>> = OnceLock::new();
    RULES.get_or_init(|| {
        let mut out = Vec::new();
        for (form, class, condition) in [
            ("은", 4, 1),
            ("는", 4, 2),
            ("도", 4, 0),
            // Choice/emphasis also follows case/restrictive particles.
            // Keep the inner coordination slots below for existing readings.
            ("이나", 4, 1),
            ("나", 4, 2),
            ("이라도", 4, 1),
            ("라도", 4, 2),
            ("이든지", 4, 1),
            ("든지", 4, 2),
            ("이든가", 4, 1),
            ("든가", 4, 2),
            ("이라든가", 4, 1),
            ("라든가", 4, 2),
            ("이라든지", 4, 1),
            ("라든지", 4, 2),
            ("이야", 4, 1),
            ("야", 4, 2),
            ("이야말로", 4, 1),
            ("야말로", 4, 2),
            ("이나마", 4, 1),
            ("나마", 4, 2),
            ("은커녕", 4, 1),
            ("는커녕", 4, 2),
            ("커녕", 4, 0),
            ("이란", 4, 1),
            ("란", 4, 2),
            ("만", 3, 0),
            ("마는", 3, 0),
            ("까지", 3, 0),
            ("부터", 3, 0),
            ("마다", 3, 0),
            ("만큼", 3, 0),
            ("대로", 3, 0),
            ("조차", 3, 0),
            ("마저", 3, 0),
            ("밖에", 3, 0),
            // Emphatic 다/다가 have separately checked adverbial/case bases.
            ("다", 3, 2),
            ("다가", 3, 2),
            // Enumerative 다/이다 require a nominal, unlike emphatic 다.
            ("다", 4, 2),
            ("이다", 4, 1),
            ("의", 2, 0),
            ("으로", 2, 3),
            ("로", 2, 4),
            ("으로서", 2, 3),
            ("로서", 2, 4),
            ("으로써", 2, 3),
            ("로써", 2, 4),
            ("으로다가", 2, 3),
            ("로다가", 2, 4),
            ("이", 1, 1),
            ("가", 1, 2),
            ("을", 1, 1),
            ("를", 1, 2),
            ("과", 1, 1),
            ("와", 1, 2),
            ("에", 1, 0),
            ("에다", 1, 0),
            ("에다가", 1, 0),
            ("에서", 1, 0),
            // Locative 서 (short 에서) follows consonants too: 시장서.
            // The separate count-emphasis homonym has narrower lexical scope.
            ("서", 1, 0),
            ("에게", 1, 0),
            ("에게다", 1, 0),
            ("에게다가", 1, 0),
            ("에게서", 1, 0),
            ("한테", 1, 0),
            ("한테다", 1, 0),
            ("한테다가", 1, 0),
            ("보고", 1, 0),
            ("더러", 1, 0),
            ("한테서", 1, 0),
            ("께", 1, 0),
            ("께서", 1, 0),
            ("보다", 1, 0),
            ("처럼", 1, 0),
            ("같이", 1, 0),
            ("이라고", 1, 1),
            ("라고", 1, 2),
            ("하고", 1, 0),
            ("이랑", 1, 1),
            ("랑", 1, 2),
            ("이나", 1, 1),
            ("나", 1, 2),
            ("이든지", 1, 1),
            ("든지", 1, 2),
            ("이든가", 1, 1),
            ("든가", 1, 2),
            ("이야", 1, 1),
            ("야", 1, 2),
            ("아", 1, 1),
            ("여", 1, 2),
            // Outer slots: ordinary particles -> distributive 들 -> polite 요.
            ("들", 5, 0),
            ("요", 6, 0),
        ] {
            out.push(Particle {
                form,
                class,
                condition,
            });
        }
        out
    })
}
pub(crate) fn particle_matches(base: &str, condition: u8) -> bool {
    match condition {
        0 => !base.is_empty(),
        1 => coda(base).is_some_and(|t| t != 0),
        2 => coda(base) == Some(0),
        3 => coda(base).is_some_and(|t| t != 0 && t != 8),
        4 => matches!(coda(base), Some(0 | 8)),
        _ => false,
    }
}

pub(crate) fn explanation(id: &str) -> Option<&'static str> {
    Some(match id {
        "pronunciation.assumed_consonant" => {
            "Conditional nominal reading: the non-Hangul base must be pronounced with a final consonant; its pronunciation is not inferred."
        }
        "pronunciation.assumed_vowel" => {
            "Conditional nominal reading: the non-Hangul base must be pronounced with a final vowel; its pronunciation is not inferred."
        }
        "pronunciation.assumed_non_rieul_consonant" => {
            "Conditional nominal reading: the non-Hangul base must be pronounced with a final consonant other than ㄹ; its pronunciation is not inferred."
        }
        "pronunciation.assumed_vowel_or_rieul" => {
            "Conditional nominal reading: the non-Hangul base must be pronounced with a final vowel or ㄹ; its pronunciation is not inferred."
        }
        "auxiliary.internal_particle" => {
            "Retain a licensed particle between an ending and the following auxiliary predicate."
        }
        "particle.concessive" => {
            "Attach concessive 만/마는 after a licensed final ending; retain the distinct nominal 만 reading where applicable."
        }
        "particle.enumerative" => {
            "Retain an enumerative or choice particle, separate from a homonymous ending or copular expression; no contextual choice is inferred."
        }
        "particle.enumerative_da" => {
            "Attach enumerative 다/이다 to a nominal in an equal-footing list; the surrounding enumeration is not inferred from this token."
        }
        "particle.emphatic_destination" => {
            "Separate a source-listed emphatic location, direction, means or recipient particle; bundled and component readings remain distinct."
        }
        "particle.emphatic_adverbial" => {
            "Attach emphatic 다/다가 to a reviewed case phrase or deictic location/direction reading, not to an arbitrary noun or predicate ending."
        }
        "particle.recipient" => {
            "This recipient reading requires a contextually appropriate referent (typically a person or animate/personified entity); lexical and contextual eligibility are not inferred."
        }
        "ending.choice" => {
            "Recognize the literal choice ending -든가 with its reviewed prefinal licenses, separately from particle 든가."
        }
        "ending.adnominal_expression" => {
            "Retain a reviewed shortened noun-modifying expression as one grammatical component."
        }
        "identity" => "Unchanged vocabulary hypothesis; no dictionary verification.",
        "suffix.adverbial.i" => {
            "Recover a scoped adjective base before adverb-forming -이; retain whole-word readings."
        }
        "derivation.adverbial.lexical" => {
            "Expand historical 달리/빨리 to 다르다/빠르다 plus -이; not a general 르 inflection rule."
        }
        "deletion.ha" => {
            "Restore 하 deleted after a ㄱ/ㄷ/ㅂ-sounding simple coda before a licensed consonant ending."
        }
        "contraction.ha_aspiration" => {
            "Restore 하 whose ㅎ aspirates the following ㄱ/ㄷ/ㅈ after a vowel or sonorant base."
        }
        "particle.contraction.n" => {
            "Expand attached ㄴ to topic/emphatic 는 after an open syllable."
        }
        "particle.contraction.nkeonyeong" => {
            "Expand attached ㄴ커녕 to the particle 는커녕 after an open syllable."
        }
        "particle.contraction.l" => {
            "Expand attached ㄹ to object/emphatic 를 after an open syllable."
        }
        "pronoun.contraction" => {
            "Recover a contracted pronoun and its case/topic particle; preserve lexical alternatives."
        }
        "particle.polite" => {
            "Attach polite particle 요 after a nominal, adverbial, or licensed ending."
        }
        "particle.distributive" => {
            "Attach 들 marking plural subjects, distinct from nominal plural suffix -들."
        }
        "suffix.plural" => {
            "Separate nominal plural -들 before particles or a copula; retain the unsplit lexical alternative."
        }
        "suffix.honorific" => {
            "Separate nominal honorific -님; preserve the whole-word alternative."
        }
        "suffix.relational" => {
            "Separate relational -적 from a nominal base; preserve the whole-word alternative."
        }
        "suffix.adjectival.dap" => {
            "Separate adjective-forming -답다 from a nominal base, with ㅂ-irregular vowel attachment."
        }
        "boundary.regular" => "Remove an ending with no stem spelling change.",
        "boundary.consonant" => "Consonant-final stem selects the consonant allomorph.",
        "boundary.open" => "Vowel-final stem selects the open-stem allomorph.",
        "boundary.eu" => "Select the (으) allomorph according to the stem boundary.",
        "boundary.copular" => {
            "License a 라-family ending after 이다 or 아니다, preserving the stem."
        }
        "boundary.attached" => "Recover an ending consonant fused into the final syllable.",
        "contraction.identical" => "Recover an absorbed 아/어 vowel.",
        "contraction.vowel" => "Undo vowel contraction (와, 워, 돼, or 여).",
        "contraction.noh" => {
            "Restore 놓아 from 놔 at an 아/어 boundary, including 놓다 compounds and auxiliaries."
        }
        "deletion.eu" => "Restore stem-final ㅡ before 아/어.",
        "deletion.rieul" => "Restore ㄹ lost before a consonant ending.",
        "irregular.digeut" => "Hypothesize ㄷ irregular class: ㄷ becomes ㄹ before a vowel.",
        "irregular.bieup" => "Hypothesize ㅂ irregular class: ㅂ becomes 우 (or restricted 오).",
        "irregular.siot" => "Hypothesize ㅅ irregular class: ㅅ disappears before a vowel.",
        "irregular.hieut" => "Hypothesize ㅎ irregular class: deletion or vowel contraction.",
        "irregular.reu" => "Restore 르 and undo doubled ㄹ before 아/어.",
        "irregular.reo" => "Restore 르 before the 러 irregular ending.",
        "irregular.ha" => "Restore 하 from 해 or 하여.",
        "irregular.pu" => "Restore 푸 from 퍼.",
        "ending" => "Match a licensed terminal ending.",
        "prefinal.past" => "Recover 았/었; at most two past markers are licensed.",
        "prefinal.honorific" => "Recover honorific (으)시 before tense/modal markers.",
        "prefinal.modal" => "Recover 겠 after honorific or past markers.",
        "prefinal.obligation" => {
            "Recover the intention or necessity expression -아/어/여야겠- as one prefinal-position bundle, without inserting an implicit 하다."
        }
        "prefinal.retrospective" => "Recover retrospective 더 after other prefinal markers.",
        "prefinal.conjectural_quotation" => {
            "Recover conjectural (으)리 before the reviewed shortened quotation -란."
        }
        "prefinal.conjectural_ra" => {
            "Recover conjectural (으)리 before a reviewed factual 라-family ending; retain existing bundled forms separately."
        }
        "ending.factual_ra" => {
            "A factual 라-family ending follows its licensed prefinal, distinct from the homonymous command ending."
        }
        "particle" => "Remove a particle with licensed order and boundary allomorph.",
        "copula" => "Separate a nominal and the affirmative copula 이다.",
        "copula.zero" => "Restore the omitted copula after a vowel-final nominal.",
        "copula.omitted_ending" => {
            "Restore omitted copular 이 after a vowel-final nominal before a reviewed ending; the nominal is not a conjugated verb stem."
        }
        "copula.omitted_honorific" => {
            "Restore omitted copular 이 before honorific 시 after a vowel-final nominal; preserve the normal prefinal order and ending restrictions."
        }
        "copula.omitted_prefinal" => {
            "Restore omitted copular 이 before modal 겠 or retrospective 더 after a vowel-final nominal, retaining prefinal order and ending restrictions."
        }
        "nominal.colloquial_geot" => {
            "Expand the colloquial 거/이거/그거/저거 nominal to 것/이것/그것/저것 before a copula; preserve the short lexical alternative."
        }
        "auxiliary" => "Separate a licensed connective plus attached auxiliary.",
        "irregular.mal" => "Restore prohibitive 말다 in the short imperatives 마, 마라 and 마요.",
        "nominalization" => "Analyze a nominalized predicate before a particle or copula.",
        "contraction.negative" => "Expand contracted 잖/찮 into 지/하지 plus auxiliary 않다.",
        "suffix.adverbial.hi" => "Recover the adverb-forming suffix -히 for a source-listed root.",
        "derivation.adverbial.bieup" => {
            "Restore the ㅂ adjective stem of a source-listed -이 adverb."
        }
        "derivation.adverbial.hada" => {
            "Link a source-listed adverb root to its related 하다 adjective."
        }
        "derivation.adverbial.adverb" => {
            "Separate a source-listed adverb base and its adverb-forming suffix; do not manufacture a predicate lemma."
        }
        "derivation.adverbial.nominal" => {
            "Separate a source-listed repeated nominal base and adverb-forming -이. The repeated base remains one component and may lack a dictionary entry."
        }
        "derivation.adverbial.shortened" => {
            "Recover 익숙히/특별히 behind shortened 익히/특히, using 익숙하다/특별하다 as lookup lemmas; retain the whole-word reading."
        }
        "ending.confirmation" => "Recognize the confirming or correcting expression -잖아/-잖아요.",
        "ending.reporting_polite" => {
            "Recognize a polite informative or reported-speech ending as one grammatical component; its sense and any implicit speaker are not inferred."
        }
        "ending.enumerative_yo" => {
            "Recognize enumerative -요 after 이다/아니다, retaining vowel-final copula omission and the separate polite-particle reading."
        }
        "ending.causal" => {
            "Recognize causal -기에/-길래 as an ending, distinct from nominalizing -기 plus particle 에; contextual reason and register are not selected."
        }
        "ending.quoted_alternative" => {
            "Recognize a source-listed quoted alternative or enumeration as one grammatical component, without inserting an implicit 하다 lemma or choosing a contextual sense."
        }
        "pronoun" => "Restore a contracted pronoun with its particle.",
        "nominal.contraction" => "Restore contracted 거/것 plus a particle.",
        "copula.polite" => "Restore the copula from 이에요/예요 or 이야/야.",
        "copula.fragment" => {
            "Recognize an explicitly spelled copula fragment without joining it to a preceding token."
        }
        "copula.omitted_fragment" => {
            "This reading assumes preceding quoted material: 라는 has an omitted copular 이. The quoted material is outside this token."
        }
        "negative_copula.polite" => "Restore 아니다 from 아니에요.",
        _ => return None,
    })
}

#[cfg(test)]
mod label_tests {
    use super::*;
    use crate::MorphemeKind;
    use std::collections::BTreeMap;

    #[test]
    fn every_emitted_grammar_form_has_a_kind_specific_sourced_label() {
        use MorphemeKind::*;
        let mut forms = BTreeMap::new();
        for ending in endings() {
            forms.insert(format!("-{}", ending.form), Ending);
        }
        for particle in particles() {
            forms.insert(particle.form.to_owned(), Particle);
        }
        // Forms emitted outside the tables: copula endings, prefinal recovery,
        // and bounded derivation. Other synthetic contractions reuse table forms.
        for form in ["에요", "야"] {
            forms.insert(format!("-{form}"), Ending);
        }
        for form in ["시", "었", "겠", "더", "으리", "어야겠"] {
            forms.insert(format!("-{form}-"), Prefinal);
        }
        for form in ["님", "들", "적", "답다", "이", "히"] {
            forms.insert(format!("-{form}"), Suffix);
        }
        let labels: BTreeMap<String, serde_json::Value> =
            serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
        assert_eq!(
            forms.keys().collect::<Vec<_>>(),
            labels.keys().collect::<Vec<_>>()
        );
        for (key, kind) in forms {
            let label = &labels[&key];
            assert_eq!(label["kind"], serde_json::to_value(kind).unwrap(), "{key}");
            assert!(!label["label"].as_str().unwrap().trim().is_empty(), "{key}");
            assert!(!label["sources"].as_array().unwrap().is_empty(), "{key}");
        }
    }
}
