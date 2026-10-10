//! Expression homonyms retain their own source identity and original examples.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Lemmatizer, TokenKind};
use serde_json::Value;
use std::{
    collections::BTreeMap,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;
#[path = "../tools/validity.rs"]
mod validity;

struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-formal-expression-{test}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/formal-volitional-expression-native.json",
        )],
        &path,
        "complete-original-formal-expression",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), dictionary)
}

fn suite() -> validity::Suite {
    serde_json::from_str(include_str!(
        "fixtures/formal-volitional-expression-validity.json"
    ))
    .unwrap()
}

#[test]
fn eight_independent_original_expression_paths_pass_without_expanding_contraction_notes() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (8, 8, 0)
    );
    assert!(!report.review_queue.is_empty());
    assert_eq!(suite.cases[4].surface, "모으렵니까");
    assert_eq!(suite.cases[4].judgments[0].lemmas, ["모으다"]);
    assert_eq!(suite.cases[0].surface, suite.cases[3].surface);
    assert_ne!(suite.cases[0].id, suite.cases[3].id);
    let (_cleanup, dictionary) = dictionary("compatible");
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 4096);
    let report = validity::evaluate_with(&suite, |surface| {
        let mut word = engine.analyze_word(surface).map_err(|e| e.to_string())?;
        let annotation = session.annotate(&word).map_err(|e| e.to_string())?;
        word.analyses
            .retain(|path| annotation.assess(path).status != Compatibility::Incompatible);
        Ok(word)
    })
    .unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_present, 8);
}

#[test]
fn original_expression_entries_preserve_every_native_field_and_separate_ending_owners() {
    let (_cleanup, dictionary) = dictionary("native");
    let expected: BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/formal-volitional-expression-native-entries.json"
    ))
    .unwrap();
    assert_eq!(expected.len(), 16);
    for (id, owner) in &expected {
        assert_eq!(
            serde_json::to_value(dictionary.entry(id).unwrap().unwrap()).unwrap(),
            *owner,
            "{id}"
        );
    }
    for id in ["krdict:89455", "krdict:89456"] {
        assert_eq!(expected[id]["homonym"], "2");
        assert_eq!(expected[id]["pos"], "품사 없음");
        assert_eq!(expected[id]["lexical_unit"], "문법‧표현");
        assert_eq!(
            expected[id]["senses"][0]["examples"]
                .as_array()
                .unwrap()
                .len(),
            4
        );
    }
    for id in [
        "krdict:86548",
        "krdict:86549",
        "krdict:86604",
        "krdict:86605",
    ] {
        assert_eq!(expected[id]["pos"], "어미");
        assert_eq!(expected[id]["lexical_unit"], "단어");
    }
}

#[test]
fn cli_library_filters_caches_unicode_and_ordered_breakdowns_agree_for_every_expression_case() {
    let (cleanup, dictionary) = dictionary("cli");
    let suite = suite();
    let engine = Lemmatizer::new();
    for encoding in ["NFC", "NFD"] {
        let text = suite
            .cases
            .iter()
            .map(|c| {
                if encoding == "NFC" {
                    c.surface.clone()
                } else {
                    c.surface.nfd().collect()
                }
            })
            .collect::<Vec<String>>()
            .join(" ");
        for flag in [None, Some("--dict-only"), Some("--dict-compatible")] {
            let mut previous = None;
            for cache in [0, 4096] {
                let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
                command.args(["text", "-", "--dictionary"]);
                command.arg(&cleanup.0);
                if let Some(flag) = flag {
                    command.arg(flag);
                }
                command.args(["--cache-bytes", &cache.to_string()]);
                let mut child = command
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .stderr(Stdio::piped())
                    .spawn()
                    .unwrap();
                child
                    .stdin
                    .take()
                    .unwrap()
                    .write_all(text.as_bytes())
                    .unwrap();
                let output = child.wait_with_output().unwrap();
                assert!(
                    output.status.success(),
                    "{}",
                    String::from_utf8_lossy(&output.stderr)
                );
                assert!(output.stderr.is_empty());
                let records: Vec<Value> = String::from_utf8(output.stdout.clone())
                    .unwrap()
                    .lines()
                    .map(|line| serde_json::from_str(line).unwrap())
                    .collect();
                let tokens = engine.analyze_text(&text).collect::<Vec<_>>();
                assert_eq!(records.len(), tokens.len());
                let mut session = DictionarySession::new(&dictionary, cache);
                for (record, token) in records.iter().zip(tokens) {
                    assert_eq!(record["surface"], token.surface);
                    assert_eq!(record["span"]["start"], token.span.start);
                    assert_eq!(record["span"]["end"], token.span.end);
                    if token.kind != TokenKind::Word {
                        continue;
                    }
                    let mut word = token.analysis.unwrap().as_ref().clone();
                    let mut annotation = session.annotate(&word).unwrap();
                    if let Some(flag) = flag {
                        let policy = if flag == "--dict-only" {
                            DictionaryFilter::Headword
                        } else {
                            DictionaryFilter::Compatible
                        };
                        annotation.filter(&mut word, policy);
                    }
                    assert_eq!(record["analysis"], serde_json::to_value(&word).unwrap());
                    assert_eq!(
                        record["dictionary"],
                        serde_json::to_value(&annotation).unwrap()
                    );
                    assert!(word.analyses.iter().all(|path| path.breakdown().is_some()));
                }
                if let Some(previous) = &previous {
                    assert_eq!(previous, &output.stdout);
                }
                previous = Some(output.stdout);
            }
        }
    }
}
