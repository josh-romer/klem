//! Explicit morphotactics and reverse spelling rules. No statistical weights.
use crate::hangul::*;
use std::{collections::HashMap, sync::OnceLock};

// Source-listed adverb roots, not a general 이/히 spelling heuristic. The
// related 하다 lemma is a lookup normalization; the suffix attaches to the root.
// KRDict 88504 and NIKL's 1999 spelling discussion; see docs/adverb-inventory.json.
pub(crate) const ADVERB_HADA_ROOTS: &[(&str, &str)] = &[
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
                    && !matches!(suffix, "다" | "다고" | "다는" | "다면")
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
            "든지",
            "든",
            "더라도",
            "더니",
            "더라",
            "더라고",
            "더군요",
            "더군",
            "던",
            "던데",
            "던데요",
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
        // Productive 아/어 family; the last stem vowel may absorb the ending.
        for (suffix, form) in [
            ("", "어"),
            ("요", "어요"),
            ("서", "어서"),
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
            ("으라면", "라면", "으라면"),
            ("으세요", "세요", "으세요"),
            ("으십시오", "십시오", "으십시오"),
            ("으냐", "냐", "으냐"),
            ("으냐는", "냐는", "으냐는"),
            ("으나", "나", "으나"),
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
        for suffix in ["라", "라서", "라고", "라는", "라면"] {
            for boundary in [Copular, ZeroCopula] {
                out.push(Ending {
                    suffix,
                    form: suffix,
                    boundary,
                    connector: false,
                });
            }
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
            ("이야", 4, 1),
            ("야", 4, 2),
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
            ("의", 2, 0),
            ("으로", 2, 3),
            ("로", 2, 4),
            ("으로서", 2, 3),
            ("로서", 2, 4),
            ("으로써", 2, 3),
            ("로써", 2, 4),
            ("이", 1, 1),
            ("가", 1, 2),
            ("을", 1, 1),
            ("를", 1, 2),
            ("과", 1, 1),
            ("와", 1, 2),
            ("에", 1, 0),
            ("에서", 1, 0),
            ("서", 1, 2),
            ("에게", 1, 0),
            ("에게서", 1, 0),
            ("한테", 1, 0),
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
        "prefinal.retrospective" => "Recover retrospective 더 after other prefinal markers.",
        "particle" => "Remove a particle with licensed order and boundary allomorph.",
        "copula" => "Separate a nominal and the affirmative copula 이다.",
        "copula.zero" => "Restore the omitted copula after a vowel-final nominal.",
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
        "ending.confirmation" => "Recognize the confirming or correcting expression -잖아/-잖아요.",
        "pronoun" => "Restore a contracted pronoun with its particle.",
        "nominal.contraction" => "Restore contracted 거/것 plus a particle.",
        "copula.polite" => "Restore the copula from 이에요/예요 or 이야/야.",
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
        for form in ["시", "었", "겠", "더"] {
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
