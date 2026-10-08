//! Optional corpus lexicon. Its identities never replace KRDict homonyms.
use super::{
    Dictionary, DictionaryMetadata, Entry, EntrySummary, InputFile, LexicalSource, Result, Sense,
};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use unicode_normalization::UnicodeNormalization;

const SOURCE: &str = include_str!("proper_names.json");

#[derive(Deserialize)]
struct Lexicon {
    source: String,
    source_url: String,
    license: String,
    license_url: String,
    attribution: String,
    names: Vec<Name>,
}
#[derive(Deserialize)]
struct Name {
    id: String,
    headword: String,
    pos: String,
    xpos: String,
    observations: Vec<Observation>,
}
#[derive(Deserialize)]
struct Observation {
    id: String,
    sentence_id: String,
    token_id: String,
    complete_original_sentence: String,
}

/// Add independently attributed training-corpus proper names to a dictionary.
/// Lookup remains exact NFC and all original entries retain their identities.
/// Currently the reviewed lexicon contains 박; it is not a name recognizer.
pub struct ProperNameDictionary<D> {
    dictionary: D,
    entries: Vec<Entry>,
    metadata: DictionaryMetadata,
    fingerprint: String,
}

impl<D: Dictionary> ProperNameDictionary<D> {
    pub fn new(dictionary: D) -> Self {
        let lexicon: Lexicon = serde_json::from_str(SOURCE).expect("bundled proper-name lexicon");
        let entries: Vec<_> = lexicon.names.into_iter().map(|name| Entry {
            summary: EntrySummary {
                id: name.id, headword: name.headword, homonym: String::new(), pos: name.pos,
            },
            url: lexicon.source_url.clone(), level: String::new(), lexical_unit: "corpus proper name".into(),
            origins: Vec::new(),
            notes: vec![format!("Original XPOS: {}", name.xpos), lexicon.attribution.clone(), format!("{}: {}", lexicon.license, lexicon.license_url),
                "Training-corpus lexical evidence; no contextual sense selection or arbitrary-name recognition.".into()],
            forms: Vec::new(),
            senses: name.observations.into_iter().map(|o| Sense {
                id: o.id, definition: format!("Proper-name observation: {} token {}", o.sentence_id, o.token_id),
                translations: Vec::new(), examples: vec![vec![o.complete_original_sentence]],
                notes: vec!["Source partition: train; original UPOS PROPN / XPOS nq.".into()], patterns: Vec::new(),
            }).collect(),
        }).collect();
        let digest = format!("{:x}", Sha256::digest(SOURCE.as_bytes()));
        // Value objects have canonical key order. Bind full generated entries,
        // including notes and context, separately from the raw corpus input.
        let projection = serde_json::to_value(&entries).expect("serializable corpus entries");
        let projection_sha256 = format!(
            "{:x}",
            Sha256::digest(serde_json::to_vec(&projection).expect("serializable corpus entries"))
        );
        let mut metadata = dictionary.metadata().clone();
        metadata.source.push_str(&format!(" + {}", lexicon.source));
        metadata.snapshot.push_str(" + proper-names");
        metadata.attribution.push_str(&format!(
            "; {} ({}, {})",
            lexicon.attribution, lexicon.license, lexicon.license_url
        ));
        metadata.entries += entries.len();
        metadata.files.push(InputFile {
            name: "proper_names.json".into(),
            sha256: digest.clone(),
            entries: entries.len(),
        });
        metadata.supplements.push(LexicalSource {
            source: lexicon.source,
            source_url: lexicon.source_url,
            license: lexicon.license,
            license_url: lexicon.license_url,
            attribution: lexicon.attribution,
            sha256: digest.clone(),
            projection_sha256: projection_sha256.clone(),
            entries: entries.len(),
        });
        let fingerprint = format!(
            "{:x}",
            Sha256::digest(format!(
                "{}:{digest}:{projection_sha256}",
                dictionary.fingerprint()
            ))
        );
        Self {
            dictionary,
            entries,
            metadata,
            fingerprint,
        }
    }
}

impl<D: Dictionary> Dictionary for ProperNameDictionary<D> {
    fn metadata(&self) -> &DictionaryMetadata {
        &self.metadata
    }
    fn fingerprint(&self) -> &str {
        &self.fingerprint
    }
    fn lookup(&self, headword: &str) -> Result<Vec<EntrySummary>> {
        let headword: String = headword.nfc().collect();
        let mut entries = self.dictionary.lookup(&headword)?;
        entries.extend(
            self.entries
                .iter()
                .filter(|e| e.summary.headword == headword)
                .map(|e| e.summary.clone()),
        );
        entries.sort_by(|a, b| a.id.cmp(&b.id));
        Ok(entries)
    }
    fn entry(&self, id: &str) -> Result<Option<Entry>> {
        if let Some(entry) = self.entries.iter().find(|e| e.summary.id == id) {
            return Ok(Some(entry.clone()));
        }
        self.dictionary.entry(id)
    }
}
