//! Explicit morphotactics and reverse spelling rules. No statistical weights.
use crate::hangul::*;
use std::{collections::HashMap, sync::OnceLock};

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
}

#[derive(Debug)]
pub(crate) struct Ending {
    pub suffix: &'static str,
    pub form: &'static str,
    pub boundary: Boundary,
    pub connector: bool,
}

pub(crate) fn recover(surface: &str, suffix: &str, boundary: Boundary) -> Vec<Recovery> {
    let Some(base) = surface.strip_suffix(suffix) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    match boundary {
        Boundary::Aeo => return aeo(base),
        Boundary::Copular => {
            if base.ends_with('이') || base == "아니" {
                push(&mut out, base.into(), "boundary.copular");
            }
        }
        Boundary::ZeroCopula => {
            if coda(base) == Some(0) {
                push(&mut out, format!("{base}이"), "copula.zero");
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
                if t != 17 && !matches!(suffix, "다" | "다고" | "다는") {
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
            "고자",
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
            ("으라", "라", "으라"),
            ("으라고", "라고", "으라고"),
            ("으라는", "라는", "으라는"),
            ("으라면", "라면", "으라면"),
            ("으세요", "세요", "으세요"),
            ("으십시오", "십시오", "으십시오"),
            ("으냐", "냐", "으냐"),
            ("으나", "나", "으나"),
            ("으리라", "리라", "으리라"),
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
            ("을수록", "수록", "을수록", 8),
            ("음", "", "음", 16),
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
            ("습시다", "시다", "습시다", 17),
            ("는다", "다", "는다", 4),
            ("는다고", "다고", "는다고", 4),
            ("는다는", "다는", "는다는", 4),
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
        for suffix in ["다고", "다는", "다니", "다면"] {
            out.push(Ending {
                suffix,
                form: suffix,
                boundary: Literal,
                connector: false,
            });
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
            ("만", 3, 0),
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
        "identity" => "Unchanged vocabulary hypothesis; no dictionary verification.",
        "suffix.plural" => {
            "Separate nominal plural -들 before particles or a copula; retain the unsplit lexical alternative."
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
        "nominalization" => "Analyze a nominalized predicate before a particle.",
        "pronoun" => "Restore a contracted pronoun with its particle.",
        "nominal.contraction" => "Restore contracted 거/것 plus a particle.",
        "copula.polite" => "Restore the copula from 이에요/예요 or 이야/야.",
        "negative_copula.polite" => "Restore 아니다 from 아니에요.",
        _ => return None,
    })
}
