//! COV-021r: original excluded fields retain individual written-form judgments.
#[path = "../tools/validity.rs"]
mod validity;

use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Error, Lemmatizer, TokenKind, WordAnalysis};
use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/excluded-paradigm-sources.json")).unwrap()
}

fn suite() -> validity::Suite {
    let source = sources();
    serde_json::from_value(serde_json::json!({
        "schema_version": 1,
        "review_status": "Finite native written head/ending review; other candidates remain unjudged.",
        "sources": source["sources"],
        "cases": source["cases"],
    })).unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-excluded-paradigms-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-excluded-paradigm.json",
            )],
            &path,
            "excluded-paradigms",
        )
        .unwrap();
        Self(path)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn retains_prior_paths(word: &WordAnalysis, frozen: &WordAnalysis) {
    assert_eq!(word.normalized, frozen.normalized);
    let retained: Vec<_> = word
        .analyses
        .iter()
        .filter(|analysis| frozen.analyses.contains(analysis))
        .collect();
    assert_eq!(retained, frozen.analyses.iter().collect::<Vec<_>>());
}

#[test]
fn original_exclusions_native_fields_and_missing_spellings_stay_intact() {
    let source = sources();
    let fixture = Fixture::new("native");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    assert_eq!(source["original_exclusions"].as_array().unwrap().len(), 67);
    assert_eq!(
        source["complete_native_entries"].as_object().unwrap().len(),
        63
    );
    let mut empty = 0;
    let mut padded = 0;
    for expected in source["source_entries"].as_array().unwrap() {
        let entry = db.entry(expected["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        assert_eq!(
            serde_json::to_value(&entry.forms).unwrap(),
            source["complete_native_entries"][&entry.summary.id]["forms"]
        );
    }
    for review in source["reviews"].as_array().unwrap() {
        let original = &review["original_observation"];
        assert!(
            source["original_exclusions"]
                .as_array()
                .unwrap()
                .contains(original)
        );
        let entry = db
            .entry(original["entry_id"].as_str().unwrap())
            .unwrap()
            .unwrap();
        let form = &entry.forms[original["form_index"].as_u64().unwrap() as usize];
        let written = original["written"].as_str().unwrap();
        assert_eq!(form.written, written);
        if written.is_empty() {
            empty += 1;
            assert!(review["diagnostic_surface"].is_null());
            assert_eq!(review["disposition"], "empty_written_field");
            assert!(!source["cases"].as_array().unwrap().iter().any(|c| {
                c["id"]
                    .as_str()
                    .unwrap()
                    .starts_with(review["id"].as_str().unwrap())
            }));
        } else {
            padded += 1;
            assert_eq!(review["diagnostic_surface"], written.trim());
            assert_ne!(written, written.trim());
        }
    }
    assert_eq!((empty, padded), (10, 57));
    let entry = db.entry("krdict:90327").unwrap().unwrap();
    assert_eq!(entry.forms[1].written, "조라들어 ");
    assert_eq!(entry.forms[1].pronunciations, ["조라드러"]);
    assert!(
        entry
            .senses
            .iter()
            .flat_map(|s| &s.examples)
            .flatten()
            .any(|example| example.contains("졸아들어"))
    );
    // A source spelling is evidence, never an automatic lookup alias.
    assert!(db.lookup("조라들다").unwrap().is_empty());
}

#[test]
fn written_paths_unicode_and_every_original_raw_candidate_are_preserved() {
    let source = sources();
    let ledger: Value = serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    for case in source["cases"].as_array().unwrap() {
        assert_eq!(
            ledger["cases"]
                .as_array()
                .unwrap()
                .iter()
                .find(|c| c["id"] == case["id"])
                .unwrap(),
            case
        );
    }
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (57, 1));
    let engine = Lemmatizer::new();
    for (surface, modes) in source["before_words"].as_object().unwrap() {
        let word = engine.analyze_word(surface).unwrap();
        let frozen: WordAnalysis = serde_json::from_value(modes["all"].clone()).unwrap();
        // Future independently licensed additions may extend these words;
        // every earlier alternative and its relative order must remain.
        retains_prior_paths(&word, &frozen);
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in word.analyses {
            assert!(a.breakdown().is_some(), "{surface}: {a:?}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    assert!(
        engine
            .analyze_word("조라들어")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.iter().any(|l| l.text == "조라들다"))
    );
    // The authored conflict rejects only 졸아들다 + 어 on this written input;
    // it must not erase the identity or hypothetical alternate root.
}

#[test]
fn padded_source_fields_have_lossless_text_offsets_and_no_silent_word_cleanup() {
    let source = sources();
    let engine = Lemmatizer::new();
    for review in source["reviews"].as_array().unwrap() {
        let written = review["original_observation"]["written"].as_str().unwrap();
        assert_eq!(
            engine.analyze_word(written).unwrap_err(),
            if written.is_empty() {
                Error::EmptyWord
            } else {
                Error::WhitespaceInWord
            }
        );
        let records: Vec<_> = engine.analyze_text(written).collect();
        assert_eq!(
            records
                .iter()
                .map(|r| r.surface.as_str())
                .collect::<String>(),
            written
        );
        let mut offset = 0;
        for record in &records {
            assert_eq!(record.span, offset..offset + record.surface.len());
            assert_eq!(record.surface, written[record.span.clone()]);
            offset = record.span.end;
            match record.kind {
                TokenKind::Word => assert_eq!(
                    record.analysis.as_deref().unwrap(),
                    &engine.analyze_word(written.trim()).unwrap()
                ),
                TokenKind::Whitespace => assert!(record.analysis.is_none()),
                TokenKind::Punctuation => panic!("unexpected punctuation: {written:?}"),
            }
        }
        assert_eq!(offset, written.len());
        let frozen = &source["before_text_records"][review["id"].as_str().unwrap()];
        let actual = serde_json::to_value(&records).unwrap();
        let expected = frozen.as_array().unwrap();
        assert_eq!(records.len(), expected.len());
        for (record, before) in records.iter().zip(expected) {
            let current = serde_json::to_value(record).unwrap();
            for field in ["surface", "span", "kind"] {
                assert_eq!(current[field], before[field]);
            }
            if let Some(word) = record.analysis.as_deref() {
                retains_prior_paths(
                    word,
                    &serde_json::from_value(before["analysis"].clone()).unwrap(),
                );
            } else {
                assert!(before["analysis"].is_null());
            }
        }
        let mut child = Command::new(env!("CARGO_BIN_EXE_klem"))
            .arg("text")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(written.as_bytes())
            .unwrap();
        let output = child.wait_with_output().unwrap();
        assert!(output.status.success());
        let cli: Vec<Value> = String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert_eq!(serde_json::to_value(cli).unwrap(), actual);
    }
}

#[test]
fn dictionary_filters_preserve_named_paths_and_match_cli_component_assessments() {
    let source = sources();
    let fixture = Fixture::new("cli");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let report = validity::evaluate_with(&suite(), |surface| {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = dictionary.annotate(&word).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut word, filter);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let output = command.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["dictionary"],
                serde_json::to_value(&annotation).unwrap()
            );
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(actual).unwrap(),
                word
            );
            assert!(dictionary.cache_bytes() <= 4096);
            if surface == "조라들어" {
                assert!(
                    !annotation
                        .lemmas
                        .iter()
                        .any(|l| l.entries.iter().any(|e| e.entry.id == "krdict:90327"))
                );
            } else {
                let case = source["cases"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .find(|c| c["surface"] == surface)
                    .unwrap();
                let head = case["judgments"][0]["lemmas"][0].as_str().unwrap();
                assert!(
                    annotation
                        .lemmas
                        .iter()
                        .any(|l| l.lemma.text == head && !l.entries.is_empty()),
                    "{flag:?} {surface}"
                );
            }
            Ok(word)
        })
        .unwrap();
        assert!(report.passed(), "{flag:?}: {:?}", report.violations);
    }
}
