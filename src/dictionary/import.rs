use super::*;
use serde::de::{self, DeserializeSeed, IgnoredAny, MapAccess, SeqAccess, Visitor};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    fmt,
    fs::{self, File, OpenOptions},
    io::{self, BufReader, Read},
    path::PathBuf,
    sync::atomic::{AtomicU64, Ordering},
};

/// Import official KRDict LMF JSON exports (not the search API format).
/// Files are streamed one entry at a time. Publication is atomic and refuses to
/// overwrite an existing destination. Failed imports leave no partial database.
/// `snapshot` is a caller-supplied release label; SHA-256 hashes identify inputs.
pub fn import_krdict(
    files: &[PathBuf],
    destination: impl AsRef<Path>,
    snapshot: &str,
) -> Result<DictionaryMetadata> {
    if files.is_empty() || snapshot.trim().is_empty() {
        return Err("input files and snapshot label are required".into());
    }
    let destination = destination.as_ref();
    if destination.exists() {
        return Err("dictionary destination already exists".into());
    }
    let mut files = files.to_vec();
    files.sort();
    let temp = Temporary::new(destination)?;
    let mut connection = Connection::open(&temp.0)?;
    connection.execute_batch(
        "PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;
        CREATE TABLE entries(id TEXT PRIMARY KEY, lookup TEXT NOT NULL, headword TEXT NOT NULL,
            homonym TEXT NOT NULL, pos TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);",
    )?;
    let transaction = connection.transaction()?;
    let mut metadata = DictionaryMetadata {
        schema: SCHEMA, source: "krdict".into(), snapshot: snapshot.into(),
        source_url: "https://krdict.korean.go.kr/download/downloadPopup".into(),
        license: "CC-BY-SA-2.0-KR".into(),
        license_url: "https://krdict.korean.go.kr/kor/kboardPolicy/copyRightTermsInfo".into(),
        attribution: "National Institute of Korean Language (국립국어원), Korean Basic Dictionary (한국어기초사전). Extracted text fields and NFC lookup keys; multimedia omitted.".into(),
        entries: 0, files: Vec::new(),
    };
    {
        let mut insert = transaction.prepare("INSERT INTO entries VALUES (?1,?2,?3,?4,?5,?6)")?;
        let mut names = BTreeSet::new();
        for path in files {
            let name = path
                .file_name()
                .and_then(|s| s.to_str())
                .ok_or("input needs a UTF-8 filename")?
                .to_owned();
            if !names.insert(name.clone()) {
                return Err("duplicate input filename".into());
            }
            let mut reader = BufReader::new(HashReader {
                inner: File::open(&path)?,
                hash: Sha256::new(),
            });
            let mut count = 0;
            let mut consume = |value: Value| -> Result<()> {
                let entry = parse_entry(&value)?;
                let key: String = entry.summary.headword.nfc().collect();
                insert.execute(rusqlite::params![
                    entry.summary.id,
                    key,
                    entry.summary.headword,
                    entry.summary.homonym,
                    entry.summary.pos,
                    serde_json::to_string(&entry)?
                ])?;
                count += 1;
                Ok(())
            };
            let mut deserializer = serde_json::Deserializer::from_reader(&mut reader);
            PathSeed {
                path: &["LexicalResource", "Lexicon", "LexicalEntry"],
                consume: &mut consume,
            }
            .deserialize(&mut deserializer)
            .map_err(|e| format!("{}: {e}", path.display()))?;
            deserializer.end()?;
            if count == 0 {
                return Err(format!("{} contains no entries", path.display()).into());
            }
            metadata.entries += count;
            metadata.files.push(InputFile {
                name,
                sha256: format!("{:x}", reader.into_inner().hash.finalize()),
                entries: count,
            });
        }
    }
    transaction.execute_batch("CREATE INDEX headwords ON entries(lookup, id)")?;
    transaction.execute(
        "INSERT INTO metadata VALUES ('manifest', ?1)",
        [serde_json::to_string(&metadata)?],
    )?;
    transaction.pragma_update(None, "user_version", SCHEMA)?;
    transaction.pragma_update(None, "application_id", APPLICATION_ID)?;
    transaction.commit()?;
    connection.close().map_err(|(_, e)| e)?;
    File::open(&temp.0)?.sync_all()?;
    // Unlike rename, hard_link cannot replace an existing destination, including
    // a concurrent import or a dangling symlink. Both paths share a directory.
    fs::hard_link(&temp.0, destination)?;
    Ok(metadata)
}

