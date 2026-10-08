//! Explicit, dictionary-backed missing-space hypotheses. Word candidates are immutable.
//! This searches nominal case phrases followed by a lexical predicate and
//! independently attested bare-noun pairs and recovered auxiliary chains.
//! Auxiliary witnesses include copular and derived owners; sentence grammar and
//! intended spacing are not validated.
use crate::dictionary::{
    Annotation, Compatibility, Dictionary, DictionaryFilter, DictionarySession, Result,
};
use crate::{Analysis, LemmaKind, MorphemeKind, Session, TokenAnalysis, TokenKind, WordAnalysis};
use serde::{Deserialize, Serialize};
use std::{
    collections::{HashMap, HashSet},
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;

mod auxiliary;
mod bound_noun;
mod nominal_bound_noun;

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
    /// Additional finite template; absent for the original case-phrase template.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub rule: Option<&'static str>,
    /// Original substrings joined with proposed spaces; never an input rewrite.
    pub spaced: String,
    /// Absolute UTF-8 positions in the original input, at which spaces are proposed.
    pub inserted_at: Vec<usize>,
    /// Each word has independent alternatives and dictionary assessments.
    pub records: Vec<SpacingSegment>,
    /// Recovered joined readings which license these auxiliary relationships.
    /// Segment readings remain independently analyzed; no role is rewritten.
    #[serde(skip_serializing_if = "Vec::is_empty")]
    pub joined_contexts: Vec<SpacingSegment>,
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
    AuxiliaryChain,
    AuxiliaryPiece,
    Modifier,
    BoundNoun,
    NominalOwner,
    BareNoun,
    ListedVerb(&'static str),
    NadaNoun(&'static str, &'static str),
    MainNada,
}

// Full native examples independently attest these bare objects before lexical
// 내다: 66599/1/8, 31325/1/8, 41886/2/5, 67521/1/8, 71927/1/10.
// 20192/1/8 additionally attests 기분 + 내키다. The exact right lexical head
// matters: its spelling is not evidence for a 기분 + 내다 pair.
// Other nouns in 내다 sense 13 and registered whole verbs are separately tracked.
const BARE_PAIRS: &[(&str, &str)] = &[
    ("신경질", "내다"),
    ("용기", "내다"),
    ("짜증", "내다"),
    ("기분", "내키다"),
];
const BARE_RULE: &str = "spacing.bare_noun_lexical_verb";

// COV-020r: exact native noun identities, supported by the complete groups in
// docs/lexical-nada-source-review.json and lexical-nada-listed-review.json.
// Main 나다 is 62210/homonym 1; auxiliary
// 62134/homonym 2 cannot supply this proof. Homonyms remain visible separately.
const NADA_PAIRS: &[(&str, &str, &str)] = &[
    ("경사", "krdict:30554", "2"),
    ("구멍", "krdict:34923", "0"),
    ("구역질", "krdict:35687", "0"),
    ("몸살", "krdict:54741", "0"),
    ("물난리", "krdict:56191", "0"),
    ("발표", "krdict:62470", "0"),
    ("배탈", "krdict:58720", "0"),
    ("산사태", "krdict:61775", "0"),
    ("상처", "krdict:62979", "2"),
    ("소리", "krdict:62379", "0"),
    ("수염", "krdict:64609", "0"),
    ("시간", "krdict:62841", "1"),
    ("식은땀", "krdict:90744", "0"),
    ("신경질", "krdict:66150", "0"),
    ("신명", "krdict:65770", "0"),
    ("실감", "krdict:14080", "0"),
    ("싸움", "krdict:24286", "0"),
    ("여드름", "krdict:67696", "0"),
    ("연기", "krdict:67478", "2"),
    ("윤기", "krdict:71077", "0"),
    ("전쟁", "krdict:29551", "0"),
    ("짜증", "krdict:71579", "0"),
    ("큰일", "krdict:72174", "1"),
    ("탄로", "krdict:80290", "0"),
    ("탈", "krdict:81494", "2"),
    ("털", "krdict:71477", "0"),
    ("토막", "krdict:80558", "0"),
    ("폼", "krdict:83727", "0"),
    ("감칠맛", "krdict:22602", "0"),
    ("코피", "krdict:72169", "0"),
    ("멀미", "krdict:54969", "0"),
    ("사고", "krdict:66370", "1"),
    ("교통사고", "krdict:35968", "0"),
    ("생각", "krdict:58162", "0"),
    ("냄새", "krdict:58180", "0"),
    ("집", "krdict:71358", "1"),
    ("사람", "krdict:58161", "0"),
    ("돈", "krdict:17204", "1"),
    ("피", "krdict:73269", "1"),
];
const NADA_RULE: &str = "spacing.bare_noun_main_nada";

#[derive(Clone, Copy)]
enum BareFamily {
    Listed,
    MainNada,
}
impl BareFamily {
    fn max_prefix_chars(self) -> usize {
        match self {
            Self::Listed => BARE_PAIRS.iter().map(|(head, _)| head.nfd().count()).max(),
            Self::MainNada => NADA_PAIRS
                .iter()
                .map(|(head, _, _)| head.nfd().count())
                .max(),
        }
        .unwrap()
    }
    fn roles(self, normalized: &str) -> Option<(Role, Role)> {
        match self {
            Self::Listed => BARE_PAIRS
                .iter()
                .find(|(head, _)| *head == normalized)
                .map(|(_, verb)| (Role::BareNoun, Role::ListedVerb(verb))),
            Self::MainNada => NADA_PAIRS
                .iter()
                .find(|(head, _, _)| *head == normalized)
                .map(|(_, id, homonym)| (Role::NadaNoun(id, homonym), Role::MainNada)),
        }
    }
    fn rule(self) -> &'static str {
        match self {
            Self::Listed => BARE_RULE,
            Self::MainNada => NADA_RULE,
        }
    }
}

