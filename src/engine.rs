use crate::{Analysis, Error, Lemma, LemmaKind, Morpheme, MorphemeKind, WordAnalysis};
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
fn nominal_derivations(word: &str) -> Vec<Analysis> {
    let mut out = vec![];
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
            });
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
                });
            }
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
    }];
    out.extend(nominal_derivations(word));
    out
}

// Source-listed predicate adverbs, separate from inflection and auxiliaries.
// Attachment is lexical: do not strip 이/히 from every noun/verb or infer a
// general 르 rule from the historical 달리/빨리 forms.
fn adverb_derivation(word: &str) -> Option<Analysis> {
    let (stem, suffix, recovery) = match word {
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
    }
    Some(Analysis {
        lemmas: vec![lemma(format!("{stem}다"), LemmaKind::Predicate)],
        morphemes: vec![morph(suffix, MorphemeKind::Suffix)],
        rules,
        unchanged: false,
    })
}

#[derive(Clone)]
struct Predicate {
    stem: String,
    auxiliaries: Vec<String>,
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
}
type PrefinalMemo = HashMap<(String, u8, u8), Vec<Predicate>>;

fn prefinals(stem: &str, stage: u8, pasts: u8, memo: &mut PrefinalMemo) -> Vec<Predicate> {
    let key = (stem.to_owned(), stage, pasts);
    if let Some(result) = memo.get(&key) {
        return result.clone();
    }
    let mut out = vec![Predicate {
        stem: stem.into(),
        auxiliaries: vec![],
        morphs: vec![],
        rules: vec![],
        connector: false,
        dap_suffix: false,
        ha_contracted: false,
        copula_contracted: false,
    }];
    let mut choices: Vec<(Recovery, u8, u8, &str, &str)> = vec![];
    if stage >= 4 {
        for r in grammar::recover(stem, "더", Boundary::Literal) {
            choices.push((r, 3, pasts, "더", "prefinal.retrospective"));
        }
    }
    if stage >= 3 {
        for r in grammar::recover(stem, "겠", Boundary::Literal) {
            choices.push((r, 2, pasts, "겠", "prefinal.modal"));
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
    }
    for (r, next, count, form, rule) in choices {
        for mut p in prefinals(&r.stem, next, count, memo) {
            p.copula_contracted |=
                r.stem.ends_with('이') && r.rules.iter().any(|r| r == "contraction.vowel");
            p.morphs.push(morph(form, MorphemeKind::Prefinal));
            p.rules.extend(r.rules.clone());
            p.rules.push(rule.into());
            out.push(p);
        }
    }
    memo.insert(key, out.clone());
    out
}

fn predicates(word: &str) -> Vec<Predicate> {
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
        let mut p = prefinals("말", 0, 0, &mut memo).remove(0);
        p.morphs.push(morph(form, MorphemeKind::Ending));
        p.rules.extend(["ending".into(), "irregular.mal".into()]);
        out.push(p);
    }
    for ending in grammar::matching_endings(word) {
        for r in grammar::recover(word, ending.suffix, ending.boundary) {
            for mut p in prefinals(&r.stem, 4, 0, &mut memo) {
                p.copula_contracted |=
                    r.stem.ends_with('이') && r.rules.iter().any(|r| r == "contraction.vowel");
                // Present conditional -ㄴ다면/-는다면 permits honorific 시,
                // but no other recovered prefinals; past/modal use plain -다면.
                if ending.form == "는다면" && p.morphs.iter().any(|m| m.form != "시") {
                    continue;
                }
                // Reviewed intention/concession families have different
                // prefinal licenses; do not inherit every terminal marker.
                if (matches!(ending.form, "으리라고" | "으나마")
                    && p.morphs.iter().any(|m| m.form == "더"))
                    || (ending.form == "을지라도"
                        && p.morphs
                            .iter()
                            .any(|m| !matches!(m.form.as_str(), "시" | "었")))
                    || (ending.form == "자면" && p.morphs.iter().any(|m| m.form != "시"))
                {
                    continue;
                }
                // KRDict -다가 licenses honorific and past markers. Keep
                // the existing vowel-boundary -어다가 path independent.
                if ending.form == "다가"
                    && p.morphs
                        .iter()
                        .any(|m| !matches!(m.form.as_str(), "시" | "었"))
                {
                    continue;
                }
                // The adjective 으냐는 allomorph is a bare-stem path;
                // prefinals use 냐는/느냐는. Retrospective 더 precedes 냐는.
                if (ending.form == "으냐는" && !p.morphs.is_empty())
                    || (matches!(ending.form, "느냐는" | "더라는")
                        && p.morphs.iter().any(|m| m.form == "더"))
                    || (matches!(ending.form, "잖아" | "잖아요")
                        && p.morphs.iter().any(|m| m.form == "더"))
                {
                    continue;
                }
                // Reviewed shortened adnominals: intention permits honorific
                // 시; proposal quotation is currently scoped to bare stems.
                if (ending.form == "으려는" && p.morphs.iter().any(|m| m.form != "시"))
                    || (ending.form == "자는" && !p.morphs.is_empty())
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
                        | "으세요"
                        | "으십시오"
                        | "읍시다"
                ) && p.morphs.iter().any(|m| m.form != "시")
                {
                    continue;
                }
                // -어라 has both command and exclamation senses. Only the
                // reviewed retrospective boundary is excluded here; do not
                // infer all of its mood restrictions from the command sense.
                if ending.form == "어라" && p.morphs.iter().any(|m| m.form == "더") {
                    continue;
                }
                let factual_ra = matches!(ending.boundary, Boundary::Literal)
                    && matches!(ending.form, "라" | "라서" | "라고" | "라는" | "라면");
                if factual_ra
                    && !p.morphs.last().is_some_and(|m| {
                        m.form == "시" || (m.form == "더" && ending.form != "라는")
                    })
                {
                    continue;
                }
                if ending.form == "란" {
                    let copular = (p.stem.ends_with('이') || p.stem == "아니")
                        && p.morphs.iter().all(|m| m.form == "시");
                    let retrospective = p.morphs.last().is_some_and(|m| m.form == "더");
                    if !copular && !retrospective {
                        continue;
                    }
                }
                p.morphs.push(morph(ending.form, MorphemeKind::Ending));
                p.rules.extend(r.rules.clone());
                p.rules.push("ending".into());
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
    for ending in ["란", "라", "라서", "라고", "라면"] {
        if let Some(base) = word.strip_suffix(ending) {
            for (suffix, boundary) in [("으리", Boundary::EuFull), ("리", Boundary::EuZero)] {
                for r in grammar::recover(base, suffix, boundary) {
                    // Honorific/past/modal may precede conjectural (으)리, not 더.
                    for mut p in prefinals(&r.stem, 3, 0, &mut memo) {
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
            head.auxiliaries.push("않".into());
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

fn predicate_analysis(p: &Predicate) -> Analysis {
    Analysis {
        lemmas: vec![lemma(format!("{}다", p.stem), LemmaKind::Predicate)],
        morphemes: p.morphs.clone(),
        rules: p.rules.clone(),
        unchanged: false,
    }
}

fn expand_predicate(p: &Predicate) -> Vec<Analysis> {
    let mut out = vec![predicate_analysis(p)];
    if p.dap_suffix
        && let Some(base) = p.stem.strip_suffix('답').filter(|s| !s.is_empty())
    {
        for mut a in nominal_bases(base) {
            // -적 combinations need their own attachment audit.
            if a.morphemes.iter().any(|m| m.form == "적") {
                continue;
            }
            a.morphemes.push(morph("답다", MorphemeKind::Suffix));
            a.morphemes.extend(p.morphs.clone());
            a.rules.extend(p.rules.clone());
            a.rules.push("suffix.adjectival.dap".into());
            out.push(a);
        }
    }
    // The restored 하 belongs to a predicate. It cannot then become a nominal
    // base before an omitted copula: 생각다 is not 생각하 + 이다 + 다.
    if !p.ha_contracted {
        add_copulas(p, &mut out);
    }
    for a in &mut out {
        a.lemmas.extend(
            p.auxiliaries
                .iter()
                .map(|s| lemma(format!("{s}다"), LemmaKind::Auxiliary)),
        );
    }
    out.retain(auxiliary_inflections_allowed);
    out
}

#[derive(Clone, Copy)]
enum PredicateClass {
    Verb,
    Adjective,
}

// Classes belong to a particular auxiliary use, not every homonym of a lemma.
// Unclassified lexical heads stay unknown; negative auxiliaries inherit a
// known preceding class. KRDict's 54-entry inventory supplies these classes.
fn auxiliary_class(
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
            Some("어" | "다가") => Some(Verb),
            Some("는가" | "은가" | "나" | "을까") => Some(Adjective),
            _ => None,
        },
        "하" => match connector {
            Some("어" | "게" | "어야" | "으려" | "으려고" | "고자" | "으면") => {
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

fn auxiliary_inflections_allowed(a: &Analysis) -> bool {
    if !a.lemmas.iter().any(|l| l.kind == LemmaKind::Auxiliary) {
        return true;
    }
    let mut cursor = 0;
    let mut previous = None;
    let mut connector = None;
    for lemma in &a.lemmas {
        let mut inflected = matches!(
            lemma.kind,
            LemmaKind::Predicate | LemmaKind::Auxiliary | LemmaKind::Copula
        );
        let mut class = if lemma.kind == LemmaKind::Auxiliary {
            auxiliary_class(
                lemma.text.strip_suffix('다').unwrap_or(&lemma.text),
                connector,
                previous,
            )
        } else {
            None
        };
        while let Some(m) = a
            .morphemes
            .get(cursor)
            .filter(|m| m.kind == MorphemeKind::Suffix)
        {
            if m.form == "답다" {
                class = Some(PredicateClass::Adjective);
                inflected = true;
            }
            cursor += 1;
        }
        let bare = inflected
            && a.morphemes
                .get(cursor)
                .is_some_and(|m| m.kind == MorphemeKind::Ending);
        while inflected
            && a.morphemes
                .get(cursor)
                .is_some_and(|m| m.kind == MorphemeKind::Prefinal)
        {
            cursor += 1;
        }
        connector = None;
        if inflected
            && let Some(m) = a
                .morphemes
                .get(cursor)
                .filter(|m| m.kind == MorphemeKind::Ending)
        {
            // Only bare-stem attachment is decided here. The ending notes
            // separately license prefinals, including adjective + 었 + 는데.
            // -자면 requires a verb even after an honorific marker.
            if matches!(class, Some(PredicateClass::Adjective)) && m.form == "자면" {
                return false;
            }
            if bare
                && match class {
                    Some(PredicateClass::Adjective) => matches!(
                        m.form.as_str(),
                        "는다"
                            | "는다고"
                            | "는다는"
                            | "는다면"
                            | "는"
                            | "는데"
                            | "는데요"
                            | "는데도"
                            | "는데다가"
                            | "는지"
                            | "는가"
                            | "는가요"
                            | "느냐"
                            | "느냐는"
                    ),
                    // Do not infer the converse: 계신가 and existential
                    // negation require a separate honorific/existential audit.
                    Some(PredicateClass::Verb) | None => false,
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
            cursor += 1;
        }
        previous = class;
    }
    true
}

// Bounded adjective attachment inventory. The known suffix is ㅂ-irregular;
// arbitrary lexical predicates still retain the engine's regular hypotheses.
fn dap_suffix_allowed(p: &Predicate) -> bool {
    if !p.stem.ends_with('답') {
        return false;
    }
    if p.morphs
        .iter()
        .find(|m| m.kind == MorphemeKind::Ending)
        .is_some_and(|m| m.form == "자면")
    {
        return false;
    }
    let first = p.morphs[0].form.as_str();
    let vowel = first.starts_with('어')
        || first.starts_with('은')
        || matches!(
            first,
            "었" | "시"
                | "으면"
                | "으니까"
                | "으니"
                | "으며"
                | "으면서"
                | "으므로"
                | "으나"
                | "으나마"
                | "으냐"
                | "으냐는"
                | "으리라"
                | "으리"
                | "으리라고"
                | "을"
                | "을까"
                | "을까요"
                | "을지"
                | "을지라도"
                | "을수록"
                | "음"
        );
    if vowel {
        return p.rules.iter().any(|r| r == "irregular.bieup");
    }
    matches!(
        first,
        "겠" | "더"
            | "다"
            | "다가"
            | "다고"
            | "다는"
            | "다니"
            | "다면"
            | "고"
            | "고요"
            | "지"
            | "지요"
            | "죠"
            | "게"
            | "게요"
            | "지만"
            | "지만요"
            | "군"
            | "군요"
            | "구나"
            | "네"
            | "네요"
            | "나"
            | "나요"
            | "냐"
            | "냐고"
            | "냐는"
            | "니"
            | "기"
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
            | "더라"
            | "더라고"
            | "더라는"
            | "더니"
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
            | "도록"
            | "습니다"
            | "습니까"
            | "소"
            | "오"
    )
}

fn copula_bases(word: &str) -> Vec<Analysis> {
    let mut out = nominal_bases(word);
    // Direct nominalizations need no intervening particle. Quoted questions
    // and connective clauses have separate attachment licenses.
    with_auxiliaries(word, PredicateEnd::CopulaBase, |p| {
        for mut a in expand_predicate(&p) {
            a.rules.push("nominalization".into());
            out.push(a);
        }
    });
    out
}

fn add_copulas(p: &Predicate, out: &mut Vec<Analysis>) {
    // Commands and proposals are not nominal copula endings. The factual
    // 라-family homonyms preserve copular readings such as 학생이라고.
    if p.morphs
        .iter()
        .find(|m| m.kind == MorphemeKind::Ending)
        .is_some_and(|m| {
            matches!(
                m.form.as_str(),
                "자면" | "으라" | "으라고" | "으라는" | "으라면" | "으란" | "으십시오" | "읍시다"
            )
        })
    {
        return;
    }
    // Bare 이다 takes quoted -냐는; -느냐는 may follow its licensed
    // prefinals, but does not attach directly to the copula.
    if p.morphs
        .first()
        .is_some_and(|m| matches!(m.form.as_str(), "느냐는" | "으냐는"))
    {
        return;
    }
    // Quotation punctuation can leave an explicitly spelled copula in its
    // own token (e.g. '농민' 이란). Preserve its role without joining tokens
    // or manufacturing an omitted nominal component.
    if p.stem == "이"
        && p.morphs
            .iter()
            .find(|m| m.kind == MorphemeKind::Ending)
            .is_some_and(|m| matches!(m.form.as_str(), "란" | "라는"))
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
            a.morphemes.extend(p.morphs.clone());
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
            a.morphemes.extend(p.morphs.clone());
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
    // The new focus particles permit nominal/adverbial bases, not a subject
    // or object case phrase. In particular 조금이나마 is not 조금 + 이 + 나마.
    if suffixes
        .first()
        .is_some_and(|m| matches!(m.form.as_str(), "커녕" | "란" | "이란"))
        || (matches!(form, "이" | "가" | "을" | "를")
            && suffixes.iter().any(|m| adverbial_focus_particle(&m.form)))
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
        || (outer == Some("만") && matches!(form, "까지" | "부터"))
        || (outer == Some("의") && matches!(class, 2 | 3) && form != "의")
}

fn choice_particle(form: &str) -> Option<u8> {
    match form {
        "이나" | "나" => Some(0),
        "이라도" | "라도" => Some(1),
        "이든지" | "든지" => Some(2),
        "이야" | "야" => Some(3),
        _ => None,
    }
}

// These particles also attach to adverbial phrases. Bare 커녕 has only
// nominal attachment in its source; do not inherit the longer forms' scope.
fn adverbial_focus_particle(form: &str) -> bool {
    matches!(
        form,
        "이야말로" | "야말로" | "이나마" | "나마" | "은커녕" | "는커녕"
    )
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
        // Only reviewed adverb-compatible particles. Subject/object marking
        // must not mistake this adverbial path for a nominalization.
        if morphs.iter().all(|m| {
            matches!(m.form.as_str(), "도" | "만" | "는" | "은" | "요" | "들")
                || choice_particle(&m.form).is_some()
                || adverbial_focus_particle(&m.form)
        }) && let Some(mut a) = adverb_derivation(base)
        {
            a.morphemes.extend(morphs.clone());
            a.rules.push("particle".into());
            out.push(a);
        }
        // 마는 is a post-ending particle, unlike the nominal homonym 만.
        if particle.form != "마는" {
            for mut a in nominal_bases(base) {
                a.morphemes.extend(morphs.clone());
                a.rules.push("particle".into());
                out.push(a);
            }
        }
        let flexible = particle.contraction.is_some() || matches!(particle.form, "요" | "들");
        if flexible
            || choice_particle(particle.form).is_some()
            || adverbial_focus_particle(particle.form)
        {
            out.push(Analysis {
                lemmas: vec![lemma(base, LemmaKind::Adverbial)],
                morphemes: morphs.clone(),
                rules: vec!["particle".into()],
                unchanged: false,
            });
        }
        // Nominalizations accept ordinary particles; connective/final endings
        // have separate, explicit licenses for the newly supported particles.
        let ending = if flexible
            || matches!(
                particle.form,
                "는" | "도" | "만" | "마는" | "나" | "라도" | "든지" | "야" | "나마"
            ) {
            PredicateEnd::BeforeParticle(particle.form)
        } else {
            PredicateEnd::Nominalized
        };
        with_auxiliaries(base, ending, |p| {
            let nominalized = PredicateEnd::Nominalized.accepts(&p);
            let concessive = matches!(particle.form, "만" | "마는")
                && p.morphs.last().is_some_and(|m| concessive_ending(&m.form));
            for mut a in expand_predicate(&p) {
                a.morphemes.extend(morphs.clone());
                a.rules.push("particle".into());
                if nominalized {
                    a.rules.push("nominalization".into());
                }
                if concessive {
                    a.rules.push("particle.concessive".into());
                }
                out.push(a);
            }
        });
        let next = if after_case && particle.form == "만" {
            1
        } else {
            particle.class
        };
        if particle.form != "마는" {
            nominals(
                base,
                next,
                particle.class == 1 || particle.class == 2,
                &morphs,
                out,
            );
        }
        for a in &mut out[start..] {
            if let Some(rule) = particle.pronunciation {
                a.rules.push(rule.into());
            }
            if let Some(rule) = particle.contraction {
                a.rules.push(rule.into());
            }
            match particle.form {
                "요" => a.rules.push("particle.polite".into()),
                "들" => a.rules.push("particle.distributive".into()),
                _ => (),
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
        "어야" => stem == "하",
        "은" | "는" => matches!(stem, "듯하" | "듯싶" | "양하" | "척하" | "체하"),
        "을" => matches!(stem, "듯하" | "듯싶" | "만하" | "법하" | "뻔하" | "성싶"),
        "음" => stem == "직하",
        "으려" | "으려고" => matches!(stem, "들" | "하"),
        "기로" | "자고" => stem == "들",
        "다" | "다가" => matches!(stem, "보" | "못하") || (connector == "다" && stem == "싶"),
        "는가" | "은가" | "나" | "을까" => matches!(stem, "보" | "싶"),
        "으면" => matches!(stem, "하" | "싶"),
        "기도" | "기는" | "기만" | "고자" => stem == "하",
        _ => false,
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
                    || (connector == "지" && aux_allowed(&right.stem, connector))
            }
            "나" => right.stem == "하" && connector == "기",
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
        "달" => matches!(
            right_forms.as_slice(),
            ["으라" | "으라고" | "으라는" | "으라면" | "오"]
        ),
        "보" if matches!(connector, "다" | "다가") => {
            matches!(right_forms.as_slice(), ["으니" | "으면"])
        }
        _ => true,
    }
}

// An internal particle consumes input before a link is considered. Keep this
// bounded to one reviewed slot and leave the packed search iterative.
fn connector_predicates(word: &str) -> Vec<Predicate> {
    let mut out = predicates(word);
    for particle in ["들", "도", "만", "는", "야", "나"] {
        if let Some(base) = word.strip_suffix(particle) {
            for mut p in predicates(base) {
                let ending = &p.morphs.last().unwrap().form;
                if p.connector && (ending == "기" || before_particle(ending, particle)) {
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
                    return matches!(m.form.as_str(), "기" | "음");
                }
                if matches!(self, Self::BeforeParticle("마는")) {
                    return concessive_ending(&m.form);
                }
                matches!(
                    m.form.as_str(),
                    "기" | "음" | "는가" | "은가" | "는지" | "은지"
                ) || match self {
                    Self::BeforeParticle(form) => before_particle(&m.form, form),
                    _ => false,
                }
            })
    }
}

fn concessive_ending(ending: &str) -> bool {
    matches!(
        ending,
        "다" | "는다" | "습니다" | "냐" | "느냐" | "으냐" | "자" | "지" | "더니"
    )
}

fn before_particle(ending: &str, particle: &str) -> bool {
    let connective = matches!(
        ending,
        "어" | "어서"
            | "어도"
            | "어야"
            | "어다가"
            | "고"
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
        "요" => {
            connective
                || matches!(
                    ending,
                    "군" | "구나"
                        | "네"
                        | "나"
                        | "니"
                        | "냐"
                        | "으냐"
                        | "더라"
                        | "더라고"
                        | "더군"
                        | "을까"
                        | "을게"
                        | "을래"
                        | "다니"
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
        "는" | "도" => connective,
        "라도" => matches!(ending, "어" | "게" | "지" | "고"),
        // KRDict 나마 explicitly illustrates an adverbial 게 clause.
        "나마" => ending == "게",
        "나" => matches!(
            ending,
            "어" | "게" | "지" | "고" | "다" | "는다" | "라" | "으라" | "어라"
        ),
        "든지" => matches!(ending, "다" | "는다" | "라" | "으라" | "어라"),
        "야" => matches!(ending, "어" | "게" | "지" | "고"),
        "만" => {
            concessive_ending(ending) || matches!(ending, "어" | "어서" | "어야" | "게" | "고")
        }
        "마는" => concessive_ending(ending),
        "를" => matches!(ending, "어" | "게" | "지" | "고"),
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
                    connector_predicates(right)
                        .into_iter()
                        .filter(|p| {
                            grammar::AUXILIARY_CONNECTORS
                                .iter()
                                .any(|c| aux_allowed(&p.stem, c))
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
        let accepts = |p: &Predicate| match path.last() {
            Some(right) => p.connector && auxiliary_link(p, right),
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
                for tail in path.iter().rev() {
                    if joined
                        .morphs
                        .last()
                        .is_some_and(|m| m.kind == MorphemeKind::Particle)
                    {
                        rules.insert("auxiliary.internal_particle");
                    }
                    joined.auxiliaries.push(tail.stem.clone());
                    joined.auxiliaries.extend(tail.auxiliaries.iter().cloned());
                    joined.morphs.extend(tail.morphs.iter().cloned());
                    rules.extend(tail.rules.iter().map(String::as_str));
                    rules.insert("auxiliary");
                    joined.connector = tail.connector;
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
            });
        }
        out.extend(adverb_derivation(&normalized));
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
            });
        }
        with_auxiliaries(&normalized, PredicateEnd::Any, |p| {
            out.extend(expand_predicate(&p));
        });
        nominals(&normalized, 7, false, &[], &mut out);
    }
    // Semantic duplicates share provenance; sorting is independent of hash order.
    let mut unique: BTreeMap<(Vec<Lemma>, Vec<Morpheme>, bool), Vec<String>> = BTreeMap::new();
    for a in out {
        unique
            .entry((a.lemmas, a.morphemes, a.unchanged))
            .or_default()
            .extend(a.rules);
    }
    let analyses = unique
        .into_iter()
        .map(|((lemmas, morphemes, unchanged), mut rules)| {
            rules.sort();
            rules.dedup();
            Analysis {
                lemmas,
                morphemes,
                rules,
                unchanged,
            }
        })
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
                    + a.rules.capacity() * size_of::<String>()
                    + a.rules.iter().map(String::capacity).sum::<usize>()
            })
            .sum::<usize>()
}
