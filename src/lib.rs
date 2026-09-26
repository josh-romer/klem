//! Korean lemma candidate generation, without a dictionary or contextual ranking.
//!
//! ```
//! let analyzer = klem::Lemmatizer::new();
//! let result = analyzer.analyze_word("먹었어요").unwrap();
//! assert!(result.lemma_strings().contains(&"먹다"));
//! ```
pub mod breakdown;
pub mod dictionary;
mod engine;
mod grammar;
mod hangul;
mod pronunciation;
mod text;

use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeSet, HashMap, VecDeque},
    fmt,
    sync::Arc,
};
pub use text::stream as analyze_reader;
pub use text::{TextIter, TokenAnalysis, TokenKind, Tokenizer};

/// A grammatical hypothesis, not a dictionary-verified part of speech.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LemmaKind {
    Unclassified,
    Nominal,
    Predicate,
    Copula,
    Auxiliary,
    /// A lexical adverb before an attachable particle; not a nominal hypothesis.
    Adverbial,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Lemma {
    pub text: String,
    pub kind: LemmaKind,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum MorphemeKind {
    /// A terminal ending or a scoped, bundled grammatical expression such as
    /// (으)려는/자는; not necessarily a single dictionary-tagged ending.
    Ending,
    Prefinal,
    Particle,
    /// A derivational suffix, distinct from a particle or lemma. Predicate-forming
    /// suffixes use their dictionary form (e.g. 답다) and precede inflection.
    /// Adverb-forming 이 follows a predicate lemma directly, without an ending.
    Suffix,
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Morpheme {
    pub form: String,
    pub kind: MorphemeKind,
}

/// All components in one analysis coexist. Different analyses are alternatives.
/// `rules` is the sorted union of supporting rule IDs, not an ordered derivation.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
pub struct Analysis {
    pub lemmas: Vec<Lemma>,
    pub morphemes: Vec<Morpheme>,
    pub rules: Vec<String>,
    pub unchanged: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct WordAnalysis {
    pub normalized: String,
    pub analyses: Vec<Analysis>,
}

impl WordAnalysis {
    /// Sorted unique lemmas. Use `analyses` when component grouping matters.
    pub fn lemma_strings(&self) -> Vec<&str> {
        self.analyses
            .iter()
            .flat_map(|a| a.lemmas.iter().map(|l| l.text.as_str()))
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect()
    }

    /// Keep complete analyses only when every lemma passes the caller's filter.
    /// Filtering a result never mutates a session's cached unfiltered result.
    pub fn filtered(&self, mut accept: impl FnMut(&Lemma) -> bool) -> Self {
        Self {
            normalized: self.normalized.clone(),
            analyses: self
                .analyses
                .iter()
                .filter(|a| a.lemmas.iter().all(&mut accept))
                .cloned()
                .collect(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    EmptyWord,
    WhitespaceInWord,
}
impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::EmptyWord => "expected a nonempty word",
            Self::WhitespaceInWord => "word contains whitespace; use text analysis",
        })
    }
}
impl std::error::Error for Error {}

/// Immutable rules; inexpensive to construct and safe to share between threads.
#[derive(Debug, Default)]
pub struct Lemmatizer;
impl Lemmatizer {
    pub fn new() -> Self {
        Self
    }
    pub fn analyze_word(&self, word: &str) -> Result<WordAnalysis, Error> {
        engine::analyze(word)
    }
    pub fn analyze_text<'a>(&'a self, text: &'a str) -> TextIter<'a> {
        TextIter::new(self, text)
    }
}

/// Per-consumer FIFO cache. Charges retained string/vector capacities plus
/// 256 bytes per entry against the byte budget; oversized entries are not cached.
/// This is an allocation estimate, not a process RSS limit. Retained map/queue
/// capacity and allocator overhead are additional but bounded by peak entry
/// count. Results retained by callers are external to the cache budget.
pub struct Session {
    analyzer: Arc<Lemmatizer>,
    cache: HashMap<String, (Arc<WordAnalysis>, usize)>,
    order: VecDeque<String>,
    budget: usize,
    used: usize,
}
impl Session {
    pub fn new(analyzer: Arc<Lemmatizer>, cache_bytes: usize) -> Self {
        Self {
            analyzer,
            cache: HashMap::new(),
            order: VecDeque::new(),
            budget: cache_bytes,
            used: 0,
        }
    }
    /// Current charged weight, in bytes (see the type's allocation caveats).
    pub fn cached_bytes(&self) -> usize {
        self.used
    }
    pub fn analyze_word(&mut self, word: &str) -> Result<Arc<WordAnalysis>, Error> {
        if let Some((result, _)) = self.cache.get(word) {
            return Ok(result.clone());
        }
        let result = Arc::new(self.analyzer.analyze_word(word)?);
        let size = engine::retained_bytes(&result) + word.len() * 2 + 256;
        if size <= self.budget {
            while self.used + size > self.budget {
                let key = self.order.pop_front().expect("cache accounting");
                self.used -= self.cache.remove(&key).expect("cache accounting").1;
            }
            self.order.push_back(word.to_owned());
            self.cache.insert(word.to_owned(), (result.clone(), size));
            self.used += size;
        }
        Ok(result)
    }
}

/// Stable rule IDs and human-readable descriptions, including boundary rules.
pub fn rule_explanation(id: &str) -> Option<&'static str> {
    grammar::explanation(id)
}
