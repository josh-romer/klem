//! Explicit morphotactics and reverse spelling rules. No statistical weights.
use crate::hangul::*;
use crate::{LemmaKind, SpellingClass};
use std::{collections::HashMap, sync::OnceLock};

// Source-listed adverb roots, not a general 이/히 spelling heuristic. The
// related 하다 lemma is a lookup normalization; the suffix attaches to the root.
// KRDict 88504 and NIKL's 1999 spelling discussion; see docs/adverb-inventory.json.
// COV-022v: all nine quantity/degree/repetition adverb-base leads in the
// pinned native example inventory. Same-spelled counting units 통/정/단 and
// lexical 씩씩 do not license their adverb homonyms. Contextual POS and a
// suffix-driven change of word class remain unjudged.
pub(crate) const SSIK_ADVERB_BASES: &[&str] = &[
    "가끔",
    "살짝",
    "이따금",
    "이만큼",
    "잠깐",
    "조금",
    "하나하나",
    "한바탕",
    "한발",
];

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

// Finite opaque roots listed under KRDict -히 (88504). The optional related
// adjective is independently attested; it is a lookup hypothesis, not an
// inserted 하 segment. See docs/opaque-adverb-source-audit.json.
pub(crate) const OPAQUE_ADVERB_ROOTS: &[(&str, &str, Option<&str>)] =
    &[("천천", "히", Some("천천하다")), ("분연", "히", None)];

// KRDict 88924, sense 1: a finite noun formation, separate from adverbial -이.
pub(crate) const NOUN_I_FORMS: &[(&str, &str)] = &[
    ("굽이", "굽다"),
    ("깊이", "깊다"),
    ("넓이", "넓다"),
    ("길이", "길다"),
    ("놀이", "놀다"),
    ("높이", "높다"),
    ("먹이", "먹다"),
    ("벌이", "벌다"),
    // KRDict sense 2; NIKL's morphology review lists 떠돌이 as V-이.
    ("떠돌이", "떠돌다"),
    // KRDict sense 3 lists 까불이; retain its native class note and both
    // 까불다 verb homonyms. The lookup relationship is a finite hypothesis.
    ("까불이", "까불다"),
];

// KRDict 88924 sense 3; selected noun-to-noun formations under Article 20.
// A nominal lookup does not select a contextual or historical base sense.
pub(crate) const NOUN_I_NOMINAL_FORMS: &[(&str, &str)] = &[
    ("까막눈이", "까막눈"),
    ("노랑이", "노랑"),
    ("동강이", "동강"),
    ("바둑이", "바둑"),
    // Independent primary sources identify these nominal bases even though
    // they are absent from the pinned learner dictionary.
    ("얼간이", "얼간"),
    ("허풍선이", "허풍선"),
];

// KRDict 88924 sense 3: finite sound/manner formations. Adverb headwords
// support lookup roles, not a contextual sense. The source-listed 뺑뺑 + 이
// boundary supplies derivational-base evidence without a standalone POS claim.
pub(crate) const NOUN_I_SOUND_FORMS: &[(&str, &str, LemmaKind)] = &[
    ("깜빡이", "깜빡", LemmaKind::Adverbial),
    ("깡깡이", "깡깡", LemmaKind::Adverbial),
    ("깽깽이", "깽깽", LemmaKind::Adverbial),
    ("꿀꿀이", "꿀꿀", LemmaKind::Adverbial),
    ("덜렁이", "덜렁", LemmaKind::Adverbial),
    ("딸랑이", "딸랑", LemmaKind::Adverbial),
    ("뺑뺑이", "뺑뺑", LemmaKind::Root),
    ("오뚝이", "오뚝", LemmaKind::Adverbial),
    ("짝짝이", "짝짝", LemmaKind::Adverbial),
];

// KRDict 88924 sense 3, Article 23 and NIKL 318501/333918/325909.
// Roots express reviewed derivational boundaries, not standalone POS claims.
// Related predicates are separate lookup hypotheses; no 하/거리 is inserted.
// 합죽거리다 belongs to the primary quiet-person sense, not the pinned
// missing-teeth sense. 미치광 stays one historical base (미치- + 狂).
pub(crate) const NOUN_I_ROOTS: &[(&str, &str, &[&str])] = &[
    ("끈끈이", "끈끈", &["끈끈하다"]),
    ("누렁이", "누렁", &[]),
    ("뚱뚱이", "뚱뚱", &["뚱뚱하다"]),
    ("멍청이", "멍청", &["멍청하다"]),
    ("미치광이", "미치광", &[]),
    ("합죽이", "합죽", &["합죽하다", "합죽거리다"]),
    ("홀쭉이", "홀쭉", &["홀쭉하다"]),
    // Positive sense-3 example supports the whole base; the separate prefix
    // path retains 왕- without substituting standalone 왕 'king'.
    ("왕눈이", "왕눈", &[]),
    // Primary reduplication research and the norm-information database supply
    // positive grouped boundaries; missing headwords do not assign this role.
    ("됨됨이", "됨됨", &[]),
    ("쭉정이", "쭉정", &[]),
];

// Individually reviewed prefix/base boundaries, never productive stripping.
pub(crate) const NOUN_I_PREFIX_FORMS: &[(&str, &str, &str, &str)] = &[
    ("왕눈이", "왕", "눈", "derivation.nominal.prefix_wang"),
    ("얼간이", "얼", "간", "derivation.nominal.prefix_eol"),
];

// KBS's primary formation explanation: 虛風 + 扇 + 이. 扇 is a bound
// Chinese root here, not one of KRDict's unrelated standalone 선 headwords.
// Preserve their origins as evidence without making a general Hanja splitter.
pub(crate) const NOUN_I_ROOT_COMPOUNDS: &[(&str, &str, &str, &str)] =
    &[("허풍선이", "허풍", "선", "扇")];

// Individual source-conflict formations: an adnominal ending is part of the
// listed noun base, not permission to attach a noun suffix to any inflection.
// The whole pre-suffix base remains an independent source-listed hypothesis.
pub(crate) const NOUN_ADNOMINAL_FORMS: &[(&str, &str, &str, &str)] = &[
    ("못난이", "못나다", "못난", "이"),
    ("흰둥이", "희다", "흰둥", "둥이"),
];

// Selected compound bases before noun-forming -이, not arbitrary segmentation.
// The two lemmas form one base; neither takes an inflectional ending here.
// NIKL 320611 confirms 밀다 + 닫다; Article 28 accounts for lost ㄹ.
pub(crate) const NOUN_I_COMPOUNDS: &[(&str, &str, LemmaKind, &str)] = &[
    // Article 19 names 박다; KRDict -박이 supplies a separate suffix reading.
    ("점박이", "점", LemmaKind::Nominal, "박다"),
    ("길잡이", "길", LemmaKind::Nominal, "잡다"),
    ("목걸이", "목", LemmaKind::Nominal, "걸다"),
    ("옷걸이", "옷", LemmaKind::Nominal, "걸다"),
    ("젖먹이", "젖", LemmaKind::Nominal, "먹다"),
    ("미닫이", "밀다", LemmaKind::Predicate, "닫다"),
];

#[derive(Debug, Clone)]
pub(crate) struct Recovery {
    pub stem: String,
    pub rules: Vec<String>,
    pub spelling: Option<SpellingClass>,
}
fn push(out: &mut Vec<Recovery>, stem: String, rule: &str) {
    if !stem.is_empty() && has_hangul(&stem) {
        out.push(Recovery {
            stem,
            rules: vec![rule.into()],
            spelling: None,
        });
    }
}

