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
    /// Recorded origin or individually reviewed lexical identity conflicts
    /// with the independently sourced bound root.
    DerivationalRoot,
    PresentDeclarativeVerb,
    BareAdjectivalQuestion,
    NegativeCopulaCommand,
    IntentionVerb,
    ResultTransferVerb,
    RepetitiveVerb,
    /// Five reviewed continuation auxiliaries require a verbal left owner.
    ContinuationVerb,
    /// Native 어 버리다 / 고 나다 exclude tense on the immediate connector owner.
    ContinuationLeftTense,
    /// Native 고 나다 places 시 on the preceding owner.
    GoNadaHonorific,
    /// Native 고 나다 excludes right-owner 겠.
    GoNadaFuture,
    /// Individually reviewed finite endings of native 고 나다.
    GoNadaFinalEnding,
    NeuraVerb,
    AuxiliaryClass,
    NegativeLexicalClass,
    AuxiliaryAdjectiveAdnominalClass,
    BarePresentAdnominalClass,
    ConjecturalAdnominalClass,
    PretenceAdnominalClass,
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

// Resolve only an unambiguous lexical class behind a represented 지-negative.
// Do not choose between homonyms or reuse an entry rejected by this spelling
// path. Unknown providers cannot prove a class. A token-initial auxiliary
// has no preceding owner; a known POS does not upgrade its lexical role.
// A suffix, copula or nonnegative auxiliary establishes another owner.
fn negative_lexical_class(
    annotation: &Annotation,
    analysis: &Analysis,
    mut preceding: &[Component],
    assessed: &[LemmaAssessment],
) -> Option<PredicateClass> {
    loop {
        let owner = preceding
            .iter()
            .rposition(|c| matches!(c, Component::Lemma(_)))?;
        let morphs = &preceding[owner + 1..];
        if morphs.iter().any(|c| {
            matches!(c, Component::Morpheme(i)
            if analysis.morphemes[*i].kind == MorphemeKind::Suffix)
        }) {
            return None;
        }
        let connector = morphs.iter().find_map(|c| match c {
            Component::Morpheme(i) if analysis.morphemes[*i].kind == MorphemeKind::Ending => {
                Some(analysis.morphemes[*i].form.as_str())
            }
            _ => None,
        });
        if connector != Some("지") {
            return None;
        }
        let Component::Lemma(index) = preceding[owner] else {
            return None;
        };
        let lemma = &analysis.lemmas[index];
        if lemma.kind == LemmaKind::Auxiliary
            && matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
        {
            preceding = &preceding[..owner];
            continue;
        }
        if lemma.kind != LemmaKind::Predicate {
            return None;
        }
        let slot = assessed.iter().find(|slot| slot.lemma_index == index)?;
        let matches = &annotation
            .lemmas
            .iter()
            .find(|m| m.lemma == *lemma)?
            .entries;
        let mut verb = false;
        let mut adjective = false;
        for entry in &slot.entries {
            // A later continuation conflict does not erase the lexical class
            // needed to assess this intervening negative's own entry. Spelling,
            // role and other earlier conflicts still disqualify the evidence.
            if entry.status == Compatibility::Incompatible
                && entry
                    .conflicts
                    .iter()
                    .any(|c| c.rule != AttachmentRule::ContinuationVerb)
            {
                continue;
            }
            match matches
                .iter()
                .find(|m| m.entry.id == entry.id)?
                .effective_pos()
            {
                "동사" | "보조 동사" => verb = true,
                "형용사" | "보조 형용사" => adjective = true,
                _ => return None,
            }
        }
        return match (verb, adjective) {
            (true, false) => Some(PredicateClass::Verb),
            (false, true) => Some(PredicateClass::Adjective),
            _ => None,
        };
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
fn expressive_hada_connector(analysis: &Analysis, rest: &[Component]) -> Option<usize> {
    eo_auxiliary_connector(analysis, rest, "하다")
}

// Scope this requirement to the reviewed native auxiliary identities. In
// particular, adjective examples of 가다 and 오다 prohibit a family-wide
// "continuation means verb" inference. Only represented 지-negatives carry
// the dependency back to an earlier owner; all other auxiliaries reset it.
// The caller classifies its own suffixes, while a later suffix resets ownership.
fn continuation_verb_connector(
    annotation: &Annotation,
    analysis: &Analysis,
    mut rest: &[Component],
) -> Option<usize> {
    let mut first = true;
    loop {
        let next = rest.iter().position(|c| matches!(c, Component::Lemma(_)))?;
        let morphs = &rest[..next];
        if !first
            && morphs.iter().any(|c| {
                matches!(c, Component::Morpheme(i)
                if analysis.morphemes[*i].kind == MorphemeKind::Suffix)
            })
        {
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
        let native_id = match (lemma.text.as_str(), form) {
            ("내다", "어") => "krdict:60625",
            ("나다", "어" | "고") => "krdict:62134",
            ("나가다", "어") => "krdict:26813",
            ("버리다", "어") => "krdict:62601",
            ("치우다", "어") => "krdict:74290",
            _ => "",
        };
        if !native_id.is_empty()
            && annotation
                .lemmas
                .iter()
                .find(|m| m.lemma == *lemma)
                .is_some_and(|m| {
                    m.entries.iter().any(|entry| {
                        entry.entry.id == native_id
                            && entry.entry.headword == lemma.text
                            && entry.entry.homonym == "2"
                            && entry.entry.pos == "보조 동사"
                            && entry.effective_pos() == "보조 동사"
                    })
                })
        {
            return Some(connector);
        }
        if form != "지" || !matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
        {
            return None;
        }
        first = false;
        rest = &rest[next + 1..];
    }
}

// Provider names or reused IDs alone cannot establish these native restrictions.
fn native_auxiliary(matched: &super::EntryMatch, head: &str, id: &str) -> bool {
    matched.entry.id == id
        && matched.entry.headword == head
        && matched.entry.homonym == "2"
        && matched.entry.pos == "보조 동사"
        && matched.effective_pos() == "보조 동사"
}

fn owner_prefinal(analysis: &Analysis, morphs: &[Component], forms: &[&str]) -> Option<usize> {
    morphs.iter().find_map(|c| match c {
        Component::Morpheme(i)
            if analysis.morphemes[*i].kind == MorphemeKind::Prefinal
                && forms.contains(&analysis.morphemes[*i].form.as_str()) =>
        {
            Some(*i)
        }
        _ => None,
    })
}

fn go_nada_final_ending(analysis: &Analysis, morphs: &[Component], ending: usize) -> bool {
    match analysis.morphemes[ending].form.as_str() {
        "는다" | "어요" | "으세요" => true,
        // The same polite final spelling also has an 어 + 요 path. Plain
        // connective 어 and particles on 어서 remain independent.
        "어" => morphs
            .iter()
            .position(|c| *c == Component::Morpheme(ending))
            .is_some_and(|i| {
                matches!(&morphs[i + 1..], [Component::Morpheme(j)]
                if analysis.morphemes[*j].kind == MorphemeKind::Particle
                && analysis.morphemes[*j].form == "요")
            }),
        _ => false,
    }
}

// Both expressive 하다 and repetitive 대다 depend on the lexical head
// through 지-negatives only. Other auxiliaries and derivations start their
// own class boundary; source restrictions must not leak across that owner.
fn eo_auxiliary_connector(
    analysis: &Analysis,
    mut rest: &[Component],
    target: &str,
) -> Option<usize> {
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
        if lemma.text == target && form == "어" {
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

// NIKL 327283 identifies the limited commands 섰거라 and 물렀거라;
// the latter names the retreat sense, not the softening/adjective homonyms.
// This establishes one attested sense in an entry, without selecting a sense
// from sentence context or extending the license to another lexical owner.
fn reviewed_past_direct_command(
    entry: &super::EntrySummary,
    lemma: &crate::Lemma,
    analysis: &Analysis,
    morphs: &[Component],
) -> bool {
    if lemma.kind != LemmaKind::Predicate
        || lemma.text != entry.headword
        || !matches!(
            (
                entry.id.as_str(),
                entry.headword.as_str(),
                entry.pos.as_str()
            ),
            ("krdict:68756", "서다", "동사") | ("krdict:55296", "무르다", "동사")
        )
    {
        return false;
    }
    let [Component::Morpheme(past), Component::Morpheme(final_)] = morphs else {
        return false;
    };
    let past = &analysis.morphemes[*past];
    let final_ = &analysis.morphemes[*final_];
    past.kind == MorphemeKind::Prefinal
        && past.form == "었"
        && final_.kind == MorphemeKind::Ending
        && final_.form == "거라"
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
        // Prefixes precede the first lemma in reading order and own no lexical
        // slot. Continue at the base so its entries and later copulas are still
        // assessed independently. `breakdown` already validated the prefix shape.
        while components.first().is_some_and(|c| {
            matches!(c, Component::Morpheme(i)
                if analysis.morphemes[*i].kind == MorphemeKind::Prefix)
        }) {
            components = &components[1..];
        }
        let mut previous_class = None;
        let mut connector: Option<usize> = None;
        let mut previous_morphs: &[Component] = &[];
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
            let negative_lexical = if class.is_none()
                && lemma.kind == LemmaKind::Auxiliary
                && matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
            {
                negative_lexical_class(
                    self,
                    analysis,
                    &order[..order.len() - rest.len() - 1],
                    &lemmas,
                )
            } else {
                None
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
            // NIKL consultation 8390 recognizes 없다-influenced 없지 않느냐.
            // Keep that immediate owner, including an internal particle, apart
            // from ordinary adjectival negatives. Missing left context cannot
            // decide whether this explicitly acknowledged use is present.
            let negative_question_exception = lemma.text == "않다"
                && connector.is_some_and(|i| analysis.morphemes[i].form == "지")
                && order[..order.len() - rest.len() - 1]
                    .iter()
                    .rev()
                    .find_map(|c| match c {
                        Component::Lemma(i) => Some(analysis.lemmas[*i].text.as_str()),
                        _ => None,
                    })
                    == Some("없다");
            // KRDict 75275/75276 and 85853 distinguish bare present 는
            // from adjective/copula 은. Evidence belongs to the immediate
            // connector owner; prefinals and auxiliary owners stay separate.
            let conjectural_present = bare
                && ending.is_some_and(|i| analysis.morphemes[i].form == "는")
                && components.first().is_some_and(|c| {
                    matches!(c, Component::Lemma(i)
                        if analysis.lemmas[*i].kind == LemmaKind::Auxiliary
                        && matches!(analysis.lemmas[*i].text.as_str(), "듯하다" | "듯싶다"))
                });
            let pretence_present = bare
                && ending.is_some_and(|i| analysis.morphemes[i].form == "는")
                && components.first().is_some_and(|c| {
                    matches!(c, Component::Lemma(i)
                        if analysis.lemmas[*i].kind == LemmaKind::Auxiliary
                        && matches!(analysis.lemmas[*i].text.as_str(), "양하다" | "척하다" | "체하다"))
                });
            let expressive_connector = if lemma.kind == LemmaKind::Predicate {
                expressive_hada_connector(analysis, rest)
            } else {
                None
            };
            let repetitive_connector = (lemma.kind == LemmaKind::Predicate)
                .then(|| eo_auxiliary_connector(analysis, rest, "대다"))
                .flatten();
            let habitual_ending = (lemma.kind == LemmaKind::Predicate)
                .then(|| habitual_condition_ending(analysis, rest))
                .flatten();
            let intention_connector = intention_auxiliary_connector(analysis, rest);
            let derived_adjective = morphs.iter().any(|c| {
                matches!(c, Component::Morpheme(i)
                    if analysis.morphemes[*i].kind == MorphemeKind::Suffix
                    && analysis.morphemes[*i].form == "답다")
            });
            let unclassified_derivation = !derived_adjective
                && morphs.iter().any(|c| {
                    matches!(c, Component::Morpheme(i)
                    if analysis.morphemes[*i].kind == MorphemeKind::Suffix)
                });
            let continuation_connector = continuation_verb_connector(self, analysis, rest);
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
                    let pos = matched.effective_pos();
                    // This independently sourced analysis explicitly names a
                    // bound noun, unlike the broad nominal role used by whole
                    // words. Preserve every lookup entry but record the known
                    // role conflict for other nominal homonyms (tooth, number,
                    // pronoun, etc.); no within-entry sense is selected.
                    if *index == 1
                        && analysis
                            .rules
                            .iter()
                            .any(|r| r == "derivation.nominal.bound_i")
                        && status == Compatibility::Compatible
                        && pos != "의존 명사"
                    {
                        status = Compatibility::Incompatible;
                    }
                    // A token-initial predicate can be a separately written
                    // auxiliary (먹고 싶었다). Its preceding word/connector is
                    // outside this analysis; do not call that a POS conflict.
                    if *index == 0
                        && lemma.kind == LemmaKind::Predicate
                        && matches!(pos, "보조 동사" | "보조 형용사")
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
                    if status == Compatibility::Compatible
                        && (conjectural_present || pretence_present)
                        && (lemma.kind == LemmaKind::Copula
                            || (lemma.kind == LemmaKind::Predicate
                                && pos == "형용사"
                                && !lemma.text.ends_with("있다")
                                && !lemma.text.ends_with("없다")
                                && lemma.text != "계시다"))
                    {
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: if conjectural_present {
                                AttachmentRule::ConjecturalAdnominalClass
                            } else {
                                AttachmentRule::PretenceAdnominalClass
                            },
                            morpheme_index: ending,
                        });
                    }
                    // 양하다 has both auxiliary POS classes. Assess the
                    // right owner's inflection per entry rather than choosing
                    // a shared class or borrowing one from the earlier head.
                    // Standalone context uncertainty cannot license a known
                    // adjective's present verb ending, but remains otherwise.
                    if matches!(status, Compatibility::Compatible | Compatibility::Unknown)
                        && lemma.text == "양하다"
                        && pos == "보조 형용사"
                        && (lemma.kind == LemmaKind::Auxiliary
                            || (*index == 0 && lemma.kind == LemmaKind::Predicate))
                        && let Some(i) = ending
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let rule = if crate::engine::present_declarative(form) {
                            Some(AttachmentRule::PresentDeclarativeVerb)
                        } else if bare && form == "는" {
                            Some(AttachmentRule::PretenceAdnominalClass)
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
                    if *index == 1
                        && analysis.rules.iter().any(|r| r == "derivation.nominal.root_compound")
                        && let Some(&(_, _, _, expected)) = crate::grammar::NOUN_I_ROOT_COMPOUNDS
                            .iter().find(|&&(_, left, root, _)| {
                                analysis.lemmas[0].text == left && lemma.text == root
                            })
                        && (matched.origins.as_ref().is_some_and(|origins|
                            !origins.is_empty() && !origins.iter().any(|origin| origin == expected))
                            // The native 선 matchmaking entry has no recorded
                            // origin. Its independently reviewed full senses
                            // identify marriage introductions and debuts, not the fan root.
                            // No conclusion is drawn from origin absence alone.
                            || (matched.entry.id == "krdict:63243"
                                && matched.entry.headword == "선"
                                && pos == "명사"))
                    {
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::DerivationalRoot,
                            morpheme_index: None,
                        });
                    }
                    if lemma.kind == LemmaKind::Auxiliary
                        && status == Compatibility::Compatible
                        && matches!(
                            (class, pos),
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
                        && matches!(
                            (negative_lexical, pos),
                            (Some(PredicateClass::Verb), "보조 형용사")
                                | (Some(PredicateClass::Adjective), "보조 동사")
                        )
                    {
                        // The six native negative entries distinguish verb
                        // and adjective owners for 지. 다/다가 못하다 is a
                        // separate adjective use handled by auxiliary_class.
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::NegativeLexicalClass,
                            morpheme_index: connector,
                        });
                    }
                    // The source POS identifies this adjective entry even
                    // when a standalone auxiliary lacks its left context.
                    // KRDict 85033/85037 require verbal present inflection;
                    // 85853 lists the existential exceptions for bare -는.
                    // Own prefinals and later owners remain independent, and
                    // earlier proved connector conflicts take precedence.
                    if matches!(status, Compatibility::Compatible | Compatibility::Unknown)
                        && pos == "보조 형용사"
                        && (lemma.kind == LemmaKind::Auxiliary
                            || (*index == 0 && lemma.kind == LemmaKind::Predicate))
                        && let Some(i) = ending
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let rule = if crate::engine::present_declarative(form) {
                            Some(AttachmentRule::PresentDeclarativeVerb)
                        } else if bare && form == "는"
                            && !lemma.text.ends_with("있다")
                            && !lemma.text.ends_with("없다")
                            && lemma.text != "계시다"
                        {
                            Some(AttachmentRule::AuxiliaryAdjectiveAdnominalClass)
                        } else if bare && form == "느냐"
                            && !lemma.text.ends_with("있다")
                            && !lemma.text.ends_with("없다")
                            && lemma.text != "계시다"
                        {
                            // KRDict 76231 lists verbs and existential exceptions.
                            if negative_question_exception {
                                None
                            } else if matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")
                                && class.is_none()
                                && negative_lexical.is_none()
                            {
                                status = Compatibility::Unknown;
                                None
                            } else {
                                Some(AttachmentRule::BareVerbalQuestion)
                            }
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
                        && pos == "동사"
                        && expressive_connector.is_some()
                    {
                        // KRDict 62888 sense 9 describes adjective attachment,
                        // but NIKL also licenses some verbs (꺼려 하다,
                        // 내키지 않아 하다). Broad verb POS cannot decide this
                        // lexical subset, including through negative auxiliaries.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible
                        && pos == "형용사"
                        && let Some(i) = repetitive_connector
                    {
                        // NIKL §3.6.27 p.514 explicitly rejects 비싸 대서,
                        // 예뻐 대서 and 어려워 댄다. Assess each POS homonym
                        // independently; verb homonyms and unknown providers
                        // remain, with no contextual sense or register choice.
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::RepetitiveVerb,
                            morpheme_index: Some(i),
                        });
                    }
                    if status == Compatibility::Compatible
                        && pos == "형용사"
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
                    // KRDict 85853 licenses bare present -는 after verbs and
                    // the listed existential adjectives. Keep those exceptions,
                    // POS homonyms, prefinals and particle alternatives distinct.
                    // A represented copula is its own owner, not the nominal's
                    // class. Preserve earlier family-specific conflicts.
                    if status == Compatibility::Compatible
                        && bare
                        && ending.is_some_and(|i| analysis.morphemes[i].form == "는")
                        && (lemma.kind == LemmaKind::Copula
                            || (lemma.kind == LemmaKind::Predicate
                                && pos == "형용사"
                                && !lemma.text.ends_with("있다")
                                && !lemma.text.ends_with("없다")
                                && lemma.text != "계시다"))
                    {
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: AttachmentRule::BarePresentAdnominalClass,
                            morpheme_index: ending,
                        });
                    }
                    // Dictionary classes belong to the lexical head, not its
                    // auxiliary, derived suffix or a later copula's ending.
                    // The represented copula owns its question independently
                    // of the nominal. Bare 느냐 (76231) requires a verb or
                    // existential; bare 으냐 (76235) requires an adjective.
                    // General 냐 and preceding prefinals remain separate.
                    if lemma.kind == LemmaKind::Copula
                        && status == Compatibility::Compatible
                        && bare
                        && let Some(i) = ending
                        && matches!(analysis.morphemes[i].form.as_str(), "느냐" | "으냐")
                    {
                        status = Compatibility::Incompatible;
                        conflicts.push(AttachmentConflict {
                            rule: if analysis.morphemes[i].form == "느냐" {
                                AttachmentRule::BareVerbalQuestion
                            } else {
                                AttachmentRule::BareAdjectivalQuestion
                            },
                            morpheme_index: Some(i),
                        });
                    }
                    if lemma.kind == LemmaKind::Predicate
                        && status == Compatibility::Compatible
                        && let Some(i) = ending
                    {
                        let form = analysis.morphemes[i].form.as_str();
                        let adjective = pos == "형용사";
                        let verb = pos == "동사";
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
                            && (matches!(form, "느냐" | "느냐지만" | "느냐니까" | "느냬" | "느냐느니")
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
                        && ending.is_some_and(|i| {
                            matches!(analysis.morphemes[i].form.as_str(), "거라" | "너라")
                        })
                        && (!bare
                            || !matches!(pos, "동사" | "보조 동사"))
                        && !reviewed_past_direct_command(&matched.entry, lemma, analysis, morphs)
                    {
                        // The modern sources establish direct verbal stems.
                        // Honorific/tense/mood and adjectival or copular wishes
                        // need separate review; do not invent a POS-wide ban.
                        status = Compatibility::Unknown;
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
                            && matches!(pos, "동사" | "보조 동사")
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
                    if status == Compatibility::Compatible && let Some(i) = ending
                        && analysis.morphemes[i].form == "더라는군"
                        && analysis.morphemes.get(i + 1).is_some_and(|m|
                            m.kind == MorphemeKind::Particle && m.form == "요")
                    {
                        // NIKL's terminal 군 + 요 transfers through the native
                        // experience-report expansion. No direct quoted example
                        // was found; do not certify that contextual license.
                        status = Compatibility::Unknown;
                    }
                    if lemma.kind == LemmaKind::Predicate
                        && status == Compatibility::Unknown && bare
                        && let Some(i) = ending
                        && crate::engine::quoted_question_report(&analysis.morphemes[i].form)
                    {
                        let form = analysis.morphemes[i].form.as_str();
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
                        && ((pos == "형용사"
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
                    if status == Compatibility::Compatible
                        && ending.is_some_and(|i| analysis.morphemes[i].form == "읍시다")
                        && (matches!(pos, "형용사" | "보조 형용사")
                            || derived_adjective
                            || matches!(class, Some(PredicateClass::Adjective))
                            || (lemma.kind == LemmaKind::Auxiliary
                                && class.is_none()
                                && matches!(lemma.text.as_str(), "않다" | "아니하다" | "못하다")))
                    {
                        // The formal proposal entries specify verbs. NIKL
                        // 318597 describes contextual adjective wishes, so a
                        // POS label cannot justify pruning those hypotheses.
                        // Unclassified negatives do not borrow lexical POS
                        // from a preceding homonym. Existing conflicts win.
                        status = Compatibility::Unknown;
                    }
                    if status == Compatibility::Compatible && let Some(i) = ending
                        && crate::engine::quoted_proposal_exclamation(&analysis.morphemes[i].form)
                        && (matches!(pos, "형용사" | "보조 형용사")
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
                        && analysis.morphemes[i].form == "으랴"
                        && morphs.iter().any(|c| matches!(c, Component::Morpheme(j)
                            if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                && !matches!(analysis.morphemes[*j].form.as_str(), "시" | "었" | "겠")))
                    {
                        // The four native -랴/-으랴 entries cover rhetorical,
                        // offer and enumerative senses collectively. Their
                        // notes name honorific/past/modal prefinals; other
                        // immediate-owner extensions remain hypotheses without
                        // certifying an unreviewed sense or register. A prior
                        // auxiliary owner's markers do not supply this test.
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
                            || (is_command && (matches!(pos, "형용사" | "보조 형용사")
                                || derived_adjective || matches!(class, Some(PredicateClass::Adjective))))
                            || (!is_command && !bare && lemma.kind != LemmaKind::Copula
                                && (matches!(pos, "동사" | "형용사" | "보조 동사" | "보조 형용사")
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
                            | "더구나" | "더구려" | "더구먼" | "더군" | "더군요"
                            | "건만" | "건마는") {
                            Some(&["시", "었", "겠"])
                        } else { None };
                        if listed.is_some_and(|ls| morphs.iter().any(|c|
                            matches!(c, Component::Morpheme(j) if analysis.morphemes[*j].kind == MorphemeKind::Prefinal
                                && !ls.contains(&analysis.morphemes[*j].form.as_str()))))
                            || (bare && form == "더구나" && pos == "동사")
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
                                WrittenVowelA | WrittenVowelEo | EuUncontracted => {
                                    matched.written_vowel.as_ref().and_then(|e| {
                                        let (own, opposite) = match recovery.class {
                                            WrittenVowelA => (&e.a, &e.eo),
                                            WrittenVowelEo => (&e.eo, &e.a),
                                            _ => (&e.uncontracted, &e.a),
                                        };
                                        if !own.is_empty() {
                                            Some(true)
                                        } else if !opposite.is_empty()
                                            || (recovery.class == EuUncontracted && !e.eo.is_empty())
                                        {
                                            // NIKL Articles 16/18 and the reviewed ㅡ
                                            // paradigms establish the incompatible
                                            // alternate series/deletion. An unrelated
                                            // or empty written form proves nothing.
                                            Some(false)
                                        } else {
                                            None
                                        }
                                    })
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
                                    pos,
                                    "동사" | "형용사" | "보조 동사" | "보조 형용사"
                                ))
                            || (lemma.kind == LemmaKind::Predicate
                                && pos == "형용사")
                            || (lemma.kind == LemmaKind::Auxiliary
                                && matches!(class, Some(PredicateClass::Adjective))
                                && pos == "보조 형용사"))
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
                    if matches!(status, Compatibility::Compatible | Compatibility::Unknown)
                        && let Some(i) = continuation_connector
                    {
                        // Judge this entry's class, never a shared homonym's.
                        // A copula and reviewed 답다 derivation are explicit
                        // nonverbal owners. Other derivations and unknown POS
                        // cannot lend the base's class to the derived owner.
                        let nonverbal = !unclassified_derivation
                            && (derived_adjective || lemma.kind == LemmaKind::Copula
                                || matches!(pos, "형용사" | "보조 형용사"));
                        // Native 중요성/최저치 examples use adjective 아프다
                        // directly before 고 나다. Preserve that source tension;
                        // do not invent a verb class or propagate it through 지.
                        let source_tension = matched.entry.id == "krdict:62239"
                            && matched.entry.headword == "아프다"
                            && matched.entry.homonym == "0"
                            && matched.entry.pos == "형용사"
                            && pos == "형용사"
                            && !derived_adjective
                            && !unclassified_derivation
                            && Some(i) == ending
                            && analysis.morphemes[i].form == "고"
                            && components.first().is_some_and(|c| {
                                matches!(c, Component::Lemma(n)
                                    if analysis.lemmas[*n].kind == LemmaKind::Auxiliary
                                    && analysis.lemmas[*n].text == "나다"
                                    && self.lemmas.iter().find(|m| m.lemma == analysis.lemmas[*n])
                                        .is_some_and(|m| m.entries.iter().any(|e|
                                            native_auxiliary(e, "나다", "krdict:62134"))))
                            });
                        if source_tension {
                            status = Compatibility::Unknown;
                        } else if nonverbal {
                            status = Compatibility::Incompatible;
                            conflicts.push(AttachmentConflict {
                                rule: AttachmentRule::ContinuationVerb,
                                morpheme_index: Some(i),
                            });
                        } else if (unclassified_derivation
                            || !matches!(pos, "동사" | "보조 동사"))
                            && status == Compatibility::Compatible
                        {
                            status = Compatibility::Unknown;
                        }
                    }
                    if matches!(status, Compatibility::Compatible | Compatibility::Unknown)
                        && lemma.kind == LemmaKind::Auxiliary
                    {
                        let go_nada = connector.is_some_and(|i| analysis.morphemes[i].form == "고")
                            && native_auxiliary(matched, "나다", "krdict:62134");
                        let eo_beorida = connector.is_some_and(|i| analysis.morphemes[i].form == "어")
                            && native_auxiliary(matched, "버리다", "krdict:62601");
                        let left_tense = (go_nada || eo_beorida)
                            .then(|| owner_prefinal(analysis, previous_morphs, &["었", "겠"]))
                            .flatten();
                        let honorific = go_nada.then(|| owner_prefinal(analysis, morphs, &["시"])).flatten();
                        let future = go_nada.then(|| owner_prefinal(analysis, morphs, &["겠"])).flatten();
                        let final_ending = ending.filter(|i|
                            go_nada && go_nada_final_ending(analysis, morphs, *i));
                        if go_nada {
                            // Seventeen complete native 고 났더니 examples
                            // conflict with the guide's broad right-past ban.
                            if owner_prefinal(analysis, morphs, &["었"]).is_some() {
                                status = Compatibility::Unknown;
                            }
                        }
                        for (rule, i) in [
                            left_tense.map(|i| (AttachmentRule::ContinuationLeftTense, i)),
                            honorific.map(|i| (AttachmentRule::GoNadaHonorific, i)),
                            future.map(|i| (AttachmentRule::GoNadaFuture, i)),
                            final_ending.map(|i| (AttachmentRule::GoNadaFinalEnding, i)),
                        ].into_iter().flatten() {
                            status = Compatibility::Incompatible;
                            conflicts.push(AttachmentConflict {
                                rule,
                                morpheme_index: Some(i),
                            });
                        }
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
            previous_morphs = morphs;
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
