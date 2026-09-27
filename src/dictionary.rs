//! Optional offline lexical evidence. Dictionary matches never change rule candidates.
//!
//! Headword lookup uses NFC only: affix hyphens, spaces, homonyms and senses remain
//! distinct. A POS match is lexical evidence, not proof of a grammatical reading.
mod import;
pub use import::import_krdict;
mod attachment;
pub use attachment::{
    AttachmentConflict, AttachmentRule, DictionaryFilter, EntryAssessment, LemmaAssessment,
    ReadingAssessment,
};

use crate::{Lemma, LemmaKind, WordAnalysis};
use rusqlite::{Connection, OpenFlags, OptionalExtension};
use serde::{Deserialize, Serialize};
use std::{
    collections::{BTreeSet, HashMap, VecDeque},
    path::Path,
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;
pub(crate) const SCHEMA: i64 = 1;
pub(crate) const APPLICATION_ID: i64 = 0x4b4c454d;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct InputFile {
    pub name: String,
    pub sha256: String,
    pub entries: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DictionaryMetadata {
    pub schema: i64,
    pub source: String,
    pub snapshot: String,
    pub source_url: String,
    pub license: String,
    pub license_url: String,
    pub attribution: String,
    pub entries: usize,
    pub files: Vec<InputFile>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EntrySummary {
    /// Namespaced upstream identifier, e.g. `krdict:27500`.
    pub id: String,
    pub headword: String,
    pub homonym: String,
    /// Original Korean POS label; missing/unknown labels are never guessed.
    pub pos: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Translation {
    /// Source language label (e.g. 영어).
    pub language: String,
    pub lemma: String,
    pub definition: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Sense {
    pub id: String,
    pub definition: String,
    pub translations: Vec<Translation>,
    /// Each inner list preserves a source example, including dialogue turns.
    pub examples: Vec<Vec<String>>,
    pub notes: Vec<String>,
    pub patterns: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WordForm {
    pub kind: String,
    pub written: String,
    pub pronunciations: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Entry {
    #[serde(flatten)]
    pub summary: EntrySummary,
    pub url: String,
    pub level: String,
    pub lexical_unit: String,
    pub origins: Vec<String>,
    pub notes: Vec<String>,
    pub forms: Vec<WordForm>,
    pub senses: Vec<Sense>,
}

/// Implement this for another local dictionary without modifying the rule engine.
pub trait Dictionary {
    fn metadata(&self) -> &DictionaryMetadata;
    /// Identifier of the imported snapshot, not just the dictionary's name.
    fn fingerprint(&self) -> &str;
    fn lookup(&self, headword: &str) -> Result<Vec<EntrySummary>>;
    fn entry(&self, id: &str) -> Result<Option<Entry>>;
}

/// Read-only indexed SQLite dictionary. Open one connection per worker.
pub struct SqliteDictionary {
    connection: Connection,
    metadata: DictionaryMetadata,
    fingerprint: String,
}
impl SqliteDictionary {
    pub fn open(path: impl AsRef<Path>) -> Result<Self> {
        let connection = Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
        let version: i64 = connection.pragma_query_value(None, "user_version", |r| r.get(0))?;
        let application: i64 =
            connection.pragma_query_value(None, "application_id", |r| r.get(0))?;
        if version != SCHEMA || application != APPLICATION_ID {
            return Err("not a supported klem dictionary database".into());
        }
        let json: String =
            connection.query_row("SELECT value FROM metadata WHERE key='manifest'", [], |r| {
                r.get(0)
            })?;
        let metadata: DictionaryMetadata = serde_json::from_str(&json)?;
        if metadata.schema != SCHEMA {
            return Err("unsupported dictionary manifest schema".into());
        }
        use sha2::{Digest, Sha256};
        let fingerprint = format!("{:x}", Sha256::digest(json.as_bytes()));
        Ok(Self {
            connection,
            metadata,
            fingerprint,
        })
    }
}
impl Dictionary for SqliteDictionary {
    fn metadata(&self) -> &DictionaryMetadata {
        &self.metadata
    }
    fn fingerprint(&self) -> &str {
        &self.fingerprint
    }
    fn lookup(&self, headword: &str) -> Result<Vec<EntrySummary>> {
        let key: String = headword.nfc().collect();
        let mut statement = self.connection.prepare_cached(
            "SELECT id, headword, homonym, pos FROM entries WHERE lookup=?1 ORDER BY id",
        )?;
        let entries = statement
            .query_map([key], |r| {
                Ok(EntrySummary {
                    id: r.get(0)?,
                    headword: r.get(1)?,
                    homonym: r.get(2)?,
                    pos: r.get(3)?,
                })
            })?
            .collect::<std::result::Result<Vec<_>, _>>()?;
        Ok(entries)
    }
    fn entry(&self, id: &str) -> Result<Option<Entry>> {
        let json: Option<String> = self
            .connection
            .prepare_cached("SELECT data FROM entries WHERE id=?1")?
            .query_row([id], |r| r.get(0))
            .optional()?;
        Ok(json.map(|s| serde_json::from_str(&s)).transpose()?)
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum Compatibility {
    Compatible,
    Incompatible,
    Unknown,
}

/// Conservative mapping from dictionary POS to klem's broad grammatical roles.
/// Unclassified candidates make no POS claim. Copulas require a headword check
/// because 이다 is labelled 조사 in KRDict and 아니다 is labelled 형용사.
pub fn pos_compatibility(lemma: &Lemma, entry: &EntrySummary) -> Compatibility {
    use Compatibility::*;
    if lemma.kind == LemmaKind::Unclassified {
        return Unknown;
    }
    let pos = entry.pos.as_str();
    if !matches!(
        pos,
        "명사"
            | "대명사"
            | "수사"
            | "의존 명사"
            | "동사"
            | "형용사"
            | "보조 동사"
            | "보조 형용사"
            | "조사"
            | "관형사"
            | "부사"
            | "감탄사"
            | "접사"
            | "어미"
    ) {
        return Unknown;
    }
    let accepted = match lemma.kind {
        LemmaKind::Nominal => matches!(pos, "명사" | "대명사" | "수사" | "의존 명사"),
        LemmaKind::Predicate => matches!(pos, "동사" | "형용사"),
        LemmaKind::Auxiliary => matches!(pos, "보조 동사" | "보조 형용사"),
        LemmaKind::Adverbial => pos == "부사",
        LemmaKind::Copula => matches!(
            (entry.headword.as_str(), pos),
            ("이다", "조사") | ("아니다", "형용사")
        ),
        LemmaKind::Unclassified => unreachable!(),
    };
    if accepted { Compatible } else { Incompatible }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EntryMatch {
    #[serde(flatten)]
    pub entry: EntrySummary,
    pub pos_compatibility: Compatibility,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LemmaMatches {
    pub lemma: Lemma,
    pub entries: Vec<EntryMatch>,
}
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Annotation {
    pub source: String,
    pub fingerprint: String,
    /// Unique (text, kind) keys referenced by the unchanged grouped analyses.
    pub lemmas: Vec<LemmaMatches>,
    /// Scoped lexical checks, in the same order as the grouped analyses.
    /// Older serialized annotations may omit this field.
    #[serde(default)]
    pub readings: Vec<ReadingAssessment>,
}
impl Annotation {
    pub fn has_match(&self, lemma: &Lemma, require_pos: bool) -> bool {
        self.lemmas
            .iter()
            .find(|m| &m.lemma == lemma)
            .is_some_and(|m| {
                m.entries
                    .iter()
                    .any(|e| !require_pos || e.pos_compatibility == Compatibility::Compatible)
            })
    }
}

/// FIFO cache of headword summaries, including negative lookups. The byte budget
/// accounts for payload and container sizes, not allocator/SQLite overhead.
pub struct DictionarySession<'a, D: Dictionary + ?Sized> {
    dictionary: &'a D,
    cache: HashMap<String, (Arc<Vec<EntrySummary>>, usize)>,
    order: VecDeque<String>,
    budget: usize,
    bytes: usize,
}
impl<'a, D: Dictionary + ?Sized> DictionarySession<'a, D> {
    pub fn new(dictionary: &'a D, cache_bytes: usize) -> Self {
        Self {
            dictionary,
            cache: HashMap::new(),
            order: VecDeque::new(),
            budget: cache_bytes,
            bytes: 0,
        }
    }
    pub fn cache_bytes(&self) -> usize {
        self.bytes
    }
    pub fn lookup(&mut self, word: &str) -> Result<Arc<Vec<EntrySummary>>> {
        let key: String = word.nfc().collect();
        if let Some((entries, _)) = self.cache.get(&key) {
            return Ok(Arc::clone(entries));
        }
        let entries = Arc::new(self.dictionary.lookup(&key)?);
        let size = 2 * (std::mem::size_of::<String>() + key.len())
            + std::mem::size_of::<(Arc<Vec<EntrySummary>>, usize)>()
            + std::mem::size_of::<Vec<EntrySummary>>()
            + entries
                .iter()
                .map(|e| {
                    std::mem::size_of::<EntrySummary>()
                        + e.id.len()
                        + e.headword.len()
                        + e.homonym.len()
                        + e.pos.len()
                })
                .sum::<usize>();
        if size <= self.budget {
            while self.bytes > self.budget - size {
                if let Some(old) = self.order.pop_front()
                    && let Some((_, bytes)) = self.cache.remove(&old)
                {
                    self.bytes -= bytes;
                }
            }
            self.order.push_back(key.clone());
            self.cache.insert(key, (Arc::clone(&entries), size));
            self.bytes += size;
        }
        Ok(entries)
    }
    pub fn annotate(&mut self, analysis: &WordAnalysis) -> Result<Annotation> {
        let keys: BTreeSet<_> = analysis
            .analyses
            .iter()
            .flat_map(|a| a.lemmas.iter())
            .collect();
        let mut lemmas = Vec::with_capacity(keys.len());
        for lemma in keys {
            let entries = self
                .lookup(&lemma.text)?
                .iter()
                .map(|entry| EntryMatch {
                    pos_compatibility: pos_compatibility(lemma, entry),
                    entry: entry.clone(),
                })
                .collect();
            lemmas.push(LemmaMatches {
                lemma: lemma.clone(),
                entries,
            });
        }
        let mut annotation = Annotation {
            source: self.dictionary.metadata().source.clone(),
            fingerprint: self.dictionary.fingerprint().to_owned(),
            lemmas,
            readings: Vec::new(),
        };
        annotation.readings = analysis
            .analyses
            .iter()
            .map(|a| annotation.assess(a))
            .collect();
        Ok(annotation)
    }
}
