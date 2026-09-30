use klem::dictionary::{Annotation, DictionaryFilter, DictionarySession, SqliteDictionary};
use klem::{Lemmatizer, Session, TokenAnalysis};
use serde::Serialize;
mod dictionary_cli;
use std::{
    env,
    fs::File,
    io::{self, BufWriter, Read, Write},
    sync::Arc,
};

const HELP: &str = "klem — Korean lemma candidates\n\nUsage:\n  klem word <word> [--format jsonl|text]\n  klem text [file|-] [--format jsonl|text] [--cache-bytes N]\n  klem explain <rule-id>\n\nJSON Lines is the default. Text records include original UTF-8 byte offsets.\nText input defaults to stdin. Cache defaults to 8 MiB; use 0 to disable.\nAll candidates are grammatical hypotheses, not dictionary-verified words.\n";

const DICTIONARY_HELP: &str = "\nOffline dictionaries:\n  klem dict import-krdict <json-directory|file> <new.db> --snapshot <label>\n  klem dict info <db>\n  klem dict lookup <db> <headword>\n  klem dict entry <db> <entry-id>\n  klem word <word> --dictionary <db> [--dict-only | --dict-compatible]\n  klem text [file|-] --dictionary <db> [--dict-only | --dict-compatible]\nDictionary annotations require JSONL and preserve every candidate by default.\n--dict-only requires --dictionary and keeps analyses with dictionary entries\nfor every lemma, regardless of POS compatibility. Unmatched words retain an\nempty analyses array; text records and offsets are preserved.\n--dict-compatible additionally excludes known lexical-role/attachment conflicts.\nUnknown classes remain; the finite checks do not prove grammatical correctness.\n--suggest-spacing adds separate dictionary-backed case-phrase/predicate hypotheses.\nOriginal tokens and candidates stay intact; no sentence grammar is inferred.\nOptional bounds: --spacing-limit N (16), --spacing-probes N (256),\n--spacing-max-chars N (64 NFC characters). Reached bounds are reported.\n";

#[derive(Serialize)]
struct Annotated<T> {
    #[serde(flatten)]
    record: T,
    dictionary: Option<Annotation>,
    #[serde(skip_serializing_if = "Option::is_none")]
    spacing: Option<klem::spacing::SpacingSuggestions>,
}

