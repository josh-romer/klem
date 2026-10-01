//! Scoped lexical attachment evidence, separate from dictionary-free generation.
//! See docs/dictionary-attachments.md for sources, exceptions and exclusions.
use super::{Annotation, Compatibility};
use crate::engine::{PredicateClass, auxiliary_class};
use crate::{
    Analysis, LemmaKind, MorphemeKind, SpellingClass, SpellingRecovery, WordAnalysis,
    breakdown::Component,
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DictionaryFilter {
    /// Every lemma has a headword entry, regardless of role or attachment.
    Headword,
    /// Headword matches with no known conflict under the scoped checks.
    /// Unknown roles/classes are retained; this is not a precision guarantee.
    Compatible,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AttachmentRule {
    LexicalRole,
    PresentDeclarativeVerb,
    BareAdjectivalQuestion,
    NegativeCopulaCommand,
    IntentionVerb,
    ResultTransferVerb,
    NeuraVerb,
    AuxiliaryClass,
    LiteraryAssertionClass,
    BareLiteraryDeclarative,
    BareLiteraryQuestion,
    VolitionalPromiseVerb,
    BareBackgroundVerb,
    BareNeuniVerb,
    BareGeolVerb,
    BareExclamationVerb,
    BareExclamationAdjective,
    BareNimanAdjective,
    HabitualConditionVerb,
    BareCopularEnding,
    BareAdjectivalReport,
    BareVerbalQuestion,
    LexicalSpelling,
    ShortStemEnding,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AttachmentConflict {
    pub rule: AttachmentRule,
    /// Index in Analysis::morphemes; absent for a lexical-role conflict or
    /// when an externally supplied auxiliary has no preceding connector.
    /// Auxiliary-class conflicts reference the preceding connector, which
    /// belongs to the previous lemma, rather than this auxiliary's ending.
    pub morpheme_index: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EntryAssessment {
    pub id: String,
    pub status: Compatibility,
    pub conflicts: Vec<AttachmentConflict>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LemmaAssessment {
    pub lemma_index: usize,
    pub status: Compatibility,
    /// Each entry is checked as a whole. A reading can retain a valid homonym
    /// without assigning another entry's POS or sense to it.
    pub entries: Vec<EntryAssessment>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ReadingAssessment {
    /// Compatibility with the finite policy, not overall grammatical validity.
    pub status: Compatibility,
    pub lemmas: Vec<LemmaAssessment>,
}

fn alternatives(statuses: impl Iterator<Item = Compatibility>) -> Compatibility {
    let mut unknown = false;
    let mut any = false;
    for status in statuses {
        any = true;
        match status {
            Compatibility::Compatible => return Compatibility::Compatible,
            Compatibility::Unknown => unknown = true,
            Compatibility::Incompatible => (),
        }
    }
    if unknown || !any {
        Compatibility::Unknown
    } else {
        Compatibility::Incompatible
    }
}

// Check only this owner's prefinals, leaving derivational suffixes independent.
// Generic hypotheses survive when the reviewed entry does not settle them.
fn unreviewed_neuni_prefinals(
    analysis: &Analysis,
    components: &[Component],
    ending: usize,
) -> bool {
    let listed: &[&str] = match analysis.morphemes[ending].form.as_str() {
        "느니" => &["시", "었", "겠"],
        "느니만" | "느니만큼" | "느니보다" | "느니보다는" => &["시"],
        "니만" => &[],
        "으니만큼" => &["시", "었", "겠", "더", "으옵"],
        "다느니" | "냐느니" | "느냐느니" | "더라느니" => &["시", "었", "겠"],
        "는다느니" | "으라느니" => &["시"],
        "라느니" => &["시", "더", "으리"],
        "자느니" | "으냐느니" => &[],
        _ => return false,
    };
    components
        .iter()
        .take_while(|c| !matches!(c, Component::Morpheme(i) if *i == ending))
        .any(|c| {
            matches!(c, Component::Morpheme(i)
            if analysis.morphemes[*i].kind == MorphemeKind::Prefinal
            && !listed.contains(&analysis.morphemes[*i].form.as_str()))
        })
}

// Exact factual forms, distinct from canonical command 으라/으라고/etc.
// KRDict licenses bare 이다/아니다, with family-specific prefinal extensions.
// This policy does not decide those extensions from the lexical head's POS.
fn bare_copular_ending(form: &str) -> bool {
    matches!(
        form,
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
            | "라며"
            | "라면서"
            | "라니"
            | "라느니"
            | "라거나"
            | "란"
            | "로구나"
            | "로구려"
            | "로구먼"
            | "로군"
    ) || crate::engine::quoted_copular_exclamation(form)
}

// Return the connector whose expressive 하다 use depends on this lexical
// head's class. Only 지-negatives preserve that dependency; a different
// auxiliary, a copula or a derivational suffix starts a new class boundary.
// Compute the requirement once, then assess each headword entry independently.
fn expressive_hada_connector(analysis: &Analysis, mut rest: &[Component]) -> Option<usize> {
    loop {
        let next = rest.iter().position(|c| matches!(c, Component::Lemma(_)))?;
        let morphs = &rest[..next];
        if morphs.iter().any(|c| {
            matches!(c, Component::Morpheme(i)
            if analysis.morphemes[*i].kind == MorphemeKind::Suffix)
        }) {
            return None;
        }
        let connector = morphs.iter().find_map(|c| match c {
            Component::Morpheme(i) if analysis.morphemes[*i].kind == MorphemeKind::Ending => {
                Some(*i)
            }
            _ => None,
        })?;
        let Component::Lemma(index) = rest[next] else {
            return None;
        };
        let lemma = &analysis.lemmas[index];
        if lemma.kind != LemmaKind::Auxiliary {
            return None;
        }
        let form = analysis.morphemes[connector].form.as_str();
        if lemma.text == "하다" && form == "어" {
            return Some(connector);
        }
        if form != "지" || !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
        {
            return None;
        }
        rest = &rest[next + 1..];
    }
}

// A final rhetorical -(으)려고 does not require a verbal head. Only a
// represented intention auxiliary establishes the connective reading here.
// 지-negatives preserve the head's class; other auxiliaries reset ownership.
fn intention_auxiliary_connector(analysis: &Analysis, mut rest: &[Component]) -> Option<usize> {
    loop {
        let next = rest.iter().position(|c| matches!(c, Component::Lemma(_)))?;
        let morphs = &rest[..next];
        if morphs.iter().any(|c| {
            matches!(c, Component::Morpheme(i)
                if analysis.morphemes[*i].kind == MorphemeKind::Suffix
                && analysis.morphemes[*i].form != "답다")
        }) {
            return None;
        }
        let connector = morphs.iter().find_map(|c| match c {
            Component::Morpheme(i) if analysis.morphemes[*i].kind == MorphemeKind::Ending => {
                Some(*i)
            }
            _ => None,
        })?;
        let Component::Lemma(index) = rest[next] else {
            return None;
        };
        let lemma = &analysis.lemmas[index];
        if lemma.kind != LemmaKind::Auxiliary {
            return None;
        }
        let form = analysis.morphemes[connector].form.as_str();
        if form == "으려고" && matches!(lemma.text.as_str(), "하다" | "들다") {
            return Some(connector);
        }
        if form != "지" || !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
        {
            return None;
        }
        rest = &rest[next + 1..];
    }
}

// -(으)ㄹ라치면 keeps its lexical class requirement through 지-negatives.
// Other auxiliaries, derivation and copulas establish their own class boundary.
fn habitual_condition_ending(analysis: &Analysis, mut rest: &[Component]) -> Option<usize> {
    loop {
        let end = rest
            .iter()
            .position(|c| matches!(c, Component::Lemma(_)))
            .unwrap_or(rest.len());
        let morphs = &rest[..end];
        if morphs.iter().any(|c| matches!(c, Component::Morpheme(i) if analysis.morphemes[*i].kind == MorphemeKind::Suffix)) {
            return None;
        }
        let ending = morphs.iter().find_map(|c| match c {
            Component::Morpheme(i) if analysis.morphemes[*i].kind == MorphemeKind::Ending => {
                Some(*i)
            }
            _ => None,
        })?;
        match analysis.morphemes[ending].form.as_str() {
            "을라치면" => return Some(ending),
            "지" => (),
            _ => return None,
        }
        let Component::Lemma(index) = rest.get(end)? else {
            return None;
        };
        let lemma = &analysis.lemmas[*index];
        if lemma.kind != LemmaKind::Auxiliary
            || !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
        {
            return None;
        }
        rest = &rest[end + 1..];
    }
}

// NIKL's restricted short stems, bound to reviewed KRDict entry identities.
// A headword alone cannot distinguish 까불다 (winnow) from 까불다 (act up),
// or the unrelated 굴다/일다/붓다 homonyms. See short-stem-inventory.json.
fn short_stem_conflict(entry: &super::EntrySummary, first: &crate::Morpheme) -> bool {
    if !matches!(first.kind, MorphemeKind::Ending | MorphemeKind::Prefinal) {
        return false;
    }
    let consonant_only = match (
        entry.id.as_str(),
        entry.headword.as_str(),
        entry.pos.as_str(),
    ) {
        ("krdict:29738", "갖다", "동사")
        | ("krdict:73401", "갖다", "보조 동사")
        | ("krdict:54454", "딛다", "동사")
        | ("krdict:41863", "내딛다", "동사")
        | ("krdict:73124", "잡숫다", "동사")
        | ("krdict:62815", "뵙다", "동사")
        | ("krdict:83942", "찾아뵙다", "동사") => true,
        ("krdict:23620", "건들다", "동사")
        | ("krdict:38390", "까불다", "동사")
        | ("krdict:15980", "머물다", "동사")
        | ("krdict:601166", "서둘다", "동사")
        | ("krdict:29045", "서툴다", "형용사") => false,
        _ => return false,
    };
    let form = first.form.as_str();
    if consonant_only {
        // Canonical 시 represents -(으)시-. Other vowel-initial canonical
        // endings include 은/을/음 and 읍시다, even when their surface onset
        // disappeared through a hypothetical irregular recovery.
        form == "시"
            || form.chars().next().is_some_and(|c| {
                let code = c as u32;
                (0xAC00..=0xD7A3).contains(&code) && (code - 0xAC00) / 588 == 11
            })
    } else {
        // ㄹ short stems retain 니/면/은/을/음 allomorphs, including 머묾.
        // Only the 아/어 family and past 었 (including 어야겠) are blocked.
        form.starts_with(['어', '었'])
    }
}

impl Annotation {
    /// Check a complete analysis against this annotation's headword evidence.
    /// Missing entries, unclassified roles and unknown POS remain unknown.
    /// Only reviewed lexical constraints are applied; no sense is selected.
    pub fn assess(&self, analysis: &Analysis) -> ReadingAssessment {
        if analysis.spelling_paths.is_empty() {
            return self.assess_path(analysis, &[]);
        }
        let paths: Vec<_> = analysis
            .spelling_paths
            .iter()
            .map(|p| self.assess_path(analysis, p))
            .collect();
        let mut merged = paths[0].clone();
        merged.status = alternatives(paths.iter().map(|p| p.status));
        for (li, lemma) in merged.lemmas.iter_mut().enumerate() {
            lemma.status = alternatives(paths.iter().map(|p| p.lemmas[li].status));
            for (ei, entry) in lemma.entries.iter_mut().enumerate() {
                entry.status = alternatives(paths.iter().map(|p| p.lemmas[li].entries[ei].status));
                entry.conflicts.clear();
                if entry.status == Compatibility::Incompatible {
                    for path in &paths {
                        for conflict in &path.lemmas[li].entries[ei].conflicts {
                            if !entry.conflicts.contains(conflict) {
                                entry.conflicts.push(conflict.clone());
                            }
                        }
                    }
                }
            }
        }
        merged
    }

    fn assess_path(&self, analysis: &Analysis, spelling: &[SpellingRecovery]) -> ReadingAssessment {
        let Some(order) = analysis.breakdown() else {
            return ReadingAssessment {
                status: Compatibility::Unknown,
                lemmas: Vec::new(),
            };
        };
        let mut lemmas = Vec::with_capacity(analysis.lemmas.len());
        let mut components = order.as_slice();
        let mut previous_class = None;
        let mut connector: Option<usize> = None;
        while let Some((Component::Lemma(index), rest)) = components.split_first() {
            let end = rest
                .iter()
                .position(|c| matches!(c, Component::Lemma(_)))
                .unwrap_or(rest.len());
            let morphs = &rest[..end];
            components = &rest[end..];
            let lemma = &analysis.lemmas[*index];
            let class = match lemma.kind {
                LemmaKind::Auxiliary => auxiliary_class(
                    lemma.text.strip_suffix('다').unwrap_or(&lemma.text),
                    connector.map(|i| analysis.morphemes[i].form.as_str()),
                    previous_class,
                ),
                LemmaKind::Copula => Some(PredicateClass::Copula),
                _ => None,
            };
            let ending = morphs.iter().find_map(|c| match c {
                Component::Morpheme(i) if analysis.morphemes[*i].kind == MorphemeKind::Ending => {
                    Some(*i)
                }
                _ => None,
            });
            let bare = morphs
                .first()
                .is_some_and(|c| matches!(c, Component::Morpheme(i) if Some(*i) == ending));
            let expressive_connector = if lemma.kind == LemmaKind::Predicate {
                expressive_hada_connector(analysis, rest)
            } else {
                None
            };
            let habitual_ending = (lemma.kind == LemmaKind::Predicate)
                .then(|| habitual_condition_ending(analysis, rest))
                .flatten();
            let intention_connector = intention_auxiliary_connector(analysis, rest);
            let derived_adjective = morphs.iter().any(|c| {
                matches!(c, Component::Morpheme(i)
                    if analysis.morphemes[*i].kind == MorphemeKind::Suffix
                    && analysis.morphemes[*i].form == "답다")
            });
            // Tense evidence belongs to the connector's immediate owner,
            // never to an earlier lexical head through a negative auxiliary.
            let intention_prefinal = intention_connector.is_some()
                && intention_connector == ending
                && morphs.iter().any(|c| {
                    matches!(c, Component::Morpheme(i)
                        if analysis.morphemes[*i].kind == MorphemeKind::Prefinal
                        && !crate::engine::honorific_prefinal(&analysis.morphemes[*i].form))
                });
            let entries: Vec<_> = self
                .lemmas
                .iter()
                .find(|m| m.lemma == *lemma)
                .into_iter()
                .flat_map(|m| &m.entries)
                .map(|matched| {
                    let mut status = matched.pos_compatibility;
                    // A token-initial predicate can be a separately written
                    // auxiliary (먹고 싶었다). Its preceding word/connector is
                    // outside this analysis; do not call that a POS conflict.
                    if *index == 0
                        && lemma.kind == LemmaKind::Predicate
                        && matches!(matched.entry.pos.as_str(), "보조 동사" | "보조 형용사")
                    {
                        status = Compatibility::Unknown;
                    }
                    let mut conflicts = Vec::new();
                    if status == Compatibility::Incompatible {
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::LexicalRole,
                            morpheme_index: None,
                        });
                    }
                    if lemma.kind == LemmaKind::Auxiliary
                        && status == Compatibility::Compatible
                        && matches!(
                            (class, matched.entry.pos.as_str()),
                            (Some(PredicateClass::Verb), "보조 형용사")
                                | (Some(PredicateClass::Adjective), "보조 동사")
                        )
                    {
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::AuxiliaryClass,
                            morpheme_index: connector,
                        });
                    }
                    if status == Compatibility::Compatible
                        && matched.entry.pos == "동사"
                        && expressive_connector.is_some()
                    {
                        // KRDict 62888 sense 9 describes adjective attachment,
                        // but NIKL also licenses some verbs (꺼려 하다,
                        // 내키지 않아 하다). Broad verb POS cannot decide this
                        // lexical subset, including through negative auxiliaries.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible
                        && matched.entry.pos == "형용사"
                        && lemma.text != "있다"
                        && let Some(i) = habitual_ending
                    {
                        // Both KRDict and KAIST explicitly attest 있을라치면.
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::HabitualConditionVerb,
                            morpheme_index: Some(i),
                        });
                    }
                    // Dictionary classes belong to the lexical head, not its
                    // auxiliary, derived suffix or a later copula's ending.
                    if lemma.kind == LemmaKind::Predicate
                        && status == Compatibility::Compatible
                        && let Some(i) = ending
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let adjective = matched.entry.pos == "형용사";
                        let verb = matched.entry.pos == "동사";
                        let rule = if bare
                            && bare_copular_ending(form)
                            && (verb || (adjective && lemma.text != "아니다"))
                        {
                            // Verb 이다 (carry on the head) is not copular 이다.
                            // The latter has its own role/entry; 아니다 is the
                            // source-listed adjective exception. Unknown POS
                            // and standalone auxiliaries are not rejected.
                            Some(AttachmentRule::BareCopularEnding)
                        } else if bare
                            && matches!(
                                form,
                                "단다" | "다지" | "다죠" | "다지만" | "다니까" | "다느니" | "대"
                                    | "다는구나" | "다는군" | "다더군" | "다더군요"
                            )
                            && verb
                        {
                            // Lexical existential/honorific senses cannot be
                            // decided from the broad verbal POS alone.
                            if matches!(lemma.text.as_str(), "있다" | "없다" | "계시다") {
                                status = Compatibility::Unknown;
                                None
                            } else {
                                Some(AttachmentRule::BareAdjectivalReport)
                            }
                        } else if bare
                            && ((form == "으니라" && verb)
                                || (form == "느니라"
                                    && adjective
                                    && !lemma.text.ends_with("있다")
                                    && !lemma.text.ends_with("없다")))
                        {
                            if matches!(lemma.text.as_str(), "있다" | "없다" | "계시다") {
                                status = Compatibility::Unknown;
                                None
                            } else {
                                Some(AttachmentRule::LiteraryAssertionClass)
                            }
                        } else if bare
                            && crate::engine::literary_na_ending(form)
                            && adjective
                            && !matches!(lemma.text.as_str(), "있다" | "없다" | "계시다")
                        {
                            Some(if form == "나이다" {
                                AttachmentRule::BareLiteraryDeclarative
                            } else {
                                AttachmentRule::BareLiteraryQuestion
                            })
                        } else if bare
                            && (matches!(form, "느냐지만" | "느냐니까" | "느냬" | "느냐느니")
                                || crate::engine::verbal_quoted_question(form))
                            && adjective
                            && !lemma.text.ends_with("있다")
                            && !lemma.text.ends_with("없다")
                        {
                            // KRDict 85642/80829 explicitly include existential
                            // adjectives. This finite policy does not infer
                            // restrictions for other question families.
                            Some(AttachmentRule::BareVerbalQuestion)
                        } else if bare
                            && form == "는바"
                            && adjective
                            && !lemma.text.ends_with("있다")
                            && !lemma.text.ends_with("없다")
                            && lemma.text != "계시다"
                        {
                            Some(AttachmentRule::BareBackgroundVerb)
                        } else if bare && crate::engine::present_exclamation(form) && adjective {
                            Some(AttachmentRule::BareExclamationVerb)
                        } else if bare && matches!(form, "구나" | "군" | "군요" | "구먼") && verb {
                            // Lexical 있다 has verb/adjective homonyms. Its
                            // existential distribution needs the particular use.
                            if matches!(lemma.text.as_str(), "있다" | "계시다") {
                                status = Compatibility::Unknown;
                                None
                            } else {
                                Some(AttachmentRule::BareExclamationAdjective)
                            }
                        } else if bare
                            && form == "는걸"
                            && adjective
                            && !lemma.text.ends_with("있다")
                            && !lemma.text.ends_with("없다")
                            && lemma.text != "계시다"
                        {
                            Some(AttachmentRule::BareGeolVerb)
                        } else if bare
                            && crate::engine::neuni_verbal_ending(form)
                            && adjective
                            && !lemma.text.ends_with("있다")
                            && !lemma.text.ends_with("없다")
                            && lemma.text != "계시다"
                        {
                            Some(AttachmentRule::BareNeuniVerb)
                        } else if bare
                            && form == "느니만"
                            && adjective
                            && (lemma.text.ends_with("있다") || lemma.text.ends_with("없다"))
                            && !matches!(lemma.text.as_str(), "있다" | "없다")
                        {
                            // This entry lists the three existential heads,
                            // unlike the explicit compound notes on 느니 and
                            // 느니만큼. Keep the remaining distribution open.
                            status = Compatibility::Unknown;
                            None
                        } else if bare && form == "니만" && verb {
                            Some(AttachmentRule::BareNimanAdjective)
                        } else if bare && form == "으니만큼" && verb && lemma.text != "알다" {
                            // KRDict 85727/85728 narrow bare adjective note
                            // conflicts with NIKL 331720 broader predicate
                            // description. 알다 is explicitly attested there.
                            // Keep other verbal distributions unresolved.
                            status = Compatibility::Unknown;
                            None
                        } else if bare && form == "음세" && adjective {
                            Some(AttachmentRule::VolitionalPromiseVerb)
                        } else if crate::engine::present_declarative(form) && adjective {
                            Some(AttachmentRule::PresentDeclarativeVerb)
                        } else if adjective && crate::engine::verbal_intention(form) {
                            Some(AttachmentRule::IntentionVerb)
                        } else if adjective && crate::engine::activity_reason(form) {
                            Some(AttachmentRule::NeuraVerb)
                        } else if adjective && crate::engine::result_connective(form) {
                            Some(AttachmentRule::ResultTransferVerb)
                        } else if bare && verb && crate::engine::adjectival_question(form) {
                            // Existential/honorific question paradigms remain
                            // COV-019h. Do not decide them from a broad POS label.
                            if matches!(lemma.text.as_str(), "있다" | "없다" | "계시다")
                                // KRDict 86329 says adjective but explicitly
                                // illustrates 듣다 in 들으냐니까는. Keep the
                                // source conflict unknown, scoped to this tail.
                                || (form == "으냐니까"
                                    && lemma.text == "듣다"
                                    && analysis.morphemes.get(i + 1).is_some_and(|m|
                                        m.kind == crate::MorphemeKind::Particle && m.form == "는"))
                                // KRDict 89688 lists adjectives but directly
                                // illustrates the clothing question 입으냬요.
                                // Preserve uncertainty only for the attested
                                // lexical head and polite form, not all verbs.
                                || (form == "으냬"
                                    && lemma.text == "입다"
                                    && analysis.morphemes.get(i + 1).is_some_and(|m|
                                        m.kind == crate::MorphemeKind::Particle && m.form == "요"))
                            {
                                status = Compatibility::Unknown;
                                None
                            } else {
                                Some(AttachmentRule::BareAdjectivalQuestion)
                            }
                        } else if adjective
                            && lemma.text == "아니다"
                            && (matches!(form, "으라니" | "으라느니")
                                || crate::engine::quoted_command_exclamation(form))
                        {
                            // Preserve factual 라니. Do not generalize this to
                            // all adjective commands/proposals: wishes exist.
                            Some(AttachmentRule::NegativeCopulaCommand)
                        } else {
                            None
                        };
                        if let Some(rule) = rule {
                            status = Compatibility::Incompatible;
                            conflicts.push(AttachmentConflict {
                                rule,
                                morpheme_index: Some(i),
                            });
                        }
                    }
                    if status == Compatibility::Compatible
                        && !bare
                        && ending.is_some_and(|i| analysis.morphemes[i].form == "음세")
                    {
                        // The reviewed sources list bare verbs. Generic
                        // prefinal hypotheses survive without claiming that
                        // this new final licenses every such combination.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible
                        && ending.is_some_and(|i| unreviewed_neuni_prefinals(analysis, morphs, i))
                    {
                        status = Compatibility::Unknown;
                    }
                    // A separately written auxiliary has unknown context,
                    // but its known lexical class still constrains this bare
                    // exclamation boundary. Do not let that context uncertainty
                    // override the entry's reviewed inflectional conflict.
                    if lemma.kind == LemmaKind::Predicate
                        && status == Compatibility::Unknown
                        && bare
                        && let Some(i) = ending
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let pos = matched.entry.pos.as_str();
                        let rule = if crate::engine::present_exclamation(form)
                            && (pos == "보조 형용사" || (pos == "보조 동사" && lemma.text == "있다"))
                        {
                            Some(AttachmentRule::BareExclamationVerb)
                        } else if matches!(form, "구나" | "군" | "군요" | "구먼")
                            && pos == "보조 동사"
                            && !matches!(lemma.text.as_str(), "있다" | "계시다" | "않다" | "아니하다" | "못하다")
                        {
                            Some(AttachmentRule::BareExclamationAdjective)
                        } else { None };
                        if let Some(rule) = rule {
                            status = Compatibility::Incompatible;
                            conflicts.push(AttachmentConflict { rule, morpheme_index: Some(i) });
                        }
                    }
                    if lemma.kind == LemmaKind::Predicate
                        && status == Compatibility::Unknown
                        && let Some(i) = ending
                        && crate::engine::quoted_exclamation(&analysis.morphemes[i].form)
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let pos = matched.entry.pos.as_str();
                        let rule = if crate::engine::present_declarative(form) && pos == "보조 형용사" {
                            Some(AttachmentRule::PresentDeclarativeVerb)
                        } else if bare && crate::engine::plain_quoted_exclamation(form)
                            && pos == "보조 동사"
                            && !matches!(lemma.text.as_str(), "있다" | "계시다" | "않다" | "아니하다" | "못하다")
                        { Some(AttachmentRule::BareAdjectivalReport) } else { None };
                        if let Some(rule) = rule {
                            status = Compatibility::Incompatible;
                            conflicts.push(AttachmentConflict { rule, morpheme_index: Some(i) });
                        }
                    }
                    if status == Compatibility::Compatible
                        && let Some(i) = ending
                        && crate::engine::quoted_exclamation(&analysis.morphemes[i].form)
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let listed: &[&str] = if crate::engine::present_declarative(form) {
                            &["시"]
                        } else { &["시", "었", "겠"] };
                        // Listing -시- in an adjective report's note does not
                        // establish a verb's present report without -ㄴ다/-는다.
                        // Preserve the hypothesis without certifying that class
                        // extension. Past/modal reports have separate evidence.
                        let honorific_verb_report = crate::engine::plain_quoted_exclamation(form)
                            && matches!(matched.entry.pos.as_str(), "동사" | "보조 동사")
                            && morphs.iter().any(|c| matches!(c, Component::Morpheme(j)
                                if analysis.morphemes[*j].kind == MorphemeKind::Prefinal))
                            && morphs.iter().all(|c| !matches!(c, Component::Morpheme(j)
                                if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                    && analysis.morphemes[*j].form != "시"));
                        if morphs.iter().any(|c| matches!(c, Component::Morpheme(j)
                            if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                && !listed.contains(&analysis.morphemes[*j].form.as_str())))
                            || honorific_verb_report
                        { status = Compatibility::Unknown; }
                    }
                    if lemma.kind == LemmaKind::Predicate
                        && status == Compatibility::Unknown && bare
                        && let Some(i) = ending
                        && crate::engine::quoted_question_report(&analysis.morphemes[i].form)
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let pos = matched.entry.pos.as_str();
                        let existential_or_negative = lemma.text.ends_with("있다")
                            || lemma.text.ends_with("없다")
                            || matches!(lemma.text.as_str(), "계시다" | "않다" | "아니하다" | "못하다");
                        let rule = if crate::engine::verbal_quoted_question(form)
                            && pos == "보조 형용사" && !existential_or_negative
                        { Some(AttachmentRule::BareVerbalQuestion) }
                        else if crate::engine::adjectival_question(form)
                            && pos == "보조 동사" && !existential_or_negative
                        { Some(AttachmentRule::BareAdjectivalQuestion) }
                        else { None };
                        if let Some(rule) = rule {
                            status = Compatibility::Incompatible;
                            conflicts.push(AttachmentConflict { rule, morpheme_index: Some(i) });
                        }
                    }
                    if status == Compatibility::Compatible
                        && let Some(i) = ending
                        && crate::engine::quoted_question_report(&analysis.morphemes[i].form)
                        && morphs.iter().any(|c| matches!(c, Component::Morpheme(j)
                            if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                && !matches!(analysis.morphemes[*j].form.as_str(), "시" | "었" | "겠")))
                    {
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible
                        && lemma.kind == LemmaKind::Auxiliary && bare && class.is_none()
                        && matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
                        && ending.is_some_and(|i|
                            crate::engine::verbal_quoted_question(&analysis.morphemes[i].form)
                            || (crate::engine::quoted_question_report(&analysis.morphemes[i].form)
                                && crate::engine::adjectival_question(&analysis.morphemes[i].form)))
                    {
                        // Negation inherits the preceding predicate's class.
                        // An unclassified lexical head cannot borrow a homonym's
                        // dictionary POS to settle this later owner's question.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible
                        && let Some(i) = ending
                        && crate::engine::verbal_quoted_question(&analysis.morphemes[i].form)
                        && ((matched.entry.pos == "형용사"
                            && !lemma.text.ends_with("있다") && !lemma.text.ends_with("없다"))
                            || lemma.kind == LemmaKind::Copula
                            || (crate::engine::quoted_conditional_question(&analysis.morphemes[i].form)
                                && (derived_adjective || matches!(class, Some(PredicateClass::Adjective)))))
                        && morphs.iter().any(|c| matches!(c, Component::Morpheme(j)
                            if analysis.morphemes[*j].kind == MorphemeKind::Prefinal))
                        && morphs.iter().all(|c| !matches!(c, Component::Morpheme(j)
                            if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                && analysis.morphemes[*j].form != "시"))
                    {
                        // The note lists -시-, but does not directly settle
                        // this nonverbal owner's honorific-only extension.
                        // Preserve it as unknown; past/modal examples provide
                        // distinct evidence and are not excluded here.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible && let Some(i) = ending
                        && crate::engine::quoted_conditional_question(&analysis.morphemes[i].form)
                        && ((analysis.morphemes.get(i + 1).is_some_and(|m|
                            m.kind == MorphemeKind::Particle && m.form == "요"))
                            || (lemma.kind == LemmaKind::Auxiliary && bare
                                && (matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
                                    || (analysis.morphemes[i].form == "으냐면"
                                        && matches!(lemma.text.as_str(), "있다" | "계시다")))))
                    {
                        // Native 요 sense 2 permits connective followers, but
                        // these quoted contractions have no directly reviewed
                        // polite example. Negative-owner paradigms remain
                        // COV-019h; do not settle them from a borrowed POS.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible && let Some(i) = ending
                        && crate::engine::quoted_proposal_exclamation(&analysis.morphemes[i].form)
                        && (matches!(matched.entry.pos.as_str(), "형용사" | "보조 형용사")
                            || derived_adjective
                            || matches!(class, Some(PredicateClass::Adjective))
                            || (lemma.kind == LemmaKind::Auxiliary
                                && (class.is_none() || matches!(lemma.text.as_str(), "있다" | "계시다")))
                            || morphs.iter().any(|c| matches!(c, Component::Morpheme(j)
                                if analysis.morphemes[*j].kind == MorphemeKind::Prefinal))
                            || (analysis.morphemes[i].form == "자는군"
                                && analysis.morphemes.get(i + 1).is_some_and(|m|
                                    m.kind == MorphemeKind::Particle && m.form == "요")))
                    {
                        // NIKL allows contextual adjective wishes, but the four
                        // quoted entries do not certify those readings. Keep
                        // existential/negative auxiliary owners, unlisted
                        // prefinals and inferred 군 + 요 independently Unknown.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible && let Some(i) = ending
                        && crate::engine::quoted_ra_exclamation(&analysis.morphemes[i].form)
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let is_command = crate::engine::quoted_command_exclamation(form);
                        let listed: &[&str] = if is_command { &["시"] } else { &["시", "더", "으리"] };
                        if morphs.iter().any(|c| matches!(c, Component::Morpheme(j)
                            if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                && !listed.contains(&analysis.morphemes[*j].form.as_str())))
                            || (is_command && (matches!(matched.entry.pos.as_str(), "형용사" | "보조 형용사")
                                || derived_adjective || matches!(class, Some(PredicateClass::Adjective))))
                            || (!is_command && !bare && lemma.kind != LemmaKind::Copula
                                && (matches!(matched.entry.pos.as_str(), "동사" | "형용사" | "보조 동사" | "보조 형용사")
                                    || derived_adjective || matches!(class, Some(PredicateClass::Verb | PredicateClass::Adjective)))
                                && lemma.text != "아니다")
                            || (matches!(form, "라는군" | "으라는군")
                                && analysis.morphemes.get(i + 1).is_some_and(|m|
                                    m.kind == MorphemeKind::Particle && m.form == "요"))
                        {
                            // Honorific/copular extensions, adjective wishes
                            // and inferred quoted 군 + 요 remain candidates,
                            // without automatic grammaticality certification.
                            status = Compatibility::Unknown;
                        }
                    }
                    if status == Compatibility::Compatible
                        && let Some(i) = ending
                        && matches!(analysis.morphemes[i].form.as_str(), "냐는군" | "느냐는군" | "으냐는군")
                        && analysis.morphemes.get(i + 1).is_some_and(|m|
                            m.kind == MorphemeKind::Particle && m.form == "요")
                    {
                        // The quoted contraction plus polite particle is an
                        // inferred candidate, not a directly reviewed source
                        // example. Preserve it without certifying the license
                        // or register; established owner conflicts still win.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible && let Some(i) = ending {
                        let form = analysis.morphemes[i].form.as_str();
                        let listed: Option<&[&str]> = if crate::engine::present_exclamation(form)
                            || crate::engine::copular_exclamation(form) {
                            Some(&["시"])
                        } else if matches!(form, "구나" | "군" | "군요" | "구려" | "구먼"
                            | "더구나" | "더구려" | "더구먼" | "더군" | "더군요") {
                            Some(&["시", "었", "겠"])
                        } else { None };
                        if listed.is_some_and(|ls| morphs.iter().any(|c|
                            matches!(c, Component::Morpheme(j) if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                && !ls.contains(&analysis.morphemes[*j].form.as_str()))))
                            || (bare && form == "더구나" && matched.entry.pos == "동사")
                        {
                            // The full 더구나 entry directly illustrates
                            // 잘되더구나 despite omitting verbs in its note.
                            // Keep generic verb readings without claiming a
                            // universal exclusion or a settled distribution.
                            status = Compatibility::Unknown;
                        }
                    }
                    if matches!(lemma.kind, LemmaKind::Predicate | LemmaKind::Auxiliary)
                        && let Some(Component::Morpheme(i)) = morphs.first()
                        && short_stem_conflict(&matched.entry, &analysis.morphemes[*i])
                    {
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::ShortStemEnding,
                            morpheme_index: Some(*i),
                        });
                    }
                    // The morpheme index belongs to this component group, not
                    // to every lemma sharing a unioned irregular rule name.
                    if matches!(lemma.kind, LemmaKind::Predicate | LemmaKind::Auxiliary) {
                        for recovery in spelling
                            .iter()
                            .filter(|r| morphs.contains(&Component::Morpheme(r.morpheme_index)))
                        {
                            use SpellingClass::*;
                            let consonant = |evidence: &Option<super::ConjugationEvidence>,
                                             regular| {
                                evidence.as_ref().map(|e| {
                                    if regular {
                                        !e.regular.is_empty()
                                    } else {
                                        !e.irregular.is_empty()
                                    }
                                })
                            };
                            let supported = match recovery.class {
                                HieutRegular => consonant(&matched.hieut, true),
                                HieutIrregular => consonant(&matched.hieut, false),
                                DigeutRegular => consonant(&matched.digeut, true),
                                DigeutIrregular => consonant(&matched.digeut, false),
                                SiotRegular => consonant(&matched.siot, true),
                                SiotIrregular => consonant(&matched.siot, false),
                                BieupRegular => consonant(&matched.bieup, true),
                                BieupIrregular => consonant(&matched.bieup, false),
                                ReuEuDeletion => {
                                    matched.reu.as_ref().map(|e| !e.eu_deletion.is_empty())
                                }
                                ReuDoubling => {
                                    matched.reu.as_ref().map(|e| !e.rieul_doubling.is_empty())
                                }
                                ReoAddition => matched.reu.as_ref().map(|e| !e.reo.is_empty()),
                                ReuUncontracted => {
                                    matched.reu.as_ref().map(|e| !e.uncontracted.is_empty())
                                }
                            };
                            if let Some(supported) = supported {
                                if !supported {
                                    status = Compatibility::Incompatible;
                                    conflicts.push(AttachmentConflict {
                                        rule: AttachmentRule::LexicalSpelling,
                                        morpheme_index: Some(recovery.morpheme_index),
                                    });
                                }
                            } else if status == Compatibility::Compatible {
                                status = Compatibility::Unknown;
                            }
                        }
                    }
                    if status == Compatibility::Compatible
                        && intention_connector.is_some()
                        && (derived_adjective
                            || lemma.kind == LemmaKind::Copula
                            || (intention_prefinal
                                && matches!(
                                    matched.entry.pos.as_str(),
                                    "동사" | "형용사" | "보조 동사" | "보조 형용사"
                                ))
                            || (lemma.kind == LemmaKind::Predicate
                                && matched.entry.pos == "형용사")
                            || (lemma.kind == LemmaKind::Auxiliary
                                && matches!(class, Some(PredicateClass::Adjective))
                                && matched.entry.pos == "보조 형용사"))
                    {
                        // The connective/auxiliary entries specify verbs, but
                        // NIKL Q&A 335000 leaves adjective state-making uses
                        // unresolved. Shortened-expression notes also conflict
                        // with tense/copula exclusions on their full expansions.
                        // Preserve uncertainty per entry, including inherited
                        // negatives and explicit 답다. Prefinals constrain
                        // only the immediate connector owner.
                        // Known role, ending and spelling conflicts above
                        // take precedence; no contextual sense is selected.
                        status = Compatibility::Unknown;
                    }
                    EntryAssessment {
                        id: matched.entry.id.clone(),
                        status,
                        conflicts,
                    }
                })
                .collect();
            lemmas.push(LemmaAssessment {
                lemma_index: *index,
                status: alternatives(entries.iter().map(|e| e.status)),
                entries,
            });
            // Preserve only represented structural knowledge, as the engine
            // does. A dictionary homonym must not lend its lexical class to a
            // different reading. Copulas reset the previous class; 답다 is an
            // explicitly adjectival derivation, unlike general 하다 suffixes.
            previous_class = if morphs.iter().any(|c| {
                matches!(c, Component::Morpheme(i)
                    if analysis.morphemes[*i].kind == MorphemeKind::Suffix
                    && analysis.morphemes[*i].form == "답다")
            }) {
                Some(PredicateClass::Adjective)
            } else {
                class
            };
            connector = ending;
        }
        let status = if lemmas
            .iter()
            .any(|l| l.status == Compatibility::Incompatible)
        {
            Compatibility::Incompatible
        } else if lemmas.iter().any(|l| l.status == Compatibility::Unknown) {
            Compatibility::Unknown
        } else {
            Compatibility::Compatible
        };
        ReadingAssessment { status, lemmas }
    }

    /// Retain whole analyses and update annotation indices and lemma references.
    /// Pass an owned/cloned WordAnalysis to keep a Session's cache unfiltered.
    /// Checks are recomputed for the supplied analyses, so a reordered or older
    /// annotation cannot apply a positional assessment to a different reading.
    pub fn filter(&mut self, analysis: &mut WordAnalysis, policy: DictionaryFilter) {
        let mut readings = Vec::new();
        analysis.analyses.retain(|a| {
            if !a.lemmas.iter().all(|l| self.has_match(l, false)) {
                return false;
            }
            let assessment = self.assess(a);
            if policy == DictionaryFilter::Compatible
                && assessment.status == Compatibility::Incompatible
            {
                return false;
            }
            readings.push(assessment);
            true
        });
        let retained: BTreeSet<_> = analysis.analyses.iter().flat_map(|a| &a.lemmas).collect();
        self.lemmas.retain(|m| retained.contains(&m.lemma));
        self.readings = readings;
    }
}
