//! Run with: cargo run --release --example dictionary_coverage -- <db> <text>
//! Reports lexical coverage, not accuracy; names and historical spellings can miss.
use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary};
use klem::{Lemmatizer, Session};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    fs::File,
    io::{self, Read},
    sync::Arc,
    time::Instant,
};

fn main() -> klem::dictionary::Result<()> {
    let args: Vec<_> = env::args().skip(1).collect();
    if args.len() != 2 {
        return Err("usage: dictionary_coverage <db> <text>".into());
    }
    let db = SqliteDictionary::open(&args[0])?;
    let mut hash = Sha256::new();
    let mut input = File::open(&args[1])?;
    let mut buffer = [0; 64 * 1024];
    loop {
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        hash.update(&buffer[..n]);
    }
    let input_hash = format!("{:x}", hash.finalize());
    let mut session = Session::new(Arc::new(Lemmatizer::new()), 8 * 1024 * 1024);
    let mut dictionary = DictionarySession::new(&db, 4 * 1024 * 1024);
    let mut words = 0usize;
    let mut any_match = 0usize;
    let mut complete_match = 0usize;
    let mut complete_pos_match = 0usize;
    let mut unique = BTreeSet::new();
    let mut unique_matched = BTreeSet::new();
    let mut unmatched = BTreeMap::<String, usize>::new();
    let start = Instant::now();
    klem::analyze_reader(File::open(&args[1])?, &mut session, |record| {
        let Some(analysis) = &record.analysis else {
            return Ok(());
        };
        words += 1;
        unique.insert(analysis.normalized.clone());
        let annotation = dictionary.annotate(analysis).map_err(io::Error::other)?;
        let any = annotation.lemmas.iter().any(|m| !m.entries.is_empty());
        let full = analysis.analyses.iter().any(|a| {
            !a.lemmas.is_empty() && a.lemmas.iter().all(|l| annotation.has_match(l, false))
        });
        let pos = analysis.analyses.iter().any(|a| {
            !a.lemmas.is_empty() && a.lemmas.iter().all(|l| annotation.has_match(l, true))
        });
        any_match += usize::from(any);
        complete_match += usize::from(full);
        complete_pos_match += usize::from(pos);
        if full {
            unique_matched.insert(analysis.normalized.clone());
        } else {
            *unmatched.entry(analysis.normalized.clone()).or_default() += 1;
        }
        Ok(())
    })?;
    let seconds = start.elapsed().as_secs_f64();
    let mut unmatched: Vec<_> = unmatched.into_iter().collect();
    unmatched.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(&b.0)));
    unmatched.truncate(50);
    serde_json::to_writer_pretty(
        io::stdout().lock(),
        &json!({
            "schema":1, "input_sha256":input_hash, "dictionary_fingerprint":db.fingerprint(),
            "dictionary":db.metadata(), "word_tokens":words, "tokens_with_any_lemma_match":any_match,
            "tokens_with_complete_analysis_match":complete_match,
            "tokens_with_complete_pos_compatible_analysis":complete_pos_match,
            "unique_word_types":unique.len(), "types_with_complete_analysis_match":unique_matched.len(),
            "most_frequent_unmatched":unmatched, "seconds":seconds,
            "lemma_cache_bytes":8*1024*1024, "dictionary_cache_budget":4*1024*1024,
            "dictionary_cache_accounted_bytes":dictionary.cache_bytes(),
            "interpretation":"Exact NFC headword coverage of generated candidates, not contextual or grammatical accuracy. Complete requires every lemma in one grouped analysis. Strict POS excludes unclassified and unknown roles."
        }),
    )?;
    Ok(())
}
