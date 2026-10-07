use crate::{
    Analysis, Error, Lemma, LemmaKind, Morpheme, MorphemeKind, SpellingClass, SpellingRecovery,
    WordAnalysis,
};
use crate::{
    grammar::{self, Boundary, Recovery},
    hangul::*,
};
use std::{
    collections::{BTreeMap, BTreeSet, HashMap},
    rc::Rc,
};
use unicode_normalization::UnicodeNormalization;

fn lemma(text: impl Into<String>, kind: LemmaKind) -> Lemma {
    Lemma {
        text: text.into(),
        kind,
    }
}
fn morph(form: impl Into<String>, kind: MorphemeKind) -> Morpheme {
    Morpheme {
        form: form.into(),
        kind,
    }
}

// Bounded suffix paths at the nominal boundary, before particles or a copula.
// Whole-word hypotheses remain: a matching tail need not be a real suffix.
fn listed_noun_prefix(word: &str) -> Option<Analysis> {
    let &(_, prefix, base, rule) = grammar::NOUN_I_PREFIX_FORMS
        .iter()
        .find(|&&(surface, _, _, _)| surface == word)?;
    Some(Analysis {
        lemmas: vec![lemma(base, LemmaKind::Nominal)],
        morphemes: vec![
            morph(prefix, MorphemeKind::Prefix),
            morph("이", MorphemeKind::Suffix),
        ],
        rules: vec!["suffix.nominal.i".into(), rule.into()],
        unchanged: false,
        spelling_paths: Vec::new(),
    })
}

