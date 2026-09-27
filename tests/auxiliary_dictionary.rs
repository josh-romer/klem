//! COV-019m: per-entry evidence, independently of raw candidate validity.
use klem::dictionary::{
    Annotation, AttachmentConflict, Compatibility, DictionaryFilter, DictionarySession,
    SqliteDictionary, import_krdict, pos_compatibility,
};
use klem::{Analysis, Lemma, Lemmatizer, Morpheme, WordAnalysis};
use serde::Deserialize;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

#[derive(Deserialize)]
struct Judgment {
    entry_id: String,
    lemma_index: usize,
    status: Compatibility,
    conflicts: Vec<AttachmentConflict>,
}

#[derive(Deserialize)]
struct Case {
    id: String,
    surface: String,
    lemmas: Vec<Lemma>,
    morphemes: Vec<Morpheme>,
    judgments: Vec<Judgment>,
}

fn cases() -> Vec<Case> {
    #[derive(Deserialize)]
    struct Ledger {
        cases: Vec<Case>,
    }
    serde_json::from_str::<Ledger>(include_str!("fixtures/auxiliary-dictionary.json"))
        .unwrap()
        .cases
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-auxiliary-classes-{}-{name}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-auxiliary-dictionary.json",
            )],
            &path,
            "auxiliary-classes",
        )
        .unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_file(&self.0).unwrap();
    }
}

fn reading<'a>(word: &'a WordAnalysis, case: &Case) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| a.lemmas == case.lemmas && a.morphemes == case.morphemes)
        .unwrap_or_else(|| panic!("{}: missing path", case.id))
}

#[test]
fn auxiliary_entry_judgments_preserve_ownership_and_alternatives() {
    let fixture = Fixture::new("judgments");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let cases = cases();
    assert_eq!(cases.len(), 43);
    assert_eq!(cases.iter().map(|c| c.judgments.len()).sum::<usize>(), 86);
    for case in cases {
        let word = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap(),
            "{}",
            case.id
        );
        let a = reading(&word, &case);
        let annotation = dictionary.annotate(&word).unwrap();
        let assessed = annotation.assess(a);
        for j in &case.judgments {
            let entry = assessed.lemmas[j.lemma_index]
                .entries
                .iter()
                .find(|e| e.id == j.entry_id)
                .unwrap();
            assert_eq!(entry.status, j.status, "{}: {}", case.id, j.entry_id);
            assert_eq!(entry.conflicts, j.conflicts, "{}: {}", case.id, j.entry_id);
        }
        // Every exact group has a supported alternative, including two slots
        // for the same lemma with different classes in 먹어보나보다.
        for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut filtered = word.clone();
            let mut annotated = annotation.clone();
            annotated.filter(&mut filtered, policy);
            assert!(filtered.analyses.contains(a), "{}", case.id);
            assert_eq!(annotated.readings.len(), filtered.analyses.len());
            for (a, r) in filtered.analyses.iter().zip(&annotated.readings) {
                assert_eq!(*r, annotated.assess(a));
            }
        }
        assert!(dictionary.cache_bytes() <= 4096);
    }
}

#[test]
fn auxiliary_class_filter_handles_missing_homonyms_and_unknown_providers() {
    let fixture = Fixture::new("unknown");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 0);
    let word = Lemmatizer::new().analyze_word("오려나봐").unwrap();
    let case = cases()
        .into_iter()
        .find(|c| c.id == "aux-class-inference")
        .unwrap();
    let a = reading(&word, &case);
    let mut annotation = dictionary.annotate(&word).unwrap();
    let slot = annotation
        .lemmas
        .iter()
        .position(|m| m.lemma == a.lemmas[1])
        .unwrap();
    // A dictionary containing only the trial homonym is insufficient for this
    // inference reading. Headword mode still retains the unmodified group.
    annotation.lemmas[slot]
        .entries
        .retain(|e| e.entry.id == "krdict:62171");
    assert_eq!(annotation.assess(a).status, Compatibility::Incompatible);
    let mut headwords = word.clone();
    annotation
        .clone()
        .filter(&mut headwords, DictionaryFilter::Headword);
    assert!(headwords.analyses.contains(a));
    let mut compatible = word.clone();
    annotation
        .clone()
        .filter(&mut compatible, DictionaryFilter::Compatible);
    assert!(!compatible.analyses.contains(a));
    let matched = &mut annotation.lemmas[slot];
    matched.entries[0].entry.pos = "unmapped provider class".into();
    matched.entries[0].pos_compatibility =
        pos_compatibility(&matched.lemma, &matched.entries[0].entry);
    assert_eq!(annotation.assess(a).status, Compatibility::Unknown);
    annotation
        .clone()
        .filter(&mut compatible, DictionaryFilter::Compatible);
    // Filtering a previously pruned list does not recreate candidates.
    assert!(!compatible.analyses.contains(a));
    annotation.filter(&mut headwords, DictionaryFilter::Compatible);
    assert!(headwords.analyses.contains(a));
}

#[test]
fn auxiliary_class_cli_library_and_reordered_annotations_agree() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for case in cases() {
        let word = Lemmatizer::new().analyze_word(&case.surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        for (flag, policy) in [
            ("--dict-only", DictionaryFilter::Headword),
            ("--dict-compatible", DictionaryFilter::Compatible),
        ] {
            let mut expected = word.clone();
            let mut annotated = annotation.clone();
            annotated.filter(&mut expected, policy);
            let output = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", &case.surface, "--dictionary"])
                .arg(&fixture.0)
                .arg(flag)
                .output()
                .unwrap();
            assert!(output.status.success());
            let value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                expected
            );
            assert_eq!(
                serde_json::from_value::<Annotation>(value["dictionary"].clone()).unwrap(),
                annotated
            );
            let mut reordered = word.clone();
            reordered.analyses.reverse();
            let mut stale = annotation.clone();
            stale.filter(&mut reordered, policy);
            reordered.analyses.reverse();
            stale.readings.reverse();
            assert_eq!(reordered, expected);
            assert_eq!(stale, annotated);
        }
    }
}
