//! Local targets authored from complete novel lines; other analyses remain open.
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
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
        "klem-conjectural-additive-novel-{test}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/conjectural-additive-novel-native.json",
        )],
        &path,
        "original-novel-context-owners",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), dictionary)
}

fn suite() -> validity::Suite {
    serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-novel-validity.json"
    ))
    .unwrap()
}

fn contexts() -> Value {
    serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-novel-contexts.json"
    ))
    .unwrap()
}

#[test]
fn every_original_novel_lexical_homonym_imports_without_changing_native_fields() {
    let (_cleanup, dictionary) = dictionary("native");
    let owners: BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-novel-native-entries.json"
    ))
    .unwrap();
    assert_eq!(owners.len(), 29);
    for (id, expected) in &owners {
        assert_eq!(
            serde_json::to_value(dictionary.entry(id).unwrap().unwrap()).unwrap(),
            *expected,
            "{id}"
        );
    }
    assert_eq!(owners["krdict:36428"]["pos"], "부사");
    assert_eq!(owners["krdict:62027"]["pos"], "관형사");
    assert_eq!(owners["krdict:86232"]["pos"], "조사");
    assert_eq!(
        owners
            .values()
            .filter(|owner| owner["headword"] == "들리다")
            .count(),
        6
    );
    assert_eq!(owners["krdict:89906"]["headword"], "내다");
}

#[test]
fn all_sixteen_independent_novel_requirements_survive_unicode_and_dictionary_policies() {
    let (_cleanup, dictionary) = dictionary("targets");
    let engine = Lemmatizer::new();
    for nfd in [false, true] {
        let mut suite = suite();
        assert_eq!(suite.cases.len(), 15);
        if nfd {
            for case in &mut suite.cases {
                case.surface = case.surface.nfd().collect();
            }
        }
        let raw = validity::evaluate(&suite).unwrap();
        assert!(raw.passed(), "{:?}", raw.violations);
        assert_eq!((raw.required_present, raw.forbidden_total), (16, 0));
        for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            for cache in [0, 4096] {
                let mut session = DictionarySession::new(&dictionary, cache);
                let report = validity::evaluate_with(&suite, |surface| {
                    let mut word = engine
                        .analyze_word(surface)
                        .map_err(|error| error.to_string())?;
                    let mut annotation =
                        session.annotate(&word).map_err(|error| error.to_string())?;
                    annotation.filter(&mut word, policy);
                    assert!(word.analyses.iter().all(|path| path.breakdown().is_some()));
                    assert!(session.cache_bytes() <= cache);
                    Ok(word)
                })
                .unwrap();
                assert!(report.passed(), "{:?}", report.violations);
                assert_eq!((report.required_present, report.forbidden_total), (16, 0));
            }
        }
    }
}

#[test]
fn complete_original_novel_lines_have_exact_cli_library_spans_policies_and_cache_parity() {
    let (cleanup, dictionary) = dictionary("cli");
    let source = contexts();
    let items = source["items"].as_array().unwrap();
    assert_eq!(items.len(), 15);
    let engine = Lemmatizer::new();
    for full_context in [true, false] {
        for nfd in [false, true] {
            let mut text = String::new();
            let mut positions = Vec::new();
            for item in items {
                let surface = item["surface"].as_str().unwrap();
                let line = item["complete_original_line"].as_str().unwrap();
                let start = (item["span"]["start"].as_u64().unwrap()
                    - item["line_byte_start"].as_u64().unwrap())
                    as usize;
                let end = (item["span"]["end"].as_u64().unwrap()
                    - item["line_byte_start"].as_u64().unwrap()) as usize;
                assert_eq!(&line[start..end], surface);
                if !text.is_empty() {
                    text.push('\n');
                }
                let group = if full_context { line } else { surface };
                let prefix = if full_context { &line[..start] } else { "" };
                positions.push(
                    text.len()
                        + if nfd {
                            prefix.nfd().collect::<String>().len()
                        } else {
                            prefix.len()
                        },
                );
                if nfd {
                    text.extend(group.nfd());
                } else {
                    text.push_str(group);
                }
            }
            for (mode, filter) in [
                ("raw", None),
                ("headword", Some(DictionaryFilter::Headword)),
                ("compatible", Some(DictionaryFilter::Compatible)),
            ] {
                let mut uncached = None;
                for cache in [0, 4096] {
                    let mut session = DictionarySession::new(&dictionary, cache);
                    let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
                    command.args(["text", "-", "--dictionary"]).arg(&cleanup.0);
                    if mode == "headword" {
                        command.arg("--dict-only");
                    }
                    if mode == "compatible" {
                        command.arg("--dict-compatible");
                    }
                    command.args(["--cache-bytes", &cache.to_string()]);
                    let mut child = command
                        .stdin(Stdio::piped())
                        .stdout(Stdio::piped())
                        .stderr(Stdio::piped())
                        .spawn()
                        .unwrap();
                    let mut input = child.stdin.take().unwrap();
                    let bytes = text.as_bytes().to_vec();
                    let writer = std::thread::spawn(move || input.write_all(&bytes));
                    let output = child.wait_with_output().unwrap();
                    writer.join().unwrap().unwrap();
                    assert!(output.status.success(), "{:?}", output.stderr);
                    assert!(output.stderr.is_empty());
                    if let Some(before) = &uncached {
                        assert_eq!(before, &output.stdout);
                    } else {
                        uncached = Some(output.stdout.clone());
                    }
                    let rows: Vec<Value> = std::str::from_utf8(&output.stdout)
                        .unwrap()
                        .lines()
                        .map(|line| serde_json::from_str(line).unwrap())
                        .collect();
                    let tokens: Vec<_> = engine.analyze_text(&text).collect();
                    assert_eq!(rows.len(), tokens.len());
                    let mut cursor = 0;
                    let mut target_count = 0;
                    for (row, token) in rows.iter().zip(tokens) {
                        assert_eq!(token.span.start, cursor);
                        assert_eq!(row["span"]["start"], cursor);
                        cursor = token.span.end;
                        assert_eq!(row["surface"], &text[token.span.clone()]);
                        let mut expected = serde_json::to_value(&token).unwrap();
                        expected["dictionary"] = Value::Null;
                        if token.kind == TokenKind::Word {
                            let mut filtered = token.analysis.as_ref().unwrap().as_ref().clone();
                            let mut annotation = session.annotate(&filtered).unwrap();
                            if let Some(policy) = filter {
                                annotation.filter(&mut filtered, policy);
                            }
                            expected["analysis"] = serde_json::to_value(&filtered).unwrap();
                            expected["dictionary"] = serde_json::to_value(&annotation).unwrap();
                            if let Some(index) = positions
                                .iter()
                                .position(|position| *position == token.span.start)
                            {
                                let mut one = suite();
                                one.cases = vec![one.cases.remove(index)];
                                one.cases[0].surface = token.surface.clone();
                                let report =
                                    validity::evaluate_with(&one, |_| Ok(filtered.clone()))
                                        .unwrap();
                                assert!(
                                    report.passed(),
                                    "{} {mode} nfd={nfd} cache={cache}: {:?}",
                                    one.cases[0].id,
                                    report.violations
                                );
                                target_count += report.required_present;
                            }
                        }
                        assert_eq!(
                            *row, expected,
                            "full_context={full_context} {mode} nfd={nfd} cache={cache}"
                        );
                    }
                    assert_eq!(cursor, text.len());
                    assert_eq!(target_count, 16);
                }
            }
        }
    }
}