fn unchanged_noun(a: &Analysis) -> bool {
    a.unchanged
        && a.lemmas.len() == 1
        && a.lemmas[0].kind == LemmaKind::Unclassified
        && a.morphemes.is_empty()
}

fn bare_noun(a: &Analysis) -> bool {
    unchanged_noun(a) && BARE_PAIRS.iter().any(|(head, _)| *head == a.lemmas[0].text)
}

fn predicate(a: &Analysis) -> bool {
    // Predicate lookup roots before reviewed noun-forming morphology are
    // nominal words rather than the endpoint of this spacing template.
    !a.rules.iter().any(|r| {
        matches!(
            r.as_str(),
            "suffix.nominal.i" | "derivation.nominal.adnominal" | "derivation.nominal.bound_i"
        )
    }) && a
        .lemmas
        .first()
        .is_some_and(|l| l.kind == LemmaKind::Predicate)
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
    if ((a.rules.iter().any(|r| r == "derivation.nominal.adnominal") && a.lemmas.len() == 1)
        || (a.rules.iter().any(|r| r == "derivation.nominal.bound_i") && a.lemmas.len() == 2))
        && a.breakdown().is_some()
    {
        return true;
    }
    // Nominal roots/derivations or explicit nominalizations, never an arbitrary
    // connective followed by a particle. Each word is checked independently.
    (((a.lemmas.len() == 1 && a.lemmas[0].kind == LemmaKind::Nominal)
        || (a.rules.iter().any(|r| r == "suffix.nominal.i")
            && a.lemmas.len()
                == if a.rules.iter().any(|r| {
                    matches!(
                        r.as_str(),
                        "derivation.nominal.compound" | "derivation.nominal.root_compound"
                    )
                }) {
                    2
                } else {
                    1
                }))
        && (!a
            .rules
            .iter()
            .any(|r| r == "derivation.nominal.root_compound")
            || a.breakdown().is_some())
        && a.morphemes[..a.morphemes.len() - tail.len()]
            .iter()
            .all(|m| {
                (m.kind == MorphemeKind::Suffix && m.form != "답다")
                    || (m.kind == MorphemeKind::Prefix
                        && crate::grammar::NOUN_I_PREFIX_FORMS
                            .iter()
                            .any(|&(_, _, _, rule)| a.rules.iter().any(|r| r == rule))
                        && a.breakdown().is_some())
            }))
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
        if role == Role::BareNoun {
            let normalized: String = surface.nfc().collect();
            if !BARE_PAIRS.iter().any(|(head, _)| *head == normalized) {
                return Ok(None);
            }
        }
        if let Role::NadaNoun(id, homonym) = role {
            let normalized: String = surface.nfc().collect();
            if !NADA_PAIRS
                .iter()
                .any(|(head, entry, hom)| *head == normalized && *entry == id && *hom == homonym)
            {
                return Ok(None);
            }
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
                    Role::Predicate => predicate(a),
                    Role::AuxiliaryChain => {
                        a.breakdown().is_some()
                            && a.lemmas.iter().any(|l| l.kind == LemmaKind::Auxiliary)
                    }
                    Role::AuxiliaryPiece => a.breakdown().is_some(),
                    Role::Modifier => bound_noun::modifier(a),
                    Role::BoundNoun => bound_noun::bound_noun(a),
                    Role::NominalOwner => nominal_bound_noun::owner(a),
                    Role::BareNoun => bare_noun(a),
                    Role::ListedVerb(head) => predicate(a) && a.lemmas[0].text == head,
                    Role::NadaNoun(_, _) => unchanged_noun(a),
                    Role::MainNada => predicate(a) && a.lemmas[0].text == "나다",
                })
                .cloned()
                .collect(),
        };
        let mut dictionary = self.dictionary.annotate(&analysis)?;
        dictionary.filter(&mut analysis, DictionaryFilter::Compatible);
        if matches!(
            role,
            Role::BareNoun | Role::ListedVerb(_) | Role::NadaNoun(_, _) | Role::MainNada
        ) {
            // A standalone auxiliary can have unknown attachment status, so
            // compatible filtering alone cannot establish a main-verb pair.
            // Retain only readings with an actual known noun/main-verb entry
            // for their own first slot; every other homonym remains inspectable.
            let required_pos = if matches!(role, Role::BareNoun | Role::NadaNoun(_, _)) {
                "명사"
            } else {
                "동사"
            };
            let supported: Vec<_> = analysis
                .analyses
                .iter()
                .filter(|a| {
                    let lemma = &a.lemmas[0];
                    let assessed = dictionary.assess(a);
                    dictionary
                        .lemmas
                        .iter()
                        .find(|m| m.lemma == *lemma)
                        .is_some_and(|m| {
                            m.entries.iter().any(|e| {
                                e.entry.headword == lemma.text
                                    && e.entry.pos == required_pos
                                    && match role {
                                        Role::NadaNoun(id, homonym) => {
                                            e.entry.id == id && e.entry.homonym == homonym
                                        }
                                        Role::MainNada => {
                                            e.entry.id == "krdict:62210" && e.entry.homonym == "1"
                                        }
                                        _ => true,
                                    }
                                    && assessed.lemmas[0].entries.iter().any(|r| {
                                        r.id == e.entry.id
                                            && r.status != Compatibility::Incompatible
                                    })
                            })
                        })
                })
                .cloned()
                .collect();
            analysis.analyses = supported;
            // Re-annotate the retained independent paths; do not relabel a raw
            // identity as nominal or borrow an auxiliary's dictionary entry.
            dictionary = self.dictionary.annotate(&analysis)?;
        }
        if role == Role::NominalOwner {
            analysis
                .analyses
                .retain(|a| nominal_bound_noun::known_owner(&dictionary, a));
            dictionary = self.dictionary.annotate(&analysis)?;
        }
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

    fn emit(&mut self, records: Vec<SpacingSegment>, rule: Option<&'static str>) {
        if self.result.alternatives.len() >= self.result.limits.alternatives {
            self.limit(SpacingLimit::Alternatives);
            return;
        }
        self.result.alternatives.push(SpacingHypothesis {
            rule,
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
            joined_contexts: Vec::new(),
        });
    }

    fn bare_pair(
        &mut self,
        start: usize,
        path: &[SpacingSegment],
        family: BareFamily,
        max_prefix_chars: usize,
    ) -> Result<()> {
        // Find only complete named noun prefixes; do not analyze arbitrary
        // substrings or split every dictionary noun before every predicate.
        for (relative, _) in self.source[start..]
            .char_indices()
            .skip(1)
            .take(max_prefix_chars)
        {
            let end = start + relative;
            let normalized: String = self.source[start..end].nfc().collect();
            let Some((noun_role, verb_role)) = family.roles(&normalized) else {
                continue;
            };
            if let Some(left) = self.segment(start, end, noun_role)?
                && let Some(right) = self.segment(end, self.source.len(), verb_role)?
            {
                let mut records = path.to_vec();
                records.extend([left, right]);
                self.emit(records, Some(family.rule()));
            }
            if !self.result.complete {
                break;
            }
        }
        Ok(())
    }
    fn walk(&mut self, start: usize, path: &mut Vec<SpacingSegment>) -> Result<()> {
        if self.dead_starts.contains(&start) {
            return Ok(());
        }
        let previous_alternatives = self.result.alternatives.len();
        if !path.is_empty()
            && let Some(last) = self.segment(start, self.source.len(), Role::Predicate)?
        {
            let mut records = path.clone();
            records.push(last);
            self.emit(records, None);
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

    fn walk_bare(
        &mut self,
        start: usize,
        path: &mut Vec<SpacingSegment>,
        family: BareFamily,
        max_prefix_chars: usize,
    ) -> Result<()> {
        if self.dead_starts.contains(&start) {
            return Ok(());
        }
        let before = self.result.alternatives.len();
        self.bare_pair(start, path, family, max_prefix_chars)?;
        if !self.result.complete {
            return Ok(());
        }
        let cuts = self.source[start..]
            .char_indices()
            .skip(1)
            .map(|(i, _)| start + i)
            .collect::<Vec<_>>();
        for end in cuts.into_iter().rev() {
            // The completed original search has already cached these case
            // edges. Successful prefixes still enumerate their own readings.
            if let Some(left) = self.segment(start, end, Role::Case)? {
                path.push(left);
                self.walk_bare(end, path, family, max_prefix_chars)?;
                path.pop();
            }
            if !self.result.complete {
                break;
            }
        }
        if self.result.complete && self.result.alternatives.len() == before {
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
    let has_bare_pair = search.result.complete && {
        let normalized: String = word.nfc().collect();
        BARE_PAIRS.iter().any(|(head, _)| normalized.contains(head))
    };
    if has_bare_pair {
        // Enumerate the original template first. New pairs use only remaining
        // work/output capacity, so they cannot displace a prior hypothesis.
        // A legacy dead suffix can contain a new pair, so reset that memo while
        // preserving all independently analyzed/cached segment results.
        search.dead_starts.clear();
        search.walk_bare(
            0,
            &mut Vec::new(),
            BareFamily::Listed,
            BareFamily::Listed.max_prefix_chars(),
        )?;
    }
    let has_nada_pair = search.result.complete && {
        let normalized: String = word.nfc().collect();
        NADA_PAIRS
            .iter()
            .any(|(head, _, _)| normalized.contains(head))
    };
    if has_nada_pair {
        // This third pass shares the remaining budget and independent segment
        // cache. It cannot displace either original case hypotheses or the four
        // already supported bare pairs, including nouns shared by both lists.
        search.dead_starts.clear();
        search.walk_bare(
            0,
            &mut Vec::new(),
            BareFamily::MainNada,
            BareFamily::MainNada.max_prefix_chars(),
        )?;
    }
    if search.result.complete {
        search.dead_starts.clear();
        search.walk_auxiliary(0, &mut Vec::new())?;
    }
    if search.result.complete && bound_noun::maybe_bound_noun(word) {
        search.dead_starts.clear();
        search.walk_bound_noun(0, &mut Vec::new())?;
    }
    if search.result.complete && nominal_bound_noun::maybe_nominal_bound_noun(word) {
        search.dead_starts.clear();
        search.walk_nominal_bound_noun(0, &mut Vec::new())?;
    }
    search.result.alternatives.sort_by(|a, b| {
        a.inserted_at
            .len()
            .cmp(&b.inserted_at.len())
            .then_with(|| a.inserted_at.cmp(&b.inserted_at))
    });
    Ok(search.result)
}