/// Classify a local written 아/어 boundary. This does not generate or discard
/// candidates and never guesses compound segmentation. 르 and ㅎ keep their
/// independently reviewed paradigms; other vowels are outside this policy.
pub(crate) fn written_vowel_recovery(stem: &str, surface: &str) -> Option<SpellingClass> {
    use SpellingClass::*;
    let (_, v, t) = last(stem)?;
    if v == 18 && t == 0 && !stem.ends_with('르') {
        if surface.strip_suffix(['아', '어']) == Some(stem) {
            Some(EuUncontracted)
        } else if replace_last(stem, V_A, 0).as_deref() == Some(surface) {
            Some(WrittenVowelA)
        } else if replace_last(stem, V_EO, 0).as_deref() == Some(surface) {
            Some(WrittenVowelEo)
        } else {
            None
        }
    } else if v == 2 && t != 27 {
        if surface.strip_suffix('아') == Some(stem) {
            Some(WrittenVowelA)
        } else if surface.strip_suffix('어') == Some(stem) {
            Some(WrittenVowelEo)
        } else {
            None
        }
    } else {
        None
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
        // Article 34 lists 켜어 -> 켜 and 펴어 -> 펴. An open ㅕ stem
        // also absorbs 어; keep the independent ㅣ + 어 -> ㅕ alternative.
        if v == 6 {
            push(&mut out, surface.into(), "contraction.yeo_absorption");
        }
        // Complete native written paradigms supply these whole-stem exceptions
        // to the generic harmony/deletion heuristic. Do not infer arbitrary
        // compound boundaries or replace the existing lexical hypotheses.
        for (form, stem) in [
            ("가냘파", "가냘프"),
            ("크나커", "크나크"),
            ("동터", "동트"),
            ("못써", "못쓰"),
            ("받아써", "받아쓰"),
            ("본떠", "본뜨"),
            ("손써", "손쓰"),
            ("싹터", "싹트"),
            ("악써", "악쓰"),
            ("약아", "약"),
            ("얇아", "얇"),
            ("얕아", "얕"),
            ("어째", "어쩌"),
        ] {
            if surface == form {
                push(&mut out, stem.into(), "inflection.written_vowel");
            }
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
        // Complete written paradigms: 그러다/이러다/저러다 and their
        // 고러다/요러다/조러다 counterparts have these contracted vowel forms.
        // These are finite verb contractions, distinct from the homonymous
        // adjective ㅎ recoveries below. Whole stems only; no suffix-wide rule
        // for arbitrary 러 verbs or fabricated prefixes (KRDict
        // 37062/24838/25001 and 91459/89713/89955).
        for (form, stem) in [
            ("그래", "그러"),
            ("이래", "이러"),
            ("저래", "저러"),
            ("고래", "고러"),
            ("요래", "요러"),
            ("조래", "조러"),
        ] {
            if surface == form {
                push(&mut out, stem.into(), "contraction.deictic_verb");
            }
        }
        for (form, stem) in [
            ("그래", "그렇"),
            ("이래", "이렇"),
            ("저래", "저렇"),
            ("어때", "어떻"),
            ("고래", "고렇"),
            ("요래", "요렇"),
            ("조래", "조렇"),
            ("아무래", "아무렇"),
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
                && let Some((_, v, t @ (0 | 8))) = last(prefix)
            {
                // Dictionary-written exceptions: 곱디곱 keeps 고와; humble
                // 듣잡/받잡 use 오 both here and before (으) endings.
                // Other stems retain the existing 돕/곱 versus 우 distinction.
                if (vowel == '오') == matches!(prefix, "도" | "고" | "곱디고" | "듣자" | "받자")
                    && (t == 0 || vowel == '우')
                {
                    // 섧 -> 설우 -> 설워 retains ㄹ. This is a lexical
                    // hypothesis; per-entry written forms distinguish regular
                    // ㄼ stems such as 넓다 and 밟다 from this paradigm.
                    push(
                        &mut out,
                        replace_last(prefix, v, if t == 8 { 11 } else { 17 }).unwrap(),
                        "irregular.bieup",
                    );
                }
            }
        }
    }
    for recovery in &mut out {
        recovery.spelling = written_vowel_recovery(&recovery.stem, surface);
    }
    out.sort_by(|a, b| (&a.stem, &a.rules).cmp(&(&b.stem, &b.rules)));
    out.dedup_by(|a, b| a.stem == b.stem && a.rules == b.rules);
    out
}

#[derive(Debug, Clone, Copy)]
pub(crate) enum Boundary {
    Literal,
    // Modern -너라 attaches directly to 오다/오다-final verb stems. Its
    // initial ㄴ is not a productive license to restore stem-final ㄹ.
    ComeStem,
    Consonant,
    // Literary 사오/사옵 and 삽 attach to closed stems, including retained
    // ㄹ. Unlike the ordinary consonant/ㅅ boundaries, they neither require
    // 으 nor delete ㄹ (e.g. the source-attested 알사옵니다).
    ClosedStem,
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
    "게끔",
    "어야",
    // Source-listed 되다 complements; their own link checks restrict joins.
    "도록",
    "어도",
    "어서",
    "어서는",
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
    "으려다",
    "으려다가",
    "으려나",
    "으려니",
    "어다",
    "어다가",
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
    // Lexical 말다 alternative complements (not general auxiliary licenses).
    "거나",
    "거니",
    "건",
    "든지",
    "든",
    "을지",
    "으나",
];

pub(crate) fn recover(surface: &str, suffix: &str, boundary: Boundary) -> Vec<Recovery> {
    let Some(base) = surface.strip_suffix(suffix) else {
        return Vec::new();
    };
    let mut out = Vec::new();
    match boundary {
        Boundary::HaDeletion | Boundary::HaAspiration => {
            // Article 40: stop-final bases lose all of 하; vowels/sonorants
            // retain ㅎ, which aspirates the following onset. COV-021c adds
            // fixed complex-coda classes from pronunciation Articles 10–11:
            // ㄳ/ㄺ/ㄿ/ㅄ are stops; ㄵ/ㄻ/ㄽ/ㄾ are sonorants. Classify
            // before the restored 하, not before the shortened ending's onset.
            // ㄼ (lexical exceptions), ㄶ and ㅀ remain under review.
            let allowed = match boundary {
                Boundary::HaDeletion => matches!(
                    coda(base),
                    Some(1 | 2 | 3 | 7 | 9 | 14 | 17 | 18 | 19 | 20 | 22 | 23 | 24 | 25 | 26)
                ),
                _ => matches!(coda(base), Some(0 | 4 | 5 | 8 | 10 | 12 | 13 | 16 | 21)),
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
                        spelling: None,
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
                    spelling: None,
                });
            }
        }
        Boundary::ComeStem => {
            if base.ends_with('오') {
                push(&mut out, base.into(), "boundary.regular");
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
        Boundary::ClosedStem => {
            if coda(base).is_some_and(|t| t != 0) {
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
                        "다" | "다고"
                            | "다니"
                            | "다느니"
                            | "단"
                            | "다는"
                            | "다면"
                            | "답니다"
                            | "다거나"
                            | "다든가"
                            | "단다"
                            | "다지"
                            | "다죠"
                            | "다지만"
                            | "다니까"
                            | "대"
                            | "다네"
                            | "다는데"
                            | "다던"
                            | "다더니"
                            | "다나"
                            | "다마는"
                            | "다만"
                            | "답시고"
                            | "다더니만"
                            | "다더니마는"
                            | "다던데"
                            | "다며"
                            | "다면서"
                    )
                {
                    recover_eu_open(&stem, &mut out, true);
                }
            }
        }
    }
    out
}

// Stem-final ㄹ drops before ㄴ/ㅂ/ㅅ-initial endings and -오/-옵.
// Attached consonants are handled separately by Boundary::Attached.
fn drops_rieul(suffix: &str) -> bool {
    suffix.starts_with('오')
        || suffix.starts_with('옵')
        || suffix
            .chars()
            .next()
            .and_then(split)
            .is_some_and(|(initial, _, _)| matches!(initial, 2 | 7 | 9))
}

