//! Explicit, dictionary-backed missing-space hypotheses. Word candidates are immutable.
//! This searches nominal case phrases followed by a lexical predicate, including
//! multiple nominal phrases. It does not validate sentence grammar or rank senses.
use crate::dictionary::{Annotation, Dictionary, DictionaryFilter, DictionarySession, Result};
use crate::{Analysis, LemmaKind, MorphemeKind, Session, TokenAnalysis, TokenKind, WordAnalysis};
use serde::{Deserialize, Serialize};
use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;

/// Per-word work/output bounds. A reached bound is reported, never silent.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SpacingLimits {
    pub token_chars: usize,
    pub segment_probes: usize,
    pub alternatives: usize,
}
impl Default for SpacingLimits {
    fn default() -> Self {
        Self {
            token_chars: 64,
            segment_probes: 256,
            alternatives: 16,
        }
    }
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum SpacingLimit {
    TokenChars,
    SegmentProbes,
    Alternatives,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SpacingSegment {
    #[serde(flatten)]
    pub record: TokenAnalysis,
    pub dictionary: Annotation,
    pub breakdowns: Vec<Option<Vec<crate::breakdown::Component>>>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SpacingHypothesis {
    /// Original substrings joined with proposed spaces; never an input rewrite.
    pub spaced: String,
    /// Absolute UTF-8 positions in the original input, at which spaces are proposed.
    pub inserted_at: Vec<usize>,
    /// Each word has independent alternatives and dictionary assessments.
    pub records: Vec<SpacingSegment>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct SpacingSuggestions {
    pub rule: &'static str,
    pub alternatives: Vec<SpacingHypothesis>,
    /// Exhaustive only for this rule template and connected dictionary, within bounds.
    pub complete: bool,
    pub limited_by: Vec<SpacingLimit>,
    pub segment_probes: usize,
    pub limits: SpacingLimits,
}
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
enum Role {
    Case,
    Predicate,
}
fn case_form(form: &str) -> bool {
    crate::grammar::particles()
        .iter()
        .any(|p| p.class <= 2 && p.form == form)
}
fn nominal_case(a: &Analysis) -> bool {
    let tail = a
        .morphemes
        .iter()
        .rev()
        .take_while(|m| m.kind == MorphemeKind::Particle)
        .collect::<Vec<_>>();
    if !tail.iter().any(|m| case_form(&m.form)) {
        return false;
    }
    // Nominal roots/derivations or explicit nominalizations, never an arbitrary
    // connective followed by a particle. Each word is checked independently.
    (a.lemmas.len() == 1
        && (a.lemmas[0].kind == LemmaKind::Nominal
            || a.rules.iter().any(|r| r == "suffix.nominal.i"))
        && a.morphemes[..a.morphemes.len() - tail.len()]
            .iter()
            .all(|m| m.kind == MorphemeKind::Suffix && m.form != "답다"))
        || a.morphemes
            .len()
            .checked_sub(tail.len() + 1)
            .and_then(|i| a.morphemes.get(i))
            .is_some_and(|m| {
                m.kind == MorphemeKind::Ending && matches!(m.form.as_str(), "음" | "기")
            })
}
fn maybe_case(surface: &str) -> bool {
    let normalized: String = surface.nfc().collect();
    crate::grammar::particles()
        .iter()
        .any(|p| normalized.ends_with(p.form))
        || matches!(crate::hangul::coda(&normalized), Some(4 | 8)) // contracted topic ㄴ / object ㄹ
}
struct Search<'a, 'd, D: Dictionary + ?Sized> {
    source: &'a str,
    offset: usize,
    session: &'a mut Session,
    dictionary: &'a mut DictionarySession<'d, D>,
    cache: HashMap<(usize, usize, Role), Option<SpacingSegment>>,
    result: SpacingSuggestions,
    // A suffix that has no complete continuation is independent of its prefix.
    // Cache exhausted dead ends so ambiguous prefixes cannot multiply work.
    dead_starts: HashSet<usize>,
}
impl<D: Dictionary + ?Sized> Search<'_, '_, D> {
    fn limit(&mut self, limit: SpacingLimit) {
        self.result.complete = false;
        if !self.result.limited_by.contains(&limit) {
            self.result.limited_by.push(limit);
        }
    }
    fn segment(&mut self, start: usize, end: usize, role: Role) -> Result<Option<SpacingSegment>> {
        let key = (start, end, role);
        if let Some(s) = self.cache.get(&key) {
            return Ok(s.clone());
        }
        let surface = &self.source[start..end];
        if role == Role::Case && !maybe_case(surface) {
            return Ok(None);
        }
        if self.result.segment_probes >= self.result.limits.segment_probes {
            self.limit(SpacingLimit::SegmentProbes);
            return Ok(None);
        }
        self.result.segment_probes += 1;
        let raw = self.session.analyze_word(surface)?;
        let mut analysis = WordAnalysis {
            normalized: raw.normalized.clone(),
            analyses: raw
                .analyses
                .iter()
                .filter(|a| match role {
                    Role::Case => nominal_case(a),
                    // A predicate lookup lemma before a noun suffix is a
                    // nominal word, not a sentence predicate for this template.
                    Role::Predicate => {
                        !a.rules.iter().any(|r| r == "suffix.nominal.i")
                            && a.lemmas
                                .first()
                                .is_some_and(|l| l.kind == LemmaKind::Predicate)
                    }
                })
                .cloned()
                .collect(),
        };
        let mut dictionary = self.dictionary.annotate(&analysis)?;
        dictionary.filter(&mut analysis, DictionaryFilter::Compatible);
        let value = (!analysis.analyses.is_empty()).then(|| SpacingSegment {
            breakdowns: analysis.analyses.iter().map(|a| a.breakdown()).collect(),
            record: TokenAnalysis {
                surface: surface.into(),
                span: self.offset + start..self.offset + end,
                kind: TokenKind::Word,
                analysis: Some(Arc::new(analysis)),
            },
            dictionary,
        });
        self.cache.insert(key, value.clone());
        Ok(value)
    }
    fn walk(&mut self, start: usize, path: &mut Vec<SpacingSegment>) -> Result<()> {
        if self.dead_starts.contains(&start) {
            return Ok(());
        }
        let previous_alternatives = self.result.alternatives.len();
        if !path.is_empty()
            && let Some(last) = self.segment(start, self.source.len(), Role::Predicate)?
        {
            if self.result.alternatives.len() >= self.result.limits.alternatives {
                self.limit(SpacingLimit::Alternatives);
                return Ok(());
            }
            let mut records = path.clone();
            records.push(last);
            self.result.alternatives.push(SpacingHypothesis {
                spaced: records
                    .iter()
                    .map(|s| s.record.surface.as_str())
                    .collect::<Vec<_>>()
                    .join(" "),
                inserted_at: records
                    .iter()
                    .skip(1)
                    .map(|s| s.record.span.start)
                    .collect(),
                records,
            });
        }
        if self.result.limited_by.contains(&SpacingLimit::Alternatives) {
            return Ok(());
        }
        let cuts = self.source[start..]
            .char_indices()
            .skip(1)
            .map(|(i, _)| start + i)
            .collect::<Vec<_>>();
        for end in cuts.into_iter().rev() {
            if let Some(left) = self.segment(start, end, Role::Case)? {
                path.push(left);
                self.walk(end, path)?;
                path.pop();
            }
            if !self.result.complete {
                break;
            }
        }
        if self.result.complete && self.result.alternatives.len() == previous_alternatives {
            self.dead_starts.insert(start);
        }
        Ok(())
    }
}
/// Preserve the word analysis and return separate spacing alternatives. Offsets
/// refer to `word` in its original encoding, including decomposed Hangul. Words
/// absent from the dictionary remain absent, and unknown compatibility survives.
pub fn suggest<D: Dictionary + ?Sized>(
    session: &mut Session,
    dictionary: &mut DictionarySession<'_, D>,
    word: &str,
    original_start: usize,
    limits: SpacingLimits,
) -> Result<SpacingSuggestions> {
    if word.is_empty() {
        return Err(crate::Error::EmptyWord.into());
    }
    if word.chars().any(char::is_whitespace) {
        return Err(crate::Error::WhitespaceInWord.into());
    }
    original_start
        .checked_add(word.len())
        .ok_or("spacing offset overflows usize")?;
    let mut result = SpacingSuggestions {
        rule: "spacing.nominal_case_predicate",
        alternatives: Vec::new(),
        complete: true,
        limited_by: Vec::new(),
        segment_probes: 0,
        limits,
    };
    if word.nfc().count() > limits.token_chars {
        result.complete = false;
        result.limited_by.push(SpacingLimit::TokenChars);
        return Ok(result);
    }
    let mut search = Search {
        source: word,
        offset: original_start,
        session,
        dictionary,
        cache: HashMap::new(),
        dead_starts: HashSet::new(),
        result,
    };
    search.walk(0, &mut Vec::new())?;
    search.result.alternatives.sort_by(|a, b| {
        a.inserted_at
            .len()
            .cmp(&b.inserted_at.len())
            .then_with(|| a.inserted_at.cmp(&b.inserted_at))
    });
    Ok(search.result)
}
