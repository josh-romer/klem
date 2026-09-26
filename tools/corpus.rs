//! Development-only corpus adapters, shared by evaluation and regression tests.
use klem::{Lemmatizer, Session};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    io::{self, BufRead, Write},
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;

#[derive(Clone, Copy)]
pub enum Corpus {
    Kaist,
    Gsd,
}
impl Corpus {
    pub fn parse(s: &str) -> Result<Self, String> {
        match s {
            "kaist" => Ok(Self::Kaist),
            "gsd" => Ok(Self::Gsd),
            _ => Err("corpus must be kaist or gsd".into()),
        }
    }
    pub fn name(self) -> &'static str {
        match self {
            Self::Kaist => "kaist",
            Self::Gsd => "gsd",
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum Conversion {
    Excluded,
    Unsupported(&'static str),
    Gold(Vec<String>),
}

fn flush(current: &mut String, predicate: &mut bool, gold: &mut Vec<String>) {
    if !current.is_empty() {
        if *predicate {
            current.push('다');
        }
        gold.push(std::mem::take(current));
        *predicate = false;
    }
}

/// Preserve adjacent nominal/root/derivational material as vocabulary units;
/// retain copulas and auxiliaries as separate components. Never use UPOS alone
/// to infer the internal morphology of an eojeol.
pub fn convert(fields: &[&str], corpus: Corpus) -> Conversion {
    if fields.len() != 10 {
        return Conversion::Unsupported("column_count");
    }
    if matches!(fields[3], "PUNCT" | "SYM")
        || !fields[1].chars().any(|c| ('가'..='힣').contains(&c))
    {
        return Conversion::Excluded;
    }
    let original = fields[9]
        .split('|')
        .find_map(|s| s.strip_prefix("OrigLemma="));
    let lemma = original.unwrap_or(fields[2]);
    if lemma == "_" || fields[4] == "_" {
        return Conversion::Unsupported("missing_morphology");
    }
    let parts: Vec<_> = lemma.split('+').collect();
    let tags: Vec<_> = fields[4].split('+').collect();
    if parts.len() != tags.len() {
        return Conversion::Unsupported("morpheme_tag_alignment");
    }
    let mut current = String::new();
    let mut predicate = false;
    let mut gold = vec![];
    for (part, tag) in parts.iter().zip(tags) {
        if part.is_empty() {
            return Conversion::Unsupported("empty_morpheme");
        }
        let (lexical, root, derived, copula, function, nominal_suffix) = match corpus {
            Corpus::Kaist => (
                matches!(
                    tag,
                    "nbn"
                        | "nbu"
                        | "ncn"
                        | "ncpa"
                        | "ncps"
                        | "nnc"
                        | "nno"
                        | "npd"
                        | "npp"
                        | "nq"
                        | "mad"
                        | "mag"
                        | "maj"
                        | "mma"
                        | "mmd"
                        | "f"
                        | "ii"
                        | "xp"
                ),
                matches!(tag, "pvg" | "pvd" | "paa" | "pad" | "px"),
                matches!(tag, "xsv" | "xsm"),
                tag == "jp",
                matches!(
                    tag,
                    "ecc"
                        | "ecs"
                        | "ecx"
                        | "ef"
                        | "ep"
                        | "etm"
                        | "etn"
                        | "jca"
                        | "jcc"
                        | "jcj"
                        | "jcm"
                        | "jco"
                        | "jcr"
                        | "jcs"
                        | "jct"
                        | "jcv"
                        | "jxc"
                        | "jxf"
                        | "jxt"
                ),
                matches!(tag, "xsn" | "xsa"),
            ),
            Corpus::Gsd => (
                matches!(
                    tag,
                    "NNG"
                        | "NNP"
                        | "NNB"
                        | "NNC"
                        | "NP"
                        | "NR"
                        | "SN"
                        | "SL"
                        | "SH"
                        | "MAG"
                        | "MAJ"
                        | "MM"
                        | "IC"
                        | "XR"
                        | "XPN"
                ),
                matches!(tag, "VV" | "VA" | "VX" | "VCN"),
                matches!(tag, "XSV" | "XSA"),
                tag == "VCP",
                matches!(
                    tag,
                    "EC" | "EF"
                        | "EP"
                        | "ETM"
                        | "ETN"
                        | "JC"
                        | "JKB"
                        | "JKC"
                        | "JKG"
                        | "JKO"
                        | "JKQ"
                        | "JKS"
                        | "JKV"
                        | "JX"
                ),
                tag == "XSN",
            ),
        };
        if lexical {
            if predicate {
                return Conversion::Unsupported("unsegmented_predicate_nominal");
            }
            current.push_str(part);
        } else if root || copula {
            flush(&mut current, &mut predicate, &mut gold);
            current.push_str(if copula { "이" } else { part });
            predicate = true;
        } else if derived {
            if current.is_empty() || predicate {
                return Conversion::Unsupported("orphan_derivational_suffix");
            }
            current.push_str(part);
            predicate = true;
        } else if nominal_suffix {
            if current.is_empty() || predicate {
                return Conversion::Unsupported("orphan_nominal_suffix");
            }
            current.push_str(part);
        } else if function {
            flush(&mut current, &mut predicate, &mut gold);
        } else {
            return Conversion::Unsupported("unsupported_tag");
        }
    }
    flush(&mut current, &mut predicate, &mut gold);
    if gold.is_empty() {
        Conversion::Unsupported("no_lexical_component")
    } else {
        Conversion::Gold(gold.into_iter().map(|s| s.nfc().collect()).collect())
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct Miss {
    pub surface: String,
    pub expected: Vec<String>,
    pub count: usize,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct Report {
    pub schema_version: u32,
    pub input_sha256: String,
    pub corpus: String,
    pub input: String,
    pub rows: usize,
    pub excluded_rows: usize,
    pub malformed_rows: usize,
    pub converted_rows: usize,
    pub unsupported: BTreeMap<String, usize>,
    pub grouped_matches: usize,
    pub gold_lemmas: usize,
    pub recovered_gold_lemmas: usize,
    pub transformed_rows: usize,
    pub transformed_matches: usize,
    pub adapter_coverage: f64,
    pub grouped_lemma_recall: f64,
    pub lemma_recall: f64,
    pub transformed_grouped_recall: f64,
    pub mean_candidates: f64,
    pub p95_candidates: usize,
    pub max_candidates: usize,
    pub common_misses: Vec<Miss>,
    /// JSONL records following the summary, indexed by stable sentence/token ID.
    #[serde(skip)]
    pub cases: BTreeMap<String, CaseOutcome>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CaseOutcome {
    pub id: String,
    pub surface: String,
    pub expected: Vec<String>,
    pub matched: bool,
    pub recovered: usize,
    /// Maximal co-recovered gold-index sets, each supported by one analysis.
    /// Indices preserve repeated gold lemmas without merging alternatives.
    pub recovered_sets: Vec<Vec<usize>>,
}

pub fn component_sets(
    gold: &[String],
    alternatives: impl IntoIterator<Item = Vec<String>>,
) -> Vec<Vec<usize>> {
    let mut sets = BTreeSet::new();
    for lemmas in alternatives {
        let mut indices = Vec::new();
        for lemma in lemmas {
            if let Some(i) = gold
                .iter()
                .enumerate()
                .position(|(i, g)| *g == lemma && !indices.contains(&i))
            {
                indices.push(i);
            }
        }
        indices.sort_unstable();
        if !indices.is_empty() {
            sets.insert(indices);
        }
    }
    sets.iter()
        .filter(|set| {
            !sets
                .iter()
                .any(|other| other.len() > set.len() && covers(other, set))
        })
        .cloned()
        .collect()
}

fn covers(actual: &[usize], previous: &[usize]) -> bool {
    previous.iter().all(|i| actual.binary_search(i).is_ok())
}

pub fn evaluate(mut reader: impl BufRead, corpus: Corpus, input: &str) -> io::Result<Report> {
    let mut report = Report {
        schema_version: 2,
        corpus: corpus.name().into(),
        input: input.into(),
        ..Report::default()
    };
    let mut session = Session::new(Arc::new(Lemmatizer::new()), 8 * 1024 * 1024);
    let mut ambiguity = vec![];
    let mut misses = BTreeMap::new();
    let mut digest = Sha256::new();
    let mut sentence_id = None;
    let mut sentence_number = 0;
    let mut in_sentence = false;
    let mut seen = BTreeSet::new();
    let mut buffer = String::new();
    loop {
        buffer.clear();
        if reader.read_line(&mut buffer)? == 0 {
            break;
        }
        digest.update(buffer.as_bytes());
        let line = buffer.trim_end_matches(['\r', '\n']);
        if line.is_empty() {
            sentence_id = None;
            in_sentence = false;
            continue;
        }
        if let Some(id) = line.strip_prefix("# sent_id = ") {
            if id.is_empty() {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    "empty sentence ID",
                ));
            }
            sentence_id = Some(id.to_owned());
            in_sentence = false;
            continue;
        }
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if !in_sentence {
            sentence_number += 1;
            in_sentence = true;
        }
        let f: Vec<_> = line.split('\t').collect();
        if f[0]
            .split_once(['-', '.'])
            .is_some_and(|(a, b)| a.parse::<usize>().is_ok() && b.parse::<usize>().is_ok())
        {
            continue;
        } // CoNLL-U multiword/empty-node rows.
        report.rows += 1;
        if f.len() != 10 || !f[0].parse::<usize>().is_ok_and(|id| id > 0) {
            report.malformed_rows += 1;
            continue;
        }
        let id = match &sentence_id {
            Some(sentence) => format!("id:{sentence}/{}", f[0]),
            None => format!("ordinal:{sentence_number}/{}", f[0]),
        };
        if !seen.insert(id.clone()) {
            return Err(io::Error::new(
                io::ErrorKind::InvalidData,
                format!("duplicate case ID: {id}"),
            ));
        }
        let gold = match convert(&f, corpus) {
            Conversion::Excluded => {
                report.excluded_rows += 1;
                continue;
            }
            Conversion::Unsupported(reason) => {
                *report.unsupported.entry(reason.into()).or_default() += 1;
                continue;
            }
            Conversion::Gold(g) => g,
        };
        let result = session
            .analyze_word(f[1])
            .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
        let matched = result
            .analyses
            .iter()
            .any(|a| a.lemmas.iter().map(|l| &l.text).eq(gold.iter()));
        let recovered_sets = component_sets(
            &gold,
            result
                .analyses
                .iter()
                .map(|a| a.lemmas.iter().map(|l| l.text.clone()).collect()),
        );
        let best = recovered_sets.iter().map(Vec::len).max().unwrap_or(0);
        report.converted_rows += 1;
        report.grouped_matches += usize::from(matched);
        report.gold_lemmas += gold.len();
        report.recovered_gold_lemmas += best;
        report.cases.insert(
            id.clone(),
            CaseOutcome {
                id,
                surface: f[1].into(),
                expected: gold.clone(),
                matched,
                recovered: best,
                recovered_sets,
            },
        );
        if gold != [result.normalized.clone()] {
            report.transformed_rows += 1;
            report.transformed_matches += usize::from(matched);
        }
        if !matched {
            *misses.entry((f[1].to_owned(), gold)).or_insert(0) += 1;
        }
        ambiguity.push(result.analyses.len());
    }
    report.input_sha256 = format!("{:x}", digest.finalize());
    let ratio = |n: usize, d: usize| if d == 0 { 0.0 } else { n as f64 / d as f64 };
    report.adapter_coverage = ratio(report.converted_rows, report.rows - report.excluded_rows);
    report.grouped_lemma_recall = ratio(report.grouped_matches, report.converted_rows);
    report.lemma_recall = ratio(report.recovered_gold_lemmas, report.gold_lemmas);
    report.transformed_grouped_recall = ratio(report.transformed_matches, report.transformed_rows);
    ambiguity.sort_unstable();
    report.mean_candidates = ratio(ambiguity.iter().sum(), ambiguity.len());
    report.p95_candidates = ambiguity
        .get((ambiguity.len() * 95 / 100).min(ambiguity.len().saturating_sub(1)))
        .copied()
        .unwrap_or(0);
    report.max_candidates = ambiguity.last().copied().unwrap_or(0);
    report.common_misses = misses
        .into_iter()
        .map(|((surface, expected), count)| Miss {
            surface,
            expected,
            count,
        })
        .collect();
    report.common_misses.sort_by(|a, b| {
        b.count
            .cmp(&a.count)
            .then(a.surface.cmp(&b.surface))
            .then(a.expected.cmp(&b.expected))
    });
    report.common_misses.truncate(30);
    Ok(report)
}

pub fn check_baseline(actual: &Report, old: &Report) -> Result<(), String> {
    validate_report(actual)?;
    validate_report(old)?;
    if actual.input_sha256 != old.input_sha256 {
        return Err("corpus SHA-256 differs; baseline requires the exact same input bytes".into());
    }
    if actual.corpus != old.corpus
        || actual.rows != old.rows
        || actual.excluded_rows != old.excluded_rows
    {
        return Err("baseline corpus/population differs".into());
    }
    let mut regressions = Vec::new();
    for (id, previous) in &old.cases {
        let Some(current) = actual.cases.get(id) else {
            regressions.push(format!(
                "{id}: {:?} is no longer converted",
                previous.surface
            ));
            continue;
        };
        if current.surface != previous.surface || current.expected != previous.expected {
            regressions.push(format!(
                "{id}: surface or expected lemmas changed; review the adapter"
            ));
        } else if previous.matched && !current.matched {
            regressions.push(format!(
                "{id}: {:?} lost grouped {:?}",
                current.surface, previous.expected
            ));
        } else if current.recovered < previous.recovered {
            regressions.push(format!(
                "{id}: {:?} recovers {} of {:?}, previously {}",
                current.surface, current.recovered, current.expected, previous.recovered
            ));
        } else {
            for set in &previous.recovered_sets {
                if !current.recovered_sets.iter().any(|now| covers(now, set)) {
                    let lemmas: Vec<_> = set.iter().map(|&i| &previous.expected[i]).collect();
                    regressions.push(format!(
                        "{id}: {:?} lost co-recovered gold indices {set:?} {lemmas:?}",
                        current.surface
                    ));
                }
            }
        }
    }
    if !regressions.is_empty() {
        let count = regressions.len();
        return Err(format!(
            "{count} individual case regression(s):\n{}",
            regressions.join("\n")
        ));
    }
    if actual.converted_rows < old.converted_rows
        || actual.grouped_matches < old.grouped_matches
        || actual.recovered_gold_lemmas < old.recovered_gold_lemmas
        || actual.transformed_matches < old.transformed_matches
        || actual.malformed_rows > old.malformed_rows
    {
        return Err(
            "corpus metrics regressed; inspect misses instead of replacing the baseline blindly"
                .into(),
        );
    }
    Ok(())
}

/// One summary record followed by one compact JSON record per converted token.
/// A single file prevents summaries and case snapshots from getting out of sync.
pub fn write_report(mut writer: impl Write, report: &Report) -> io::Result<()> {
    validate_report(report).map_err(invalid_data)?;
    serde_json::to_writer(&mut writer, report)?;
    writeln!(writer)?;
    for case in report.cases.values() {
        serde_json::to_writer(&mut writer, case)?;
        writeln!(writer)?;
    }
    writer.flush()
}

pub fn read_report(mut reader: impl BufRead) -> io::Result<Report> {
    let mut header = String::new();
    reader.read_line(&mut header)?;
    let mut report: Report = serde_json::from_str(&header).map_err(|e| {
        invalid_data(format!(
            "expected a versioned JSONL baseline (legacy aggregate JSON is insufficient): {e}"
        ))
    })?;
    if report.schema_version != 2 {
        return Err(invalid_data(
            "unsupported baseline schema; version 2 component sets are required; regenerate with the unchanged engine and review the migration",
        ));
    }
    for line in reader.lines() {
        let line = line?;
        let case: CaseOutcome = serde_json::from_str(&line).map_err(invalid_data)?;
        let id = case.id.clone();
        if report.cases.insert(id.clone(), case).is_some() {
            return Err(invalid_data(format!("duplicate baseline case ID: {id}")));
        }
    }
    validate_report(&report).map_err(invalid_data)?;
    Ok(report)
}

fn invalid_data(error: impl std::fmt::Display) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, error.to_string())
}

fn validate_report(report: &Report) -> Result<(), String> {
    if report.schema_version != 2 {
        return Err("unsupported baseline schema; version 2 component sets are required".into());
    }
    if report.input_sha256.len() != 64
        || !report.input_sha256.bytes().all(|b| b.is_ascii_hexdigit())
    {
        return Err("invalid corpus SHA-256".into());
    }
    if report.cases.len() != report.converted_rows
        || report.cases.values().filter(|c| c.matched).count() != report.grouped_matches
        || report
            .cases
            .values()
            .map(|c| c.expected.len())
            .sum::<usize>()
            != report.gold_lemmas
        || report.cases.values().map(|c| c.recovered).sum::<usize>() != report.recovered_gold_lemmas
    {
        return Err("baseline case records do not agree with summary counts".into());
    }
    let transformed: Vec<_> = report
        .cases
        .values()
        .filter(|c| c.expected != [c.surface.nfc().collect::<String>()])
        .collect();
    if transformed.len() != report.transformed_rows
        || transformed.iter().filter(|c| c.matched).count() != report.transformed_matches
        || report.converted_rows
            + report.excluded_rows
            + report.malformed_rows
            + report.unsupported.values().sum::<usize>()
            != report.rows
    {
        return Err("baseline population/transformed counts do not agree with case records".into());
    }
    for (id, c) in &report.cases {
        if c.id != *id
            || c.expected.is_empty()
            || c.recovered > c.expected.len()
            || (c.matched && c.recovered != c.expected.len())
            || c.recovered_sets.iter().map(Vec::len).max().unwrap_or(0) != c.recovered
            || c.recovered_sets.windows(2).any(|w| w[0] >= w[1])
            || c.recovered_sets.iter().any(|set| {
                set.is_empty()
                    || set.iter().any(|&i| i >= c.expected.len())
                    || set.windows(2).any(|w| w[0] >= w[1])
                    || c.recovered_sets
                        .iter()
                        .any(|other| other.len() > set.len() && covers(other, set))
            })
        {
            return Err(format!("invalid baseline outcome: {id}"));
        }
    }
    Ok(())
}