fn run() -> klem::dictionary::Result<()> {
    let mut args = env::args().skip(1);
    let Some(command) = args.next() else {
        print!("{HELP}{DICTIONARY_HELP}");
        return Ok(());
    };
    if command == "--help" || command == "-h" {
        print!("{HELP}{DICTIONARY_HELP}");
        return Ok(());
    }
    if command == "--version" {
        println!("klem {}", env!("CARGO_PKG_VERSION"));
        return Ok(());
    }
    if command == "dict" {
        return dictionary_cli::run(args.collect());
    }
    let mut input = None;
    let mut format = "jsonl".to_owned();
    let mut budget = 8 * 1024 * 1024;
    let mut dictionary_path = None;
    let mut dict_only = false;
    let mut dict_compatible = false;
    let mut suggest_spacing = false;
    let mut spacing_limits = klem::spacing::SpacingLimits::default();
    let mut spacing_options = false;
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--help" | "-h" => {
                print!("{HELP}{DICTIONARY_HELP}");
                return Ok(());
            }
            "--format" => format = args.next().ok_or("--format needs jsonl or text")?,
            "--suggest-spacing" => suggest_spacing = true,
            "--spacing-limit" | "--spacing-probes" | "--spacing-max-chars" => {
                spacing_options = true;
                let value = args
                    .next()
                    .ok_or("spacing limits need an integer")?
                    .parse()?;
                match arg.as_str() {
                    "--spacing-limit" => spacing_limits.alternatives = value,
                    "--spacing-probes" => spacing_limits.segment_probes = value,
                    _ => spacing_limits.token_chars = value,
                }
            }
            "--dict-only" => dict_only = true,
            "--dict-compatible" => dict_compatible = true,
            "--dictionary" => {
                let path = args.next().ok_or("--dictionary needs a database path")?;
                if dictionary_path.replace(path).is_some() {
                    return Err("--dictionary may only be supplied once".into());
                }
            }
            "--cache-bytes" => {
                budget = args
                    .next()
                    .ok_or("--cache-bytes needs an integer")?
                    .parse()?
            }
            "-" => {
                if input.replace(arg).is_some() {
                    return Err("too many inputs".into());
                }
            }
            _ if arg.starts_with('-') => return Err(format!("unknown option: {arg}").into()),
            _ => {
                if input.replace(arg).is_some() {
                    return Err("too many inputs".into());
                }
            }
        }
    }
    if !matches!(format.as_str(), "jsonl" | "text") {
        return Err("--format must be jsonl or text".into());
    }
    if spacing_options && !suggest_spacing {
        return Err("spacing limits require --suggest-spacing".into());
    }
    if suggest_spacing && dictionary_path.is_none() {
        return Err("--suggest-spacing requires --dictionary <db>".into());
    }
    if (dict_only || dict_compatible) && dictionary_path.is_none() {
        return Err(if dict_compatible {
            "--dict-compatible requires --dictionary <db>"
        } else {
            "--dict-only requires --dictionary <db>"
        }
        .into());
    }
    if dictionary_path.is_some()
        && (format != "jsonl" || !matches!(command.as_str(), "word" | "text"))
    {
        return Err("--dictionary requires word/text with --format jsonl".into());
    }
    let filter = if dict_compatible {
        Some(DictionaryFilter::Compatible)
    } else if dict_only {
        Some(DictionaryFilter::Headword)
    } else {
        None
    };
    let dictionary = dictionary_path.map(SqliteDictionary::open).transpose()?;
    let mut dictionary_session = dictionary
        .as_ref()
        .map(|d| DictionarySession::new(d, 4 * 1024 * 1024));
    let engine = Arc::new(Lemmatizer::new());
    let mut out = BufWriter::new(io::stdout().lock());
    match command.as_str() {
        "word" => {
            let word = input.ok_or("word requires one word")?;
            let mut result = engine.analyze_word(&word)?;
            if format == "jsonl" {
                if let Some(session) = &mut dictionary_session {
                    let spacing = if suggest_spacing {
                        let mut words = Session::new(engine.clone(), budget);
                        Some(klem::spacing::suggest(
                            &mut words,
                            session,
                            &word,
                            0,
                            spacing_limits,
                        )?)
                    } else {
                        None
                    };
                    let mut annotation = session.annotate(&result)?;
                    if let Some(policy) = filter {
                        annotation.filter(&mut result, policy);
                    }
                    serde_json::to_writer(
                        &mut out,
                        &Annotated {
                            record: &result,
                            dictionary: Some(annotation),
                            spacing,
                        },
                    )?;
                } else {
                    serde_json::to_writer(&mut out, &result)?;
                }
                writeln!(out)?;
            } else {
                for a in &result.analyses {
                    let lemmas = a
                        .lemmas
                        .iter()
                        .map(|l| l.text.as_str())
                        .collect::<Vec<_>>()
                        .join(" + ");
                    let morphs = a
                        .morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .collect::<Vec<_>>()
                        .join(" + ");
                    writeln!(out, "{lemmas}\t{morphs}\t{}", a.rules.join(", "))?;
                }
            }
        }
        "text" => {
            let reader: Box<dyn Read> = match input.as_deref() {
                None | Some("-") => Box::new(io::stdin().lock()),
                Some(path) => Box::new(File::open(path)?),
            };
            let mut spacing_words = suggest_spacing.then(|| Session::new(engine.clone(), budget));
            let mut session = Session::new(engine, budget);
            klem::analyze_reader(reader, &mut session, |mut record| {
                if let Some(dictionary) = &mut dictionary_session {
                    let spacing = if record.kind == klem::TokenKind::Word
                        && let Some(words) = &mut spacing_words
                    {
                        Some(
                            klem::spacing::suggest(
                                words,
                                dictionary,
                                &record.surface,
                                record.span.start,
                                spacing_limits,
                            )
                            .map_err(io::Error::other)?,
                        )
                    } else {
                        None
                    };
                    let mut annotation = record
                        .analysis
                        .as_ref()
                        .map(|a| dictionary.annotate(a))
                        .transpose()
                        .map_err(io::Error::other)?;
                    if let Some(policy) = filter
                        && let (Some(analysis), Some(annotation)) =
                            (record.analysis.as_mut(), annotation.as_mut())
                    {
                        // Session cache entries stay unfiltered for future consumers.
                        annotation.filter(Arc::make_mut(analysis), policy);
                    }
                    serde_json::to_writer(
                        &mut out,
                        &Annotated {
                            record: &record,
                            dictionary: annotation,
                            spacing,
                        },
                    )?;
                    writeln!(out)
                } else {
                    write_record(&mut out, &record, &format)
                }
            })?;
        }
        "explain" => {
            let id = input.ok_or("explain requires a rule ID")?;
            writeln!(
                out,
                "{}",
                klem::rule_explanation(&id).ok_or("unknown rule ID")?
            )?;
        }
        _ => return Err(format!("unknown command: {command}\n{HELP}").into()),
    }
    out.flush()?;
    Ok(())
}

fn write_record(out: &mut impl Write, record: &TokenAnalysis, format: &str) -> io::Result<()> {
    if format == "jsonl" {
        serde_json::to_writer(&mut *out, record)?;
        writeln!(out)
    } else {
        let lemmas = record
            .analysis
            .as_ref()
            .map(|a| a.lemma_strings().join(", "))
            .unwrap_or_default();
        writeln!(
            out,
            "{}..{}\t{}\t{}",
            record.span.start,
            record.span.end,
            serde_json::to_string(&record.surface)?,
            lemmas
        )
    }
}

fn main() {
    if let Err(error) = run() {
        if error
            .downcast_ref::<io::Error>()
            .is_some_and(|e| e.kind() == io::ErrorKind::BrokenPipe)
            || error
                .downcast_ref::<serde_json::Error>()
                .is_some_and(|e| e.io_error_kind() == Some(io::ErrorKind::BrokenPipe))
        {
            return;
        }
        eprintln!("klem: {error}");
        std::process::exit(1);
    }
}