fn listed_noun_derivations(word: &str) -> Vec<Analysis> {
    if let Some(base) = crate::nominal_hwa::nominal(word) {
        return vec![Analysis {
            lemmas: vec![lemma(base, LemmaKind::Nominal)],
            morphemes: vec![morph("화", MorphemeKind::Suffix)],
            rules: vec![crate::nominal_hwa::RULE.into()],
            unchanged: false,
            spelling_paths: Vec::new(),
        }];
    }
    if let Some(base) = crate::nominal_si::nominal(word) {
        return vec![Analysis {
            lemmas: vec![lemma(base, LemmaKind::Nominal)],
            morphemes: vec![morph("시", MorphemeKind::Suffix)],
            rules: vec![crate::nominal_si::RULE.into()],
            unchanged: false,
            spelling_paths: Vec::new(),
        }];
    }
    if let Some(&(_, head, root, suffix)) = grammar::NOUN_ADNOMINAL_FORMS
        .iter()
        .find(|&&(surface, _, _, _)| surface == word)
    {
        let mut out = vec![
            Analysis {
                lemmas: vec![lemma(root, LemmaKind::Root)],
                morphemes: vec![morph("이", MorphemeKind::Suffix)],
                rules: vec!["suffix.nominal.i".into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            },
            Analysis {
                lemmas: vec![lemma(head, LemmaKind::Predicate)],
                morphemes: vec![
                    morph("ㄴ", MorphemeKind::Ending),
                    morph(suffix, MorphemeKind::Suffix),
                ],
                rules: vec![
                    "ending".into(),
                    "boundary.regular".into(),
                    "derivation.nominal.adnominal".into(),
                    if suffix == "이" {
                        "suffix.nominal.i"
                    } else {
                        "suffix.nominal.dungi"
                    }
                    .into(),
                ],
                unchanged: false,
                spelling_paths: Vec::new(),
            },
        ];
        if word == "못난이" {
            // Preserve the older NIKL bound-noun analysis alongside its newer
            // suffix treatment, without resolving the disagreement by date.
            out.push(Analysis {
                lemmas: vec![
                    lemma(head, LemmaKind::Predicate),
                    lemma("이", LemmaKind::Nominal),
                ],
                morphemes: vec![morph("ㄴ", MorphemeKind::Ending)],
                rules: vec![
                    "ending".into(),
                    "boundary.regular".into(),
                    "derivation.nominal.bound_i".into(),
                ],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
        return out;
    }
    if let Some(&(_, root, related)) = grammar::NOUN_I_ROOTS
        .iter()
        .find(|&&(surface, _, _)| surface == word)
    {
        let mut out = vec![Analysis {
            lemmas: vec![lemma(root, LemmaKind::Root)],
            morphemes: vec![morph("이", MorphemeKind::Suffix)],
            rules: vec!["suffix.nominal.i".into()],
            unchanged: false,
            spelling_paths: Vec::new(),
        }];
        for &head in related {
            out.push(Analysis {
                lemmas: vec![lemma(head, LemmaKind::Predicate)],
                morphemes: vec![morph("이", MorphemeKind::Suffix)],
                rules: vec![
                    "suffix.nominal.i".into(),
                    "derivation.nominal.related_root".into(),
                ],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
        if let Some(prefix) = listed_noun_prefix(word) {
            out.push(prefix);
        }
        return out;
    }
    if let Some(&(_, base, kind)) = grammar::NOUN_I_SOUND_FORMS
        .iter()
        .find(|&&(surface, _, _)| surface == word)
    {
        return vec![Analysis {
            lemmas: vec![lemma(base, kind)],
            morphemes: vec![morph("이", MorphemeKind::Suffix)],
            rules: vec!["suffix.nominal.i".into()],
            unchanged: false,
            spelling_paths: Vec::new(),
        }];
    }
    if let Some(&(_, base)) = grammar::NOUN_I_NOMINAL_FORMS
        .iter()
        .find(|&&(surface, _)| surface == word)
    {
        let mut out = vec![Analysis {
            lemmas: vec![lemma(base, LemmaKind::Nominal)],
            morphemes: vec![morph("이", MorphemeKind::Suffix)],
            rules: vec!["suffix.nominal.i".into()],
            unchanged: false,
            spelling_paths: Vec::new(),
        }];
        if let Some(prefix) = listed_noun_prefix(word) {
            out.push(prefix);
        }
        if let Some(&(_, left, right, _)) = grammar::NOUN_I_ROOT_COMPOUNDS
            .iter()
            .find(|&&(surface, _, _, _)| surface == word)
        {
            out.push(Analysis {
                lemmas: vec![
                    lemma(left, LemmaKind::Nominal),
                    lemma(right, LemmaKind::Root),
                ],
                morphemes: vec![morph("이", MorphemeKind::Suffix)],
                rules: vec![
                    "suffix.nominal.i".into(),
                    "derivation.nominal.root_compound".into(),
                ],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
        return out;
    }
    if let Some(&(_, left, kind, right)) = grammar::NOUN_I_COMPOUNDS
        .iter()
        .find(|&&(surface, _, _, _)| surface == word)
    {
        let mut rules = vec![
            "suffix.nominal.i".into(),
            "derivation.nominal.compound".into(),
        ];
        if word == "미닫이" {
            rules.push("derivation.nominal.compound_l_loss".into());
        }
        let mut out = vec![Analysis {
            lemmas: vec![lemma(left, kind), lemma(right, LemmaKind::Predicate)],
            morphemes: vec![morph("이", MorphemeKind::Suffix)],
            rules,
            unchanged: false,
            spelling_paths: Vec::new(),
        }];
        if word == "점박이" {
            out.push(Analysis {
                lemmas: vec![lemma("점", LemmaKind::Nominal)],
                morphemes: vec![morph("박이", MorphemeKind::Suffix)],
                rules: vec!["suffix.nominal.bagi".into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
        return out;
    }
    let Some(&(_, head)) = grammar::NOUN_I_FORMS
        .iter()
        .find(|&&(surface, _)| surface == word)
    else {
        return Vec::new();
    };
    vec![Analysis {
        lemmas: vec![lemma(head, LemmaKind::Predicate)],
        morphemes: vec![morph("이", MorphemeKind::Suffix)],
        rules: vec!["suffix.nominal.i".into()],
        unchanged: false,
        spelling_paths: Vec::new(),
    }]
}

fn simple_nominal_derivations(word: &str) -> Vec<Analysis> {
    let mut out = listed_noun_derivations(word);
    // One honorific, relational, or plural suffix; also honorific + plural.
    // Each shorter base is a lexical hypothesis, never recursively re-split.
    for (form, rule) in [
        ("님", "suffix.honorific"),
        ("적", "suffix.relational"),
        ("들", "suffix.plural"),
    ] {
        if let Some(base) = word.strip_suffix(form).filter(|s| !s.is_empty()) {
            out.push(Analysis {
                lemmas: vec![lemma(base, LemmaKind::Nominal)],
                morphemes: vec![morph(form, MorphemeKind::Suffix)],
                rules: vec![rule.into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
            if form == "들" {
                for mut a in listed_noun_derivations(base) {
                    a.morphemes.push(morph(form, MorphemeKind::Suffix));
                    a.rules.push(rule.into());
                    out.push(a);
                }
            }
            // Only honorific + plural is licensed in this batch.
            if form == "들"
                && let Some(root) = base.strip_suffix('님').filter(|s| !s.is_empty())
            {
                out.push(Analysis {
                    lemmas: vec![lemma(root, LemmaKind::Nominal)],
                    morphemes: vec![
                        morph("님", MorphemeKind::Suffix),
                        morph("들", MorphemeKind::Suffix),
                    ],
                    rules: vec!["suffix.honorific".into(), "suffix.plural".into()],
                    unchanged: false,
                    spelling_paths: Vec::new(),
                });
            }
        }
    }
    out
}

fn nominal_derivations(word: &str) -> Vec<Analysis> {
    let mut out = simple_nominal_derivations(word);
    // Quantity distribution and unexpected degree are conditional meanings of
    // the same -씩 suffix. A nominal hypothesis does not decide whether the
    // surrounding phrase supplies a quantity or the speaker's expectation.
    // Strip once; whole bases and the existing finite noun derivations remain.
    if let Some(base) = word.strip_suffix('씩').filter(|s| !s.is_empty()) {
        let mut bases = simple_nominal_derivations(base);
        bases.push(Analysis {
            lemmas: vec![lemma(base, LemmaKind::Nominal)],
            morphemes: vec![],
            rules: vec![],
            unchanged: false,
            spelling_paths: Vec::new(),
        });
        for mut a in bases {
            a.morphemes.push(morph("씩", MorphemeKind::Suffix));
            a.rules.push("suffix.distributive.ssik".into());
            out.push(a);
        }
    }
    // Approximation follows a nominal (including the existing bounded suffix
    // paths). Do not recursively peel 쯤 or treat a preceding particle/ending
    // as a noun phrase: those attachment classes need separate evidence.
    if let Some(base) = word.strip_suffix('쯤').filter(|s| !s.is_empty()) {
        let mut bases = simple_nominal_derivations(base);
        bases.push(Analysis {
            lemmas: vec![lemma(base, LemmaKind::Nominal)],
            morphemes: vec![],
            rules: vec![],
            unchanged: false,
            spelling_paths: Vec::new(),
        });
        for mut a in bases {
            a.morphemes.push(morph("쯤", MorphemeKind::Suffix));
            a.rules.push("suffix.approximation".into());
            out.push(a);
        }
    }
    out
}

fn nominal_bases(word: &str) -> Vec<Analysis> {
    let mut out = vec![Analysis {
        lemmas: vec![lemma(word, LemmaKind::Nominal)],
        morphemes: vec![],
        rules: vec![],
        unchanged: false,
        spelling_paths: Vec::new(),
    }];
    out.extend(nominal_derivations(word));
    out
}

// Source-listed predicate adverbs, separate from inflection and auxiliaries.
// Attachment is lexical: do not strip 이/히 from every noun/verb or infer a
// general 르 rule from the historical 달리/빨리 forms.
fn adverb_derivations(word: &str) -> Vec<Analysis> {
    let mut out: Vec<_> = adverb_derivation(word).into_iter().collect();
    if let Some(base) = word.strip_suffix('씩')
        && grammar::SSIK_ADVERB_BASES.contains(&base)
    {
        out.push(Analysis {
            lemmas: vec![lemma(base, LemmaKind::Adverbial)],
            morphemes: vec![morph("씩", MorphemeKind::Suffix)],
            rules: vec![
                "suffix.distributive.ssik".into(),
                "suffix.distributive.ssik.adverbial_base".into(),
            ],
            unchanged: false,
            spelling_paths: Vec::new(),
        });
    }

    for &(root, suffix, related) in grammar::OPAQUE_ADVERB_ROOTS {
        if word.strip_suffix(suffix) != Some(root) {
            continue;
        }
        out.push(Analysis {
            lemmas: vec![lemma(root, LemmaKind::Root)],
            morphemes: vec![morph(suffix, MorphemeKind::Suffix)],
            rules: vec![
                "derivation.adverbial.opaque".into(),
                "suffix.adverbial.hi".into(),
            ],
            unchanged: false,
            spelling_paths: Vec::new(),
        });
        if let Some(head) = related {
            out.push(Analysis {
                lemmas: vec![lemma(head, LemmaKind::Predicate)],
                morphemes: vec![morph(suffix, MorphemeKind::Suffix)],
                rules: vec![
                    "derivation.adverbial.related_opaque".into(),
                    "derivation.adverbial.hada".into(),
                    "suffix.adverbial.hi".into(),
                ],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
    }
    out
}

fn adverb_derivation(word: &str) -> Option<Analysis> {
    for (root, suffix, kind, rule) in grammar::ADVERB_ADVERB_ROOTS
        .iter()
        .map(|&(root, suffix)| {
            (
                root,
                suffix,
                LemmaKind::Adverbial,
                "derivation.adverbial.adverb",
            )
        })
        .chain(grammar::ADVERB_NOMINAL_ROOTS.iter().map(|&root| {
            (
                root,
                "이",
                LemmaKind::Nominal,
                "derivation.adverbial.nominal",
            )
        }))
    {
        if word.strip_suffix(suffix) == Some(root) {
            return Some(Analysis {
                lemmas: vec![lemma(root, kind)],
                morphemes: vec![morph(suffix, MorphemeKind::Suffix)],
                rules: vec![
                    rule.into(),
                    if suffix == "이" {
                        "suffix.adverbial.i"
                    } else {
                        "suffix.adverbial.hi"
                    }
                    .into(),
                ],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
    }
    let (stem, suffix, recovery) = match word {
        "익히" => (
            "익숙하".into(),
            "히",
            Some("derivation.adverbial.shortened"),
        ),
        "특히" => (
            "특별하".into(),
            "히",
            Some("derivation.adverbial.shortened"),
        ),
        "달리" => ("다르".into(), "이", Some("derivation.adverbial.lexical")),
        "빨리" => ("빠르".into(), "이", Some("derivation.adverbial.lexical")),
        _ => {
            let (stem, suffix) = word
                .strip_suffix('이')
                .map(|s| (s, "이"))
                .or_else(|| word.strip_suffix('히').map(|s| (s, "히")))?;
            if suffix == "이"
                && (stem.ends_with("같")
                    || stem.ends_with("없")
                    || matches!(stem, "굳" | "길" | "깊" | "높" | "많" | "헛되" | "적잖"))
            {
                (stem.into(), suffix, None)
            } else if suffix == "이"
                && matches!(stem, "가까" | "가벼" | "고" | "새로" | "외로" | "즐거")
            {
                let (_, vowel, _) = last(stem)?;
                (
                    replace_last(stem, vowel, 17)?,
                    suffix,
                    Some("derivation.adverbial.bieup"),
                )
            } else if grammar::ADVERB_HADA_ROOTS
                .iter()
                .any(|&(root, form)| root == stem && form == suffix)
            {
                (
                    format!("{stem}하"),
                    suffix,
                    Some("derivation.adverbial.hada"),
                )
            } else {
                return None;
            }
        }
    };
    let mut rules = vec![if suffix == "이" {
        "suffix.adverbial.i".into()
    } else {
        "suffix.adverbial.hi".into()
    }];
    if let Some(rule) = recovery {
        rules.push(rule.into());
        if rule == "derivation.adverbial.shortened" {
            rules.push("derivation.adverbial.hada".into());
        }
    }
    Some(Analysis {
        lemmas: vec![lemma(format!("{stem}다"), LemmaKind::Predicate)],
        morphemes: vec![morph(suffix, MorphemeKind::Suffix)],
        rules,
        unchanged: false,
        spelling_paths: Vec::new(),
    })
}

#[derive(Clone)]
struct Predicate {
    stem: String,
    // Following predicates and intervening adverbs retain their own role.
    following: Vec<(String, LemmaKind)>,
    leading_lemmas: Vec<Lemma>,
    morphs: Vec<Morpheme>,
    rules: Vec<String>,
    connector: bool,
    // Decided before auxiliary provenance is merged, so an irregular auxiliary
    // cannot license an incorrectly conjugated -답다 on the left.
    dap_suffix: bool,
    ha_contracted: bool,
    // Track the initial copula's 이 + 어 -> 여 separately from contractions
    // inside later auxiliaries; merged rule provenance cannot distinguish them.
    copula_contracted: bool,
    // Restored 이 belongs to a copula, never to a fabricated lexical verb.
    copula_only: bool,
    spellings: Vec<SpellingRecovery>,
}
// Capture the local recovery before auxiliary rules are unioned. Retaining a
// reviewed consonant before a vowel requires its regular paradigm; an irregular
// recovery requires that entry's irregular paradigm. Consonant endings do not.
fn record_spelling(p: &mut Predicate, r: &Recovery, vowel_boundary: bool) {
    if p.stem != r.stem {
        return;
    }
    use SpellingClass::*;
    if let Some(class) = r.spelling {
        p.spellings.push(SpellingRecovery {
            morpheme_index: p.morphs.len(),
            class,
        });
    }
    let class = if r.stem.ends_with('르') {
        r.rules.iter().find_map(|rule| match rule.as_str() {
            "deletion.eu" => Some(ReuEuDeletion),
            "irregular.reu" => Some(ReuDoubling),
            "irregular.reo" => Some(ReoAddition),
            "boundary.regular" if vowel_boundary => Some(ReuUncontracted),
            _ => None,
        })
    } else {
        let (regular, irregular, rule) = match coda(&r.stem) {
            Some(27) => (HieutRegular, HieutIrregular, "irregular.hieut"),
            Some(7) => (DigeutRegular, DigeutIrregular, "irregular.digeut"),
            Some(19) => (SiotRegular, SiotIrregular, "irregular.siot"),
            Some(11 | 17) => (BieupRegular, BieupIrregular, "irregular.bieup"),
            _ => return,
        };
        if r.rules.iter().any(|r| r == rule) {
            Some(irregular)
        } else if vowel_boundary || r.rules.iter().any(|r| r == "contraction.noh") {
            Some(regular)
        } else {
            None
        }
    };
    if let Some(class) = class {
        p.spellings.push(SpellingRecovery {
            morpheme_index: p.morphs.len(),
            class,
        });
    }
}

fn shifted_spellings(
    spellings: &[SpellingRecovery],
    offset: usize,
) -> impl Iterator<Item = SpellingRecovery> + '_ {
    spellings.iter().map(move |r| SpellingRecovery {
        morpheme_index: r.morpheme_index + offset,
        class: r.class,
    })
}

// Append a predicate to an existing nominal/copular component sequence.
fn append_predicate_morphs(a: &mut Analysis, p: &Predicate) {
    let extra: Vec<_> = shifted_spellings(&p.spellings, a.morphemes.len()).collect();
    if !extra.is_empty() {
        if a.spelling_paths.is_empty() {
            a.spelling_paths.push(extra);
        } else {
            for path in &mut a.spelling_paths {
                path.extend(extra.iter().cloned());
            }
        }
    }
    a.morphemes.extend(p.morphs.clone());
}

// The polite allomorph depends on the following boundary as well as the stem.
// ㄴ/ㄹ/ㅁ and vowel/mediating-vowel endings take 오; other consonants take 옵.
#[derive(Clone, Copy, Hash, PartialEq, Eq)]
struct PrefinalFollowing {
    polite_open: bool,
    consonant: bool,
}

impl PrefinalFollowing {
    const OPEN: Self = Self {
        polite_open: true,
        consonant: false,
    };
    const CONSONANT: Self = Self {
        polite_open: false,
        consonant: true,
    };
}

fn prefinal_following(suffix: &str, boundary: Boundary) -> PrefinalFollowing {
    // NIKL explicitly attests 옵/사옵 + 나이다/나이까 despite their ㄴ onset.
    // These final combinations' retained ㅂ does not extend to ordinary 니/면.
    if literary_na_ending(suffix) {
        return PrefinalFollowing::CONSONANT;
    }
    let vowel_boundary = matches!(
        boundary,
        Boundary::Aeo | Boundary::EuFull | Boundary::EuZero | Boundary::Attached(_)
    );
    let initial = suffix
        .chars()
        .next()
        .and_then(crate::hangul::split)
        .map(|(initial, _, _)| initial);
    PrefinalFollowing {
        polite_open: vowel_boundary || initial.is_some_and(|i| matches!(i, 2 | 5 | 6 | 11)),
        consonant: !vowel_boundary && initial.is_some_and(|i| i != 11),
    }
}

type PrefinalMemo = HashMap<(String, u8, u8, PrefinalFollowing, bool), Vec<Predicate>>;

pub(crate) fn honorific_prefinal(form: &str) -> bool {
    matches!(form, "시" | "으옵시" | "사옵시" | "자옵시")
}

pub(crate) fn present_exclamation(form: &str) -> bool {
    matches!(form, "는구나" | "는구려" | "는구먼" | "는군" | "는군요")
}
pub(crate) fn copular_exclamation(form: &str) -> bool {
    matches!(form, "로구나" | "로구려" | "로구먼" | "로군")
}
fn added_exclamation(form: &str) -> bool {
    present_exclamation(form)
        || copular_exclamation(form)
        || matches!(form, "구려" | "구먼" | "더구나" | "더구려" | "더구먼")
}

pub(crate) fn quoted_exclamation(form: &str) -> bool {
    matches!(
        form,
        "는다는구나"
            | "는다는군"
            | "는다더군"
            | "는다더군요"
            | "다는구나"
            | "다는군"
            | "다더군"
            | "다더군요"
            | "더라는구나"
            | "더라는군"
    )
}
pub(crate) fn plain_quoted_exclamation(form: &str) -> bool {
    matches!(form, "다는구나" | "다는군" | "다더군" | "다더군요")
}

pub(crate) fn quoted_command_exclamation(form: &str) -> bool {
    matches!(form, "으라는구나" | "으라는군" | "으라더군" | "으라더군요")
}
pub(crate) fn quoted_copular_exclamation(form: &str) -> bool {
    matches!(form, "라는구나" | "라는군" | "라더군" | "라더군요")
}
pub(crate) fn quoted_ra_exclamation(form: &str) -> bool {
    quoted_command_exclamation(form) || quoted_copular_exclamation(form)
}

pub(crate) fn quoted_proposal_exclamation(form: &str) -> bool {
    matches!(form, "자는구나" | "자는군" | "자더군" | "자더군요")
}

pub(crate) fn verbal_quoted_question_exclamation(form: &str) -> bool {
    matches!(form, "느냐는구나" | "느냐는군" | "느냐더군" | "느냐더군요")
}
pub(crate) fn quoted_question_exclamation(form: &str) -> bool {
    verbal_quoted_question_exclamation(form)
        || matches!(
            form,
            "냐는구나"
                | "냐는군"
                | "냐더군"
                | "냐더군요"
                | "으냐는구나"
                | "으냐는군"
                | "으냐더군"
                | "으냐더군요"
        )
}

// Finite source-reviewed question report families share owner/class checks.
// Keep their distinct provenance and follower inventories separate.
pub(crate) fn quoted_conditional_question(form: &str) -> bool {
    matches!(form, "냐면" | "느냐면" | "으냐면")
}
pub(crate) fn verbal_quoted_question(form: &str) -> bool {
    verbal_quoted_question_exclamation(form) || matches!(form, "느냐면" | "느냐던데")
}
pub(crate) fn quoted_question_report(form: &str) -> bool {
    quoted_question_exclamation(form)
        || quoted_conditional_question(form)
        || matches!(form, "냐던데" | "느냐던데" | "으냐던데")
}

// These native report contractions have separate statement, command,
// proposal and question licenses. No implicit reporting 하다 is a lemma.
pub(crate) fn reporting_retrospective(form: &str) -> bool {
    matches!(
        form,
        "다던"
            | "다던데"
            | "는다던"
            | "는다던데"
            | "라던"
            | "라던데"
            | "으라던"
            | "으라던데"
            | "자던"
            | "자던데"
            | "냐던데"
            | "느냐던데"
            | "으냐던데"
    )
}
pub(crate) fn plain_reporting_retrospective(form: &str) -> bool {
    matches!(form, "다던" | "다던데")
}

pub(crate) fn literary_na_ending(form: &str) -> bool {
    // Only these two source-reviewed finals share this attachment class.
    matches!(form, "나이다" | "나이까")
}

fn jaop_stem(stem: &str) -> bool {
    // Modern sources describe a lexical subset, not every ㄷ/ㅈ/ㅊ stem.
    // Do not split historical/unknown compounds or intervene with earlier 시.
    matches!(stem, "듣" | "묻" | "받" | "좇")
}

fn prefinals(
    stem: &str,
    stage: u8,
    pasts: u8,
    following: PrefinalFollowing,
    polite_available: bool,
    memo: &mut PrefinalMemo,
) -> Vec<Predicate> {
    let key = (stem.to_owned(), stage, pasts, following, polite_available);
    if let Some(result) = memo.get(&key) {
        return result.clone();
    }
    let mut out = vec![Predicate {
        stem: stem.into(),
        following: vec![],
        leading_lemmas: vec![],
        morphs: vec![],
        rules: vec![],
        connector: false,
        dap_suffix: false,
        ha_contracted: false,
        copula_contracted: false,
        copula_only: false,
        spellings: Vec::new(),
    }];
    let mut choices: Vec<(Recovery, u8, u8, &str, &str)> = vec![];
    if stage >= 5 {
        for boundary in [Boundary::Literal, Boundary::OmittedCopula(0)] {
            for r in grammar::recover(stem, "더", boundary) {
                choices.push((r, 4, pasts, "더", "prefinal.retrospective"));
            }
        }
    }
    if stage >= 4 && polite_available {
        let variants = if following.polite_open {
            [("으오", Boundary::EuFull), ("오", Boundary::EuZero)]
        } else {
            [("으옵", Boundary::EuFull), ("옵", Boundary::EuZero)]
        };
        for (suffix, boundary) in variants {
            for r in grammar::recover(stem, suffix, boundary) {
                choices.push((r, 3, pasts, "으옵", "prefinal.polite"));
            }
        }
        // Literary 누구오리까 attests omitted 이 before polite 오. Keep
        // nominal recovery separate from predicate irregulars. The outer
        // ending check below limits this recovery to the reviewed question;
        // a general omission license would also invent 여자와 = 여자+이+오+어.
        if following.polite_open {
            for r in grammar::recover(stem, "오", Boundary::OmittedCopula(0)) {
                choices.push((r, 3, pasts, "으옵", "prefinal.polite"));
            }
        }
        // These are distinct modern literary paradigms, not additional
        // allomorphs of 으옵. Their preceding consonant is kept, including ㄹ.
        let suffix = if following.polite_open {
            "사오"
        } else {
            "사옵"
        };
        for r in grammar::recover(stem, suffix, Boundary::ClosedStem) {
            choices.push((r, 3, pasts, "사옵", "prefinal.humble_saop"));
        }
        if following.consonant {
            for r in grammar::recover(stem, "삽", Boundary::ClosedStem) {
                choices.push((r, 3, pasts, "삽", "prefinal.humble_sap"));
            }
        }
    }
    if polite_available {
        // The source lists 받자오시면: ordinary 시 can follow the lexical
        // 자오 form. This finite bare-root recovery also works at stage 0;
        // it does not reopen the productive polite or tense stages.
        let suffix = if following.polite_open {
            "자오"
        } else {
            "자옵"
        };
        for r in grammar::recover(stem, suffix, Boundary::Literal) {
            if jaop_stem(&r.stem) {
                choices.push((r, 0, pasts, "자옵", "prefinal.lexical_jaop"));
            }
        }
        if following.consonant {
            for r in grammar::recover(stem, "잡", Boundary::Literal) {
                if jaop_stem(&r.stem) {
                    choices.push((r, 0, pasts, "잡", "prefinal.lexical_jap"));
                }
            }
        }
        if stage >= 1 {
            for r in grammar::recover(stem, "자옵시", Boundary::Literal) {
                if jaop_stem(&r.stem) {
                    choices.push((r, 0, pasts, "자옵시", "prefinal.lexical_jaopsi"));
                }
            }
        }
    }
    if stage >= 1 && polite_available {
        // NIKL treats these as single honorific bundles. Their notes allow
        // following endings, including tense/modal markers, and explicitly
        // allow preceding 었/겠 on 으옵시/사옵시. This is not the ordinary
        // polite-then-시 order. Consume the polite position even when earlier
        // tense/modal markers are recovered through the bundle.
        for (suffix, boundary, form) in [
            ("으옵시", Boundary::EuFull, "으옵시"),
            ("옵시", Boundary::EuZero, "으옵시"),
            ("사옵시", Boundary::ClosedStem, "사옵시"),
        ] {
            for r in grammar::recover(stem, suffix, boundary) {
                choices.push((r, 3, pasts, form, "prefinal.honorific_polite"));
            }
        }
    }
    if stage >= 3 {
        for boundary in [Boundary::Literal, Boundary::OmittedCopula(0)] {
            for r in grammar::recover(stem, "겠", boundary) {
                choices.push((r, 2, pasts, "겠", "prefinal.modal"));
            }
        }
        // KRDict treats -아/어/여야겠- as one expression. Keep it as a
        // prefinal-position bundle, without inventing an omitted 하다 lemma.
        // Its 아/어 boundary uses the same inflection and earlier tense/
        // honorific recovery as other vowel-initial forms. Modal/retrospective
        // markers cannot precede it through this path; 더 may follow it.
        for r in grammar::recover(stem, "야겠", Boundary::Aeo) {
            choices.push((r, 2, pasts, "어야겠", "prefinal.obligation"));
        }
    }
    if stage >= 2
        && pasts < 2
        && let Some((_, v, 20)) = last(stem)
    {
        for r in grammar::aeo(&replace_last(stem, v, 0).unwrap()) {
            choices.push((r, 2, pasts + 1, "었", "prefinal.past"));
        }
    }
    if stage >= 1 {
        for (suffix, boundary) in [("으시", Boundary::EuFull), ("시", Boundary::EuZero)] {
            for r in grammar::recover(stem, suffix, boundary) {
                choices.push((r, 0, pasts, "시", "prefinal.honorific"));
            }
        }
        // Honorific 시 can follow an omitted copula after a vowel-final
        // nominal. Recover at this boundary, before the normal tense stack;
        // predicate irregulars must not alter the nominal itself.
        for r in grammar::recover(stem, "시", Boundary::OmittedCopula(0)) {
            choices.push((r, 0, pasts, "시", "prefinal.honorific"));
        }
    }
    for (r, next, count, form, rule) in choices {
        let bundle = matches!(form, "으옵시" | "사옵시");
        let available = polite_available
            && !matches!(
                form,
                "으옵" | "사옵" | "삽" | "으옵시" | "사옵시" | "자옵" | "잡" | "자옵시"
            );
        // Ordinary (으)시 has a vowel/mediating-vowel boundary. The finite
        // 자옵 family permits following 시 and therefore needs this context
        // even at stage 0; consonant-only 잡 must not borrow that allomorph.
        let following = if matches!(form, "시" | "었" | "어야겠") {
            PrefinalFollowing::OPEN
        } else {
            PrefinalFollowing::CONSONANT
        };
        for mut p in prefinals(&r.stem, next, count, following, available, memo) {
            // These entries list bare stems or immediate past/modal markers,
            // not a direct earlier 시. Keep unknown lexical stems separate.
            if bundle
                && p.morphs
                    .last()
                    .is_some_and(|m| !matches!(m.form.as_str(), "었" | "겠" | "어야겠"))
            {
                continue;
            }
            if r.rules.iter().any(|r| r == "copula.omitted_ending") {
                p.copula_only = true;
                p.rules.push(
                    if form == "시" {
                        "copula.omitted_honorific"
                    } else if form == "으옵" {
                        "copula.omitted_polite"
                    } else {
                        "copula.omitted_prefinal"
                    }
                    .into(),
                );
            }
            p.copula_contracted |=
                r.stem.ends_with('이') && r.rules.iter().any(|r| r == "contraction.vowel");
            record_spelling(
                &mut p,
                &r,
                matches!(form, "시" | "었" | "어야겠" | "으옵" | "으옵시"),
            );
            p.morphs.push(morph(form, MorphemeKind::Prefinal));
            p.rules.extend(r.rules.clone());
            p.rules.push(rule.into());
            out.push(p);
        }
    }
    memo.insert(key, out.clone());
    out
}

// Canonical present-declarative forms share verb attachment and only permit
// honorific 시 before the ending. Past/modal reports use the plain 다 family.
pub(crate) fn present_declarative(form: &str) -> bool {
    matches!(
        form,
        "는다"
            | "는다고"
            | "는다는"
            | "는다면"
            | "는답니다"
            | "는다거나"
            | "는다든가"
            | "는다네"
            | "는다는데"
            | "는다던"
            | "는다더니"
            | "는다나"
            | "는다더니만"
            | "는다더니마는"
            | "는다던데"
            | "는다며"
            | "는다면서"
            | "는다니"
            | "는단"
            | "는단다"
            | "는대"
            | "는다지"
            | "는다죠"
            | "는다지만"
            | "는다니까"
            | "는다느니"
            | "는다는구나"
            | "는다는군"
            | "는다더군"
            | "는다더군요"
    )
}

// These are the adjectival 으냐 forms, distinct from general 냐 and verbal
// 느냐. Their source notes license a bare adjective, not recovered prefinals.
pub(crate) fn adjectival_question(form: &str) -> bool {
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

// Reviewed intention connectives share verb attachment and honorific 시 only.
// Other 려 families have different source licenses; do not match by prefix.
fn intention_connective(form: &str) -> bool {
    matches!(
        form,
        "으려거든"
            | "으려기에"
            | "으려는데"
            | "으려다"
            | "으려다가"
            | "으려더니"
            | "으려도"
            | "으려야"
    )
}

pub(crate) fn verbal_intention(form: &str) -> bool {
    intention_connective(form) || matches!(form, "으려는" | "으려는가" | "으려는지")
}

fn ryeo_expression(form: &str) -> bool {
    matches!(
        form,
        "으려니" | "으려니까" | "으려더라" | "으려던" | "으려면서" | "으려든지"
    )
}

pub(crate) fn activity_reason(form: &str) -> bool {
    matches!(form, "느라" | "느라고")
}

pub(crate) fn quoted_neuni_ending(form: &str) -> bool {
    matches!(
        form,
        "다느니"
            | "는다느니"
            | "라느니"
            | "으라느니"
            | "자느니"
            | "냐느니"
            | "느냐느니"
            | "으냐느니"
            | "더라느니"
    )
}

pub(crate) fn neuni_verbal_ending(form: &str) -> bool {
    matches!(
        form,
        "느니" | "느니만" | "느니만큼" | "느니보다" | "느니보다는"
    )
}

pub(crate) fn result_connective(form: &str) -> bool {
    matches!(form, "어다" | "어다가")
}

fn predicates(word: &str) -> Vec<Predicate> {
    let mut out = single_predicates(word);
    out.extend(nominal_mal_predicates(word));
    out
}

fn single_predicates(word: &str) -> Vec<Predicate> {
    let mut out = vec![];
    let mut memo = HashMap::new();
    // Article 18: prohibitive 말다 has the optional short imperatives 마/마라/마요.
    // This is a whole-stem exception, not productive ㄹ loss before every vowel.
    let short_mal = match word {
        "마" => Some("어"),
        "마라" => Some("어라"),
        "마요" => Some("어요"),
        _ => None,
    };
    if let Some(form) = short_mal {
        let mut p = prefinals("말", 0, 0, PrefinalFollowing::CONSONANT, true, &mut memo).remove(0);
        p.morphs.push(morph(form, MorphemeKind::Ending));
        p.rules.extend(["ending".into(), "irregular.mal".into()]);
        out.push(p);
    }
    for ending in grammar::matching_endings(word) {
        for r in grammar::recover(word, ending.suffix, ending.boundary) {
            for mut p in prefinals(
                &r.stem,
                5,
                0,
                prefinal_following(ending.suffix, ending.boundary),
                true,
                &mut memo,
            ) {
                // -너라's lexical owner itself must end in 오. Do not borrow
                // a polite prefinal 오 from another stem to satisfy that note.
                if ending.form == "너라" && !p.stem.ends_with('오') {
                    continue;
                }
                // KRDict 73877 lists direct 오다/오다-final stems. Other
                // prefinals need separate evidence; do not reuse adnominal 은.
                if ending.form == "ㄴ" && (!p.stem.ends_with('오') || !p.morphs.is_empty()) {
                    continue;
                }
                p.copula_only |= matches!(ending.boundary, Boundary::OmittedCopula(_));
                if p.rules.iter().any(|r| r == "copula.omitted_polite")
                    && (ending.form != "으리까"
                        || p.morphs.len() != 1
                        || p.morphs[0].form != "으옵")
                {
                    continue;
                }
                // NIKL 112447/416361 license honorific/past/modal and attested
                // polite families, but does not list retrospective 더.
                if literary_na_ending(ending.form) && p.morphs.iter().any(|m| m.form == "더") {
                    continue;
                }
                // NIKL 리까/으리까 list bare predicates/copula, honorific,
                // past and polite 오. 사오리까 independently licenses the
                // humble combination, including earlier 겠. Do not borrow
                // that license for an immediately preceding bare modal.
                if ending.form == "으리까"
                    && (p.morphs.iter().any(|m| m.form == "더")
                        || p.morphs.last().is_some_and(|m| {
                            !honorific_prefinal(&m.form)
                                && !matches!(m.form.as_str(), "었" | "으옵" | "사옵" | "자옵")
                        }))
                {
                    continue;
                }
                if ending.form == "요" {
                    // This connective attaches to bare 이다/아니다 only.
                    // A lexical stem ending in 이 is not sufficient evidence.
                    if !p.morphs.is_empty() {
                        continue;
                    }
                    p.copula_only = p.stem != "아니";
                }
                p.copula_contracted |=
                    r.stem.ends_with('이') && r.rules.iter().any(|r| r == "contraction.vowel");
                if ending.form == "으되" {
                    let extended = p
                        .morphs
                        .last()
                        .is_some_and(|m| matches!(m.form.as_str(), "었" | "겠" | "어야겠"))
                        || (p.morphs.is_empty()
                            && (p.stem.ends_with("있") || p.stem.ends_with("없")));
                    if (ending.suffix == "으되" && !extended)
                        || (ending.suffix == "되"
                            && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    {
                        continue;
                    }
                }
                // KRDict 87110–87113 list distinct local prefinal licenses:
                // 은바 takes honorific 시; 는바/던바 also take past/modal.
                // Do not borrow the retrospective bundle's license for 더.
                if matches!(ending.form, "은바" | "는바" | "던바")
                    && p.morphs.iter().any(|m| {
                        m.form != "시"
                            && (ending.form == "은바" || !matches!(m.form.as_str(), "었" | "겠"))
                    })
                {
                    continue;
                }
                // Retrospective 더 has its own following-ending licenses.
                // These source-reviewed families do not take it, including
                // bundles that already contain a retrospective component.
                // Check the recovered marker, not a lexical stem ending in 더.
                if p.morphs.iter().any(|m| m.form == "더")
                    && matches!(
                        ending.form,
                        "다" | "다고"
                            | "다는"
                            | "다니"
                            | "다면"
                            | "어"
                            | "어요"
                            | "지"
                            | "지요"
                            | "죠"
                            | "습니다"
                            | "습니까"
                            | "네"
                            | "네요"
                            | "나요"
                            | "고"
                            | "고요"
                            | "지만"
                            | "지마는"
                            | "지만요"
                            | "거든"
                            | "거든요"
                            | "거나"
                            | "건"
                            | "더라"
                            | "더라고"
                            | "더라는"
                            | "더니"
                            | "더라도"
                            | "더군"
                            | "더군요"
                            | "던"
                            | "던데"
                            | "던데요"
                            | "나"
                            | "으나"
                            | "기"
                            | "기로"
                            | "기가"
                            | "기는"
                            | "기도"
                            | "기만"
                            | "기를"
                            | "기보다"
                            | "음"
                            | "게"
                            | "게요"
                            | "도록"
                            | "듯"
                            | "듯이"
                            | "으면"
                            | "으며"
                            | "으면서"
                            | "으므로"
                            | "어서"
                            | "어서야"
                            | "어도"
                            | "어야"
                            | "어야지"
                            | "어야죠"
                            | "어다"
                            | "어다가"
                            | "어서는"
                            | "어서도"
                            | "고자"
                            | "건대"
                            | "소"
                            | "오"
                            | "는"
                            | "는데"
                            | "는데요"
                            | "는데도"
                            | "는데다가"
                            | "는가"
                            | "는가요"
                            | "는지"
                            | "을"
                            | "을까"
                            | "을까요"
                            | "을게"
                            | "을게요"
                            | "을래"
                            | "을래요"
                            | "을지"
                            | "을수록"
                            | "던가"
                            | "던지"
                            | "더라네"
                            | "더라는데"
                    )
                {
                    continue;
                }
                // Native retrospective reports: commands permit honorifics,
                // proposals are bare, plain statements permit 시/었/겠.
                // Apply this only to the immediate predicate's own markers.
                // Native 82004 assigns 아니다 to the factual 라더니 sense,
                // while 89662 requires a verb for canonical command 으라더니.
                // KRDict 74698 lists honorific, past and modal markers.
                // Present forms use the shared honorific-only restriction.
                if ending.form == "다나"
                    && p.morphs.iter().any(|m| {
                        !honorific_prefinal(&m.form)
                            && !matches!(m.form.as_str(), "었" | "겠" | "어야겠")
                    })
                {
                    continue;
                }
                if ending.form == "으라더니" && p.stem == "아니" {
                    continue;
                }
                if (matches!(ending.form, "으라던" | "으라던데" | "으라더니")
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (matches!(ending.form, "자던" | "자던데") && !p.morphs.is_empty())
                    || (plain_reporting_retrospective(ending.form)
                        && p.morphs.iter().any(|m| {
                            !honorific_prefinal(&m.form)
                                && !matches!(m.form.as_str(), "었" | "겠" | "어야겠")
                        }))
                    || (matches!(ending.form, "라던" | "라더니")
                        && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                {
                    continue;
                }
                // Quoted -며/-면서 families have separate prefinal licenses.
                if (matches!(ending.form, "으라며" | "으라면서")
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (matches!(ending.form, "자며" | "자면서") && !p.morphs.is_empty())
                    || (matches!(
                        ending.form,
                        "다며" | "다면서" | "더라며" | "더라면서" | "느냐며" | "느냐면서"
                    ) && p.morphs.iter().any(|m| m.form == "더"))
                {
                    continue;
                }
                // Surprise/quoted -니 homonyms differ from plain-다 reports:
                // bare verbs also take 다니. Commands permit 시, proposals and
                // adjectival 으냐니 are bare, and 느냐니/더라니 exclude 더.
                // Generic 냐니 + 더 remains outside this reviewed restriction.
                if (ending.form == "으라니"
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (ending.form == "자니" && !p.morphs.is_empty())
                    || (matches!(ending.form, "느냐니" | "더라니")
                        && p.morphs.iter().any(|m| m.form == "더"))
                {
                    continue;
                }
                // Quoted listings retain distinct source licenses. Commands
                // allow honorifics, proposals are bare, and the statement/
                // verbal-question/retrospective bundles do not repeat 더.
                // General 냐느니 keeps unreviewed markers as hypotheses.
                if (ending.form == "으라느니"
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (ending.form == "자느니" && !p.morphs.is_empty())
                    || (matches!(ending.form, "다느니" | "느냐느니" | "더라느니")
                        && p.morphs.iter().any(|m| m.form == "더"))
                {
                    continue;
                }
                // KRDict 81040/81045, 81050, 81056 and 76460/76475 keep
                // different slots. The bare 은걸 bundle permits honorification;
                // 는걸/던걸 additionally permit past/modal, while 을걸 permits
                // past but not a second modal or retrospective marker.
                if (ending.form == "은걸" && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (matches!(ending.form, "는걸" | "던걸")
                        && p.morphs.iter().any(|m| {
                            !honorific_prefinal(&m.form)
                                && !matches!(m.form.as_str(), "었" | "겠" | "어야겠")
                        }))
                    || (ending.form == "을걸"
                        && p.morphs
                            .iter()
                            .any(|m| !honorific_prefinal(&m.form) && m.form != "었"))
                {
                    continue;
                }
                if (present_exclamation(ending.form) || copular_exclamation(ending.form))
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form))
                {
                    continue;
                }
                if matches!(
                    ending.form,
                    "구려" | "구먼" | "더구나" | "더구려" | "더구먼"
                ) && p.morphs.iter().any(|m| {
                    !honorific_prefinal(&m.form)
                        && !matches!(m.form.as_str(), "었" | "겠" | "어야겠")
                }) {
                    continue;
                }
                if quoted_exclamation(ending.form)
                    && !present_declarative(ending.form)
                    && p.morphs.iter().any(|m| {
                        !honorific_prefinal(&m.form)
                            && !matches!(m.form.as_str(), "었" | "겠" | "어야겠")
                    })
                {
                    continue;
                }
                // KRDict's contractions preserve the embedded proposal owner.
                // NIKL 308936 excludes 시 + 자; its grammar report (pp. 355–356)
                // excludes past/modal + 자. Unsettled prefinals stay hypotheses.
                if quoted_proposal_exclamation(ending.form)
                    && p.morphs
                        .iter()
                        .any(|m| matches!(m.form.as_str(), "시" | "었" | "겠" | "어야겠"))
                {
                    continue;
                }
                if quoted_command_exclamation(ending.form)
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form))
                {
                    continue;
                }
                if quoted_question_report(ending.form)
                    && p.morphs.iter().any(|m| {
                        !honorific_prefinal(&m.form)
                            && !matches!(m.form.as_str(), "었" | "겠" | "어야겠")
                    })
                {
                    continue;
                }
                // Bare 로 forms list 이다/아니다. A listed honorific starts
                // a different local boundary; unknown lexical homonyms survive.
                if copular_exclamation(ending.form)
                    && p.morphs.is_empty()
                    && !p.stem.ends_with('이')
                    && p.stem != "아니"
                {
                    continue;
                }
                // Short quotation and change/conditional homonyms keep their
                // own licenses. Plain 단 also abbreviates 다가는, so it admits
                // bare verbs, including represented auxiliaries.
                if (matches!(ending.form, "단" | "다간" | "다가는" | "느냔")
                    && p.morphs.iter().any(|m| m.form == "더"))
                    || (ending.form == "잔" && !p.morphs.is_empty())
                {
                    continue;
                }
                // KRDict reports/confirmations: commands allow 시, proposals
                // are bare, and statement/question/experience bundles reject 더.
                if (matches!(ending.form, "다지만" | "냐지만" | "느냐지만" | "더라지만")
                    && p.morphs.iter().any(|m| m.form == "더"))
                    || (ending.form == "자지만" && !p.morphs.is_empty())
                {
                    continue;
                }
                if (matches!(ending.form, "다니까" | "냐니까" | "느냐니까" | "더라니까")
                    && p.morphs.iter().any(|m| m.form == "더"))
                    || (ending.form == "자니까" && !p.morphs.is_empty())
                {
                    continue;
                }
                // KRDict 80327/80328 and NIKL 2014 grammar research:
                // verbs and honorific 시, without tense/modal/retrospective markers.
                if activity_reason(ending.form)
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form))
                {
                    continue;
                }
                // Short reports inherit the source's 시/었/겠 slots, not
                // retrospective 더. Proposals remain bare; adjectival 으냬
                // uses the shared bare-adjective question restriction below.
                if (matches!(ending.form, "대" | "냬" | "느냬" | "더래")
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었" | "겠" | "어야겠"
                        )
                    }))
                    || (ending.form == "재" && !p.morphs.is_empty())
                {
                    continue;
                }
                if (ending.form == "잔다" && !p.morphs.is_empty())
                    || (matches!(
                        ending.form,
                        "단다" | "다지" | "다죠" | "냔다" | "느냔다" | "더란다"
                    ) && p.morphs.iter().any(|m| m.form == "더"))
                {
                    continue;
                }
                if ending.form == "느냐고" && p.morphs.iter().any(|m| m.form == "더") {
                    continue;
                }
                // COV-017bu: each canonical 으냐-family entry takes a
                // non-ㄹ closed underlying stem (e.g. KRDict 76235, 79258,
                // 87444, 80180, 86361). Check the recovered stem: EuZero
                // still licenses 추우냐 -> 춥다 and 어떠냐 -> 어떻다.
                if adjectival_question(ending.form)
                    && crate::hangul::coda(&p.stem).is_some_and(|t| matches!(t, 0 | 8))
                {
                    continue;
                }
                if adjectival_question(ending.form) && !p.morphs.is_empty() {
                    continue;
                }
                // Literary assertion forms have separate source licenses:
                // -(으)니라 permits 시; -느니라 also permits past/modal forms.
                // Their lexical adjective/verb classes remain hypotheses.
                if (ending.form == "으니라"
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (ending.form == "느니라"
                        && p.morphs.iter().any(|m| {
                            !matches!(
                                m.form.as_str(),
                                "으옵시" | "사옵시" | "자옵시" | "시" | "었" | "겠" | "어야겠"
                            )
                        }))
                {
                    continue;
                }
                // Present reported forms permit honorific 시 but no other
                // prefinals; past/modal use their plain 다- counterparts.
                if present_declarative(ending.form)
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form))
                {
                    continue;
                }
                // Informative/reported -답니다 permits honorific, past and
                // modal markers; retrospective 더 instead takes -랍니다.
                if matches!(
                    ending.form,
                    "답니다" | "다거나" | "다든가" | "다네" | "다는데"
                ) && p.morphs.iter().any(|m| m.form == "더")
                {
                    continue;
                }
                // Source-listed causal endings: 기에 licenses honorific,
                // past and modal markers; 길래 licenses honorific and past.
                // Keep 기 + 에 nominalization as a separate existing path.
                if (ending.form == "기에"
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었" | "겠" | "어야겠"
                        )
                    }))
                    || (ending.form == "길래"
                        && p.morphs.iter().any(|m| {
                            !matches!(
                                m.form.as_str(),
                                "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                            )
                        }))
                {
                    continue;
                }
                // Reviewed intention/concession families have different
                // prefinal licenses; do not inherit every terminal marker.
                if (matches!(ending.form, "으리라고" | "으리다" | "으나마")
                    && p.morphs.iter().any(|m| m.form == "더"))
                    || (ending.form == "을지라도"
                        && p.morphs.iter().any(|m| {
                            !matches!(
                                m.form.as_str(),
                                "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                            )
                        }))
                    || (ending.form == "자면"
                        && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                {
                    continue;
                }
                // KRDict -다가 licenses honorific and past markers. Keep
                // the existing vowel-boundary -어다가 path independent.
                if ending.form == "다가"
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                        )
                    })
                {
                    continue;
                }
                // KRDict 86489/86616 list verb stems and honorific 시,
                // not a recovered past/modal/retrospective stack.
                if ending.form == "을라치면"
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form))
                {
                    continue;
                }
                // KRDict 85762/85772 permit predicates/copulas, honorific
                // 시 and past 었; this final ending is not particle 밖에.
                if ending.form == "을밖에"
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                        )
                    })
                {
                    continue;
                }
                // The reviewed concessive paradigms differ: -(으)ㄴ들 lists
                // bare stems and honorific 시; 망정/지언정 additionally list 었.
                // A retrospective -던들 needs its own ending analysis.
                if (ending.form == "은들" && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (matches!(ending.form, "을망정" | "을지언정")
                        && p.morphs.iter().any(|m| {
                            !matches!(
                                m.form.as_str(),
                                "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                            )
                        }))
                {
                    continue;
                }
                if ending.form == "던들"
                    && (!p.morphs.last().is_some_and(|m| m.form == "었")
                        || p.morphs.iter().any(|m| {
                            !matches!(
                                m.form.as_str(),
                                "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                            )
                        }))
                {
                    continue;
                }
                // Result-transfer 어다(가) has a bare verb boundary, unlike
                // literal 다가. Lexical 모시다 keeps its stem-internal 시.
                if result_connective(ending.form) && !p.morphs.is_empty() {
                    continue;
                }
                // Literal 고서 permits honorific 시, not a recovered tense/
                // modal stack. Its 아니다 conditional use remains lexical.
                if ending.form == "고서" && p.morphs.iter().any(|m| !honorific_prefinal(&m.form))
                {
                    continue;
                }
                // Retrospective 더 precedes 냐는, not 느냐는. Adjectival
                // question prefinals are checked by the shared family above.
                if (ending.form == "느냐는" && p.morphs.iter().any(|m| m.form == "더"))
                    || (matches!(ending.form, "잖아" | "잖아요")
                        && p.morphs.iter().any(|m| m.form == "더"))
                {
                    continue;
                }
                // Reviewed shortened adnominals: intention permits honorific
                // 시; proposal quotation is currently scoped to bare stems.
                if (verbal_intention(ending.form)
                    && p.morphs.iter().any(|m| !honorific_prefinal(&m.form)))
                    || (matches!(ending.form, "자는" | "자거나") && !p.morphs.is_empty())
                {
                    continue;
                }
                if ending.form == "을는지"
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                        )
                    })
                {
                    continue;
                }
                // KRDict 79416/79417 license honorific/past; the separate
                // polite expression 86747 also lists 겠. Keep 요 bundled so
                // that its broader license cannot leak to the bare ending.
                if matches!(ending.form, "을라고" | "을라고요")
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                        ) && !(ending.form == "을라고요"
                            && matches!(m.form.as_str(), "겠" | "어야겠"))
                    })
                {
                    continue;
                }
                // These shortened expressions have broader notes than the
                // verb-only intention family. KRDict 86601 also licenses past/
                // modal on the assumption homonym of 으려니. Only 으려니까
                // lacks those licenses (86696/86726); all retain honorific 시.
                if ryeo_expression(ending.form)
                    && p.morphs.iter().any(|m| {
                        !honorific_prefinal(&m.form)
                            && (ending.form == "으려니까"
                                || !matches!(m.form.as_str(), "었" | "겠" | "어야겠"))
                    })
                {
                    continue;
                }
                // The question homonym of -(으)려나 allows adjectives and
                // copulas as well as verbs, with 시/었/겠. It is distinct
                // from the narrower shortened intention expression.
                if ending.form == "으려나"
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었" | "겠" | "어야겠"
                        )
                    })
                {
                    continue;
                }
                // Commands/quoted commands and formal request/proposal
                // endings do not inherit past, modal or retrospective slots.
                // Keep honorific and unknown lexical-stem alternatives.
                if matches!(
                    ending.form,
                    "으라"
                        | "으라고"
                        | "으라는"
                        | "으라면"
                        | "으란"
                        | "으래"
                        | "으랍니다"
                        | "으란다"
                        | "으라지"
                        | "으라죠"
                        | "으라지만"
                        | "으라니까"
                        | "으라네"
                        | "으라는데"
                        | "으라거나"
                        | "으세요"
                        | "으십시오"
                        | "으소서"
                        | "으옵소서"
                        | "읍시다"
                ) && p.morphs.iter().any(|m| !honorific_prefinal(&m.form))
                {
                    continue;
                }
                // -어라 has both command and exclamation senses. Only the
                // reviewed retrospective boundary is excluded here; do not
                // infer all of its mood restrictions from the command sense.
                if ending.form == "어라" && p.morphs.iter().any(|m| m.form == "더") {
                    continue;
                }
                // The wider 라는데 family includes retrospective 더라는데
                // (KRDict 86356); 라는데요 (82264) also lists conjectural 으리.
                // Preserve their split components despite the shorter entry's
                // narrower attachment note, as with bundled 더라네 below.
                let factual_ra = matches!(ending.boundary, Boundary::Literal)
                    && (quoted_copular_exclamation(ending.form)
                        || matches!(
                            ending.form,
                            "라" | "라도"
                                | "라야"
                                | "라야만"
                                | "라서"
                                | "라고"
                                | "라는"
                                | "라면"
                                | "랍니다"
                                | "란다"
                                | "래"
                                | "라지"
                                | "라죠"
                                | "라지만"
                                | "라니까"
                                | "라든가"
                                | "라네"
                                | "라는데"
                                | "라더니"
                                | "라던"
                                | "라던데"
                                | "라며"
                                | "라면서"
                                | "라니"
                                | "라느니"
                        ));
                if factual_ra
                    && !p.morphs.last().is_some_and(|m| {
                        honorific_prefinal(&m.form)
                            || (m.form == "더"
                                && !matches!(
                                    ending.form,
                                    "라는" | "라야" | "라야만" | "라던" | "라더니"
                                ))
                    })
                {
                    continue;
                }
                if ending.form == "란" {
                    let copular = (p.stem.ends_with('이') || p.stem == "아니")
                        && p.morphs.iter().all(|m| honorific_prefinal(&m.form));
                    // KRDict 86297 also licenses honorific 시, as does the
                    // full factual 라는 form. Keep this distinct from 으란.
                    let licensed_prefinal = p.morphs.last().is_some_and(|m| {
                        matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "더"
                        )
                    });
                    if !copular && !licensed_prefinal {
                        continue;
                    }
                }
                // KRDict 82342 lists bare predicates, honorific 시 and past 었.
                if ending.form == "든가"
                    && p.morphs.iter().any(|m| {
                        !matches!(
                            m.form.as_str(),
                            "으옵시" | "사옵시" | "자옵시" | "시" | "었"
                        )
                    })
                {
                    continue;
                }
                let vowel_boundary = matches!(ending.boundary, Boundary::Aeo | Boundary::EuFull)
                    || (matches!(ending.boundary, Boundary::Consonant)
                        && ending.suffix.starts_with(['은', '을', '음', '으']));
                record_spelling(&mut p, &r, vowel_boundary);
                p.morphs.push(morph(ending.form, MorphemeKind::Ending));
                p.rules.extend(r.rules.clone());
                p.rules.push("ending".into());
                if ending.form == "ㄴ" {
                    p.rules.push("ending.friendly_command.n".into());
                }
                if matches!(ending.form, "거라" | "너라") {
                    p.rules.push("ending.direct_command".into());
                }
                if ending.form == "으리다" {
                    p.rules.push("ending.literary_ri".into());
                }
                if quoted_exclamation(ending.form) {
                    p.rules.push("ending.quoted_exclamation".into());
                }
                if quoted_ra_exclamation(ending.form) {
                    p.rules.push("ending.quoted_ra_exclamation".into());
                }
                if quoted_proposal_exclamation(ending.form) {
                    p.rules.push("ending.quoted_proposal_exclamation".into());
                }
                if quoted_conditional_question(ending.form) {
                    p.rules.push("ending.quoted_conditional_question".into());
                }
                if quoted_question_exclamation(ending.form) {
                    p.rules.push("ending.quoted_question_exclamation".into());
                }
                if added_exclamation(ending.form)
                    || (matches!(ending.form, "구나" | "군" | "군요")
                        && matches!(ending.boundary, Boundary::OmittedCopula(_)))
                {
                    p.rules.push("ending.exclamation".into());
                }
                if ending.suffix.ends_with("구만") {
                    p.rules.push("ending.exclamation_variant".into());
                }
                if matches!(ending.form, "은걸" | "는걸" | "던걸" | "을걸") {
                    p.rules.push("ending.geol".into());
                }
                if quoted_neuni_ending(ending.form) {
                    p.rules.push("ending.quoted_neuni".into());
                }
                if neuni_verbal_ending(ending.form) || matches!(ending.form, "니만" | "으니만큼")
                {
                    p.rules.push("ending.neuni".into());
                }
                if matches!(ending.form, "은바" | "는바" | "던바") {
                    p.rules.push("ending.background_ba".into());
                }
                if ending.form == "음세" {
                    p.rules.push("ending.volitional_promise".into());
                }
                if matches!(ending.form, "으련만" | "으련마는") {
                    p.rules.push("ending.counterfactual_ryeon".into());
                }
                if matches!(ending.form, "라더니" | "으라더니") {
                    p.rules.push("ending.reported_command_deoni".into());
                }
                if matches!(ending.form, "다나" | "는다나") {
                    p.rules.push("ending.reported_dana".into());
                }
                if matches!(ending.form, "다더니" | "는다더니") {
                    p.rules.push("ending.reported_deoni".into());
                }
                if matches!(
                    ending.form,
                    "더니만"
                        | "더니마는"
                        | "다더니만"
                        | "다더니마는"
                        | "는다더니만"
                        | "는다더니마는"
                ) {
                    p.rules.push("ending.deoniman".into());
                }
                if ending.form == "으리만큼" {
                    p.rules.push("ending.degree_rimankeum".into());
                }
                if ending.form == "으리까" {
                    p.rules.push("ending.literary_question_ri".into());
                }
                if ending.form == "으랴" {
                    p.rules.push("ending.rya".into());
                    if matches!(ending.boundary, Boundary::OmittedCopula(_)) {
                        p.rules.push("copula.omitted_rya".into());
                    }
                }
                if ending.form == "을라" {
                    p.rules.push("ending.caution".into());
                }
                if ending.form == "으되" {
                    p.rules.push("ending.contrast_doe".into());
                }
                if ending.form == "요" {
                    p.rules.push("ending.enumerative_yo".into());
                }
                if matches!(ending.form, "기에" | "길래") {
                    p.rules.push("ending.causal".into());
                }
                if ending.form == "든가" {
                    p.rules.push("ending.choice".into());
                }
                if matches!(
                    ending.form,
                    "다거나"
                        | "는다거나"
                        | "라거나"
                        | "으라거나"
                        | "자거나"
                        | "다든가"
                        | "는다든가"
                        | "라든가"
                ) {
                    p.rules.push("ending.quoted_alternative".into());
                }
                if matches!(
                    ending.form,
                    "단다"
                        | "는단다"
                        | "란다"
                        | "으란다"
                        | "잔다"
                        | "냔다"
                        | "느냔다"
                        | "으냔다"
                        | "더란다"
                ) {
                    p.rules.push("ending.reporting_familiar".into());
                }
                if matches!(
                    ending.form,
                    "다지" | "는다지" | "라지" | "으라지" | "다죠" | "는다죠" | "라죠" | "으라죠"
                ) {
                    p.rules.push("ending.reporting_confirmation".into());
                }
                if matches!(
                    ending.form,
                    "다지만"
                        | "는다지만"
                        | "라지만"
                        | "으라지만"
                        | "냐지만"
                        | "느냐지만"
                        | "으냐지만"
                        | "자지만"
                        | "더라지만"
                ) {
                    p.rules.push("ending.reporting_contrast".into());
                }
                if ryeo_expression(ending.form) {
                    p.rules.push("ending.ryeo_expression".into());
                }
                if activity_reason(ending.form) {
                    p.rules.push("ending.activity_reason".into());
                }
                if matches!(ending.form, "을라고" | "을라고요") {
                    p.rules.push("ending.rhetorical_llago".into());
                }
                if short_report(ending.form) {
                    p.rules.push("ending.reporting_short".into());
                }
                if reporting_nikka(ending.form) {
                    p.rules.push("ending.reporting_reason".into());
                }
                if matches!(ending.form, "답니다" | "는답니다" | "랍니다" | "으랍니다")
                {
                    p.rules.push("ending.reporting_polite".into());
                }
                if reporting_retrospective(ending.form) {
                    p.rules.push("ending.reporting_retrospective".into());
                }
                if matches!(
                    ending.form,
                    "다네"
                        | "는다네"
                        | "라네"
                        | "으라네"
                        | "다는데"
                        | "는다는데"
                        | "라는데"
                        | "으라는데"
                        | "더라네"
                        | "더라는데"
                ) {
                    p.rules.push("ending.reporting_ne".into());
                }
                if matches!(
                    ending.form,
                    "단" | "는단" | "다간" | "다가는" | "잔" | "냔" | "느냔" | "으냔"
                ) {
                    p.rules.push("ending.short_clause".into());
                }
                if reporting_ni(ending.form) {
                    p.rules.push("ending.reporting_ni".into());
                }
                if reporting_myeo(ending.form) {
                    p.rules.push("ending.reporting_myeo".into());
                }
                if matches!(ending.form, "을는지" | "으려는가" | "으려는지") {
                    p.rules.push("ending.uncertainty".into());
                }
                if intention_connective(ending.form) {
                    p.rules.push("ending.intention_connective".into());
                }
                if result_connective(ending.form) {
                    p.rules.push("ending.result_connective".into());
                }
                if ending.form == "으려나" {
                    p.rules.push("ending.expectation_question".into());
                }
                if matches!(ending.form, "은감" | "는감" | "던감") {
                    p.rules.push("ending.refuting_question".into());
                }
                if ending.form == "게끔" {
                    p.rules.push("ending.emphatic_purpose".into());
                }
                if matches!(ending.form, "고말고" | "다마다") {
                    p.rules.push("ending.emphatic_affirmation".into());
                }
                if matches!(ending.form, "으니라" | "느니라") {
                    p.rules.push("ending.literary_assertion".into());
                }
                if ending.form == "을밖에" {
                    p.rules.push("ending.necessity".into());
                }
                if ending.form == "을라치면" {
                    p.rules.push("ending.habitual_condition".into());
                }
                if matches!(ending.form, "은들" | "을망정" | "을지언정" | "던들") {
                    p.rules.push("ending.concessive".into());
                }
                if matches!(ending.form, "건만" | "건마는") {
                    p.rules.push("ending.expectation_contrast".into());
                }
                if factual_ra {
                    p.rules.push("ending.factual_ra".into());
                }
                if matches!(ending.form, "잖아" | "잖아요") {
                    p.rules.push("ending.confirmation".into());
                }
                if matches!(
                    ending.form,
                    "으려는" | "자는" | "냐는" | "느냐는" | "으냐는" | "더라는" | "란" | "으란"
                ) {
                    p.rules.push("ending.adnominal_expression".into());
                }
                p.connector = ending.connector;
                p.dap_suffix = dap_suffix_allowed(&p);
                p.ha_contracted = matches!(
                    ending.boundary,
                    Boundary::HaDeletion | Boundary::HaAspiration
                );
                out.push(p);
            }
        }
    }
    // Conjectural (으)리 precedes this source-listed factual family only.
    // Preserve existing bundled -(으)리라 / -(으)리라고 alternatives.
    for ending in [
        "란",
        "라",
        "라도",
        "라서",
        "라고",
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
        // Native 26318/55367 attest conjectural -리라던 despite
        // the shorter grammar entry's narrower attachment note.
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
    ] {
        if let Some(base) = word.strip_suffix(ending) {
            for (suffix, boundary) in [("으리", Boundary::EuFull), ("리", Boundary::EuZero)] {
                for r in grammar::recover(base, suffix, boundary) {
                    // Honorific/past/modal may precede conjectural (으)리, not 더.
                    for mut p in prefinals(&r.stem, 3, 0, PrefinalFollowing::OPEN, true, &mut memo)
                    {
                        record_spelling(&mut p, &r, matches!(boundary, Boundary::EuFull));
                        p.morphs.push(morph("으리", MorphemeKind::Prefinal));
                        p.morphs.push(morph(ending, MorphemeKind::Ending));
                        p.rules.extend(r.rules.clone());
                        p.rules.extend([
                            if ending == "란" {
                                "prefinal.conjectural_quotation"
                            } else {
                                "prefinal.conjectural_ra"
                            }
                            .into(),
                            if ending == "란" {
                                "ending.adnominal_expression"
                            } else {
                                "ending.factual_ra"
                            }
                            .into(),
                            "ending".into(),
                        ]);
                        if ending == "라니까" {
                            p.rules.push("ending.reporting_reason".into());
                        }
                        if ending == "라지만" {
                            p.rules.push("ending.reporting_contrast".into());
                        }
                        if matches!(ending, "라지" | "라죠") {
                            p.rules.push("ending.reporting_confirmation".into());
                        }
                        if ending == "래" {
                            p.rules.push("ending.reporting_short".into());
                        }
                        if ending == "란다" {
                            p.rules.push("ending.reporting_familiar".into());
                        }
                        if ending == "랍니다" {
                            p.rules.push("ending.reporting_polite".into());
                        }
                        if reporting_retrospective(ending) {
                            p.rules.push("ending.reporting_retrospective".into());
                        }
                        if matches!(ending, "라네" | "라는데") {
                            p.rules.push("ending.reporting_ne".into());
                        }
                        if ending == "라든가" {
                            p.rules.push("ending.quoted_alternative".into());
                        }
                        if quoted_neuni_ending(ending) {
                            p.rules.push("ending.quoted_neuni".into());
                        }
                        if reporting_ni(ending) {
                            p.rules.push("ending.reporting_ni".into());
                        }
                        if reporting_myeo(ending) {
                            p.rules.push("ending.reporting_myeo".into());
                        }
                        if quoted_ra_exclamation(ending) {
                            p.rules.push("ending.quoted_ra_exclamation".into());
                        }
                        p.dap_suffix = dap_suffix_allowed(&p);
                        out.push(p);
                    }
                }
            }
        }
    }
    // Article 39 restores a predicate boundary, not just a longer spelling.
    // Keep the original lexical predicate alongside its negative expansion.
    let mut expanded = vec![];
    for p in &out {
        let left = if let Some(base) = p.stem.strip_suffix('잖') {
            format!("{base}지")
        } else if let Some(base) = p.stem.strip_suffix('찮') {
            // The intervening 하 retains ㅎ only in the aspiration class:
            // 거북하지 않다 contracts to 거북잖다, not 거북찮다.
            if grammar::recover(&format!("{base}치"), "치", Boundary::HaAspiration).is_empty() {
                continue;
            }
            format!("{base}하지")
        } else {
            continue;
        };
        for mut head in predicates(&left) {
            if head.morphs.last().is_none_or(|m| m.form != "지") {
                continue;
            }
            // -찮 restores predicate 하, just like Article 40 shortening.
            // Do not reinterpret that inserted 하 as a nominal followed by
            // an omitted copula (간편찮다 != 간편하 + 이다 + 지 + 않다).
            head.ha_contracted |= p.stem.ends_with('찮');
            head.following.push(("않".into(), LemmaKind::Auxiliary));
            head.spellings
                .extend(shifted_spellings(&p.spellings, head.morphs.len()));
            head.morphs.extend(p.morphs.clone());
            head.rules.extend(p.rules.clone());
            head.rules
                .extend(["auxiliary".into(), "contraction.negative".into()]);
            head.connector = p.connector;
            expanded.push(head);
        }
    }
    out.extend(expanded);
    out
}

// Joined input can retain lexical 말다's noun contrast and source-listed
// transitive objects. This does not recommend omitting ordinary word spacing
// and does not introduce a general noun + verb segmentation rule.
fn nominal_mal_predicates(word: &str) -> Vec<Predicate> {
    let mut out = vec![];
    for (index, _) in word
        .char_indices()
        .filter(|&(i, c)| i > 0 && matches!(c, '말' | '마'))
    {
        let base = &word[..index];
        let right = &word[index..];
        let mut objects = vec![];
        for (suffix, condition) in [("을", 1), ("를", 2)] {
            if let Some(root) = base.strip_suffix(suffix)
                && grammar::particle_matches(root, condition)
            {
                for mut a in nominal_bases(root) {
                    a.morphemes.push(morph("를", MorphemeKind::Particle));
                    a.rules.push("particle".into());
                    objects.push(a);
                }
            }
        }
        let listed_object = matches!(base, "걱정" | "염려" | "주저" | "지체" | "생각" | "상관");
        let fixed_adverb = base == "꼼짝";
        // The only generic bare-nominal contrast is literal 말고. Other
        // nominal constructions require an object or a reviewed lexical base;
        // skip their impossible boundaries before recovering the right stem.
        if objects.is_empty() && !listed_object && !fixed_adverb && right != "말고" {
            continue;
        }
        // Only single predicates enter this boundary. Nested nominal splitting
        // stays outside this helper, keeping long 말다 chains iterative.
        for p in single_predicates(right)
            .into_iter()
            .filter(|p| p.stem == "말" && p.leading_lemmas.is_empty())
        {
            let contrast = p.morphs.len() == 1 && p.morphs[0].form == "고";
            let short = p.rules.iter().any(|r| r == "irregular.mal");
            let mut bases = if !short { objects.clone() } else { vec![] };
            if contrast || listed_object {
                bases.extend(nominal_bases(base));
            }
            // The corrected NIKL 326347 answer retains the fixed expression
            // 꼼짝 말다 but retracts the proposed hidden 하지. Preserve its
            // dictionary adverb directly; infer neither an object nor a verb.
            if fixed_adverb {
                bases.push(Analysis {
                    lemmas: vec![lemma(base, LemmaKind::Adverbial)],
                    morphemes: vec![],
                    rules: vec!["lexical.mal.fixed_adverb".into()],
                    unchanged: false,
                    spelling_paths: vec![],
                });
            }
            // No leading nominal is shared between alternatives.
            for a in bases {
                let mut joined = p.clone();
                joined.leading_lemmas = a.lemmas;
                joined.spellings = shifted_spellings(&p.spellings, a.morphemes.len()).collect();
                joined.morphs = a.morphemes;
                joined.morphs.extend(p.morphs.iter().cloned());
                joined.rules.extend(a.rules);
                joined.rules.push("lexical.mal.nominal".into());
                out.push(joined);
            }
        }
    }
    out
}

fn predicate_analysis(p: &Predicate) -> Analysis {
    Analysis {
        lemmas: p
            .leading_lemmas
            .iter()
            .cloned()
            .chain([lemma(format!("{}다", p.stem), LemmaKind::Predicate)])
            .collect(),
        morphemes: p.morphs.clone(),
        rules: p.rules.clone(),
        unchanged: false,
        spelling_paths: if p.spellings.is_empty() {
            Vec::new()
        } else {
            vec![p.spellings.clone()]
        },
    }
}

fn expand_predicate(p: &Predicate) -> Vec<Analysis> {
    let mut out = if p.copula_only {
        vec![]
    } else {
        vec![predicate_analysis(p)]
    };
    if p.dap_suffix
        && let Some(base) = p.stem.strip_suffix('답').filter(|s| !s.is_empty())
    {
        for mut a in nominal_bases(base) {
            // -적/-쯤 combinations need their own attachment audit.
            // Noun-forming -이 followed by -답다 needs a separate derivation audit.
            if a.rules.iter().any(|r| r == "suffix.nominal.i")
                || a.morphemes
                    .iter()
                    .any(|m| matches!(m.form.as_str(), "적" | "쯤" | "씩"))
            {
                continue;
            }
            a.morphemes.push(morph("답다", MorphemeKind::Suffix));
            let boundary = a.morphemes.len();
            append_predicate_morphs(&mut a, p);
            // -답다's fixed ㅂ class is enforced by dap_suffix. It is not a
            // lexical spelling requirement on the preceding nominal lemma.
            for path in &mut a.spelling_paths {
                path.retain(|r| {
                    r.morpheme_index != boundary
                        || !matches!(
                            r.class,
                            SpellingClass::BieupRegular | SpellingClass::BieupIrregular
                        )
                });
            }
            if a.spelling_paths.iter().any(Vec::is_empty) {
                a.spelling_paths.clear();
            }
            a.rules.extend(p.rules.clone());
            a.rules.push("suffix.adjectival.dap".into());
            out.push(a);
        }
    }
    // The restored 하 belongs to a predicate. It cannot then become a nominal
    // base before an omitted copula: 생각다 is not 생각하 + 이다 + 다.
    if !p.ha_contracted && p.leading_lemmas.is_empty() {
        add_copulas(p, &mut out);
    }
    for a in &mut out {
        a.lemmas.extend(p.following.iter().map(|(s, kind)| {
            lemma(
                if *kind == LemmaKind::Adverbial {
                    s.clone()
                } else {
                    format!("{s}다")
                },
                *kind,
            )
        }));
    }
    out.retain_mut(auxiliary_inflections_allowed);
    out
}

// Preserve every whole-word parent and expand independent suffix owners
// iteratively. Processing owners from right to left keeps original morpheme
// insertion indices valid and avoids a recursion or bit-width cutoff.
fn add_doeda_suffixes(out: &mut Vec<Analysis>) {
    add_predicate_suffixes(
        out,
        crate::doeda_suffix::formation,
        "되다",
        crate::doeda_suffix::rule,
        false,
    );
}
fn add_hada_suffixes(out: &mut Vec<Analysis>) {
    add_predicate_suffixes(
        out,
        crate::hada_suffix::formation,
        "하다",
        crate::hada_suffix::rule,
        false,
    );
    add_predicate_suffixes(
        out,
        crate::hada_remaining::verbal,
        "하다",
        |_| crate::hada_suffix::RULE,
        false,
    );
    add_predicate_suffixes(
        out,
        crate::hada_remaining::adjectival,
        "하다",
        |_| crate::hada_suffix::ADJECTIVE_RULE,
        false,
    );
    add_predicate_suffixes(
        out,
        crate::hada_remaining::auxiliary_verbal,
        "하다",
        |_| crate::hada_remaining::AUX_VERB_RULE,
        true,
    );
    add_predicate_suffixes(
        out,
        crate::hada_remaining::auxiliary_adjectival,
        "하다",
        |_| crate::hada_remaining::AUX_ADJECTIVE_RULE,
        true,
    );
}
fn add_predicate_suffixes(
    out: &mut Vec<Analysis>,
    formation: fn(&str) -> Option<(&'static str, LemmaKind, PredicateClass)>,
    suffix: &str,
    rule: fn(PredicateClass) -> &'static str,
    include_auxiliary: bool,
) {
    let original = out.len();
    for i in 0..original {
        if !out[i].lemmas.iter().any(|l| {
            (l.kind == LemmaKind::Predicate
                || (include_auxiliary && l.kind == LemmaKind::Auxiliary))
                && formation(&l.text).is_some()
        }) {
            continue;
        }
        let parent = out[i].clone();
        let Some(order) = parent.breakdown() else {
            continue;
        };
        let mut owners = vec![];
        for (position, component) in order.iter().enumerate() {
            let crate::breakdown::Component::Lemma(index) = *component else {
                continue;
            };
            let l = &parent.lemmas[index];
            if l.kind != LemmaKind::Predicate
                && !(include_auxiliary && l.kind == LemmaKind::Auxiliary)
            {
                continue;
            }
            let Some((base, kind, class)) = formation(&l.text) else {
                continue;
            };
            let rest = &order[position + 1..];
            let end = rest
                .iter()
                .position(|c| matches!(c, crate::breakdown::Component::Lemma(_)))
                .unwrap_or(rest.len());
            let Some(crate::breakdown::Component::Morpheme(at)) = rest.first() else {
                continue;
            };
            if !matches!(parent.morphemes[*at].kind, MorphemeKind::Prefinal | MorphemeKind::Ending)
                || !rest[..end].iter().any(|c| matches!(c, crate::breakdown::Component::Morpheme(j) if parent.morphemes[*j].kind == MorphemeKind::Ending))
            { continue; }
            owners.push((index, *at, base, kind, class));
        }
        let mut branches = vec![parent];
        for (index, at, base, kind, class) in owners.into_iter().rev() {
            let count = branches.len();
            for j in 0..count {
                let mut a = branches[j].clone();
                a.lemmas[index] = lemma(base, kind);
                a.morphemes.insert(at, morph(suffix, MorphemeKind::Suffix));
                for path in &mut a.spelling_paths {
                    for recovery in path {
                        if recovery.morpheme_index >= at {
                            recovery.morpheme_index += 1;
                        }
                    }
                }
                a.rules.push(rule(class).into());
                // Validate this insertion's class before analysis-wide rule
                // unions can borrow another owner's alternative class.
                if auxiliary_inflections_allowed_for(&mut a, Some((index, class))) {
                    branches.push(a);
                }
            }
        }
        out.extend(branches.into_iter().skip(1).filter_map(|mut a| {
            (a.breakdown().is_some() && auxiliary_inflections_allowed(&mut a)).then_some(a)
        }));
    }
}

fn add_listed_nominal_decompositions(out: &mut Vec<Analysis>) {
    add_nominal_decompositions(
        out,
        crate::nominal_si::nominal,
        crate::nominal_si::passive,
        "시",
        crate::nominal_si::RULE,
    );
    add_nominal_decompositions(
        out,
        crate::nominal_hwa::nominal,
        crate::nominal_hwa::passive,
        "화",
        crate::nominal_hwa::RULE,
    );
}
fn add_nominal_decompositions(
    out: &mut Vec<Analysis>,
    nominal: fn(&str) -> Option<&'static str>,
    passive_head: fn(&str) -> Option<&'static str>,
    suffix: &str,
    rule: &str,
) {
    let original = out.len();
    for i in 0..original {
        if !out[i].lemmas.iter().any(|l| {
            (l.kind == LemmaKind::Nominal && nominal(&l.text).is_some())
                || (l.kind == LemmaKind::Predicate && passive_head(&l.text).is_some())
        }) {
            continue;
        }
        let parent = out[i].clone();
        let Some(order) = parent.breakdown() else {
            continue;
        };
        let mut owners = vec![];
        for (position, component) in order.iter().enumerate() {
            let crate::breakdown::Component::Lemma(index) = *component else {
                continue;
            };
            let l = &parent.lemmas[index];
            let (base, passive) = match l.kind {
                LemmaKind::Nominal => (nominal(&l.text), false),
                LemmaKind::Predicate => (passive_head(&l.text), true),
                _ => (None, false),
            };
            let Some(base) = base else {
                continue;
            };
            let rest = &order[position + 1..];
            let end = rest
                .iter()
                .position(|c| matches!(c, crate::breakdown::Component::Lemma(_)))
                .unwrap_or(rest.len());
            if passive && !rest[..end].iter().any(|c| matches!(c, crate::breakdown::Component::Morpheme(j) if parent.morphemes[*j].kind == MorphemeKind::Ending)) {
                continue;
            }
            let at = rest
                .iter()
                .find_map(|c| match c {
                    crate::breakdown::Component::Morpheme(j) => Some(*j),
                    _ => None,
                })
                .unwrap_or(parent.morphemes.len());
            owners.push((index, at, base, passive));
        }
        let mut branches = vec![parent];
        for (index, at, base, passive) in owners.into_iter().rev() {
            let count = branches.len();
            for j in 0..count {
                let mut a = branches[j].clone();
                a.lemmas[index] = lemma(base, LemmaKind::Nominal);
                let inserted = if passive { 2 } else { 1 };
                if passive {
                    a.morphemes.insert(at, morph("되다", MorphemeKind::Suffix));
                    a.rules.push("suffix.verb.doeda".into());
                }
                a.morphemes.insert(at, morph(suffix, MorphemeKind::Suffix));
                for path in &mut a.spelling_paths {
                    for recovery in path {
                        if recovery.morpheme_index >= at {
                            recovery.morpheme_index += inserted;
                        }
                    }
                }
                a.rules.push(rule.into());
                branches.push(a);
            }
        }
        out.extend(branches.into_iter().skip(1).filter_map(|mut a| {
            (a.breakdown().is_some() && auxiliary_inflections_allowed(&mut a)).then_some(a)
        }));
    }
}
fn add_predicate_compounds(out: &mut Vec<Analysis>) {
    let original = out.len();
    for i in 0..original {
        let owners: Vec<_> = out[i]
            .lemmas
            .iter()
            .enumerate()
            .filter(|(_, l)| l.kind == LemmaKind::Predicate && l.text == "잘되다")
            .map(|(index, _)| index)
            .collect();
        if owners.is_empty() || out[i].breakdown().is_none() {
            continue;
        }
        let mut branches = vec![out[i].clone()];
        // Inserting lookup lemmas changes no morpheme or spelling-recovery index.
        // Right-to-left expansion also preserves later auxiliary ownership.
        for index in owners.into_iter().rev() {
            for j in 0..branches.len() {
                let mut a = branches[j].clone();
                a.lemmas[index] = lemma("되다", LemmaKind::Predicate);
                a.lemmas.insert(index, lemma("잘", LemmaKind::Adverbial));
                a.rules.push(crate::predicate_compound::RULE.into());
                branches.push(a);
            }
        }
        out.extend(branches.into_iter().skip(1).filter_map(|mut a| {
            (a.breakdown().is_some() && auxiliary_inflections_allowed(&mut a)).then_some(a)
        }));
    }
}

#[derive(Clone, Copy)]
pub(crate) enum PredicateClass {
    Verb,
    Adjective,
    /// Both independently recorded classes remain possible for this owner.
    VerbOrAdjective,
    Copula,
}

// KRDict 89858 treats these 되다 senses as verbs; NIKL separately
// describes an auxiliary construction. This class belongs only to the new
// attributed lexical role, leaving every historical auxiliary use unchanged.
pub(crate) fn lexical_doeda_role(lemma: &Lemma, connector: Option<&str>, rules: &[String]) -> bool {
    lemma.kind == LemmaKind::Predicate
        && lemma.text == "되다"
        && ((matches!(connector, Some("게" | "게끔"))
            && rules.iter().any(|r| r == "lexical.doeda.complement"))
            || (matches!(
                connector,
                Some("도록" | "기" | "어야" | "으면" | "어도" | "어" | "어서" | "어서는")
            ) && rules.iter().any(|r| r == "lexical.doeda.extended")))
}

// The adverb owns no inflection. Preserve the actual preceding predicate's
// connector through this explicitly attributed bridge, without lending it to
// arbitrary adverbs, compounds or later unrelated owners.
pub(crate) fn doeda_negative_bridge(a: &Analysis, index: usize) -> bool {
    a.lemmas[index].kind == LemmaKind::Adverbial
        && a.lemmas[index].text == "안"
        && a.lemmas.get(index + 1).is_some_and(|l| {
            l.text == "되다" && matches!(l.kind, LemmaKind::Predicate | LemmaKind::Auxiliary)
        })
        && a.rules.iter().any(|r| r == "doeda.negative_bridge")
}

// Classes belong to a particular auxiliary use, not every homonym of a lemma.
// Unclassified lexical heads stay unknown; negative auxiliaries inherit a
// known preceding class. KRDict's 54-entry inventory supplies these classes.
pub(crate) fn auxiliary_class(
    stem: &str,
    connector: Option<&str>,
    previous: Option<PredicateClass>,
) -> Option<PredicateClass> {
    use PredicateClass::*;
    match stem {
        "듯싶" | "듯하" | "만하" | "법하" | "뻔하" | "성싶" | "싶" | "직하" => {
            Some(Adjective)
        }
        "않" | "아니하" => previous,
        "못하" if matches!(connector, Some("다" | "다가")) => Some(Adjective),
        "못하" => previous,
        "보" => match connector {
            Some("어" | "다가" | "으려다" | "으려다가") => Some(Verb),
            Some("는가" | "은가" | "던가" | "나" | "을까" | "으려나") => {
                Some(Adjective)
            }
            _ => None,
        },
        "되" if matches!(
            connector,
            Some("어야" | "으면" | "어도" | "어서" | "어서는" | "어")
        ) =>
        {
            Some(Verb)
        }
        "하" => match connector {
            Some("어" | "게" | "게끔" | "어야" | "으려" | "으려고" | "고자" | "으면") => {
                Some(Verb)
            }
            _ => None,
        },
        "가" | "가지" | "갖" | "계시" | "나가" | "나" | "내" | "놓" | "달" | "대" | "두"
        | "드리" | "들" | "마지아니하" | "마지않" | "말" | "먹" | "버릇하" | "버리" | "빠지"
        | "생기" | "쌓" | "오" | "있" | "자빠지" | "재끼" | "젖히" | "주" | "죽" | "지"
        | "척하" | "체하" | "치우" | "터지" => Some(Verb),
        // 양하다 has both classes; legacy 되다 is not in this KRDict auxiliary
        // inventory. Neither is assigned a class by elimination.
        _ => None,
    }
}

// Direct finite intention constructions reviewed in COV-017aw. Related
// shortened expressions have conflicting attachment notes (see the source
// review), so do not extrapolate this check to every following 하다 form.
fn finite_intention_auxiliary(stem: &str, morphs: &[Morpheme]) -> bool {
    matches!(stem, "하" | "들")
        && morphs
            .iter()
            .position(|m| m.kind == MorphemeKind::Ending)
            .is_some_and(|i| {
                matches!(morphs[i].form.as_str(), "는다" | "다" | "어요" | "습니다")
                    // The same informal polite surface also has a separate
                    // 어 + particle 요 path. It must obey the same boundary.
                    || (morphs[i].form == "어"
                        && morphs.get(i + 1).is_some_and(|m| {
                            m.kind == MorphemeKind::Particle && m.form == "요"
                        }))
            })
}

pub(crate) fn derivational_class(
    lemma: &Lemma,
    rules: &[String],
    morphs: &[Morpheme],
) -> Option<PredicateClass> {
    crate::doeda_suffix::owner_class(lemma, rules, morphs)
        .or_else(|| crate::hada_suffix::owner_class(lemma, rules, morphs))
        .or_else(|| crate::hada_remaining::owner_class(lemma, rules, morphs))
}

fn auxiliary_inflections_allowed(a: &mut Analysis) -> bool {
    auxiliary_inflections_allowed_for(a, None)
}
fn auxiliary_inflections_allowed_for(
    a: &mut Analysis,
    forced_owner: Option<(usize, PredicateClass)>,
) -> bool {
    if !a.lemmas.iter().any(|l| l.kind == LemmaKind::Auxiliary)
        && !a.rules.iter().any(|r| {
            matches!(
                r.as_str(),
                "lexical.doeda.complement"
                    | "lexical.doeda.extended"
                    | "suffix.verb.doeda"
                    | "suffix.adjective.doeda"
                    | "suffix.verb.hada"
                    | "suffix.adjective.hada"
                    | "suffix.auxiliary.verb.hada"
                    | "suffix.auxiliary.adjective.hada"
                    | "compound.predicate.well_doeda"
            )
        })
    {
        return true;
    }
    let mut cursor = 0;
    let mut previous = None;
    let mut connector = None;
    let mut previous_report_stative = false;
    let mut previous_relational_nominal = false;
    let mut previous_relational_copula = false;
    let mut previous_non_honorific_prefinal = false;
    let mut previous_past_prefinal = false;
    for (lemma_index, lemma) in a.lemmas.iter().enumerate() {
        let forced_class = forced_owner
            .filter(|(index, _)| *index == lemma_index)
            .map(|(_, class)| class);
        if !crate::hada_remaining::auxiliary_attachment_allowed(
            lemma,
            &a.rules,
            &a.morphemes[cursor..],
            connector,
            previous,
            forced_class,
        ) {
            return false;
        }
        if crate::predicate_compound::is_left(a, lemma_index) {
            continue;
        }
        if doeda_negative_bridge(a, lemma_index) {
            continue;
        }
        // NIKL's verbal/adjectival -게 하다 constructions also permit
        // emphatic -게끔 하다: past belongs to right-hand 하다. Scope this
        // new join's control to the immediately preceding represented owner;
        // earlier past and right-hand inflections remain independent.
        if lemma.kind == LemmaKind::Auxiliary
            && lemma.text == "하다"
            && connector == Some("게끔")
            && previous_past_prefinal
        {
            return false;
        }
        if lemma.kind == LemmaKind::Auxiliary
            && connector == Some("으려고")
            && previous_non_honorific_prefinal
            && finite_intention_auxiliary(
                lemma.text.strip_suffix('다').unwrap_or(&lemma.text),
                &a.morphemes[cursor..],
            )
        {
            return false;
        }
        // The copular rhetorical ending (학생이려고?) is not the intention
        // connector in 학생이려고 한다. The class belongs to the left owner.
        if lemma.kind == LemmaKind::Auxiliary
            && connector == Some("으려고")
            && matches!(previous, Some(PredicateClass::Copula))
            && finite_intention_auxiliary(
                lemma.text.strip_suffix('다').unwrap_or(&lemma.text),
                &a.morphemes[cursor..],
            )
        {
            // KAIST attests 인간적이려고 하는. The existing relational
            // -적 analysis supplies a possible state-making nominal reading,
            // including the unsplit lexical alternative. Preserve this local
            // hypothesis; dictionary assessment leaves its license unknown.
            if !previous_relational_copula {
                return false;
            }
            a.rules.push("copula.intention_relational".into());
        }
        // Continuative/resultative 있다 and honorific 계시다 select verbs.
        // Check the immediately preceding represented role, including classes
        // inherited through negatives; an unknown lexical head stays unknown.
        if lemma.kind == LemmaKind::Auxiliary
            && matches!(lemma.text.as_str(), "있다" | "계시다")
            && matches!(connector, Some("어" | "고"))
            && matches!(
                previous,
                Some(PredicateClass::Adjective | PredicateClass::Copula)
            )
        {
            return false;
        }
        // NIKL grammar-expression guide §3.6.27 selects verbs for -어 대다
        // and explicitly marks adjective examples invalid. The immediate
        // represented owner supplies its class, including negatives and
        // 답다; a later verb auxiliary resets an earlier adjective class.
        // Unknown lexical predicates retain their dictionary-free hypotheses.
        if lemma.kind == LemmaKind::Auxiliary
            && lemma.text == "대다"
            && connector == Some("어")
            && matches!(
                previous,
                Some(PredicateClass::Adjective | PredicateClass::Copula)
            )
        {
            return false;
        }
        // Expressive -어 하다 selects an adjective. Check the immediately
        // preceding known role, including inherited negative classes. A
        // lexical head remains unknown without dictionary/sense analysis.
        if lemma.kind == LemmaKind::Auxiliary
            && lemma.text == "하다"
            && connector == Some("어")
            && matches!(
                previous,
                Some(PredicateClass::Verb | PredicateClass::Copula)
            )
        {
            return false;
        }
        let mut inflected = matches!(
            lemma.kind,
            LemmaKind::Predicate | LemmaKind::Auxiliary | LemmaKind::Copula
        );
        let doeda_class =
            forced_class.or_else(|| derivational_class(lemma, &a.rules, &a.morphemes[cursor..]));
        let mut class = if doeda_class.is_some() {
            doeda_class
        } else if lemma.kind == LemmaKind::Auxiliary {
            auxiliary_class(
                lemma.text.strip_suffix('다').unwrap_or(&lemma.text),
                connector,
                previous,
            )
        } else if lemma.kind == LemmaKind::Copula {
            Some(PredicateClass::Copula)
        } else if lexical_doeda_role(lemma, connector, &a.rules)
            || crate::predicate_compound::is_owner(a, lemma_index)
        {
            Some(PredicateClass::Verb)
        } else {
            None
        };
        let relational_copula = matches!(class, Some(PredicateClass::Copula))
            && ((lemma.kind == LemmaKind::Copula && previous_relational_nominal)
                || (lemma.kind == LemmaKind::Auxiliary && previous_relational_copula));
        let mut relational_nominal = lemma.kind == LemmaKind::Nominal
            && lemma.text.strip_suffix('적').is_some_and(|s| !s.is_empty());
        // Auxiliary 있다/계시다 have stative plain-다 report readings despite
        // their verbal POS. Negative auxiliaries retain this possibility.
        let report_stative = lemma.kind == LemmaKind::Auxiliary
            && (matches!(lemma.text.as_str(), "있다" | "계시다")
                || (matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
                    && previous_report_stative));
        while let Some(m) = a
            .morphemes
            .get(cursor)
            .filter(|m| m.kind == MorphemeKind::Suffix)
        {
            relational_nominal = lemma.kind == LemmaKind::Nominal && m.form == "적";
            if m.form == "답다" {
                class = Some(PredicateClass::Adjective);
                inflected = true;
            }
            if matches!(m.form.as_str(), "되다" | "하다") && doeda_class.is_some() {
                inflected = true;
            }
            cursor += 1;
        }
        let bare = inflected
            && a.morphemes
                .get(cursor)
                .is_some_and(|m| m.kind == MorphemeKind::Ending);
        // Auxiliary 있다 describes an ongoing action/result/state, rather than
        // lexical 있다's dynamic 'stay' reading. Its bare declarative uses 다,
        // not 는다. Do not inherit this restriction through negative auxiliaries
        // or apply it to honorific 계시다, which also permits 계신다.
        let bare_stative_iss = bare && lemma.kind == LemmaKind::Auxiliary && lemma.text == "있다";
        let mut non_honorific_prefinal = false;
        let mut past_prefinal = false;
        while inflected
            && a.morphemes
                .get(cursor)
                .is_some_and(|m| m.kind == MorphemeKind::Prefinal)
        {
            non_honorific_prefinal |= !honorific_prefinal(&a.morphemes[cursor].form);
            past_prefinal |= a.morphemes[cursor].form == "었";
            cursor += 1;
        }
        connector = None;
        if inflected
            && let Some(m) = a
                .morphemes
                .get(cursor)
                .filter(|m| m.kind == MorphemeKind::Ending)
        {
            if bare && m.form == "는" && matches!(doeda_class, Some(PredicateClass::Adjective)) {
                return false;
            }
            // KRDict 73878/73888 list bare adjectives/copulas; 73879 lists
            // verbs and existential heads. Unknown lexical classes survive.
            // Negative paradigms need their own evidence, not inherited POS.
            if bare
                && !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
                && ((m.form == "은감" && matches!(class, Some(PredicateClass::Verb)))
                    || (m.form == "는감"
                        && (matches!(class, Some(PredicateClass::Copula))
                            || (matches!(class, Some(PredicateClass::Adjective))
                                && !matches!(lemma.text.as_str(), "있다" | "없다" | "계시다")))))
            {
                return false;
            }
            if bare
                // Negative paradigms are not resolved from inherited POS:
                // KRDict -으니라 even illustrates 되지는 않으니라.
                && !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
                && ((m.form == "느니라"
                    && matches!(
                        class,
                        Some(PredicateClass::Adjective | PredicateClass::Copula)
                    ))
                    || (m.form == "으니라"
                        && matches!(class, Some(PredicateClass::Verb))
                        && !matches!(lemma.text.as_str(), "있다" | "계시다")))
            {
                return false;
            }
            // The explicit 느냐지만/느냐니까 sources include existential adjectives.
            // Do not resolve negative auxiliary paradigms solely from the
            // inherited adjective class (COV-019h remains open).
            if bare
                && matches!(m.form.as_str(), "느냐지만" | "느냐니까" | "느냬")
                && matches!(class, Some(PredicateClass::Adjective))
                && !lemma.text.ends_with("있다")
                && !lemma.text.ends_with("없다")
                && !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
            {
                return false;
            }
            // A factual copular report cannot borrow the ending's command
            // sense for a known bare lexical owner ending in 이.
            if bare
                && quoted_copular_exclamation(&m.form)
                && matches!(
                    class,
                    Some(
                        PredicateClass::Verb
                            | PredicateClass::Adjective
                            | PredicateClass::VerbOrAdjective
                    )
                )
                && lemma.text != "아니다"
            {
                return false;
            }
            if bare
                && verbal_quoted_question(&m.form)
                && matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
                && !lemma.text.ends_with("있다")
                && !lemma.text.ends_with("없다")
                && !matches!(
                    lemma.text.as_str(),
                    "계시다" | "않다" | "아니하다" | "못하다"
                )
            {
                return false;
            }
            // KRDict 78483/78496 list verb attachment. Apply the bare
            // class check to this owner, never to an earlier lexical head.
            // Prefinal combinations need a separate distribution review.
            if bare
                && m.form == "음세"
                && matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
            {
                return false;
            }
            // These class checks belong to the immediate bare owner.
            // A prefinal/other auxiliary establishes a distinct boundary.
            if bare
                && (neuni_verbal_ending(&m.form) || m.form == "는걸")
                && matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
                && !lemma.text.ends_with("있다")
                && !lemma.text.ends_with("없다")
                && lemma.text != "계시다"
            {
                return false;
            }
            if bare
                && present_exclamation(&m.form)
                && (matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                ) || bare_stative_iss)
            {
                // NIKL 307876: auxiliary 있다 inflects adjectivally here;
                // do not borrow the lexical verb homonym's present paradigm.
                return false;
            }
            if bare
                && m.form == "구먼"
                && matches!(class, Some(PredicateClass::Verb))
                && !bare_stative_iss
                && !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
            {
                return false;
            }
            if bare && m.form == "니만" && matches!(class, Some(PredicateClass::Verb)) {
                return false;
            }
            // The existential exception belongs to this ending's owner.
            if bare
                && m.form == "는바"
                && matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
                && !lemma.text.ends_with("있다")
                && !lemma.text.ends_with("없다")
                && lemma.text != "계시다"
            {
                return false;
            }
            if bare_stative_iss && present_declarative(&m.form) {
                return false;
            }
            // NIKL's bare 나이다/나이까 stems are verbs or three existential /
            // honorific heads. Polite combinations directly attest adjectives and
            // copulas, so apply this only before any prefinal intervenes.
            // Negative auxiliary class inheritance remains independently open.
            if bare
                && literary_na_ending(&m.form)
                && matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
                && !matches!(
                    lemma.text.as_str(),
                    "있다" | "없다" | "계시다" | "않다" | "아니하다" | "못하다"
                )
            {
                return false;
            }
            if (verbal_intention(&m.form) || result_connective(&m.form) || activity_reason(&m.form))
                && matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
            {
                return false;
            }
            if present_declarative(&m.form)
                && matches!(
                    class,
                    Some(PredicateClass::Adjective | PredicateClass::Copula)
                )
            {
                return false;
            }
            // These other verbal families also exclude known adjectives,
            // including after honorific 시.
            if matches!(class, Some(PredicateClass::Adjective))
                && matches!(
                    m.form.as_str(),
                    "으라더니"
                        | "으라던"
                        | "으라던데"
                        | "자던"
                        | "자던데"
                        | "으라며"
                        | "으라면서"
                        | "으라니"
                        | "으라느니"
                        | "자느니"
                        | "자니"
                        | "잔"
                        | "자며"
                        | "자면서"
                        | "자면"
                        | "으랍니다"
                        | "으란다"
                        | "으라지"
                        | "으라죠"
                        | "으라지만"
                        | "으라니까"
                        | "자지만"
                        | "자니까"
                        | "으래"
                        | "재"
                        | "잔다"
                        | "으라네"
                        | "으라는데"
                        | "으라거나"
                        | "자거나"
                        | "고서"
                        | "을라치면"
                )
            {
                return false;
            }
            // These restrictions apply only at the bare-stem boundary;
            // e.g. adjective + 었 + 는데 remains a licensed composition.
            if bare
                && match class {
                    Some(PredicateClass::Adjective) => matches!(
                        m.form.as_str(),
                        "는" | "는데"
                            | "는데요"
                            | "는데도"
                            | "는데다가"
                            | "는지"
                            | "는가"
                            | "는가요"
                            | "느냐"
                            | "느냐느니"
                            | "느냐고"
                            | "느냐는"
                            | "느냐며"
                            | "느냐면서"
                            | "느냐니"
                            | "느냔"
                            | "느냔다"
                    ),
                    // Do not infer the converse: 계신가 and existential
                    // negation require a separate honorific/existential audit.
                    Some(PredicateClass::Verb) => {
                        (adjectival_question(&m.form) && !(m.form == "으냐면" && report_stative))
                            || (!report_stative
                                && matches!(
                                    m.form.as_str(),
                                    "다거나"
                                        | "다든가"
                                        | "다네"
                                        | "다는데"
                                        | "다던"
                                        | "다던데"
                                        | "다며"
                                        | "다면서"
                                        | "단다"
                                        | "다지"
                                        | "다죠"
                                        | "다지만"
                                        | "다니까"
                                        | "다느니"
                                        | "다는구나"
                                        | "다는군"
                                        | "다더군"
                                        | "다더군요"
                                        | "대"
                                ))
                    }
                    Some(PredicateClass::Copula | PredicateClass::VerbOrAdjective) | None => false,
                }
            {
                return false;
            }
            connector = Some(m.form.as_str());
            cursor += 1;
        }
        while a
            .morphemes
            .get(cursor)
            .is_some_and(|m| m.kind == MorphemeKind::Particle)
        {
            relational_nominal = false;
            cursor += 1;
        }
        previous = class;
        previous_report_stative = report_stative;
        previous_relational_nominal = relational_nominal;
        previous_relational_copula = relational_copula;
        previous_non_honorific_prefinal = non_honorific_prefinal;
        previous_past_prefinal = past_prefinal;
    }
    true
}

// Bounded adjective attachment inventory. The known suffix is ㅂ-irregular;
// arbitrary lexical predicates still retain the engine's regular hypotheses.
fn dap_suffix_allowed(p: &Predicate) -> bool {
    if p.morphs
        .first()
        .is_some_and(|m| verbal_quoted_question(&m.form))
    {
        return false;
    }
    if p.morphs.first().is_some_and(|m| {
        neuni_verbal_ending(&m.form)
            || present_exclamation(&m.form)
            || copular_exclamation(&m.form)
            || matches!(m.form.as_str(), "음세" | "는바" | "는걸" | "는감")
    }) {
        return false;
    }
    if p.morphs.first().is_some_and(|m| {
        matches!(
            m.form.as_str(),
            "느냐고" | "느냐느니" | "느냐다" | "느냐지만" | "느냐니까" | "느냬"
        )
    }) {
        return false;
    }
    if !p.stem.ends_with('답') {
        return false;
    }
    if p.morphs
        .iter()
        .find(|m| m.kind == MorphemeKind::Ending)
        .is_some_and(|m| {
            present_declarative(&m.form)
                || verbal_intention(&m.form)
                || result_connective(&m.form)
                || activity_reason(&m.form)
                || matches!(
                    m.form.as_str(),
                    "으라더니"
                        | "으라던"
                        | "으라던데"
                        | "자던"
                        | "자던데"
                        | "으라며"
                        | "으라면서"
                        | "으라니"
                        | "으라느니"
                        | "자느니"
                        | "자니"
                        | "잔"
                        | "자며"
                        | "자면서"
                        | "자면"
                        | "으랍니다"
                        | "으란다"
                        | "으라지"
                        | "으라죠"
                        | "으라지만"
                        | "으라니까"
                        | "자지만"
                        | "자니까"
                        | "으래"
                        | "재"
                        | "잔다"
                        | "으라네"
                        | "으라는데"
                        | "으라거나"
                        | "자거나"
                        | "고서"
                        | "을라치면"
                )
        })
    {
        return false;
    }
    let first = p.morphs[0].form.as_str();
    if first == "느니라" {
        return false;
    }
    let vowel = first.starts_with('어')
        || first.starts_with('은')
        || adjectival_question(first)
        || quoted_command_exclamation(first)
        || matches!(
            first,
            "었" | "시"
                | "으면"
                | "으니까"
                | "으니"
                | "니만"
                | "으니만큼"
                | "으니라"
                | "으소서"
                | "으옵소서"
                | "으옵"
                | "으옵시"
                | "으며"
                | "으면서"
                | "으므로"
                | "으나"
                | "으나마"
                | "으냐"
                | "으냐고"
                | "으냐는"
                | "으냐며"
                | "으냐면서"
                | "으냐니"
                | "으냐느니"
                | "으냔"
                | "으냔다"
                | "으냬"
                | "으냐지만"
                | "으냐니까"
                | "으려나"
                | "으려니"
                | "으려니까"
                | "으려더라"
                | "으려던"
                | "으려면서"
                | "으려든지"
                // KRDict 69067 also has a final rhetorical adjective sense.
                // Keep derived 답다 beside lexical adjectives such as 넓다.
                | "으려고"
                | "으리라"
                | "으리만큼"
                | "으련만"
                | "으련마는"
                | "으리"
                | "으리라고"
                | "으리까"
                | "을"
                | "을걸"
                | "을까"
                | "을까요"
                | "을지"
                | "을는지"
                | "을라"
                | "을라고"
                | "을라고요"
                | "을지라도"
                | "을밖에"
                | "을망정"
                | "을지언정"
                | "을수록"
                | "음"
        );
    if vowel {
        return p.rules.iter().any(|r| r == "irregular.bieup");
    }
    quoted_proposal_exclamation(first)
        || matches!(
            first,
            "겠" | "더"
                | "사옵"
                | "사옵시"
                | "삽"
                | "다"
                | "다가"
                | "단"
                | "다간"
                | "다가는"
                | "냔"
                | "다고"
                | "다는"
                | "다니"
                | "다느니"
                | "냐느니"
                | "냐면"
                | "더라느니"
                | "다면"
                | "답니다"
                | "단다"
                | "다지"
                | "다죠"
                | "다지만"
                | "다니까"
                | "냐지만"
                | "냐니까"
                | "더라지만"
                | "더라니까"
                | "냔다"
                | "더란다"
                | "대"
                | "냬"
                | "더래"
                | "다며"
                | "다면서"
                | "더라며"
                | "더라면서"
                | "더라니"
                | "냐니"
                | "냐며"
                | "냐면서"
                | "다는구나"
                | "냐는구나"
                | "냐는군"
                | "냐더군"
                | "냐더군요"
                | "다는군"
                | "다더군"
                | "다더군요"
                | "더라는구나"
                | "더라는군"
                | "다네"
                | "다는데"
                | "다던"
                | "다더니"
                | "다나"
                | "다더니만"
                | "다더니마는"
                | "다던데"
                | "냐던데"
                | "으되"
                | "더라네"
                | "더라는데"
                | "다거나"
                | "다든가"
                | "고"
                | "고말고"
                | "다마다"
                | "고요"
                | "지"
                | "지요"
                | "죠"
                | "게"
                | "게요"
                | "게끔"
                | "지만"
                | "지마는"
                | "지만요"
                | "군"
                | "군요"
                | "구나"
                | "구려"
                | "구먼"
                | "더구나"
                | "더구려"
                | "더구먼"
                | "로구나"
                | "로구려"
                | "로구먼"
                | "로군"
                | "는구나"
                | "는구려"
                | "는구먼"
                | "는군"
                | "는군요"
                | "네"
                | "네요"
                | "나"
                | "나요"
                | "냐"
                | "냐고"
                | "냐는"
                | "니"
                | "기"
                | "기에"
                | "길래"
                | "기로"
                | "기가"
                | "기는"
                | "기도"
                | "기만"
                | "기를"
                | "기보다"
                | "던"
                | "던데"
                | "던데요"
                | "던가"
                | "던지"
                | "더라"
                | "더라고"
                | "더라는"
                | "더니"
                | "더니만"
                | "더니마는"
                | "더군"
                | "더군요"
                | "더라도"
                | "거든"
                | "거든요"
                | "거나"
                | "건"
                | "거니"
                | "거니와"
                | "든"
                | "든지"
                | "든가"
                | "도록"
                | "습니다"
                | "습니까"
                | "소"
                | "오"
        )
}

fn copula_bases(word: &str) -> Vec<Analysis> {
    let mut out = nominal_bases(word);
    // COV-020m: source-attested adverbial copula bases. Preserve a separate
    // nominal homonym where present; an adverb POS alone is not a license for
    // every adverb or every contextual sense. See docs/adverb-copula-evaluation.json.
    if matches!(
        word,
        "고만"
            | "그만"
            | "그럭저럭"
            | "그대로"
            | "그만큼"
            | "딱"
            | "들쑥날쑥"
            | "들쭉날쭉"
            | "먼저"
            | "물론"
            | "별로"
            | "왜"
            | "제법"
    ) {
        out.push(Analysis {
            lemmas: vec![lemma(word, LemmaKind::Adverbial)],
            morphemes: vec![],
            rules: vec!["copula.adverbial_base".into()],
            unchanged: false,
            spelling_paths: Vec::new(),
        });
    }
    let expanded = match word {
        "거" => Some("것"),
        "이거" => Some("이것"),
        "그거" => Some("그것"),
        "저거" => Some("저것"),
        _ => None,
    };
    if let Some(expanded) = expanded {
        let mut a = nominal_bases(expanded).remove(0);
        a.rules.push("nominal.colloquial_geot".into());
        out.push(a);
    }
    // Direct nominalizations and the reviewed -어서 clause need no particle.
    // Keep the connective's role and provenance distinct from nominalization.
    with_auxiliaries(word, PredicateEnd::CopulaBase, |p| {
        for mut a in expand_predicate(&p) {
            a.rules.push(
                if p.morphs.last().is_some_and(|m| m.form == "어서") {
                    "copula.connective_seo"
                } else {
                    "nominalization"
                }
                .into(),
            );
            out.push(a);
        }
    });
    out
}

fn add_copulas(p: &Predicate, out: &mut Vec<Analysis>) {
    if p.morphs.iter().any(|m| {
        m.kind == MorphemeKind::Ending
            && (quoted_command_exclamation(&m.form) || quoted_proposal_exclamation(&m.form))
    }) {
        return;
    }

    // Bare 음세 selects verbs; 는바 excludes a bare copula.
    // 나이다/나이까 is verbal/existential.
    // Direct copula examples for the latter instead
    // include a polite prefinal (e.g. 소원이옵나이다); retain those paths.
    if p.morphs.first().is_some_and(|m| {
        literary_na_ending(&m.form)
            || neuni_verbal_ending(&m.form)
            || present_exclamation(&m.form)
            || matches!(m.form.as_str(), "음세" | "는바" | "는걸" | "는감")
    }) {
        return;
    }
    // Commands and proposals are not nominal copula endings. The factual
    // 라-family homonyms preserve copular readings such as 학생이라고.
    if p.morphs
        .iter()
        .find(|m| m.kind == MorphemeKind::Ending)
        .is_some_and(|m| {
            (m.form == "으려더라"
                && !p
                    .morphs
                    .iter()
                    .any(|m| matches!(m.form.as_str(), "었" | "겠" | "어야겠")))
                || present_declarative(&m.form)
                || verbal_intention(&m.form)
                || result_connective(&m.form)
                || activity_reason(&m.form)
                || matches!(
                    m.form.as_str(),
                    "으라더니"
                        | "으라던"
                        | "으라던데"
                        | "자던"
                        | "자던데"
                        | "으라며"
                        | "으라면서"
                        | "으라니"
                        | "으라느니"
                        | "자느니"
                        | "자니"
                        | "잔"
                        | "자며"
                        | "자면서"
                        | "자면"
                        | "고서"
                        | "을라치면"
                        | "으라"
                        | "으라고"
                        | "으라는"
                        | "으라면"
                        | "으란"
                        | "으랍니다"
                        | "으란다"
                        | "으라지"
                        | "으라죠"
                        | "으라지만"
                        | "으라니까"
                        | "자지만"
                        | "자니까"
                        | "으래"
                        | "재"
                        | "잔다"
                        | "으라네"
                        | "으라는데"
                        | "으라거나"
                        | "자거나"
                        | "으십시오"
                        | "으소서"
                        | "으옵소서"
                        | "읍시다"
                )
        })
    {
        return;
    }
    if p.morphs
        .first()
        .is_some_and(|m| plain_quoted_exclamation(&m.form))
    {
        return;
    }
    // Bare 이다 takes quoted -냐는; -느냐는 may follow its licensed
    // prefinals, but does not attach directly to the copula.
    if p.morphs.first().is_some_and(|m| {
        verbal_quoted_question(&m.form)
            || matches!(
                m.form.as_str(),
                "으냐는구나" | "으냐는군" | "으냐더군" | "으냐더군요" | "으냐면"
            )
    }) {
        return;
    }
    if p.morphs.first().is_some_and(|m| {
        matches!(
            m.form.as_str(),
            "다며"
                | "다느니"
                | "느냐느니"
                | "으냐느니"
                | "다면서"
                | "느냐"
                | "느냐고"
                | "으냐고"
                | "느냔다"
                | "으냔다"
                | "단다"
                | "대"
                | "느냬"
                | "으냬"
                | "다지"
                | "다죠"
                | "다지만"
                | "다니까"
                | "느냐지만"
                | "느냐니까"
                | "으냐지만"
                | "으냐니까"
                | "느니라"
                | "느냐며"
                | "느냐면서"
                | "느냐니"
                | "으냐니"
                | "으냔"
                | "느냔"
                | "으냐며"
                | "으냐면서"
                | "느냐는"
                | "으냐는"
                | "답니다"
                | "는답니다"
                | "다네"
                | "는다네"
                | "다는데"
                | "는다는데"
                | "다던"
                | "다던데"
                | "으냐던데"
                | "다거나"
                | "는다거나"
                | "다든가"
                | "는다든가"
        )
    }) {
        return;
    }
    // Quotation punctuation can leave an explicitly spelled copula in its
    // own token (e.g. '농민' 이란). Preserve its role without joining tokens
    // or manufacturing an omitted nominal component.
    if p.stem == "이"
        && p.morphs
            .iter()
            .find(|m| m.kind == MorphemeKind::Ending)
            .is_some_and(|m| matches!(m.form.as_str(), "란" | "라는" | "요"))
    {
        let mut a = predicate_analysis(p);
        a.lemmas[0].kind = LemmaKind::Copula;
        a.rules.push("copula.fragment".into());
        out.push(a);
    }
    if let Some(base) = p.stem.strip_suffix('이').filter(|s| !s.is_empty()) {
        let mut bases = copula_bases(base);
        // Preserve the separate particle + explicit-copula path. This does
        // not license arbitrary particles before an omitted copula.
        nominals(base, 5, false, &[], &mut bases);
        for mut a in bases {
            a.lemmas.push(lemma("이다", LemmaKind::Copula));
            append_predicate_morphs(&mut a, p);
            a.rules.extend(p.rules.clone());
            a.rules.push("copula".into());
            if p.copula_contracted
                && let Some(rule) = crate::pronunciation::assumption(base, 2)
            {
                a.rules.push(rule.into());
            }
            out.push(a);
        }
    }
    // The 라 family reconstructs 이 at its boundary; 다 permits omission here.
    if p.morphs.len() == 1 && coda(&p.stem) == Some(0) && p.morphs[0].form == "다" {
        for mut a in copula_bases(&p.stem) {
            a.lemmas.push(lemma("이다", LemmaKind::Copula));
            append_predicate_morphs(&mut a, p);
            a.rules.extend(p.rules.clone());
            a.rules.push("copula.zero".into());
            out.push(a);
        }
    }
}

fn particle_allowed(
    class: u8,
    form: &str,
    stage: u8,
    after_case: bool,
    suffixes: &[Morpheme],
) -> bool {
    // Designation particles have different inner boundaries. The long 은
    // forms preserve the base particle's licenses, not unrestricted stacking.
    if let Some(outer) = suffixes.first().map(|m| m.form.as_str()) {
        let allowed = match outer {
            "ㄹ랑" | "ㄹ랑은" => matches!(form, "에" | "에서" | "서"),
            "설랑" | "설랑은" => form == "에",
            "을랑" | "을랑은" | "일랑" | "일랑은" | "에설랑" => false,
            _ => true,
        };
        if !allowed {
            return false;
        }
    }
    if suffixes
        .first()
        .is_some_and(|m| matches!(m.form.as_str(), "다" | "다가"))
        && !matches!(
            form,
            "에" | "에서" | "서" | "에게" | "게" | "한테" | "께" | "로" | "으로"
        )
    {
        return false;
    }
    // The new focus particles permit nominal/adverbial bases, not a subject
    // or object case phrase. In particular 조금이나마 is not 조금 + 이 + 나마.
    if suffixes.first().is_some_and(|m| {
        matches!(
            m.form.as_str(),
            "커녕"
                | "란"
                | "이란"
                | "이라든가"
                | "이라든지"
                | "치고"
                | "치고는"
                | "치고서"
                | "토록"
                | "마냥"
                | "깨나"
                | "게로"
                | "에게로"
                | "한테로"
        )
    }) || (matches!(form, "이" | "가" | "을" | "를")
        && suffixes.iter().any(|m| {
            adverbial_focus_particle(&m.form)
                || matches!(m.form.as_str(), "든가" | "이든가" | "이라야만" | "라야만")
        }))
    {
        return false;
    }
    // A choice particle may occupy an inner or outer slot, but the two
    // slots do not license repeating the same particle family.
    if let Some(family) = choice_particle(form)
        && suffixes
            .iter()
            .any(|m| choice_particle(&m.form) == Some(family))
    {
        return false;
    }
    let outer = suffixes.first().map(|m| m.form.as_str());
    class < stage
        || (after_case && form == "만")
        || (outer == Some("만")
            && (matches!(form, "까지" | "부터") || source_particle_prefix(form).is_some()))
        || (outer == Some("의") && matches!(class, 2 | 3) && form != "의")
        || outer.is_some_and(|outer| range_case_link(form, outer))
        || outer.is_some_and(|outer| mada_case_link(form, outer))
        || outer.is_some_and(|outer| additive_particle_link(form, outer))
        || outer.is_some_and(|outer| comparison_case_link(form, outer))
}

// NIKL's 학교에서처럼(만), KAIST's 전에처럼, and locative short 서.
// 같이 after a case phrase is a separate adverb, not this particle chain.
fn comparison_case_link(inner: &str, outer: &str) -> bool {
    outer == "처럼" && matches!(inner, "에" | "에서" | "서")
}

// Concrete additive combinations in Wei (2020), examples 31 and 35.
// Do not turn the source's broad case/auxiliary categories into free ordering.
fn additive_particle_link(inner: &str, outer: &str) -> bool {
    matches!(
        (inner, outer),
        ("까지", "조차" | "마저") | ("조차" | "마저", "가" | "를")
    )
}

// Source-attested case marking after a range particle. These pairs cross
// the usual case-before-focus stages; they do not reorder every particle.
fn range_case_link(inner: &str, outer: &str) -> bool {
    let inner = if source_particle_prefix(inner).is_some() {
        "부터"
    } else {
        inner
    };
    let outer = source_particle_prefix(outer).map_or(outer, |(form, _)| form);
    matches!(
        (inner, outer),
        ("까지", "가" | "를" | "에" | "로") | ("부터", "가")
    )
}

// Lee (2025), printed p.70, explicitly places modern 마다 before adverbial
// case particles. Recover the observed KAIST 마다+에 edge while preserving
// the nominal left boundary and the surrounding ordinary particle stages.
fn mada_case_link(inner: &str, outer: &str) -> bool {
    inner == "마다" && outer == "에"
}

// A bundled source particle has two boundaries: 부터 governs what follows,
// while its case prefix governs what may precede it. Preserve the same stage
// and reviewed exceptions as the existing split path (e.g. 만+으로+부터).
fn source_particle_prefix(form: &str) -> Option<(&'static str, u8)> {
    match form {
        "으로부터" => Some(("으로", 2)),
        "로부터" => Some(("로", 2)),
        "에서부터" => Some(("에서", 1)),
        "서부터" => Some(("서", 1)),
        _ => None,
    }
}

fn choice_particle(form: &str) -> Option<u8> {
    match form {
        "이나" | "나" => Some(0),
        "이라도" | "라도" => Some(1),
        "이든지" | "든지" | "이든가" | "든가" => Some(2),
        "이야" | "야" => Some(3),
        "이라든가" | "라든가" | "이라든지" | "라든지" => Some(4),
        _ => None,
    }
}

// These particles also attach to adverbial phrases. Bare 커녕 has only
// nominal attachment in its source; do not inherit the longer forms' scope.
fn adverbial_focus_particle(form: &str) -> bool {
    matches!(
        form,
        "이야말로"
            | "야말로"
            | "이나마"
            | "나마"
            | "은커녕"
            | "는커녕"
            | "라든가"
            | "라든지"
            | "이라야"
            | "라야"
            | "ㄴ들"
            | "인들"
    )
}

// Ordinary focus particles with reviewed adverbial attachment. The surrounding
// particle chain must also be adverb-compatible: this does not turn an adverb
// into a nominal before arbitrary subject/object/case marking.
fn ordinary_adverbial_particle(form: &str) -> bool {
    matches!(form, "도" | "은" | "는" | "만" | "까지" | "부터")
}

// These case-shaped emphasis uses are lexical, unlike ordinary focus
// particles. KRDict gives 도대체가, 맘껏을/매번을/매일을 and 빨리를;
// NIKL also gives 곧이를. Do not infer arbitrary adverb case marking.
fn emphatic_adverb_case(base: &str, form: &str) -> bool {
    matches!(
        (base, form),
        ("도대체", "가") | ("맘껏" | "매번" | "매일", "을") | ("빨리" | "곧이", "를")
    )
}

fn adverbial_particle_chain(morphemes: &[Morpheme]) -> bool {
    morphemes.iter().all(|m| {
        ordinary_adverbial_particle(&m.form)
            || matches!(m.form.as_str(), "요" | "들")
            || choice_particle(&m.form).is_some_and(|family| family != 4)
            || adverbial_focus_particle(&m.form)
    })
}

// Closed pronoun paradigms supplement productive ㄴ/ㄹ attachment. The old
// bare 거/것 representations remain available for compatibility; expanded
// demonstratives use the case allomorph appropriate to their recovered noun.
fn pronoun_particles(word: &str) -> Vec<(&str, &'static str, u8, &'static str)> {
    let mut out = vec![];
    for (surface, base, form, class) in [
        ("내가", "나", "가", 1),
        ("네가", "너", "가", 1),
        ("제가", "저", "가", 1),
        ("누가", "누구", "가", 1),
        ("내", "나", "의", 2),
        ("네", "너", "의", 2),
        ("제", "저", "의", 2),
    ] {
        if word == surface {
            out.push((base, form, class, "pronoun"));
        }
    }
    for (surface, form, class) in [("게", "이", 1), ("건", "는", 4), ("걸", "를", 1)] {
        if word == surface {
            for base in ["거", "것"] {
                out.push((base, form, class, "nominal.contraction"));
            }
        }
    }
    for (prefix, short, full) in [
        ("이", "이거", "이것"),
        ("그", "그거", "그것"),
        ("저", "저거", "저것"),
    ] {
        if let Some(tail) = word.strip_prefix(prefix) {
            let pair = match tail {
                "게" => Some(("가", "이", 1)),
                "건" => Some(("는", "은", 4)),
                "걸" => Some(("를", "을", 1)),
                _ => None,
            };
            if let Some((s, f, class)) = pair {
                out.push((short, s, class, "pronoun.contraction"));
                out.push((full, f, class, "pronoun.contraction"));
            }
        }
    }
    if word == "뭘" {
        out.push(("뭐", "를", 1, "pronoun.contraction"));
        out.push(("무엇", "을", 1, "pronoun.contraction"));
    }
    out
}

struct ParticleRecovery {
    base: String,
    form: &'static str,
    class: u8,
    contraction: Option<&'static str>,
    pronunciation: Option<&'static str>,
}

/// Suffix peeling is acyclic: each particle consumes input, decreases a grammar
/// stage, or removes a coda before descending to a lower stage. No cutoff.
fn nominals(
    word: &str,
    stage: u8,
    after_case: bool,
    suffixes: &[Morpheme],
    out: &mut Vec<Analysis>,
) {
    for (base, form, class, rule) in pronoun_particles(word) {
        if particle_allowed(class, form, stage, after_case, suffixes) {
            let mut morphs = vec![morph(form, MorphemeKind::Particle)];
            morphs.extend_from_slice(suffixes);
            out.push(Analysis {
                lemmas: vec![lemma(base, LemmaKind::Nominal)],
                morphemes: morphs,
                rules: vec![rule.into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
    }
    let mut recoveries: Vec<_> = grammar::particles()
        .iter()
        .filter_map(|p| {
            let base = word.strip_suffix(p.form)?;
            let pronunciation = crate::pronunciation::assumption(base, p.condition);
            (grammar::particle_matches(base, p.condition) || pronunciation.is_some()).then(|| {
                ParticleRecovery {
                    base: base.into(),
                    form: p.form,
                    class: p.class,
                    contraction: None,
                    pronunciation,
                }
            })
        })
        .collect();
    if let Some(base) = word.strip_suffix("커녕")
        && let Some((_, v, 4)) = last(base)
    {
        recoveries.push(ParticleRecovery {
            base: replace_last(base, v, 0).unwrap(),
            form: "는커녕",
            class: 4,
            contraction: Some("particle.contraction.nkeonyeong"),
            pronunciation: None,
        });
    }
    for (tail, coda, form, class) in [
        ("들", 4, "ㄴ들", 4),
        ("랑", 8, "ㄹ랑", 3),
        ("랑은", 8, "ㄹ랑은", 4),
    ] {
        if let Some(base) = word.strip_suffix(tail)
            && let Some((_, vowel, t)) = last(base)
            && t == coda
        {
            recoveries.push(ParticleRecovery {
                base: replace_last(base, vowel, 0).unwrap(),
                form,
                class,
                contraction: Some("particle.coda"),
                pronunciation: None,
            });
        }
    }
    if let Some((_, v, t @ (4 | 8))) = last(word) {
        let base = replace_last(word, v, 0).unwrap();
        if t == 4 {
            recoveries.push(ParticleRecovery {
                base,
                form: "는",
                class: 4,
                contraction: Some("particle.contraction.n"),
                pronunciation: None,
            });
        } else {
            // Object ㄹ and emphatic ㄹ after an adverbial particle use
            // different chain slots, but share the canonical display form 를.
            for class in [1, 4] {
                recoveries.push(ParticleRecovery {
                    base: base.clone(),
                    form: "를",
                    class,
                    contraction: Some("particle.contraction.l"),
                    pronunciation: None,
                });
            }
        }
    }
    for particle in recoveries {
        if !particle_allowed(particle.class, particle.form, stage, after_case, suffixes) {
            continue;
        }
        let base = particle.base.as_str();
        let mut morphs = vec![morph(particle.form, MorphemeKind::Particle)];
        morphs.extend_from_slice(suffixes);
        let start = out.len();
        let emphatic_case =
            emphatic_adverb_case(base, particle.form) && adverbial_particle_chain(suffixes);
        let additive_adverb = particle.form == "조차"
            && matches!(base, "잠깐" | "조금" | "천천히")
            && adverbial_particle_chain(suffixes);
        // Only reviewed adverb-compatible particles. Subject/object marking
        // must not mistake this adverbial path for a nominalization.
        if adverbial_particle_chain(&morphs) || emphatic_case {
            for mut a in adverb_derivations(base) {
                a.morphemes.extend(morphs.clone());
                a.rules.push("particle".into());
                if emphatic_case {
                    a.rules.push("particle.adverbial_case".into());
                }
                out.push(a);
            }
        }
        let enumerative_da = particle.class == 4 && matches!(particle.form, "다" | "이다");
        let emphatic_adverbial = !enumerative_da && matches!(particle.form, "다" | "다가");
        // Only the reviewed location/direction senses license a bare 다/다가
        // base. Other lexical adverbials require a separate semantic inventory.
        if emphatic_adverbial {
            let kind = match base {
                "여기" | "거기" | "저기" | "어디" => Some(LemmaKind::Nominal),
                "이리" | "그리" | "저리" => Some(LemmaKind::Adverbial),
                _ => None,
            };
            if let Some(kind) = kind {
                out.push(Analysis {
                    lemmas: vec![lemma(base, kind)],
                    morphemes: morphs.clone(),
                    rules: vec!["particle".into()],
                    unchanged: false,
                    spelling_paths: Vec::new(),
                });
            }
        }
        // 마는 is post-ending; emphatic 다/다가 need the bases above or an
        // explicit case phrase. None license arbitrary nominal suffix peeling.
        if particle.form != "마는" && !emphatic_adverbial {
            for mut a in nominal_bases(base) {
                a.morphemes.extend(morphs.clone());
                a.rules.push("particle".into());
                out.push(a);
            }
        }
        let flexible = particle.contraction.is_some_and(|r| r != "particle.coda")
            || matches!(particle.form, "요" | "들");
        if flexible
            || choice_particle(particle.form).is_some_and(|family| family != 4)
            || adverbial_focus_particle(particle.form)
        {
            out.push(Analysis {
                lemmas: vec![lemma(base, LemmaKind::Adverbial)],
                morphemes: morphs.clone(),
                rules: vec!["particle".into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        } else if (ordinary_adverbial_particle(particle.form) && adverbial_particle_chain(&morphs))
            || emphatic_case
            || additive_adverb
        {
            out.push(Analysis {
                lemmas: vec![lemma(base, LemmaKind::Adverbial)],
                morphemes: morphs.clone(),
                rules: vec![
                    "particle".into(),
                    if additive_adverb {
                        "particle.additive_adverb"
                    } else if emphatic_case {
                        "particle.adverbial_case"
                    } else {
                        "particle.adverbial_focus"
                    }
                    .into(),
                ],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
        // Nominalizations accept ordinary particles; connective/final endings
        // have separate, explicit licenses for the newly supported particles.
        let ending = if flexible
            || question_clause_particle(particle.form)
            || matches!(
                particle.form,
                "은" | "는"
                    | "가"
                    | "를"
                    | "도"
                    | "만"
                    | "마는"
                    | "나"
                    | "라도"
                    | "든지"
                    | "든가"
                    | "야"
                    | "나마"
                    | "부터"
                    | "보다"
                    | "만치"
                    | "만큼"
                    | "조차"
                    | "마저"
                    | "밖에"
                    | "ㄹ랑"
                    | "ㄹ랑은"
                    | "설랑"
                    | "설랑은"
            ) {
            PredicateEnd::BeforeParticle(particle.form)
        } else {
            PredicateEnd::Nominalized
        };
        if !emphatic_adverbial {
            with_auxiliaries(base, ending, |p| {
                let nominalized = PredicateEnd::Nominalized.accepts(&p);
                let future_question = p.morphs.last().is_some_and(|m| m.form == "을지");
                let quoted_question = p
                    .morphs
                    .last()
                    .is_some_and(|m| question_clause_particle_boundary(&m.form, particle.form));
                let concessive = matches!(particle.form, "만" | "마는")
                    && p.morphs.last().is_some_and(|m| concessive_ending(&m.form));
                for mut a in expand_predicate(&p) {
                    a.morphemes.extend(morphs.clone());
                    a.rules.push("particle".into());
                    if quoted_question {
                        a.rules.push("particle.quoted_question".into());
                    }
                    if nominalized {
                        a.rules.push("nominalization".into());
                    }
                    if future_question {
                        a.rules.push("particle.future_question".into());
                    }
                    if concessive {
                        a.rules.push("particle.concessive".into());
                    }
                    if particle.form == "밖에" && !nominalized {
                        a.rules.push("particle.quoted_restrictive".into());
                    }
                    if matches!(particle.form, "조차" | "마저") && !nominalized {
                        a.rules.push("particle.additive_connective".into());
                    }
                    if matches!(particle.form, "만치" | "만큼")
                        && p.morphs.last().is_some_and(|m| m.form == "어서")
                    {
                        a.rules.push("particle.comparison_seo".into());
                    }
                    out.push(a);
                }
            });
        }
        let inner_class =
            source_particle_prefix(particle.form).map_or(particle.class, |(_, class)| class);
        let next = if after_case && particle.form == "만" {
            1
        } else {
            inner_class
        };
        // Enumerative 다/이다 follows a nominal, not a preceding case phrase.
        if particle.form != "마는" && !enumerative_da {
            nominals(
                base,
                next,
                inner_class == 1 || inner_class == 2,
                &morphs,
                out,
            );
        }
        for a in &mut out[start..] {
            if suffixes
                .first()
                .is_some_and(|m| comparison_case_link(particle.form, &m.form))
            {
                a.rules.push("particle.comparison_case".into());
            }
            if suffixes
                .first()
                .is_some_and(|m| additive_particle_link(particle.form, &m.form))
            {
                a.rules.push("particle.additive_chain".into());
            }
            if suffixes
                .first()
                .is_some_and(|m| range_case_link(particle.form, &m.form))
            {
                a.rules.push("particle.range_case".into());
            }
            if suffixes
                .first()
                .is_some_and(|m| mada_case_link(particle.form, &m.form))
            {
                a.rules.push("particle.mada_case".into());
            }
            if let Some(rule) = particle.pronunciation {
                a.rules.push(rule.into());
            }
            if let Some(rule) = particle.contraction {
                a.rules.push(rule.into());
            }
            match particle.form {
                "요" => a.rules.push("particle.polite".into()),
                "치고" | "치고는" | "치고서" => a.rules.push("particle.chigo".into()),
                "만치" | "마냥" | "토록" => a.rules.push("particle.comparison_extent".into()),
                "들" => a.rules.push("particle.distributive".into()),
                "다" | "이다" if enumerative_da => {
                    a.rules.push("particle.enumerative_da".into());
                }
                "다" | "다가" => a.rules.push("particle.emphatic_adverbial".into()),
                "에다" | "에다가" | "에게다" | "에게다가" | "한테다" | "한테다가" | "로다가"
                | "으로다가" => {
                    a.rules.push("particle.emphatic_destination".into());
                }
                "이든가" | "든가" | "이라든가" | "라든가" | "이라든지" | "라든지" =>
                {
                    a.rules.push("particle.enumerative".into());
                }
                _ => (),
            }
            if matches!(
                particle.form,
                "보고" | "더러" | "게" | "게서" | "에게다" | "에게다가" | "한테다" | "한테다가"
            ) {
                a.rules.push("particle.recipient".into());
            }
        }
        // Preserve NIKL's explicit compound decompositions without allowing
        // arbitrary focus particles to cross the ordering stages. The longer
        // (이)라야만 entries retain their nominal attachment scope.
        let components = match particle.form {
            "에야" => Some(["에", "야"]),
            "이라야만" => Some(["이라야", "만"]),
            "라야만" => Some(["라야", "만"]),
            _ => None,
        };
        if let Some([first, second]) = components {
            let end = out.len();
            for i in start..end {
                let mut split = out[i].clone();
                let slot = split.morphemes.len() - suffixes.len() - 1;
                debug_assert_eq!(split.morphemes[slot].form, particle.form);
                for path in &mut split.spelling_paths {
                    for r in path {
                        if r.morpheme_index > slot {
                            r.morpheme_index += 1;
                        }
                    }
                }
                split.morphemes.splice(
                    slot..=slot,
                    [
                        morph(first, MorphemeKind::Particle),
                        morph(second, MorphemeKind::Particle),
                    ],
                );
                out.push(split);
            }
        }
    }
}

fn aux_allowed(stem: &str, connector: &str) -> bool {
    match connector {
        "어" => matches!(
            stem,
            "보" | "주"
                | "드리"
                // NIKL 2024-12-10/16 confirms the reaching-state use. The
                // KRDict third-sense 고 note conflicts with its 어 examples.
                | "들"
                | "버리"
                | "놓"
                | "두"
                | "가"
                | "오"
                | "지"
                | "있"
                | "내"
                | "대"
                | "계시"
                | "나가"
                | "나"
                | "가지"
                | "갖"
                | "달"
                | "마지아니하"
                | "마지않"
                | "먹"
                | "버릇하"
                | "빠지"
                | "쌓"
                | "재끼"
                | "젖히"
                | "죽"
                | "치우"
                | "터지"
                | "하"
        ),
        "고" => matches!(
            stem,
            "있" | "싶" | "말" | "계시" | "나" | "들" | "보" | "자빠지" | "하"
        ),
        "지" => matches!(stem, "않" | "못하" | "말" | "아니하"),
        "게" => matches!(stem, "되" | "하" | "생기"),
        // NIKL explicitly licenses emphatic causative 하다; the original
        // KAIST rows independently attest 되다. Other 게 auxiliaries require
        // their own connector evidence rather than automatic extrapolation.
        "게끔" => matches!(stem, "되" | "하"),
        "어야" => stem == "하",
        "은" | "는" => matches!(stem, "듯하" | "듯싶" | "양하" | "척하" | "체하"),
        "을" => matches!(stem, "듯하" | "듯싶" | "만하" | "법하" | "뻔하" | "성싶"),
        "음" => stem == "직하",
        "으려" | "으려고" => matches!(stem, "들" | "하"),
        "기로" | "자고" => stem == "들",
        "다" | "다가" => matches!(stem, "보" | "못하") || (connector == "다" && stem == "싶"),
        "으려다" | "으려다가" => stem == "보",
        "어다" | "어다가" => matches!(stem, "주" | "드리" | "놓" | "두" | "달"),
        "으려나" => stem == "보",
        "으려니" => matches!(stem, "하" | "싶"),
        "는가" | "은가" | "던가" | "나" | "을까" => matches!(stem, "보" | "싶"),
        "으면" => matches!(stem, "하" | "싶"),
        "기도" | "기는" | "기만" | "고자" => stem == "하",
        _ => false,
    }
}

// Lexical 말다 (KRDict 69296), distinct from auxiliary 72580. Paired
// alternatives keep their own two endings, including asymmetric 을지 + 지.
fn lexical_mal_link(left: &Predicate, right: &Predicate, branch_end: Option<&str>) -> bool {
    if right.stem != "말" || !right.leading_lemmas.is_empty() {
        return false;
    }
    let Some(last) = left
        .morphs
        .last()
        .filter(|m| m.kind == MorphemeKind::Ending)
    else {
        return false;
    };
    if right.rules.iter().any(|r| r == "irregular.mal") {
        return false;
    }
    if matches!(last.form.as_str(), "다" | "다가" | "으려다" | "으려다가") {
        return true;
    }
    // The complete entry directly attests 슬퍼 말다. It supplies no general
    // -어 complement license for arbitrary predicates (e.g. 먹어 말다).
    // Keep this attested lexical construction distinct from auxiliary 말다.
    if last.form == "어" {
        return left.stem == "슬프" && left.following.is_empty();
    }
    let paired = |form: &str| {
        // Polite 요 may have a bundled ending representation. The split
        // particle representation is recovered separately by nominals().
        let form = form.strip_suffix('요').unwrap_or(form);
        match last.form.as_str() {
            "을까" | "든지" | "든" | "거나" | "거니" | "건" => form == last.form,
            "을지" => form == "지",
            // Both allomorph entries license paired alternatives. Own right
            // inflection is checked separately below; a following chain may
            // close with either allomorph on its own final predicate.
            "나" | "으나" => matches!(form, "나" | "으나"),
            _ => false,
        }
    };
    let own_ending = right
        .morphs
        .last()
        .filter(|m| m.kind == MorphemeKind::Ending);
    let own_pair = own_ending.is_some_and(|m| paired(&m.form))
        && right.morphs[..right.morphs.len() - 1]
            .iter()
            .all(|m| m.kind == MorphemeKind::Prefinal)
        // Bare 말 and honorific 시 take 나. The paired recovery must not
        // promote a generic 으나 hypothesis for their open/ㄹ boundary.
        // Past/modal consonantal prefinals take 으나 (KRDict 80160).
        && (own_ending.is_none_or(|m| m.form.strip_suffix('요').unwrap_or(&m.form) != "으나")
            || right.morphs.iter().rev().nth(1).is_some_and(|m| {
                matches!(m.form.as_str(), "었" | "겠" | "어야겠")
            }));
    // Reuse the right predicate's existing inflection recovery. A validated
    // following chain can close the alternative too (말아 버리거나). Keep
    // immediate paired links available before further auxiliaries, preserving
    // readings such as 할까 말까 싶다 without a whole-chain ending ban.
    own_pair
        || (right.connector
            && !own_ending.is_some_and(|m| paired(&m.form))
            && branch_end.is_some_and(paired))
}

#[derive(Clone, Copy)]
struct PredicateLink {
    role: LemmaKind,
    rule: &'static str,
    paired_branch: bool,
}

// KRDict 89858 senses 17/18/19/21. Each particle belongs to the
// immediately preceding connector; the cause/concession ending 기로 is not
// used to manufacture the decision construction 기 + 로.
fn extended_doeda_link(left: &Predicate, right: &Predicate) -> Option<PredicateLink> {
    if right.stem != "되"
        || !(right.leading_lemmas.is_empty()
            || (right.leading_lemmas.len() == 1
                && right.leading_lemmas[0] == lemma("안", LemmaKind::Adverbial)))
    {
        return None;
    }
    let index = left
        .morphs
        .iter()
        .rposition(|m| m.kind == MorphemeKind::Ending)?;
    let connector = left.morphs[index].form.as_str();
    let particles = &left.morphs[index + 1..];
    let particle = |form: &str| {
        particles.len() == 1
            && particles[0].kind == MorphemeKind::Particle
            && particles[0].form == form
    };
    let scheduled =
        (connector == "도록" && particles.is_empty()) || (connector == "기" && particle("로"));
    let extended = (matches!(connector, "어야" | "으면" | "어도") && particles.is_empty())
        || (connector == "어" && (particle("야") || particle("도")))
        || (!right.leading_lemmas.is_empty()
            && ((connector == "어서" && particle("는"))
                || (connector == "어서는" && particles.is_empty())));
    if scheduled {
        Some(PredicateLink {
            role: LemmaKind::Predicate,
            rule: "lexical.doeda.extended",
            paired_branch: false,
        })
    } else if extended {
        Some(PredicateLink {
            role: LemmaKind::Auxiliary,
            rule: "auxiliary.doeda.extended",
            paired_branch: false,
        })
    } else {
        None
    }
}

fn predicate_link(
    left: &Predicate,
    right: &Predicate,
    branch_end: Option<&str>,
) -> Option<PredicateLink> {
    if lexical_mal_link(left, right, branch_end) {
        Some(PredicateLink {
            role: LemmaKind::Predicate,
            rule: "lexical.mal.complement",
            paired_branch: !lexical_mal_link(left, right, None),
        })
    } else if let Some(link) = extended_doeda_link(left, right) {
        Some(link)
    } else if right.leading_lemmas.is_empty() && auxiliary_link(left, right) {
        Some(PredicateLink {
            role: LemmaKind::Auxiliary,
            rule: "auxiliary",
            paired_branch: false,
        })
    } else {
        None
    }
}

// Source-specific restrictions which need more than the left ending's name.
fn auxiliary_link(left: &Predicate, right: &Predicate) -> bool {
    let Some(index) = left
        .morphs
        .iter()
        .rposition(|m| m.kind == MorphemeKind::Ending)
    else {
        return false;
    };
    let connector = left.morphs[index].form.as_str();
    let particles = &left.morphs[index + 1..];
    let bare_link = if particles.is_empty() {
        aux_allowed(&right.stem, connector)
    } else if particles.len() == 1 {
        match particles[0].form.as_str() {
            "도" | "만" | "들" => {
                (connector == "기" && right.stem == "하" && particles[0].form != "들")
                    || (before_particle(connector, &particles[0].form)
                        && aux_allowed(&right.stem, connector))
            }
            "는" => {
                (right.stem == "하" && matches!(connector, "고" | "기"))
                    // Contrastive 고는 싶다 (also contracted 곤 싶다).
                    || (right.stem == "싶" && connector == "고")
                    // Contrastive 고는/어는 있다 and honorific 계시다.
                    // Keep the connector's left-class and inflection checks.
                    || (matches!(right.stem.as_str(), "있" | "계시")
                        && matches!(connector, "고" | "어"))
                    || (connector == "지" && aux_allowed(&right.stem, connector))
            }
            "나" => right.stem == "하" && connector == "기",
            "가" | "를" => {
                before_particle(connector, &particles[0].form)
                    && aux_allowed(&right.stem, connector)
            }
            "야" => {
                (right.stem == "하" && connector == "기")
                    || (right.stem == "말" && connector == "고")
            }
            _ => false,
        }
    } else {
        false
    };
    if !bare_link {
        return false;
    }
    // A final rhetorical -(으)려고 permits past (풀었으려고?), but the
    // direct finite intention construction licenses only honorific 시 here.
    // Inspect this connector's owner, preserving earlier and right-hand tense.
    if connector == "으려고"
        && finite_intention_auxiliary(&right.stem, &right.morphs)
        && left.morphs[..index]
            .iter()
            .rev()
            .take_while(|m| m.kind != MorphemeKind::Ending)
            .any(|m| m.kind == MorphemeKind::Prefinal && !honorific_prefinal(&m.form))
    {
        return false;
    }
    // Necessity/intention belongs outside progressive 고 있다/계시다:
    // 먹고 있어야겠다, not 먹어야겠고 있다. Inspect only the predicate
    // immediately before this connector, not earlier members of the chain.
    if connector == "고"
        && matches!(right.stem.as_str(), "있" | "계시")
        && left.morphs[..index]
            .iter()
            .rev()
            .take_while(|m| m.kind != MorphemeKind::Ending)
            .any(|m| m.form == "어야겠")
    {
        return false;
    }
    // Short 마 is prohibitive; it cannot replace completive 고 말다 or act
    // as a connective 어. Full 말다 remains available in questions, wishes,
    // quotations and embedded clauses: mood cannot be decided from this token.
    if right.rules.iter().any(|r| r == "irregular.mal") && connector != "지" {
        return false;
    }
    // -었으면 하다/싶다 are wishes, rather than unrestricted 으면 links.
    if connector == "으면" && !left.morphs[..index].iter().any(|m| m.form == "었") {
        return false;
    }
    let right_forms: Vec<_> = right.morphs.iter().map(|m| m.form.as_str()).collect();
    match right.stem.as_str() {
        "가지" | "갖" => right_forms == ["고"],
        // 달다 has the restricted request paradigm 달라/다오. Quoted
        // requests also use the reviewed command endings (e.g. the source
        // entry's 도와 달라며). Do not inherit ordinary tense or honorific
        // slots, factual 라-family endings, or arbitrary following endings.
        "달" => matches!(
            right_forms.as_slice(),
            ["으라"
                | "으라고"
                | "으라는"
                | "으란"
                | "으래"
                | "으란다"
                | "으라지"
                | "으라죠"
                | "으라지만"
                | "으라니까"
                | "으라면"
                | "으랍니다"
                | "으라네"
                | "으라는데"
                | "으라더니"
                | "으라던"
                | "으라던데"
                | "으라며"
                | "으라면서"
                | "으라니"
                | "으라느니"
                | "으라거나"
                | "으라는구나"
                | "으라는군"
                | "으라더군"
                | "으라더군요"
                | "오"]
        ),
        "보" if matches!(connector, "다" | "다가" | "으려다" | "으려다가") => {
            matches!(right_forms.as_slice(), ["으니" | "으면"])
        }
        _ => true,
    }
}

// An internal particle consumes input before a link is considered. Keep this
// bounded to one reviewed slot and leave the packed search iterative.
fn connector_predicates(word: &str) -> Vec<Predicate> {
    let mut out = predicates(word);
    for particle in ["들", "도", "만", "는", "야", "나", "가", "를", "로"] {
        if let Some(base) = word.strip_suffix(particle) {
            for mut p in predicates(base) {
                let ending = &p.morphs.last().unwrap().form;
                if p.connector
                    && ((particle == "로" && ending == "기")
                        || (particle != "로"
                            && (ending == "기" || before_particle(ending, particle))))
                {
                    p.morphs.push(morph(particle, MorphemeKind::Particle));
                    p.rules.push("particle".into());
                    out.push(p);
                }
            }
        }
    }
    for (short, ending) in [('곤', "고"), ('진', "지")] {
        if let Some(base) = word.strip_suffix(short) {
            for mut p in predicates(&format!("{base}{ending}")) {
                if p.morphs.last().is_some_and(|m| m.form == ending) {
                    p.morphs.push(morph("는", MorphemeKind::Particle));
                    p.rules
                        .extend(["particle".into(), "particle.contraction.n".into()]);
                    out.push(p);
                }
            }
        }
    }
    // Emphatic ㄹ is the contracted spelling of 를 after the same licensed
    // connectors. Preserve full and contracted internal-particle paths.
    if let Some((_, v, 8)) = last(word) {
        let base = replace_last(word, v, 0).unwrap();
        for mut p in predicates(&base) {
            if p.connector
                && p.morphs
                    .last()
                    .is_some_and(|m| before_particle(&m.form, "를"))
            {
                p.morphs.push(morph("를", MorphemeKind::Particle));
                p.rules
                    .extend(["particle".into(), "particle.contraction.l".into()]);
                out.push(p);
            }
        }
    }
    out
}

// Negative 안 is recovered only on the right of a validated complement.
// Keeping it out of prefix bases prevents an unrelated following auxiliary
// from manufacturing a stand-alone adverb + 되다 split (안되겠지만).
fn predicate_tails(word: &str) -> Vec<Predicate> {
    let mut out = connector_predicates(word);
    if let Some(base) = word.strip_prefix("안") {
        for mut p in connector_predicates(base) {
            if p.stem == "되" {
                p.leading_lemmas.push(lemma("안", LemmaKind::Adverbial));
                p.rules.push("doeda.negative_bridge".into());
                out.push(p);
            }
        }
    }
    out
}

#[derive(Clone, Copy)]
enum PredicateEnd {
    Any,
    Nominalized,
    CopulaBase,
    BeforeParticle(&'static str),
}
impl PredicateEnd {
    fn accepts(self, p: &Predicate) -> bool {
        matches!(self, Self::Any)
            || p.morphs.last().is_some_and(|m| {
                if matches!(self, Self::CopulaBase) {
                    return matches!(m.form.as_str(), "기" | "음" | "어서");
                }
                if matches!(self, Self::BeforeParticle("마는")) {
                    return concessive_ending(&m.form);
                }
                matches!(
                    m.form.as_str(),
                    "기" | "음"
                        | "는가"
                        | "은가"
                        | "는지"
                        | "은지"
                        | "던가"
                        | "던지"
                        | "을지"
                        | "을는지"
                        | "으려는가"
                        | "으려는지"
                ) || match self {
                    Self::BeforeParticle(form) => before_particle(&m.form, form),
                    _ => false,
                }
            })
    }
}

// KRDict's native examples attest case-bearing questions (하느냐에,
// 먹느냐가, 취업이냐의, 더운밥이냐를, 이루느냐보다); KAIST also
// attests 하느냐와. Native 넣느냐는/붙느냐는 also attest a topic-bearing
// question clause; retain the separate quoted-ending bundle alternatives.
// The modern 2016 NARS attestation 내느냐도 additionally licenses additive 도.
// These clauses retain their question ending, rather
// than acquiring an invented nominalizer or a quoted-report ending.
fn question_clause_particle(particle: &str) -> bool {
    matches!(
        particle,
        "에" | "의" | "와" | "가" | "를" | "보다" | "는" | "도"
    )
}

fn question_clause_particle_boundary(ending: &str, particle: &str) -> bool {
    matches!(ending, "냐" | "느냐" | "으냐") && question_clause_particle(particle)
}

fn concessive_ending(ending: &str) -> bool {
    matches!(
        ending,
        "다" | "는다"
            | "습니다"
            | "냐"
            | "느냐"
            | "으냐"
            | "으리까"
            | "으랴"
            | "자"
            | "지"
            | "더니"
    )
}

fn reporting_nikka(form: &str) -> bool {
    matches!(
        form,
        "다니까"
            | "는다니까"
            | "라니까"
            | "으라니까"
            | "냐니까"
            | "느냐니까"
            | "으냐니까"
            | "자니까"
            | "더라니까"
    )
}

fn short_report(form: &str) -> bool {
    matches!(
        form,
        "대" | "는대" | "래" | "으래" | "재" | "냬" | "느냬" | "으냬" | "더래"
    )
}

fn reporting_ni(form: &str) -> bool {
    matches!(
        form,
        "다니" | "는다니" | "라니" | "으라니" | "더라니" | "자니" | "냐니" | "느냐니" | "으냐니"
    )
}

fn reporting_myeo(form: &str) -> bool {
    matches!(
        form,
        "다며"
            | "는다며"
            | "라며"
            | "으라며"
            | "더라며"
            | "자며"
            | "냐며"
            | "느냐며"
            | "으냐며"
            | "다면서"
            | "는다면서"
            | "라면서"
            | "으라면서"
            | "더라면서"
            | "자면서"
            | "냐면서"
            | "느냐면서"
            | "으냐면서"
    )
}

fn reporting_go(ending: &str) -> bool {
    matches!(
        ending,
        "다고" | "는다고" | "라고" | "으라고" | "냐고" | "느냐고" | "으냐고" | "자고"
    )
}

fn before_particle(ending: &str, particle: &str) -> bool {
    if question_clause_particle_boundary(ending, particle) {
        return true;
    }
    let connective = intention_connective(ending)
        || result_connective(ending)
        || matches!(
            ending,
            "어" | "어서"
                | "어도"
                | "어야"
                | "고"
                | "고서"
                | "게"
                | "지"
                | "지만"
                | "는데"
                | "은데"
                | "던데"
                | "거든"
                | "으면"
                | "으니"
                | "으니까"
                | "으며"
                | "으면서"
                | "으므로"
                | "으려고"
                | "으려면"
                | "으려니"
                | "으려니까"
                | "으려면서"
                | "으려든지"
                | "으려"
                | "고자"
                | "느라고"
                | "도록"
                | "더라도"
                | "더니"
                | "거나"
                | "든지"
                | "자마자"
                | "라고"
                | "으라고"
                | "다고"
                | "는다고"
                | "냐고"
                | "자고"
                | "라서"
                | "라면"
                | "다면"
        );
    match particle {
        "밖에" => reporting_go(ending),
        "요" => {
            // NIKL consultation 309656 explicitly accepts both polite forms.
            activity_reason(ending)
                || short_report(ending)
                || reporting_go(ending)
                || quoted_conditional_question(ending)
                // Native 한다던데요 and NIKL teaching examples license
                // polite statement reports; other report followers stay separate.
                || matches!(ending, "다던데" | "는다던데" | "라던데" | "으라던데"
                    | "자던데" | "냐던데" | "느냐던데" | "으냐던데")
                || reporting_myeo(ending)
                || reporting_ni(ending)
                || matches!(
                    ending,
                    "은들" | "을망정" | "을지언정" | "던들" | "을라치면" | "을밖에"
                )
                || connective
                || matches!(
                    ending,
                    "군" | "구나"
                        // Direct native declarative reports, plus the explicit
                        // experience-report inference reviewed in COV-018aa.
                        | "는다는군"
                        | "다는군"
                        | "더라는군"
                        | "구먼"
                        | "는구먼"
                        | "는군"
                        | "더구먼"
                        | "다더군"
                        | "는다더군"
                        | "라더군"
                        | "으라더군"
                        | "라는군"
                        | "으라는군"
                        | "자더군"
                        // Inferred from 자고 하는군 plus NIKL 330060;
                        // optional compatibility keeps this follower Unknown.
                        | "자는군"
                        | "냐더군"
                        | "느냐더군"
                        | "으냐더군"
                        // Inferred from the quoted 하는군 contraction and
                        // NIKL 330060's terminal ending + polite particle.
                        | "냐는군"
                        | "느냐는군"
                        | "으냐는군"
                        | "로구먼"
                        | "로군"
                        | "은걸"
                        | "는걸"
                        | "던걸"
                        | "을걸"
                        | "으려나"
                        // The original novel explicitly has 그렇고말고요.
                        | "고말고"
                        | "네"
                        | "나"
                        | "니"
                        | "냐"
                        | "으냐"
                        | "더라"
                        | "으려더라"
                        | "더라고"
                        | "더군"
                        | "을까"
                        | "을게"
                        | "을래"
                        | "다니"
                        | "으되"
                        | "지마는"
                        | "다지만"
                        | "다니까"
                        | "는다지만"
                        | "는다니까"
                        | "라지만"
                        | "라니까"
                        | "으라지만"
                        | "으라니까"
                        | "냐지만"
                        | "냐니까"
                        | "느냐지만"
                        | "느냐니까"
                        | "으냐지만"
                        | "으냐니까"
                        | "자지만"
                        | "자니까"
                        | "더라지만"
                        | "더라니까"
                        | "다지"
                        | "는다지"
                        | "라지"
                        | "으라지"
                        | "다네"
                        | "는다네"
                        | "라네"
                        | "으라네"
                        | "다는데"
                        | "는다는데"
                        | "라는데"
                        | "으라는데"
                        | "더라네"
                        | "더라는데"
                )
        }
        "들" => matches!(
            ending,
            "어" | "게"
                | "지"
                | "고"
                | "라고"
                | "으라고"
                | "다고"
                | "는다고"
                | "냐고"
                | "자고"
                | "다"
                | "는다"
                | "어라"
                | "자"
                | "어요"
                | "습니다"
                | "으세요"
        ),
        "은" | "는" => connective || reporting_nikka(ending),
        // Source-listed -다는데도/-라는데도 families retain their own
        // present/command/factual licenses before concessive 도.
        "도" => {
            (reporting_myeo(ending) && ending.ends_with("면서"))
                || connective
                // Factual/copular 라 + 도 also has the bundled 라도 reading.
                // Quoted commands retain their separate canonical 으라 form.
                || ending == "라"
                || matches!(
                    ending,
                    "다는데" | "는다는데" | "라는데" | "으라는데" | "더라는데"
                )
        }
        "라도" => matches!(ending, "어" | "게" | "지" | "고"),
        // KRDict 나마 explicitly illustrates an adverbial 게 clause.
        "나마" => ending == "게",
        "나" => matches!(
            ending,
            "어" | "게" | "지" | "고" | "다" | "는다" | "라" | "으라" | "어라"
        ),
        "든지" | "든가" => matches!(ending, "다" | "는다" | "라" | "으라" | "어라"),
        "야" => matches!(ending, "어" | "어서" | "게" | "지" | "고" | "고서"),
        "부터" => matches!(ending, "어서" | "고" | "으면서"),
        "보다" => ending == "어서",
        "만치" | "만큼" => ending == "어서",
        // KAIST additionally attests 거룩하게조차. This is distinct from
        // nominalized indirect questions, accepted by PredicateEnd above.
        "조차" => matches!(ending, "어서" | "으려고" | "다가" | "게"),
        "마저" => ending == "어서",
        "만" => {
            concessive_ending(ending)
                || matches!(
                    ending,
                    "어" | "어서" | "어야" | "라야" | "게" | "고" | "고서"
                )
        }
        "마는" => concessive_ending(ending),
        "를" => matches!(ending, "어" | "게" | "지" | "고"),
        "가" => ending == "지",
        "ㄹ랑" | "ㄹ랑은" => matches!(ending, "고서" | "어서" | "지"),
        "설랑" | "설랑은" => matches!(ending, "고" | "어"),
        _ => false,
    }
}

struct AuxEdge {
    left: usize,
    tails: Rc<Vec<Predicate>>,
}
struct AuxNode {
    bases: Vec<Predicate>,
    edges: Vec<AuxEdge>,
}

// A packed prefix DAG stores only single predicates and links to shorter input.
// Expanded chains are never cached. Equal suffix strings share tail recoveries.
// Both construction and traversal are iterative, including on very long tokens.
fn with_auxiliaries(word: &str, ending: PredicateEnd, mut emit: impl FnMut(Predicate)) {
    let mut boundaries: Vec<_> = word.char_indices().map(|(i, _)| i).collect();
    boundaries.push(word.len());
    let root = boundaries.len() - 1;
    let mut nodes: Vec<Option<AuxNode>> = (0..=root).map(|_| None).collect();
    let mut tails_cache: HashMap<&str, Rc<Vec<Predicate>>> = HashMap::new();
    let mut pending = vec![root];
    while let Some(end) = pending.pop() {
        if nodes[end].is_some() {
            continue;
        }
        let accepts = |p: &Predicate| {
            if end == root {
                p.morphs
                    .last()
                    .is_some_and(|m| m.kind == MorphemeKind::Ending)
                    && ending.accepts(p)
            } else {
                p.connector
            }
        };
        let candidates = if end == root {
            predicates(&word[..boundaries[end]])
        } else {
            connector_predicates(&word[..boundaries[end]])
        };
        let bases = candidates.into_iter().filter(&accepts).collect();
        let mut edges = vec![];
        for start in 1..end {
            let right = &word[boundaries[start]..boundaries[end]];
            let tails = tails_cache.entry(right).or_insert_with(|| {
                Rc::new(
                    predicate_tails(right)
                        .into_iter()
                        .filter(|p| {
                            p.stem == "되"
                                || (p.leading_lemmas.is_empty()
                                    && (p.stem == "말"
                                        || grammar::AUXILIARY_CONNECTORS
                                            .iter()
                                            .any(|c| aux_allowed(&p.stem, c))))
                        })
                        .collect(),
                )
            });
            if tails.iter().any(&accepts) {
                edges.push(AuxEdge {
                    left: start,
                    tails: Rc::clone(tails),
                });
                if nodes[start].is_none() {
                    pending.push(start);
                }
            }
        }
        nodes[end] = Some(AuxNode { bases, edges });
    }
    // Frames enumerate one right-to-left path at a time. Every link consumes
    // input; no search-depth or candidate cutoff is needed.
    struct Frame {
        node: usize,
        base: usize,
        edge: usize,
        tail: usize,
    }
    let frame = |node| Frame {
        node,
        base: 0,
        edge: 0,
        tail: 0,
    };
    let mut frames = vec![frame(root)];
    let mut path: Vec<&Predicate> = vec![];
    while let Some(current) = frames.last_mut() {
        let node = nodes[current.node].as_ref().unwrap();
        let branch_end = path
            .first()
            .and_then(|p| p.morphs.last())
            .filter(|m| m.kind == MorphemeKind::Ending)
            .map(|m| m.form.as_str());
        let accepts = |p: &Predicate| match path.last() {
            Some(right) => p.connector && predicate_link(p, right, branch_end).is_some(),
            None => {
                p.morphs
                    .last()
                    .is_some_and(|m| m.kind == MorphemeKind::Ending)
                    && ending.accepts(p)
            }
        };
        if let Some(base) = node.bases.get(current.base) {
            current.base += 1;
            if accepts(base) {
                let mut joined = base.clone();
                // Provenance is a set, not a derivation trace. Deduplicate it
                // before materializing output, rather than retaining every step.
                let mut rules: BTreeSet<&str> = base.rules.iter().map(String::as_str).collect();
                let mut previous = base;
                for tail in path.iter().rev() {
                    let link = predicate_link(previous, tail, branch_end).unwrap();
                    if link.paired_branch {
                        rules.insert("lexical.mal.paired_branch");
                    }
                    if joined
                        .morphs
                        .last()
                        .is_some_and(|m| m.kind == MorphemeKind::Particle)
                    {
                        rules.insert("auxiliary.internal_particle");
                    }
                    joined
                        .following
                        .extend(tail.leading_lemmas.iter().map(|l| (l.text.clone(), l.kind)));
                    joined.following.push((tail.stem.clone(), link.role));
                    joined.following.extend(tail.following.iter().cloned());
                    joined
                        .spellings
                        .extend(shifted_spellings(&tail.spellings, joined.morphs.len()));
                    joined.morphs.extend(tail.morphs.iter().cloned());
                    rules.extend(tail.rules.iter().map(String::as_str));
                    rules.insert(link.rule);
                    if link.role == LemmaKind::Auxiliary {
                        rules.insert("auxiliary");
                    }
                    joined.connector = tail.connector;
                    previous = tail;
                }
                joined.rules = rules.into_iter().map(str::to_owned).collect();
                emit(joined);
            }
        } else if let Some(edge) = node.edges.get(current.edge) {
            if let Some(tail) = edge.tails.get(current.tail) {
                current.tail += 1;
                if accepts(tail) {
                    path.push(tail);
                    frames.push(frame(edge.left));
                }
            } else {
                current.edge += 1;
                current.tail = 0;
            }
        } else {
            frames.pop();
            path.pop();
        }
    }
}

fn add_lexical_doeda_roles(out: &mut Vec<Analysis>) {
    // Project only already validated, source-listed 되다 links. Original paths and
    // their evidence stay intact; nominal/copula expansion and outer endings
    // have finished, so the ordered components identify each actual owner.
    let original_count = out.len();
    for original in 0..original_count {
        let base = &out[original];
        if !base
            .lemmas
            .iter()
            .any(|l| l.kind == LemmaKind::Auxiliary && l.text == "되다")
        {
            continue;
        }
        let Some(components) = base.breakdown() else {
            continue;
        };
        let mut slots = Vec::new();
        let mut connector = None;
        for component in components {
            match component {
                crate::breakdown::Component::Lemma(i) => {
                    if base.lemmas[i].kind == LemmaKind::Auxiliary && base.lemmas[i].text == "되다"
                    {
                        let rule = if matches!(connector, Some("게" | "게끔")) {
                            Some("lexical.doeda.complement")
                        } else if matches!(
                            connector,
                            Some("어야" | "으면" | "어도" | "어" | "어서" | "어서는")
                        ) && base.rules.iter().any(|r| r == "auxiliary.doeda.extended")
                        {
                            Some("lexical.doeda.extended")
                        } else {
                            None
                        };
                        if let Some(rule) = rule {
                            slots.push((i, rule));
                        }
                    }
                    if !doeda_negative_bridge(base, i) {
                        connector = None;
                    }
                }
                crate::breakdown::Component::Morpheme(i)
                    if base.morphemes[i].kind == MorphemeKind::Ending =>
                {
                    connector = Some(base.morphemes[i].form.as_str());
                }
                _ => {}
            }
        }
        if slots.is_empty() {
            continue;
        }
        let mut variant = base.clone();

        // Binary enumeration without shifts, recursion or an arbitrary role
        // cutoff. Each link can keep its auxiliary role or take the lexical
        // alternative independently, including multiple 되다 owners.
        loop {
            let mut cursor = 0;
            while let Some(&(slot, _)) = slots.get(cursor) {
                if variant.lemmas[slot].kind == LemmaKind::Auxiliary {
                    variant.lemmas[slot].kind = LemmaKind::Predicate;
                    break;
                }
                variant.lemmas[slot].kind = LemmaKind::Auxiliary;
                cursor += 1;
            }
            if cursor == slots.len() {
                break;
            }
            let mut candidate = variant.clone();
            for &(slot, rule) in &slots {
                if candidate.lemmas[slot].kind == LemmaKind::Predicate {
                    candidate.rules.push(rule.into());
                }
            }
            if !slots.iter().any(|&(slot, rule)| {
                rule == "lexical.doeda.extended"
                    && candidate.lemmas[slot].kind == LemmaKind::Auxiliary
            }) {
                candidate.rules.retain(|r| r != "auxiliary.doeda.extended");
            }
            if !candidate
                .lemmas
                .iter()
                .any(|l| l.kind == LemmaKind::Auxiliary)
            {
                candidate.rules.retain(|r| r != "auxiliary");
            }
            if auxiliary_inflections_allowed(&mut candidate) {
                out.push(candidate);
            }
        }
    }
}

pub(crate) fn analyze(word: &str) -> Result<WordAnalysis, Error> {
    if word.is_empty() {
        return Err(Error::EmptyWord);
    }
    if word.chars().any(char::is_whitespace) {
        return Err(Error::WhitespaceInWord);
    }
    let normalized: String = word.nfc().collect();
    let mut out = vec![Analysis {
        lemmas: vec![lemma(&normalized, LemmaKind::Unclassified)],
        morphemes: vec![],
        rules: vec!["identity".into()],
        unchanged: true,
        spelling_paths: Vec::new(),
    }];
    if has_hangul(&normalized) {
        // Closing quotation punctuation can leave 라는 in its own token.
        // This conditional fragment has no recoverable nominal in this word;
        // do not invent one or use the empty base in general suffix recovery.
        if normalized == "라는" {
            out.push(Analysis {
                lemmas: vec![lemma("이다", LemmaKind::Copula)],
                morphemes: vec![morph("라는", MorphemeKind::Ending)],
                rules: vec!["copula.omitted_fragment".into(), "ending".into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
        out.extend(adverb_derivations(&normalized));
        out.extend(nominal_derivations(&normalized));
        for (suffix, vowel_only) in [
            ("이에요", false),
            ("예요", true),
            ("이야", false),
            ("야", true),
        ] {
            if let Some(base) = normalized.strip_suffix(suffix).filter(|s| !s.is_empty())
                && (!vowel_only
                    || coda(base) == Some(0)
                    || crate::pronunciation::assumption(base, 2).is_some())
            {
                for mut a in copula_bases(base) {
                    a.lemmas.push(lemma("이다", LemmaKind::Copula));
                    a.morphemes.push(morph(
                        if suffix.ends_with("요") {
                            "에요"
                        } else {
                            "야"
                        },
                        MorphemeKind::Ending,
                    ));
                    a.rules.push("copula.polite".into());
                    if vowel_only && let Some(rule) = crate::pronunciation::assumption(base, 2) {
                        a.rules.push(rule.into());
                    }
                    out.push(a);
                }
            }
        }
        // Pure non-Hangul bases do not enter predicate spelling recovery.
        // A nominal followed by omitted 이 + 다 has its own conditional path.
        if let Some(base) = normalized.strip_suffix('다')
            && let Some(rule) = crate::pronunciation::assumption(base, 2)
        {
            let mut a = Analysis {
                lemmas: vec![
                    lemma(base, LemmaKind::Nominal),
                    lemma("이다", LemmaKind::Copula),
                ],
                morphemes: vec![morph("다", MorphemeKind::Ending)],
                rules: vec!["copula.zero".into(), rule.into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            };
            // This path has the same terminal-ending provenance as a Hangul base.
            a.rules.push("ending".into());
            out.push(a);
        }
        if normalized == "아니에요" {
            out.push(Analysis {
                lemmas: vec![lemma("아니다", LemmaKind::Predicate)],
                morphemes: vec![morph("에요", MorphemeKind::Ending)],
                rules: vec!["negative_copula.polite".into()],
                unchanged: false,
                spelling_paths: Vec::new(),
            });
        }
        with_auxiliaries(&normalized, PredicateEnd::Any, |p| {
            out.extend(expand_predicate(&p));
        });
        nominals(&normalized, 7, false, &[], &mut out);
    }
    // Outer polite 요 is appended after predicate expansion. Recheck only
    // its split 어 + 요 intention paths now that the complete owner group is
    // available; canonical 어요 and the split representation share a license.
    out.retain_mut(|a| {
        !a.morphemes
            .iter()
            .any(|m| m.kind == MorphemeKind::Ending && m.form == "으려고")
            || !a.morphemes.windows(2).any(|pair| {
                pair[0].kind == MorphemeKind::Ending
                    && pair[0].form == "어"
                    && pair[1].kind == MorphemeKind::Particle
                    && pair[1].form == "요"
            })
            || auxiliary_inflections_allowed(a)
    });
    add_lexical_doeda_roles(&mut out);
    add_doeda_suffixes(&mut out);
    add_hada_suffixes(&mut out);
    add_listed_nominal_decompositions(&mut out);
    add_predicate_compounds(&mut out);
    // Noun/adverb -이 homonyms retain distinct functions despite identical
    // lemma/morpheme fields. Other semantic duplicates share rule names, but spelling paths remain
    // alternatives. A derivation with no spelling obligation subsumes others.
    type Key = (Vec<Lemma>, Vec<Morpheme>, bool, bool);
    type Evidence = (Vec<String>, Vec<Vec<SpellingRecovery>>);
    let mut unique: BTreeMap<Key, Evidence> = BTreeMap::new();
    for a in out {
        use std::collections::btree_map::Entry;
        let paths = a.spelling_paths;
        let noun_i = a.rules.iter().any(|r| r == "suffix.nominal.i");
        match unique.entry((a.lemmas, a.morphemes, a.unchanged, noun_i)) {
            Entry::Vacant(v) => {
                v.insert((a.rules, paths));
            }
            Entry::Occupied(mut o) => {
                let (rules, existing) = o.get_mut();
                rules.extend(a.rules);
                if paths.is_empty() {
                    existing.clear();
                } else if !existing.is_empty() {
                    existing.extend(paths);
                }
            }
        }
    }
    let analyses = unique
        .into_iter()
        .map(
            |((lemmas, morphemes, unchanged, _), (mut rules, mut spelling_paths))| {
                rules.sort();
                rules.dedup();
                for path in &mut spelling_paths {
                    path.sort();
                    path.dedup();
                }
                spelling_paths.sort();
                spelling_paths.dedup();
                Analysis {
                    lemmas,
                    morphemes,
                    rules,
                    unchanged,
                    spelling_paths,
                }
            },
        )
        .collect();
    Ok(WordAnalysis {
        normalized,
        analyses,
    })
}

pub(crate) fn retained_bytes(result: &WordAnalysis) -> usize {
    use std::mem::size_of;
    size_of::<WordAnalysis>()
        + result.normalized.capacity()
        + result.analyses.capacity() * size_of::<Analysis>()
        + result
            .analyses
            .iter()
            .map(|a| {
                a.lemmas.capacity() * size_of::<Lemma>()
                    + a.lemmas.iter().map(|l| l.text.capacity()).sum::<usize>()
                    + a.morphemes.capacity() * size_of::<Morpheme>()
                    + a.morphemes.iter().map(|m| m.form.capacity()).sum::<usize>()
                    + a.spelling_paths.capacity() * size_of::<Vec<SpellingRecovery>>()
                    + a.spelling_paths
                        .iter()
                        .map(|p| p.capacity() * size_of::<SpellingRecovery>())
                        .sum::<usize>()
                    + a.rules.capacity() * size_of::<String>()
                    + a.rules.iter().map(String::capacity).sum::<usize>()
            })
            .sum::<usize>()
}