struct Temporary(PathBuf);
impl Temporary {
    fn new(destination: &Path) -> Result<Self> {
        static COUNTER: AtomicU64 = AtomicU64::new(0);
        let name = destination
            .file_name()
            .ok_or("destination needs a filename")?
            .to_string_lossy();
        loop {
            let path = destination.with_file_name(format!(
                ".{name}.import-{}-{}",
                std::process::id(),
                COUNTER.fetch_add(1, Ordering::Relaxed)
            ));
            match OpenOptions::new().write(true).create_new(true).open(&path) {
                Ok(_) => return Ok(Self(path)),
                Err(e) if e.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(e) => return Err(e.into()),
            }
        }
    }
}
impl Drop for Temporary {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
struct HashReader<R> {
    inner: R,
    hash: Sha256,
}
impl<R: Read> Read for HashReader<R> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        let n = self.inner.read(buf)?;
        self.hash.update(&buf[..n]);
        Ok(n)
    }
}

struct PathSeed<'a> {
    path: &'a [&'a str],
    consume: &'a mut dyn FnMut(Value) -> Result<()>,
}
impl<'de> DeserializeSeed<'de> for PathSeed<'_> {
    type Value = ();
    fn deserialize<D: serde::Deserializer<'de>>(self, d: D) -> std::result::Result<(), D::Error> {
        if self.path.is_empty() {
            d.deserialize_any(Entries(self.consume))
        } else {
            d.deserialize_map(self)
        }
    }
}
impl<'de> Visitor<'de> for PathSeed<'_> {
    type Value = ();
    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "KRDict LMF object containing {}", self.path[0])
    }
    fn visit_map<M: MapAccess<'de>>(self, mut map: M) -> std::result::Result<(), M::Error> {
        let mut found = false;
        while let Some(key) = map.next_key::<String>()? {
            if key == self.path[0] {
                if found {
                    return Err(de::Error::custom("duplicate LMF container"));
                }
                found = true;
                map.next_value_seed(PathSeed {
                    path: &self.path[1..],
                    consume: &mut *self.consume,
                })?;
            } else {
                map.next_value::<IgnoredAny>()?;
            }
        }
        if !found {
            return Err(de::Error::custom(format!(
                "missing LMF container {}",
                self.path[0]
            )));
        }
        Ok(())
    }
}
struct Entries<'a>(&'a mut dyn FnMut(Value) -> Result<()>);
impl<'de> Visitor<'de> for Entries<'_> {
    type Value = ();
    fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
        f.write_str("LexicalEntry array or object")
    }
    fn visit_seq<S: SeqAccess<'de>>(self, mut seq: S) -> std::result::Result<(), S::Error> {
        while let Some(entry) = seq.next_element::<Value>()? {
            (self.0)(entry).map_err(de::Error::custom)?;
        }
        Ok(())
    }
    fn visit_map<M: MapAccess<'de>>(self, map: M) -> std::result::Result<(), M::Error> {
        let value = Value::deserialize(de::value::MapAccessDeserializer::new(map))?;
        (self.0)(value).map_err(de::Error::custom)
    }
}

