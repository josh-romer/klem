//! Independent judgments and observed alternatives have separate scopes.
use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{collections::BTreeMap, path::PathBuf, sync::OnceLock};
use unicode_normalization::UnicodeNormalization;
#[path = "../tools/validity.rs"]
mod validity;

fn history() -> &'static Value {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    HISTORY.get_or_init(|| {
        serde_json::from_str(include_str!(
            "fixtures/formal-volitional-novel-history.json"
        ))
        .unwrap()
    })
}

#[test]
fn four_manually_reviewed_novel_paths_recover_their_lexical_verbs() {
    let suite = serde_json::from_str(include_str!(
        "fixtures/formal-volitional-novel-validity.json"
    ))
    .unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (4, 0));
    assert!(!report.review_queue.is_empty());
}

#[test]
fn complete_changed_novel_frames_keep_every_previous_path_and_unicode_equivalence() {
    let engine = Lemmatizer::new();
    let frames = history()["raw_changed_frames"].as_array().unwrap();
    assert_eq!(frames.len(), 4);
    assert_eq!(
        history()["source_sha256"],
        "50a02d2f5f11f148497f2f00c782733ee3f8c2e331e1c0e5f74e3b7c8b0ca4dc"
    );
    for frame in frames {
        let surface = frame["after"]["surface"].as_str().unwrap();
        let before: WordAnalysis =
            serde_json::from_value(frame["before"]["analysis"].clone()).unwrap();
        let expected: WordAnalysis =
            serde_json::from_value(frame["after"]["analysis"].clone()).unwrap();
        let current = engine.analyze_word(surface).unwrap();
        assert_eq!(current, expected, "{surface}");
        assert_eq!(
            current,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            current
                .analyses
                .iter()
                .filter(|path| before.analyses.contains(path))
                .cloned()
                .collect::<Vec<_>>(),
            before.analyses
        );
        assert!(
            frame["complete_original_line"]
                .as_str()
                .unwrap()
                .contains(surface)
        );
    }
}

struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn every_observed_novel_alternative_keeps_its_complete_native_assessment() {
    let file = std::env::temp_dir().join(format!(
        "klem-formal-volitional-novel-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/formal-volitional-novel-native.json",
        )],
        &file,
        "complete-original-formal-volitional-novel",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let entries: BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/formal-volitional-novel-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 11);
    for (id, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 4096);
    let observations = history()["individual_additions"].as_array().unwrap();
    assert_eq!(observations.len(), 32);
    for observation in observations {
        let surface = observation["surface"].as_str().unwrap();
        let path: Analysis = serde_json::from_value(observation["analysis"].clone()).unwrap();
        let word = engine.analyze_word(surface).unwrap();
        assert!(word.analyses.contains(&path), "{}", observation["id"]);
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            serde_json::to_value(session.annotate(&word).unwrap().assess(&path)).unwrap(),
            observation["dictionary_assessment"],
            "{}",
            observation["id"]
        );
        assert!(
            path.rules
                .iter()
                .any(|rule| rule == "ending.formal_volitional")
        );
        assert!(
            path.rules
                .iter()
                .all(|rule| klem::rule_explanation(rule).is_some())
        );
        assert!(path.breakdown().is_some());
        assert_eq!(observation["contextual_verdict"], "unjudged");
        assert_eq!(observation["independent_review"], "pending");
    }
    let spacing = history()["individual_spacing_additions"]
        .as_array()
        .unwrap();
    assert_eq!(spacing.len(), 2);
    assert!(
        spacing
            .iter()
            .all(|item| item["contextual_verdict"] == "unjudged"
                && item["independent_review"] == "pending")
    );
}

fn without_fingerprints(value: &mut Value) {
    match value {
        Value::Object(fields) => {
            fields.remove("fingerprint");
            for child in fields.values_mut() {
                without_fingerprints(child);
            }
        }
        Value::Array(values) => {
            for child in values {
                without_fingerprints(child);
            }
        }
        _ => {}
    }
}

#[test]
fn recorded_spacing_hypotheses_keep_exact_owners_and_original_unicode_bytes() {
    use klem::dictionary::{DictionarySession, SqliteDictionary, import_krdict};
    use klem::spacing::{SpacingLimits, suggest};
    let file = std::env::temp_dir().join(format!(
        "klem-formal-volitional-spacing-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(file.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/formal-volitional-novel-native.json",
        )],
        &file,
        "krdict",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&file).unwrap();
    let mut dictionary_session = DictionarySession::new(&dictionary, 4096);
    let mut session = klem::Session::new(std::sync::Arc::new(Lemmatizer::new()), 4096);
    for observation in history()["individual_spacing_additions"]
        .as_array()
        .unwrap()
    {
        let original = observation["original_surface"].as_str().unwrap();
        let start = observation["original_span"]["start"].as_u64().unwrap() as usize;
        let mut expected = observation["hypothesis"].clone();
        without_fingerprints(&mut expected);
        let before = session.analyze_word(original).unwrap();
        let actual = suggest(
            &mut session,
            &mut dictionary_session,
            original,
            start,
            SpacingLimits::default(),
        )
        .unwrap();
        assert_eq!(before, session.analyze_word(original).unwrap());
        let mut captured = actual
            .alternatives
            .iter()
            .find(|hypothesis| {
                hypothesis.spaced == expected["spaced"].as_str().unwrap()
                    && serde_json::to_value(&hypothesis.inserted_at).unwrap()
                        == expected["inserted_at"]
            })
            .map(|hypothesis| serde_json::to_value(hypothesis).unwrap())
            .unwrap_or_else(|| panic!("{}", observation["id"]));
        without_fingerprints(&mut captured);
        assert_eq!(captured, expected, "{}", observation["id"]);

        let decomposed: String = original.nfd().collect();
        let parts: Vec<String> = expected["records"]
            .as_array()
            .unwrap()
            .iter()
            .map(|record| record["surface"].as_str().unwrap().nfd().collect())
            .collect();
        let mut boundaries = Vec::new();
        let mut offset = start;
        for part in parts.iter().take(parts.len() - 1) {
            offset += part.len();
            boundaries.push(offset);
        }
        let actual = suggest(
            &mut session,
            &mut dictionary_session,
            &decomposed,
            start,
            SpacingLimits::default(),
        )
        .unwrap();
        let hypothesis = actual
            .alternatives
            .iter()
            .find(|hypothesis| {
                hypothesis.spaced == parts.join(" ") && hypothesis.inserted_at == boundaries
            })
            .unwrap_or_else(|| panic!("decomposed {}", observation["id"]));
        let mut cursor = start;
        for segment in &hypothesis.records {
            assert_eq!(segment.record.span.start, cursor);
            assert_eq!(
                &decomposed[segment.record.span.start - start..segment.record.span.end - start],
                segment.record.surface
            );
            cursor = segment.record.span.end;
        }
        assert_eq!(cursor, start + decomposed.len());
        for segment in hypothesis.records.iter().chain(&hypothesis.joined_contexts) {
            assert_eq!(
                &decomposed[segment.record.span.start - start..segment.record.span.end - start],
                segment.record.surface
            );
            assert!(
                !segment
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .is_empty()
            );
            assert!(
                segment
                    .dictionary
                    .readings
                    .iter()
                    .all(|reading| reading.status != klem::dictionary::Compatibility::Incompatible)
            );
        }
    }
}
