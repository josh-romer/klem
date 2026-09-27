//! Scoped lexical attachment evidence, separate from dictionary-free generation.
//! See docs/dictionary-attachments.md for sources, exceptions and exclusions.
use super::{Annotation, Compatibility};
use crate::engine::{PredicateClass, auxiliary_class};
use crate::{Analysis, LemmaKind, MorphemeKind, WordAnalysis, breakdown::Component};
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
    AuxiliaryClass,
    LiteraryAssertionClass,
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

impl Annotation {
    /// Check a complete analysis against this annotation's headword evidence.
    /// Missing entries, unclassified roles and unknown POS remain unknown.
    /// Only reviewed lexical constraints are applied; no sense is selected.
    pub fn assess(&self, analysis: &Analysis) -> ReadingAssessment {
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
                        } else if crate::engine::present_declarative(form) && adjective {
                            Some(AttachmentRule::PresentDeclarativeVerb)
                        } else if adjective && crate::engine::verbal_intention(form) {
                            Some(AttachmentRule::IntentionVerb)
                        } else if adjective && crate::engine::result_connective(form) {
                            Some(AttachmentRule::ResultTransferVerb)
                        } else if bare && verb && crate::engine::adjectival_question(form) {
                            // Existential/honorific question paradigms remain
                            // COV-019h. Do not decide them from a broad POS label.
                            if matches!(lemma.text.as_str(), "있다" | "없다" | "계시다") {
                                status = Compatibility::Unknown;
                                None
                            } else {
                                Some(AttachmentRule::BareAdjectivalQuestion)
                            }
                        } else if adjective && lemma.text == "아니다" && form == "으라니" {
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