// The export collapses one-element arrays to objects at every LMF level.
fn many(value: &Value) -> &[Value] {
    match value {
        Value::Array(a) => a,
        Value::Null => &[],
        v => std::slice::from_ref(v),
    }
}
fn features(value: &Value, name: &str) -> Vec<String> {
    many(&value["feat"])
        .iter()
        .filter(|f| f["att"] == name)
        .filter_map(|f| f["val"].as_str())
        .map(decode_entities)
        .collect()
}
fn feature(value: &Value, name: &str) -> String {
    features(value, name).into_iter().next().unwrap_or_default()
}
fn id(value: &Value) -> Result<String> {
    let id = value["val"].as_str().ok_or("missing LMF identifier")?;
    if value["att"] != "id" || id.is_empty() || !id.bytes().all(|c| c.is_ascii_digit()) {
        return Err("invalid LMF identifier".into());
    }
    Ok(id.to_owned())
}
fn parse_entry(raw: &Value) -> Result<Entry> {
    let source_id = id(raw)?;
    let headwords: Vec<_> = many(&raw["Lemma"])
        .iter()
        .flat_map(|l| features(l, "writtenForm"))
        .collect();
    if headwords.len() != 1 || headwords[0].trim().is_empty() {
        return Err(format!("entry {source_id}: expected one writtenForm headword").into());
    }
    let headword = headwords[0].clone();
    let lexical_unit = feature(raw, "lexicalUnit");
    // LMF idioms/proverbs reuse their parent word's identifier. Give these
    // subentries stable derived IDs while keeping the upstream parent URL.
    let entry_id = if matches!(lexical_unit.as_str(), "관용구" | "속담") {
        let digest = Sha256::digest(format!("{lexical_unit}\0{headword}").as_bytes());
        format!("krdict:{source_id}:{digest:x}")
    } else {
        format!("krdict:{source_id}")
    };
    let mut senses = Vec::new();
    let mut seen = BTreeSet::new();
    for sense in many(&raw["Sense"]) {
        let id = id(sense)?;
        if !seen.insert(id.clone()) {
            return Err("duplicate sense identifier".into());
        }
        let definition = feature(sense, "definition");
        if definition.is_empty() {
            return Err(format!("entry {source_id}: missing sense definition").into());
        }
        let translations = many(&sense["Equivalent"])
            .iter()
            .map(|t| Translation {
                language: feature(t, "language"),
                lemma: feature(t, "lemma"),
                definition: feature(t, "definition"),
            })
            .collect();
        let examples = many(&sense["SenseExample"])
            .iter()
            .map(|e| features(e, "example"))
            .collect();
        let mut notes = features(sense, "annotation");
        notes.extend(features(sense, "syntacticAnnotation"));
        senses.push(Sense {
            id,
            definition,
            translations,
            examples,
            notes,
            patterns: features(sense, "syntacticPattern"),
        });
    }
    if senses.is_empty() {
        return Err(format!("entry {source_id}: missing senses").into());
    }
    Ok(Entry {
        summary: EntrySummary {
            id: entry_id,
            headword,
            homonym: feature(raw, "homonym_number"),
            pos: feature(raw, "partOfSpeech"),
        },
        url: format!("https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo={source_id}"),
        level: feature(raw, "vocabularyLevel"),
        lexical_unit,
        origins: features(raw, "origin"),
        notes: features(raw, "annotation"),
        forms: many(&raw["WordForm"])
            .iter()
            .map(|form| WordForm {
                kind: feature(form, "type"),
                written: feature(form, "writtenForm"),
                pronunciations: features(form, "pronunciation"),
            })
            .collect(),
        senses,
    })
}

/// Decode XML entities left in JSON text by the export, exactly once.
fn decode_entities(input: &str) -> String {
    let mut output = String::with_capacity(input.len());
    let mut rest = input;
    while let Some(start) = rest.find('&') {
        output.push_str(&rest[..start]);
        rest = &rest[start..];
        if let Some(end) = rest.find(';').filter(|&n| n <= 12) {
            let name = &rest[1..end];
            let ch = match name {
                "amp" => Some('&'),
                "lt" => Some('<'),
                "gt" => Some('>'),
                "quot" => Some('"'),
                "apos" => Some('\''),
                "nbsp" => Some('\u{a0}'),
                _ => name
                    .strip_prefix("#x")
                    .and_then(|s| u32::from_str_radix(s, 16).ok())
                    .or_else(|| name.strip_prefix('#').and_then(|s| s.parse().ok()))
                    .and_then(char::from_u32),
            };
            if let Some(ch) = ch {
                output.push(ch);
                rest = &rest[end + 1..];
                continue;
            }
        }
        output.push('&');
        rest = &rest[1..];
    }
    output.push_str(rest);
    output
}