fn recover_eu_open(base: &str, out: &mut Vec<Recovery>, allow_h: bool) {
    for vowel in ['우', '오'] {
        if let Some(prefix) = base.strip_suffix(vowel)
            && let Some((_, v, t @ (0 | 8))) = last(prefix)
            && (vowel == '오') == matches!(prefix, "듣자" | "받자")
            && (t == 0 || vowel == '우')
        {
            push(
                out,
                replace_last(prefix, v, if t == 8 { 11 } else { 17 }).unwrap(),
                "irregular.bieup",
            );
        }
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
        // KRDict 73877: colloquial friendly command after 오다 or an
        // 오다-final verb. The engine checks the recovered owner separately.
        out.push(Ending {
            suffix: "",
            form: "ㄴ",
            boundary: Attached(4),
            connector: false,
        });
        // NIKL 305262 and FAQ 6416: separate regular modern endings;
        // -거라 is not restricted to 가다, and 오거라 coexists with 오너라.
        for (suffix, boundary) in [("거라", Literal), ("너라", ComeStem)] {
            out.push(Ending {
                suffix,
                form: suffix,
                boundary,
                connector: false,
            });
        }
        // 되/으되 are not a productive (으) vowel-boundary pair: ordinary
        // consonants keep 되; lexical/prefinal licenses are checked later.
        for suffix in ["되", "으되"] {
            out.push(Ending {
                suffix,
                form: "으되",
                boundary: Literal,
                connector: false,
            });
        }
        for suffix in [
            "다",
            "단",
            "다간",
            "다가는",
            "잔",
            "냔",
            "느냔",
            "답니다",
            "단다",
            "대",
            "재",
            "냬",
            "느냬",
            "더래",
            "다지",
            "다죠",
            "다지만",
            "다니까",
            "다느니",
            "냐느니",
            "느냐느니",
            "자느니",
            "자는구나",
            "자는군",
            "자더군",
            "자더군요",
            "더라느니",
            "냐지만",
            "냐니까",
            "느냐지만",
            "느냐니까",
            "자지만",
            "자니까",
            "더라지만",
            "더라니까",
            "잔다",
            "냔다",
            "느냔다",
            "더란다",
            "다네",
            "다는데",
            "다던",
            "다더니",
            "다나",
            "다더니만",
            "다더니마는",
            "다던데",
            "자던",
            "자던데",
            "냐던데",
            "느냐던데",
            "더라네",
            "더라는데",
            "다며",
            "다면서",
            "더라며",
            "더라면서",
            "더라니",
            "자니",
            "냐니",
            "느냐니",
            "자며",
            "자면서",
            "냐며",
            "냐면서",
            "느냐며",
            "느냐면서",
            "다거나",
            "다든가",
            "다가",
            "고자",
            "건대",
            "구나",
            "다는구나",
            "다는군",
            "다더군",
            "다더군요",
            "더라는구나",
            "더라는군",
            "냐는구나",
            "냐는군",
            "냐더군",
            "냐더군요",
            "느냐는구나",
            "느냐는군",
            "느냐더군",
            "느냐더군요",
            "라는구나",
            "라는군",
            "라더군",
            "라더군요",
            "구려",
            "구먼",
            "는구나",
            "는구려",
            "는구먼",
            "는군",
            "는군요",
            "더구나",
            "더구려",
            "더구먼",
            "로구나",
            "로구려",
            "로구먼",
            "로군",
            "군",
            "군요",
            "는가",
            "는가요",
            "는감",
            "는고",
            "는데도",
            "는데다가",
            "느냐",
            "느냐고",
            "냐면",
            "느냐면",
            "느니라",
            "느니",
            "느니만",
            "느니만큼",
            "느니보다",
            "느니보다는",
            "나이다",
            "나이까",
            "느라고",
            "느라",
            "고",
            "고말고",
            "고서",
            "고요",
            "지만",
            "지마는",
            "건만",
            "건마는",
            "지만요",
            "지",
            "지요",
            "죠",
            "게",
            "게끔",
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
            "더니만",
            "더니마는",
            "더라",
            "더라고",
            "더라는",
            "더군요",
            "더군",
            "던",
            "는바",
            "는걸",
            "던걸",
            "던바",
            "던데",
            "던데요",
            "던가",
            "던감",
            "던고",
            "던지",
            "던들",
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
            "다마는",
            "다만",
            "답시고",
            "다마다",
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
                connector: matches!(suffix, "고" | "지" | "게" | "게끔"),
            });
        }
        // Native arrow entries redirect these input spellings to 구먼.
        // This is tolerant reading support, not a claim of normative spelling.
        for (suffix, form) in [
            ("구만", "구먼"),
            ("는구만", "는구먼"),
            ("더구만", "더구먼"),
            ("로구만", "로구먼"),
        ] {
            out.push(Ending {
                suffix,
                form,
                boundary: Literal,
                connector: false,
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
            // Original KRDict 73889 건고 preserves the contracted copula.
            ("고", "은고", 4),
            ("가요", "은가요", 4),
            ("까", "을까", 8),
            ("까요", "을까요", 8),
            ("지", "을지", 8),
            ("니다", "습니다", 17),
            ("니까", "습니까", 17),
            ("냐", "냐", 0),
            ("냐고", "냐고", 0),
            ("니", "니", 0),
            ("니", "으니", 0),
            ("니라", "으니라", 0),
            ("니까", "으니까", 0),
            ("고", "고", 0),
            ("지만", "지만", 0),
            ("지마는", "지마는", 0),
            // NIKL FAQ 8917 accepts 나라건만 alongside 나라이건만.
            // The full form keeps the same vowel-final copula boundary.
            ("건만", "건만", 0),
            ("건마는", "건마는", 0),
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
            // Reviewed vowel-final copula omission; unlisted owner classes
            // keep their existing dictionary uncertainty.
            ("리만큼", "으리만큼", 0),
            ("련만", "으련만", 0),
            ("련마는", "으련마는", 0),
            ("더니만", "더니만", 0),
            ("더니마는", "더니마는", 0),
            ("더라도", "더라도", 0),
            ("던데", "던데", 0),
            ("던데요", "던데요", 0),
            ("던가", "던가", 0),
            ("던지", "던지", 0),
            ("더라네", "더라네", 0),
            ("더라는데", "더라는데", 0),
            ("더라며", "더라며", 0),
            ("더라면서", "더라면서", 0),
            ("더라니", "더라니", 0),
            ("더라느니", "더라느니", 0),
            ("냐느니", "냐느니", 0),
            ("더란다", "더란다", 0),
            ("더래", "더래", 0),
            ("냬", "냬", 0),
            ("더라지만", "더라지만", 0),
            ("더라니까", "더라니까", 0),
            ("냐지만", "냐지만", 0),
            ("냐니까", "냐니까", 0),
            ("냔다", "냔다", 0),
            // KRDict 86544 explicitly illustrates 우스갯소리려니.
            ("려니", "으려니", 0),
            // KRDict 85653 explicitly illustrates 누구냔.
            ("냔", "냔", 0),
            // 리까 lists 이다 attachment; omitted 이 keeps the existing
            // vowel-final nominal condition and never inflects the nominal.
            ("리까", "으리까", 0),
            // KRDict 79260 licenses 이다; NIKL documents vowel-final 이
            // omission generally. Keep their unreviewed Rya composition as
            // an explicitly marked hypothesis, with Unknown attachment.
            ("랴", "으랴", 0),
            ("걸", "은걸", 4),
            ("걸", "을걸", 8),
            ("던걸", "던걸", 0),
            ("구나", "구나", 0),
            ("군", "군", 0),
            ("군요", "군요", 0),
            ("구려", "구려", 0),
            ("구먼", "구먼", 0),
            ("구만", "구먼", 0),
            ("더구나", "더구나", 0),
            ("더라는구나", "더라는구나", 0),
            ("더라는군", "더라는군", 0),
            ("냐던데", "냐던데", 0),
            ("냐는구나", "냐는구나", 0),
            ("냐는군", "냐는군", 0),
            ("냐더군", "냐더군", 0),
            ("냐더군요", "냐더군요", 0),
            ("더구려", "더구려", 0),
            ("더구먼", "더구먼", 0),
            ("더구만", "더구먼", 0),
            ("로구나", "로구나", 0),
            ("로구려", "로구려", 0),
            ("로구먼", "로구먼", 0),
            ("로군", "로군", 0),
            ("로구만", "로구먼", 0),
        ] {
            out.push(Ending {
                suffix,
                form,
                boundary: OmittedCopula(attached),
                connector: matches!(suffix, "지" | "고"),
            });
        }
        // KRDict 85824 is an exact reviewed comparative expression with
        // no POS, not a license to reinterpret arbitrary expressions. Its
        // vowel/ㄹ variant is retained without inventing a missing full entry.
        out.push(Ending {
            suffix: "니만",
            form: "니만",
            boundary: EuZero,
            connector: false,
        });
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
            ("다", "어다"),
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
            ("으니만큼", "니만큼", "으니만큼"),
            ("으니라", "니라", "으니라"),
            ("으며", "며", "으며"),
            ("으면서", "면서", "으면서"),
            ("으므로", "므로", "으므로"),
            ("으러", "러", "으러"),
            ("으려고", "려고", "으려고"),
            ("으려면", "려면", "으려면"),
            ("으려", "려", "으려"),
            ("으려는", "려는", "으려는"),
            ("으려는가", "려는가", "으려는가"),
            ("으려는지", "려는지", "으려는지"),
            ("으려나", "려나", "으려나"),
            ("으려니", "려니", "으려니"),
            ("으려니까", "려니까", "으려니까"),
            ("으려더라", "려더라", "으려더라"),
            ("으려던", "려던", "으려던"),
            ("으려면서", "려면서", "으려면서"),
            ("으려든지", "려든지", "으려든지"),
            ("으려거든", "려거든", "으려거든"),
            ("으려기에", "려기에", "으려기에"),
            ("으려는데", "려는데", "으려는데"),
            ("으려다", "려다", "으려다"),
            ("으려다가", "려다가", "으려다가"),
            ("으려더니", "려더니", "으려더니"),
            ("으려도", "려도", "으려도"),
            ("으려야", "려야", "으려야"),
            ("으라", "라", "으라"),
            ("으라고", "라고", "으라고"),
            ("으라는", "라는", "으라는"),
            ("으란", "란", "으란"),
            ("으란다", "란다", "으란다"),
            ("으래", "래", "으래"),
            ("으라지", "라지", "으라지"),
            ("으라죠", "라죠", "으라죠"),
            ("으라지만", "라지만", "으라지만"),
            ("으라니까", "라니까", "으라니까"),
            ("으라면", "라면", "으라면"),
            ("으랍니다", "랍니다", "으랍니다"),
            ("으라네", "라네", "으라네"),
            ("으라는데", "라는데", "으라는데"),
            ("으라던", "라던", "으라던"),
            ("으라더니", "라더니", "으라더니"),
            ("으라던데", "라던데", "으라던데"),
            ("으라며", "라며", "으라며"),
            ("으라면서", "라면서", "으라면서"),
            ("으라니", "라니", "으라니"),
            ("으라느니", "라느니", "으라느니"),
            ("으라는구나", "라는구나", "으라는구나"),
            ("으라는군", "라는군", "으라는군"),
            ("으라더군", "라더군", "으라더군"),
            ("으라더군요", "라더군요", "으라더군요"),
            ("으라거나", "라거나", "으라거나"),
            ("으세요", "세요", "으세요"),
            ("으십시오", "십시오", "으십시오"),
            // Modern prayers/literary requests; the polite 옵소서 form is
            // a synchronic ending bundle (NIKL consultation 315692).
            ("으소서", "소서", "으소서"),
            ("으옵소서", "옵소서", "으옵소서"),
            ("으냐", "냐", "으냐"),
            ("으냐고", "냐고", "으냐고"),
            ("으냐면", "냐면", "으냐면"),
            ("으냐던데", "냐던데", "으냐던데"),
            ("으냐지만", "냐지만", "으냐지만"),
            ("으냐니까", "냐니까", "으냐니까"),
            ("으냔다", "냔다", "으냔다"),
            ("으냬", "냬", "으냬"),
            ("으냐는", "냐는", "으냐는"),
            ("으냐며", "냐며", "으냐며"),
            ("으냐면서", "냐면서", "으냐면서"),
            ("으냐니", "냐니", "으냐니"),
            ("으냐느니", "냐느니", "으냐느니"),
            ("으냐는구나", "냐는구나", "으냐는구나"),
            ("으냐는군", "냐는군", "으냐는군"),
            ("으냐더군", "냐더군", "으냐더군"),
            ("으냐더군요", "냐더군요", "으냐더군요"),
            ("으냔", "냔", "으냔"),
            ("으나", "나", "으나"),
            ("으나마", "나마", "으나마"),
            ("으리라", "리라", "으리라"),
            ("으리라고", "리라고", "으리라고"),
            // Literary/formal future or intention: keep 리다 as a final
            // bundle, distinct from conjectural 으리 + factual 라.
            // NIKL, 임동훈 (1998), 어미의 사전적 처리, section 2.2.
            ("으리다", "리다", "으리다"),
            // NIKL 리까/으리까 are final questions; polite 오/사오
            // remain separate prefinals rather than part of this ending.
            ("으리까", "리까", "으리까"),
            // Native 79260/79261 (rhetorical question / offer) and
            // 80308/80306 (enumeration). Keep the lexical ㄹ boundary.
            ("으랴", "랴", "으랴"),
            // Native KRdict 87692/86608: degree or grounds ending.
            ("으리만큼", "리만큼", "으리만큼"),
            // Native 86545/86602 and 86546/86603: counterfactual expectation.
            ("으련마는", "련마는", "으련마는"),
            ("으련만", "련만", "으련만"),
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
            // KRDict 87110/87112: background connective, not bound noun 바.
            ("은바", "바", "은바", 4),
            // KRDict 81040/81045: realization/explanation, distinct from 것 + 를.
            ("은걸", "걸", "은걸", 4),
            ("은지", "지", "은지", 4),
            ("은가", "가", "은가", 4),
            // KRDict 73878/73888: refuting questions, preserving ㄴ/은 spelling.
            ("은감", "감", "은감", 4),
            // KRDict 73889/73901: literary ㄴ고/은고 question allomorphs.
            ("은고", "고", "은고", 4),
            ("은가요", "가요", "은가요", 4),
            ("은데도", "데도", "은데도", 4),
            ("은데다가", "데다가", "은데다가", 4),
            ("은들", "들", "은들", 4),
            ("을", "", "을", 8),
            // KRDict 76460/76475: conjecture/regret, preserving stem-final ㄹ.
            ("을걸", "걸", "을걸", 8),
            ("을까", "까", "을까", 8),
            ("을까요", "까요", "을까요", 8),
            ("을게", "게", "을게", 8),
            ("을게요", "게요", "을게요", 8),
            ("을래", "래", "을래", 8),
            ("을래요", "래요", "을래요", 8),
            ("을지", "지", "을지", 8),
            ("을는지", "는지", "을는지", 8),
            // KRDict 77345/77346: a caution final. Attached ㄹ preserves
            // lexical ㄹ (들라) and vowel/irregular recovery (들을라).
            ("을라", "라", "을라", 8),
            ("을라고", "라고", "을라고", 8),
            ("을라고요", "라고요", "을라고요", 8),
            ("을지라도", "지라도", "을지라도", 8),
            ("을밖에", "밖에", "을밖에", 8),
            ("을라치면", "라치면", "을라치면", 8),
            ("을망정", "망정", "을망정", 8),
            ("을지언정", "지언정", "을지언정", 8),
            ("을수록", "수록", "을수록", 8),
            ("음", "", "음", 16),
            // KRDict 78483/78496: a promise final, distinct from nominal 음.
            // ㄹ + ㅁ retains ㄹ as ㄻ (삶세), rather than deleting it.
            ("음세", "세", "음세", 16),
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
            ("는다마는", "다마는", "는다마는", 4),
            ("는다만", "다만", "는다만", 4),
            ("는답시고", "답시고", "는답시고", 4),
            ("는다고", "다고", "는다고", 4),
            ("는다는", "다는", "는다는", 4),
            ("는다면", "다면", "는다면", 4),
            ("는답니다", "답니다", "는답니다", 4),
            ("는다네", "다네", "는다네", 4),
            ("는다는데", "다는데", "는다는데", 4),
            ("는다던", "다던", "는다던", 4),
            ("는다더니", "다더니", "는다더니", 4),
            // KRDict 74691/74697: present reports keep the verb allomorph.
            ("는다나", "다나", "는다나", 4),
            ("는다더니만", "다더니만", "는다더니만", 4),
            ("는다더니마는", "다더니마는", "는다더니마는", 4),
            ("는다던데", "다던데", "는다던데", 4),
            ("는다며", "다며", "는다며", 4),
            ("는다면서", "다면서", "는다면서", 4),
            ("는다니", "다니", "는다니", 4),
            ("는다느니", "다느니", "는다느니", 4),
            ("는다는구나", "다는구나", "는다는구나", 4),
            ("는다는군", "다는군", "는다는군", 4),
            ("는다더군", "다더군", "는다더군", 4),
            ("는다더군요", "다더군요", "는다더군요", 4),
            ("는단", "단", "는단", 4),
            ("는단다", "단다", "는단다", 4),
            ("는대", "대", "는대", 4),
            ("는다지", "다지", "는다지", 4),
            ("는다죠", "다죠", "는다죠", 4),
            ("는다지만", "다지만", "는다지만", 4),
            ("는다니까", "다니까", "는다니까", 4),
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
            ("지마는", "치마는"),
            ("지만요", "치만요"),
            ("다", "타"),
            ("다고", "타고"),
            ("다는", "타는"),
            ("다니", "타니"),
            ("다느니", "타느니"),
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
        for suffix in [
            "라",
            "라도",
            "라야",
            "라야만",
            "라서",
            "라고",
            "라는",
            "라면",
            "랍니다",
            "란다",
            "래",
            "라지",
            "라죠",
            "라지만",
            "라니까",
            "라든가",
            "라네",
            "라는데",
            "라더니",
            "라던",
            "라던데",
            "라며",
            "라면서",
            "라니",
            "라느니",
            "라는구나",
            "라는군",
            "라더군",
            "라더군요",
            "냐면",
        ] {
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
            ("이라야", 4, 1),
            ("라야", 4, 2),
            ("이라야만", 4, 1),
            ("라야만", 4, 2),
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
            // NIKL 327751 also accepts uncontracted 새인들/장사인들.
            ("인들", 4, 0),
            ("을랑", 3, 1),
            ("일랑", 3, 1),
            ("설랑", 3, 0),
            ("에설랑", 3, 0),
            ("을랑은", 4, 1),
            ("일랑은", 4, 1),
            ("설랑은", 4, 0),
            ("만", 3, 0),
            ("마는", 3, 0),
            ("까지", 3, 0),
            ("부터", 3, 0),
            // Bundled source particles retain the outer stage of 부터.
            // Their inner case boundary is restored when peeling the base.
            ("으로부터", 3, 3),
            ("로부터", 3, 4),
            ("에서부터", 3, 0),
            ("서부터", 3, 0),
            ("마다", 3, 0),
            ("만큼", 3, 0),
            ("만치", 3, 0),
            ("마냥", 3, 0),
            ("토록", 3, 0),
            ("대로", 3, 0),
            ("조차", 3, 0),
            ("마저", 3, 0),
            ("깨나", 3, 0),
            ("밖에", 3, 0),
            ("치고", 3, 0),
            ("치고는", 3, 0),
            ("치고서", 3, 0),
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
            ("에야", 1, 0),
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
            // Independent KRDict particles, especially 내게/네게/제게.
            // Preserve their surface pronoun bases rather than inventing an
            // underlying 나/너/저 + 에게 contraction.
            ("게", 1, 0),
            ("게서", 1, 0),
            // Bundled recipient + directional case; the outer stage matches
            // the existing 게/에게/한테 + 로 decomposition.
            ("게로", 2, 0),
            ("에게로", 2, 0),
            ("한테로", 2, 0),
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
            ("이여", 1, 1),
            ("시여", 1, 2),
            ("이시여", 1, 1),
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
        "lexical.mal.paired_branch" => {
            "Close a lexical 말다 alternative at the ending of its validated following predicate chain, preserving each predicate's own inflection and auxiliary role."
        }
        "lexical.mal.complement" => {
            "Retain lexical 말다 after a cessative or source-listed paired alternative complement; preserve both predicates and their own endings."
        }
        "lexical.doeda.complement" => {
            "A lexical verb reading of 되다 after -게/-게끔. The earlier predicate and 되다 retain their own endings; a separate auxiliary reading may also be available."
        }
        "lexical.doeda.extended" => {
            "Retain lexical verb 되다 after a source-listed scheduled, necessity, conditional or permission/prohibition complement, preserving each owner's own inflection."
        }
        "auxiliary.doeda.extended" => {
            "A separately attributed auxiliary 되다 reading after necessity, conditional or permission/prohibition complements; dictionary verb classification is preserved independently."
        }
        "doeda.negative_bridge" => {
            "Retain intervening negative adverb 안 before 되다 as its own component; it neither supplies a predicate ending nor replaces the lexical compound 안되다."
        }
        "lexical.mal.nominal" => {
            "Retain lexical 말다 after nominal contrast, an explicit object, or a source-listed bare object in joined input; ordinary word spacing is not inferred."
        }
        "lexical.mal.fixed_adverb" => {
            "Retain the source-attested fixed expression 꼼짝 말다 with its dictionary adverb; do not invent an omitted 하지 or assert object syntax."
        }
        "auxiliary.internal_particle" => {
            "Retain a licensed particle between an ending and the following auxiliary predicate."
        }
        "particle.quoted_restrictive" => {
            "Attach restrictive 밖에 to a reported clause, preserving its ending and any auxiliary or copula components; contextual polarity is not resolved."
        }
        "particle.concessive" => {
            "Attach concessive 만/마는 after a licensed final ending; retain the distinct nominal 만 reading where applicable."
        }
        "particle.chigo" => {
            "Attach 치고/치고는/치고서 to a nominal; retain bundled and component alternatives without selecting the contextual generalization or exception sense."
        }
        "particle.range_case" => {
            "Retain source-attested case marking after 까지 or 부터; the immediately preceding surface still determines the case allomorph."
        }
        "particle.mada_case" => {
            "Recover nominal 마다 + 에 using the independently sourced modern case-following license; preserve outer particle order without selecting a distributive sense or contextual semantic suitability."
        }
        "particle.comparison_extent" => {
            "Recover comparison/extent particles 만치, 마냥 or 토록; contextual comparison and duration are not inferred."
        }
        "particle.comparison_seo" => {
            "Attach source-listed 만치/만큼 after the 어서 connective; this rule represents the particle sense."
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
        "ending.quoted_exclamation" => {
            "Recover a source-listed contracted report with exclamation or recalled reporting as one ending bundle. The implicit reporting predicate is not inserted, and another speaker's experience remains distinct from the current speaker's own retrospective ending."
        }
        "ending.quoted_ra_exclamation" => {
            "Recover a source-listed contracted copular report or reported command as an ending bundle. Factual 라 and command 으라 preserve distinct owners and allomorphs; no implicit reporting predicate or contextual sense is inserted."
        }
        "ending.quoted_proposal_exclamation" => {
            "Recover a source-listed contracted proposal report as an ending bundle. Prefinals belong to the immediate proposal owner; adjective wishes, contextual register and inferred polite followers are not automatically certified, and no implicit reporting predicate is inserted."
        }
        "ending.quoted_conditional_question" => {
            "Recover a source-listed contracted conditional question report as an ending bundle. General spoken 냐, verbal/existential 느냐 and adjectival 으냐 keep distinct immediate owners and allomorphs; no implicit reporting predicate, contextual sense or universal follower license is inserted."
        }
        "ending.quoted_question_exclamation" => {
            "Recover a source-listed contracted question report as one ending bundle. General spoken 냐, verbal/existential 느냐 and adjectival 으냐 retain distinct attachment paths; the implicit reporting predicate and contextual register are not inferred."
        }
        "ending.exclamation" => {
            "Recover distinct present, retrospective and copular exclamation bundles. 구려 also has a recommendation sense; morphology does not choose the contextual meaning."
        }
        "ending.exclamation_variant" => {
            "The input 구만/는구만/더구만/로구만 spelling is retained while its grammatical component follows the KRDict redirect to 구먼. This tolerant reading is not normative spelling certification."
        }
        "ending.geol" => {
            "Recover realization/explanation 은걸/는걸, retrospective 던걸 and conjecture/regret 을걸 as distinct source-listed ending bundles. Attachment follows the immediate predicate owner; dictionary membership does not choose the contextual sense or a bound-noun reading."
        }
        "ending.quoted_neuni" => {
            "Recover source-reviewed listings of quoted statements, questions, commands, proposals and retrospective reports as distinct bundles. Preserve copular/command homonyms and immediate owners; contextual interpretation and unreviewed polite prefinals are not inferred."
        }
        "spacing.nominal_case_predicate" => {
            "Offer explicit missing-space hypotheses between dictionary-backed nominal case phrases and a separately analyzed predicate. Additional source-attested bare-noun/main-verb hypotheses identify their own rule. Preserve original byte spans and every word's independent readings; sentence grammar and intended spacing are not validated."
        }
        "spacing.bare_noun_lexical_verb" => {
            "Offer a separate spacing hypothesis for source-attested 신경질/용기/짜증 before lexical 내다 and 기분 before 내키다, including independently analyzed inflections of each exact verb. Require actual noun and main-verb dictionary entries; preserve raw identity roles, auxiliary homonyms, whole-word alternatives and original byte spans. Other noun/verb pairs and contextual meaning are not inferred."
        }
        "spacing.bare_noun_main_nada" => {
            "Offer separate spacing hypotheses for 39 source-reviewed bare nouns before lexical 나다, including 사고/교통사고, 실감, 신명, 집, 사람, 돈 and literal 피. Require the exact native noun identity and main 나다 62210/homonym 1 with known noun/verb POS and no known conflict; auxiliary 나다 cannot supply that proof. Preserve raw roles, whole-word readings, original UTF-8 spans and prior spacing search priority. Context, sense and intended spacing are not inferred."
        }
        "ending.neuni" => {
            "Recover comparative/enumerative/assertive 느니, comparative 느니만/니만/느니보다/느니보다는 and causal 느니만큼/으니만큼 as reviewed bundles. Contextual sense and unreviewed prefinal combinations are not inferred."
        }
        "ending.rya" => {
            "Recover source-listed -랴/-으랴 rhetorical questions, offers and enumerative endings as the 으랴 allomorph family. Preserve lexical ㄹ, irregular spelling, adjective/copula and prefinal alternatives without selecting a contextual sense or register."
        }
        "ending.caution" => {
            "Recover the source-listed caution final -ㄹ라/-을라 as 을라, preserving lexical ㄹ, irregular stems, explicit copulas and prefinal ownership. Contextual meaning and unlisted attachment extensions remain unreviewed."
        }
        "ending.background_ba" => {
            "Recover literary background connectives -ㄴ바/-은바, -는바 and -던바. Preserve the ending bundle separately from adnominal plus bound noun 바; contextual background and sense are not inferred."
        }
        "ending.volitional_promise" => {
            "Recover promise final -ㅁ세/-음세 as canonical 음세; ㄹ is retained before attached ㅁ. Speaker and contextual suitability are not inferred."
        }
        "ending.choice" => {
            "Recognize the literal choice ending -든가 with its reviewed prefinal licenses, separately from particle 든가."
        }
        "ending.adnominal_expression" => {
            "Retain a reviewed shortened noun-modifying expression as one grammatical component."
        }
        "identity" => "Unchanged vocabulary hypothesis; no dictionary verification.",
        "suffix.nominal.i" => {
            "Separate a source-listed base and noun-forming 이. Preserve lexical nouns and adverbial homonyms; this finite rule does not strip 이 from arbitrary words or attach through prefinals."
        }
        "derivation.nominal.prefix_wang" => {
            "Separate the finite 왕눈이 prefix 왕- and nominal 눈 before noun-forming 이. Preserve the complete 왕눈 base and whole noun. Prefix homonyms remain lookup alternatives; no standalone 왕 king meaning or productive arbitrary prefix stripping is inferred."
        }
        "derivation.nominal.prefix_eol" => {
            "Retain the finite 얼간이 reading as prefix 얼- plus nominal 간 plus noun-forming 이, alongside the independently attested 얼간 noun base and whole word. The prefix source explicitly lists 얼간; all 간 homonyms remain without choosing a contextual sense or historical meaning."
        }
        "derivation.nominal.root_compound" => {
            "Retain the finite 허풍선이 formation as nominal 허풍 plus bound root 선 (扇, fan) before noun-forming 이, following the primary KBS explanation. Whole 허풍선 and 허풍선이 remain. The root makes no standalone POS claim; dictionary 선 homonyms with other recorded origins cannot supply the 扇 reading. This is not general Chinese-root splitting or an exclusive historical analysis."
        }
        "suffix.nominal.bagi" => {
            "Separate the source-listed 점박이 noun as 점 plus the dictionary suffix 박이, alongside the reviewed 점 + 박다 + 이 possibility and whole noun. Only this finite spelling licenses the suffix boundary; contextual senses and historical exclusivity are not selected."
        }
        "derivation.nominal.adnominal" => {
            "Retain the adnominal ㄴ inside the finite 못난이 or 흰둥이 noun formation, before its independently supported 이 or 둥이 suffix. This does not license noun suffixes after arbitrary inflections or prefinals."
        }
        "derivation.nominal.bound_i" => {
            "Preserve NIKL's older 못나다 + adnominal ㄴ + bound noun 이 analysis of 못난이 alongside the newer suffix treatment. The bound noun owns outer suffixes and particles; neither answer date nor dictionary membership resolves the source conflict."
        }
        "suffix.nominal.dungi" => {
            "Separate the finite 흰둥이 formation as 희다 + adnominal ㄴ + 둥이, following the standard-language suffix evidence. Preserve the competing source-listed whole 흰둥 + 이 boundary and lexical noun, without productive 둥이 stripping."
        }
        "derivation.nominal.related_root" => {
            "Link a finite noun-forming root to a reviewed related predicate as a separate lookup hypothesis. The related 하다/거리다 form does not insert a surface segment or license productive restoration, inflection or contextual sense selection."
        }
        "derivation.nominal.compound" => {
            "The first two lookup lemmas form one reviewed compound base before noun-forming 이. Neither component has an inflectional ending; following particles and copulas belong to the derived noun."
        }
        "compound.predicate.well_doeda" => {
            "Retain NIKL's finite 잘되다 compound as adverb 잘 plus lexical verb 되다. 되다 owns the original prefinals and ending; whole 잘되다 readings remain. This is not the suffix -되다, a license for arbitrary adverbs, or a contextual sense selection. Source: 한국어 교육 어휘 내용 개발(4단계), printed p. 54 (2015)."
        }
        "derivation.nominal.compound_l_loss" => {
            "Retain the source-listed 미닫이 compound as 밀다 + 닫다 + noun-forming 이, restoring ㄹ to the first lookup stem under Article 28. This is not productive inflectional ㄹ deletion."
        }
        "suffix.adverbial.i" => {
            "Recover a scoped adjective base before adverb-forming -이; retain whole-word readings."
        }
        "derivation.adverbial.lexical" => {
            "Expand historical 달리/빨리 to 다르다/빠르다 plus -이; not a general 르 inflection rule."
        }
        "deletion.ha" => {
            "Restore 하 deleted after a reviewed ㄱ/ㄷ/ㅂ-sounding coda before a licensed consonant ending."
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
        "particle.coda" => "Separate attached ㄴ들 or ㄹ랑(은) from the preceding open syllable.",
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
        "suffix.approximation" => {
            "Separate approximate amount/degree suffix -쯤 after a nominal base; preserve whole-word alternatives and existing nominal suffixes."
        }
        "suffix.distributive.ssik.adverbial_base" => {
            "A source-listed quantity, degree or repetition adverb is an alternative base before -씩; contextual POS and a suffix-driven word-class change are not inferred."
        }
        "suffix.distributive.ssik" => {
            "Separate -씩 for quantity distribution or unexpected amount/degree after a nominal hypothesis. Quantity context, the source's some-noun restriction and speaker expectation are not inferred; whole-word and standalone 씩 adverb readings remain."
        }
        "suffix.adjectival.dap" => {
            "Separate adjective-forming -답다 from a nominal base, with ㅂ-irregular vowel attachment."
        }
        "suffix.adjective.hada" => {
            "Separate adjectival -하다 from a source-listed noun, adverb or root; retain its independently recorded base role and adjective attachment class, alongside the whole lexical head."
        }
        "suffix.verb.hada" => {
            "Separate verbal -하다 from a source-listed noun, adverb or root; independently licensed nominal bases keep nested -화 or -시 distinct. The suffix owns its inflection; whole lexical readings remain."
        }
        "suffix.auxiliary.verb.hada" => {
            "Separate source-listed auxiliary verbal -하다 from its bound-noun base; retain the original auxiliary parent and its connector, inflection and lexical homonyms independently."
        }
        "suffix.auxiliary.adjective.hada" => {
            "Separate source-listed auxiliary adjectival -하다 from its bound-noun base; retain the original auxiliary parent and its connector, inflection and lexical homonyms independently."
        }
        "suffix.verb.doeda" => {
            "A source-listed passive verb formed from a nominal base and -되다; prefinals and endings belong to the suffix, while the whole lexical head remains a separate candidate."
        }
        "suffix.nominal.hwa" => {
            "Separate source-listed noun-forming -화 (化); separately recorded nested passive -되다 owns its own inflection."
        }
        "suffix.nominal.si" => {
            "Separate noun-forming -시 (視), meaning considering/seeing as, in finite KRDict 71567 examples with recorded noun bases; separately sourced passive heads may add -되다. Honorific -시- remains a distinct prefinal."
        }
        "suffix.adjective.doeda" => {
            "A source-listed adjective formed from a noun, adverb or bound root and -되다; the suffix owns its own inflections and its adjective class is independent of base homonyms."
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
        "contraction.yeo_absorption" => {
            "Recover 어 absorbed after an open ㅕ stem (켜, 펴); retain the separate ㅣ + 어 contraction reading."
        }
        "inflection.written_vowel" => {
            "Recover a finite dictionary-listed whole-stem vowel form, including compound ㅡ deletion, 약아/얇아/얕아 and 어째; do not infer arbitrary compound boundaries."
        }
        "contraction.vowel" => "Undo vowel contraction (와, 워, 돼, or 여).",
        "contraction.deictic_verb" => {
            "Recover dictionary-listed 그러/이러/저러 and 고러/요러/조러 vowel contractions, including past inflection; preserve the homonymous adjective and whole-word readings."
        }
        "contraction.noh" => {
            "Restore 놓아 from 놔 at an 아/어 boundary, including 놓다 compounds and auxiliaries."
        }
        "deletion.eu" => "Restore stem-final ㅡ before 아/어.",
        "deletion.rieul" => "Restore ㄹ lost before a consonant ending.",
        "irregular.digeut" => "Hypothesize ㄷ irregular class: ㄷ becomes ㄹ before a vowel.",
        "irregular.bieup" => {
            "Hypothesize ㅂ irregular class: ㅂ becomes 우 (or restricted 오); ㄼ retains ㄹ before 우, as in 섧다 → 설워. Written entry forms determine lexical compatibility."
        }
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
        "prefinal.polite" => {
            "Recover polite (으)오/(으)옵 before its licensed following boundary, after honorific/past/modal markers; contextual politeness is not selected."
        }
        "prefinal.humble_saop" => {
            "Recover literary humble 사오/사옵 after a consonant stem or past/modal marker, retaining ㄹ and selecting the allomorph from the following ending."
        }
        "prefinal.humble_sap" => {
            "Recover the separate literary humble 삽 paradigm after a consonant stem or past/modal marker, before a consonant-initial ending. No vowel allomorph is inferred."
        }
        "prefinal.honorific_polite" => {
            "Recover the NIKL literary honorific bundle (으)옵시 or 사옵시 as one prefinal, keeping its stem boundary and tense/modal ownership separate from the 옵소서 final bundle."
        }
        "prefinal.lexical_jaop" => {
            "Recover modern literary 자오/자옵 immediately after the reviewed 듣/묻/받/좇 lexical subset; preserve whole-predicate alternatives and the following allomorph boundary."
        }
        "prefinal.lexical_jap" => {
            "Recover the separate consonant-following 잡 form only after the reviewed 듣/묻/받/좇 subset; do not extend historical coda distributions productively."
        }
        "prefinal.lexical_jaopsi" => {
            "Recover NIKL's single 자옵시 subject-honorific bundle after the reviewed lexical subset; keep later tense/modal markers separate."
        }
        "prefinal.obligation" => {
            "Recover the intention or necessity expression -아/어/여야겠- as one prefinal-position bundle, without inserting an implicit 하다."
        }
        "prefinal.retrospective" => "Recover retrospective 더 after other prefinal markers.",
        "prefinal.conjectural_quotation" => {
            "Recover conjectural (으)리 before the reviewed shortened quotation -란."
        }
        "ending.literary_question_go" => {
            "Recover the original literary -(으)ㄴ고, -는고 and -던고 question endings while preserving their stem boundaries; contextual register and sense remain unselected."
        }
        "ending.ostensible_reason" => {
            "Recover the source-owned -답시고 and present -(느)ㄴ답시고 connective endings without choosing a contextual speaker attitude."
        }
        "ending.declarative_contrast" => {
            "Recover the source-owned -다마는/-다만 and present -(느)ㄴ다마는/-(느)ㄴ다만 connective bundles; retain final-ending plus particle alternatives without selecting a contextual sense."
        }
        "prefinal.conjectural_ni" => {
            "Recover source-attested literary (으)리 before 니 or 니라, preserving written allomorphs and earlier honorific/past/modal ownership without selecting a contextual sense."
        }
        "prefinal.conjectural_ra" => {
            "Recover conjectural (으)리 before a reviewed factual 라-family ending; retain existing bundled forms separately."
        }
        "ending.factual_ra" => {
            "A factual 라-family ending follows its licensed prefinal, distinct from the homonymous command ending."
        }
        "particle" => "Remove a particle with licensed order and boundary allomorph.",
        "particle.quoted_question" => {
            "Retain a -냐/-느냐/-으냐 question clause before reviewed 에/의/와/가/를/보다 case particles, topic 는 or additive 도; preserve the question owner's inflection, existing particle chains and separate quoted-ending alternatives."
        }
        "particle.future_question" => {
            "Separate a particle following the question noun clause -(으)ㄹ지, retaining its ending and inherited allomorph and immediate-owner checks. No unwritten nominalizer or following verb is restored; context and register remain unselected."
        }
        "particle.comparison_case" => {
            "Recover reviewed 에/에서/서 before comparison particle 처럼; keep case order and distinguish separately spaced adverb 같이."
        }
        "particle.additive_connective" => {
            "Recover reviewed connective endings before additive 조차 or 마저, separately from nominalization."
        }
        "particle.additive_adverb" => {
            "Recover source-attested 잠깐/조금/천천히 before 조차 while preserving the adverbial role."
        }
        "particle.additive_chain" => {
            "Recover reviewed 까지 plus an additive particle, or an additive particle plus subject/object case, in source order."
        }
        "particle.adverbial_focus" => {
            "An adverbial base can take reviewed focus particles 도/은/는/만/까지/부터 and compatible outer particles. Preserve separate nominal and whole-word hypotheses; dictionary and context determine the lexical class."
        }
        "particle.adverbial_case" => {
            "Recover a source-listed emphatic adverb with 가/을/를, preserving its adverbial role and any separately licensed outer particles."
        }
        "copula" => "Separate a nominal and the affirmative copula 이다.",
        "copula.zero" => "Restore the omitted copula after a vowel-final nominal.",
        "copula.omitted_ending" => {
            "Restore omitted copular 이 after a vowel-final nominal before a reviewed ending; the nominal is not a conjugated verb stem."
        }
        "copula.omitted_rya" => {
            "Retain a vowel-final nominal plus omitted 이다 before -랴 as a hypothesis from the copula license and general omission rule; Rya-specific attachment and register remain unreviewed, with dictionary compatibility Unknown."
        }
        "copula.omitted_honorific" => {
            "Restore omitted copular 이 before honorific 시 after a vowel-final nominal; preserve the normal prefinal order and ending restrictions."
        }
        "copula.omitted_prefinal" => {
            "Restore omitted copular 이 before modal 겠 or retrospective 더 after a vowel-final nominal, retaining prefinal order and ending restrictions."
        }
        "copula.omitted_polite" => {
            "Restore omitted copular 이 after a vowel-final nominal before literary polite 오 + 리까; preserve the nominal and separate copula, polite and question components. Further polite followers require separate review."
        }
        "copula.intention_relational" => {
            "Preserve a possible relational -적 nominal state-making copula before intention 하다/들다; dictionary attachment remains unknown."
        }
        "nominal.colloquial_geot" => {
            "Expand the colloquial 거/이거/그거/저거 nominal to 것/이것/그것/저것 before a copula; preserve the short lexical alternative."
        }
        "auxiliary" => "Separate a licensed connective plus attached auxiliary.",
        "irregular.mal" => {
            "Restore 말다 in the short imperatives 마, 마라 and 마요, including lexical 걱정 마 and prohibitive 하지 마."
        }
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
        "derivation.adverbial.opaque" => {
            "Separate a reviewed opaque root and its adverb-forming suffix. The root role does not assert a standalone noun, adverb or predicate dictionary entry."
        }
        "derivation.adverbial.related_opaque" => {
            "Use an independently attested related adjective as a possible lookup lemma for a reviewed opaque adverb root. This relationship is inferred from root/suffix evidence; dictionary headword availability is separate."
        }
        "ending.confirmation" => "Recognize the confirming or correcting expression -잖아/-잖아요.",
        "ending.reporting_reason" => {
            "Recognize repeated assertions, commands, questions, proposals and reports used as reasons; preserve source homonyms without inserting an implicit reporting verb."
        }
        "ending.reporting_contrast" => {
            "Recognize contrasting reported statements, commands, questions, proposals and retrospective reports; preserve canonical alternatives without inserting an implicit reporting verb."
        }
        "ending.reporting_confirmation" => {
            "Recognize confirming and reported -다지/-라지 families and contracted polite -죠 forms; preserve factual and command alternatives without inferring an implicit speaker or reporting verb."
        }
        "ending.direct_command" => {
            "Separate modern command -거라 from a verb stem, or -너라 from an 오다-final stem. These are independent regular endings; lexical mood, register and intervening prefinals require separate review."
        }
        "ending.friendly_command.n" => {
            "Separate colloquial friendly-command -ㄴ from a bare 오다-final stem. KRDict 73877 illustrates adults addressing children or small animals; speaker, addressee, register, lexical sense and auxiliary attachment remain contextual hypotheses."
        }
        "ending.activity_reason" => {
            "Recognize full -느라고 and short -느라 reason/purpose endings after verbs or honorific 시; clause-level subject and meaning constraints require context."
        }
        "ending.ryeo_expression" => {
            "Recover a shortened intention expression or the homonymous -(으)려니 assumption ending; preserve its own attachment licenses without inserting implicit 하다 or choosing a contextual sense."
        }
        "ending.rhetorical_llago" => {
            "Recognize -(으)ㄹ라고 doubt and -(으)ㄹ라고요 doubt/strong affirmation; the surface can also occur as colloquial intention, which requires context."
        }
        "ending.reporting_short" => {
            "Recognize short reported statements, requests, proposals, questions and experiences; retain factual/command homonyms and surprise senses without inserting implicit 하다."
        }
        "ending.reporting_familiar" => {
            "Preserve familiar informative/reported statements, commands, questions, proposals and retrospective reports as distinct canonical endings; no implicit 하다 is inserted."
        }
        "ending.reporting_polite" => {
            "Recognize a polite informative or reported-speech ending as one grammatical component; its sense and any implicit speaker are not inferred."
        }
        "ending.short_clause" => {
            "Recognize a reviewed contracted quotation or change/conditional family as one component; preserve homonyms without adding an implicit reporting verb or choosing a contextual sense."
        }
        "ending.uncertainty" => {
            "Recover -(으)ㄹ는지 or the shortened -(으)려는가/지 expression with its own boundary and prefinal licenses; no implicit 하다 or contextual sense is selected."
        }
        "ending.intention_connective" => {
            "Recover a reviewed -(으)려 connective or shortened intention expression as one component, with verb attachment and honorific 시; no implicit 하다 or contextual sense is selected."
        }
        "ending.result_connective" => {
            "Recover -아/어/여다(가) at a bare verb boundary, preserving the short and full forms and reviewed following auxiliaries; sentence-level transfer and object constraints are not inferred."
        }
        "ending.literary_assertion" => {
            "Recognize literary -(으)니라/-느니라 assertions with their distinct boundary and prefinal licenses; lexical class and contextual suitability remain separate evidence."
        }
        "copula.adverbial_base" => {
            "Retain a source-attested adverbial base before a copula, separately from any nominal homonym; the source inventory does not select its contextual sense."
        }
        "copula.connective_seo" => {
            "Attach a copula to a clause ending in -아/어/여서; preserve the connective rather than treating it as a nominalizer. The clause's contextual meaning remains unresolved."
        }
        "ending.necessity" => {
            "Recover -(으)ㄹ밖에 as a necessity ending, distinct from particle 밖에; retain its honorific and past boundaries."
        }
        "ending.habitual_condition" => {
            "Recover -(으)ㄹ라치면 as one conditional ending, with its verb/honorific boundary and attested 있다 use."
        }
        "ending.concessive" => {
            "Recover concessive -(으)ㄴ들/-(으)ㄹ망정/지언정 or counterfactual -던들 with its reviewed stem and prefinal boundary; retain separate particle readings."
        }
        "ending.counterfactual_ryeon" => {
            "Recover -(으)련만 and -(으)련마는 with their own stem allomorphs; retain conjectural and contextual interpretations separately."
        }
        "ending.reported_command_deoni" => {
            "Recover source-listed -라더니 factual copular/negative and -(으)라더니 command reports with separate stem and honorific boundaries; preserve contextual alternatives without inserting an implicit reporting lemma."
        }
        "ending.reported_dana" => {
            "Recover the source-listed casual report -다나/-ㄴ다나/-는다나, preserving statement allomorphs and all lexical hypotheses; annoyance, uncertainty and the implicit speaker are not selected."
        }
        "ending.reported_deoni" => {
            "Recover source-listed -다더니/-ㄴ다더니/-는다더니 as quoted observation endings; preserve canonical components and contextual alternatives without inserting an implicit reporting lemma."
        }
        "ending.deoniman" => {
            "Recover primary -더니만/-더니마는 whole-ending readings and source-attested quoted statement bundles while retaining split alternatives. Contextual sense and register remain unselected."
        }
        "ending.degree_rimankeum" => {
            "Recover -(으)리만큼 as a degree or grounds ending with its own stem allomorph; keep lexical and contextual interpretations separate."
        }
        "ending.expectation_contrast" => {
            "Recover -건만 and -건마는 as distinct expectation-versus-result endings; preserve explicit copulas and vowel-final omitted copulas without choosing a contextual interpretation."
        }
        "ending.expectation_question" => {
            "Recover -(으)려나 as a question or shortened intention expression, preserving dictionary homonyms without inserting implicit 하다 or choosing a contextual sense."
        }
        "ending.refuting_question" => {
            "Recover -(으)ㄴ감, -는감 or -던감 as a refuting question ending; retain its stem boundary and native dictionary identity without choosing a contextual interpretation."
        }
        "ending.emphatic_purpose" => {
            "Recover -게끔 as an emphatic purpose, result, manner or degree ending, preserving source-backed 하다/되다 auxiliary joins and each owner's inflections."
        }
        "ending.emphatic_affirmation" => {
            "Recover -고말고 or -다마다 as an emphatic affirmation ending without choosing a contextual sense; preserve explicit copulas and source-attested polite particles."
        }
        "ending.reporting_ni" => {
            "Recognize a surprise, reported statement, command, proposal or question in a -니 family; preserve homonyms without inserting an implicit reporting verb or selecting a contextual sense."
        }
        "ending.reporting_myeo" => {
            "Recognize a reported statement, command, proposal or question in a -며/-면서 contraction; preserve confirmation homonyms without inserting an implicit reporting verb."
        }
        "ending.reporting_retrospective" => {
            "Recognize a contracted recalled report of a statement, command, proposal or question; keep factual and command allomorphs separate, without inserting an implicit reporting verb or choosing a contextual sense."
        }
        "ending.reporting_ne" => {
            "Recognize a 다네/다는데-family information or reported-speech component, keeping copular/factual and command allomorphs separate; do not infer an implicit 하다 or contextual sense."
        }
        "ending.literary_ri" => {
            "Recover the literary/formal (으)리다 final bundle; do not split it into conjectural 으리 and plain 다."
        }
        "ending.literary_question_ri" => {
            "Recover the literary/formal -(으)리까 question with its own stem and preceding-marker licenses; preserve explicit polite/humble components without selecting intention or conjectural sense."
        }
        "ending.contrast_doe" => {
            "Recognize 되/으되 contrast, qualification or quotation, selecting the written allomorph by the lexical/prefinal boundary rather than general vowel-triggered recovery."
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
        for form in ["ㄴ들", "ㄹ랑", "ㄹ랑은"] {
            forms.insert(form.to_owned(), Particle);
        }
        // Forms emitted outside the tables: copula endings, prefinal recovery,
        // and bounded derivation. Other synthetic contractions reuse table forms.
        for form in ["에요", "야"] {
            forms.insert(format!("-{form}"), Ending);
        }
        for form in [
            "시",
            "었",
            "겠",
            "더",
            "으리",
            "어야겠",
            "으옵",
            "사옵",
            "삽",
            "으옵시",
            "사옵시",
            "자옵",
            "잡",
            "자옵시",
        ] {
            forms.insert(format!("-{form}-"), Prefinal);
        }
        for form in [
            "님", "들", "적", "답다", "되다", "하다", "이", "히", "쯤", "씩", "박이", "둥이", "시",
            "화",
        ] {
            forms.insert(format!("-{form}"), Suffix);
        }
        forms.insert("왕-".to_owned(), Prefix);
        forms.insert("얼-".to_owned(), Prefix);
        let labels: BTreeMap<String, serde_json::Value> =
            serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
        assert_eq!(
            forms.keys().collect::<Vec<_>>(),
            labels
                .iter()
                .filter(|(_, label)| label.get("components").is_none()
                    && label.get("context").is_none())
                .map(|(key, _)| key)
                .collect::<Vec<_>>()
        );
        for (key, label) in &labels {
            if let Some(context) = label.get("context") {
                // Contextual hints reference ordered canonical atoms of different
                // kinds; the hint is not an additional emitted grammar form.
                let context = context.as_array().unwrap();
                assert!(context.len() >= 2, "{key}: context needs multiple atoms");
                for component in context {
                    let form = component["form"].as_str().unwrap();
                    let kind: crate::MorphemeKind =
                        serde_json::from_value(component["kind"].clone()).unwrap();
                    let atom = match kind {
                        Prefinal => format!("-{form}-"),
                        crate::MorphemeKind::Particle => form.to_owned(),
                        crate::MorphemeKind::Prefix => format!("{form}-"),
                        _ => format!("-{form}"),
                    };
                    assert_eq!(forms.get(&atom), Some(&kind), "{key}: {atom}");
                }
                assert_eq!(label["kind"], context.last().unwrap()["kind"], "{key}");
                assert!(
                    label.get("components").is_none(),
                    "{key}: one context schema"
                );
            } else if let Some(components) = label.get("components") {
                // A viewer context references existing atoms; it does not add
                // a synthetic morpheme to the engine's complete form inventory.
                assert_eq!(
                    label["kind"],
                    serde_json::to_value(Prefinal).unwrap(),
                    "{key}"
                );
                let components = components.as_array().unwrap();
                assert!(components.len() >= 2, "{key}: context needs multiple atoms");
                let mut combined = String::new();
                for component in components {
                    let form = component.as_str().unwrap();
                    assert_eq!(forms.get(&format!("-{form}-")), Some(&Prefinal), "{key}");
                    combined.push_str(form);
                }
                assert_eq!(*key, format!("-{combined}-"), "{key}");
            } else {
                assert_eq!(
                    label["kind"],
                    serde_json::to_value(forms[key]).unwrap(),
                    "{key}"
                );
            }
            assert!(!label["label"].as_str().unwrap().trim().is_empty(), "{key}");
            let sources = label["sources"].as_array().unwrap();
            let references = label["references"].as_array();
            assert!(
                !sources.is_empty() || references.is_some_and(|r| !r.is_empty()),
                "{key}: missing source evidence"
            );
            for reference in references.into_iter().flatten() {
                assert!(
                    !reference["title"].as_str().unwrap().trim().is_empty(),
                    "{key}"
                );
                assert!(
                    reference["url"].as_str().unwrap().starts_with("https://"),
                    "{key}"
                );
            }
        }
    }
}
