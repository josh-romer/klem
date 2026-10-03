//! COV-021p: standard written inflections stay distinct from pronunciation.
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/phonetic-paradigm-sources.json")).unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-phonetic-paradigms-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-phonetic-paradigm.json",
            )],
            &path,
            "phonetic-paradigms",
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

fn matches(analysis: &Analysis, judgment: &Value) -> bool {
    analysis
        .lemmas
        .iter()
        .map(|l| l.text.as_str())
        .eq(judgment["lemmas"]
            .as_array()
            .unwrap()
            .iter()
            .map(|s| s.as_str().unwrap()))
        && serde_json::to_value(analysis.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == judgment["lemma_kinds"]
        && analysis
            .morphemes
            .iter()
            .map(|m| m.form.as_str())
            .eq(judgment["morphemes"]
                .as_array()
                .unwrap()
                .iter()
                .map(|s| s.as_str().unwrap()))
        && serde_json::to_value(
            analysis
                .morphemes
                .iter()
                .map(|m| m.kind)
                .collect::<Vec<_>>(),
        )
        .unwrap()
            == judgment["morpheme_kinds"]
}

#[test]
fn import_preserves_conflicting_written_fields_and_separate_pronunciations() {
    let source = sources();
    let fixture = Fixture::new("native");
    let dictionary = SqliteDictionary::open(&fixture.0).unwrap();
    for expected in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(
                dictionary
                    .entry(expected["id"].as_str().unwrap())
                    .unwrap()
                    .unwrap()
            )
            .unwrap(),
            *expected
        );
    }
    for review in source["reviews"].as_array().unwrap() {
        let original = &review["original_observation"];
        let entry = dictionary
            .entry(original["entry_id"].as_str().unwrap())
            .unwrap()
            .unwrap();
        let form = &entry.forms[original["form_index"].as_u64().unwrap() as usize];
        assert_eq!(form.written, original["written"].as_str().unwrap());
        assert_ne!(
            form.written,
            review["standard_written_companion"].as_str().unwrap()
        );
        // Spelling adjudication must not mutate pronunciation evidence or native fields.
        let native = &source["complete_native_entries"][&entry.summary.id];
        assert_eq!(serde_json::to_value(&entry.forms).unwrap(), native["forms"]);
    }
}

#[test]
fn scoped_spelling_judgments_preserve_raw_alternatives_and_unicode() {
    let source = sources();
    let ledger: Value = serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    let engine = Lemmatizer::new();
    for (surface, frozen) in source["before_words"].as_object().unwrap() {
        let before: WordAnalysis = serde_json::from_value(frozen.clone()).unwrap();
        let word = engine.analyze_word(surface).unwrap();
        let retained: Vec<_> = word
            .analyses
            .iter()
            .filter(|analysis| before.analyses.contains(analysis))
            .cloned()
            .collect();
        assert_eq!(retained, before.analyses, "{surface}");
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().all(|a| a.breakdown().is_some()));
    }
    for case in source["cases"].as_array().unwrap() {
        assert_eq!(
            ledger["cases"]
                .as_array()
                .unwrap()
                .iter()
                .find(|item| item["id"] == case["id"])
                .unwrap(),
            case
        );
        let word = engine
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        let judgment = &case["judgments"][0];
        assert_eq!(
            word.analyses.iter().any(|a| matches(a, judgment)),
            judgment["verdict"] == "required",
            "{}",
            case["id"]
        );
        if judgment["verdict"] == "forbidden" {
            assert!(word.analyses.iter().any(|a| a.unchanged), "{}", case["id"]);
        }
    }
}

#[test]
fn source_forms_do_not_create_aliases_and_all_cli_filters_match_the_library() {
    let source = sources();
    let fixture = Fixture::new("cli");
    let dictionary = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 4096);
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        for surface in source["before_words"].as_object().unwrap().keys() {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = session.annotate(&word).unwrap();
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
            let mut actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(annotation).unwrap()
            );
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(actual).unwrap(),
                word
            );
            for case in source["cases"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|c| c["surface"] == surface.as_str())
            {
                let judgment = &case["judgments"][0];
                assert_eq!(
                    word.analyses.iter().any(|a| matches(a, judgment)),
                    judgment["verdict"] == "required",
                    "{flag:?} {}",
                    case["id"]
                );
            }
        }
    }
}
