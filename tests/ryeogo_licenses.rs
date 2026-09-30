//! COV-017aw: connective class uncertainty versus supported final homonyms.
use klem::dictionary::{
    AttachmentConflict, Compatibility, DictionaryFilter, DictionarySession, SqliteDictionary,
    import_krdict,
};
use klem::{Analysis, Lemma, Lemmatizer, Morpheme, WordAnalysis};
use serde::Deserialize;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

#[derive(Deserialize)]
struct Judgment {
    id: String,
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
    serde_json::from_str::<Ledger>(include_str!("fixtures/ryeogo-license-assessments.json"))
        .unwrap()
        .cases
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-ryeogo-licenses-{}-{name}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-ryeogo-licenses.json")],
            &path,
            "ryeogo-licenses",
        )
        .unwrap();
        Self(path)
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
fn primary_source_tokens_preserve_structural_paths_without_selecting_a_sense() {
    #[derive(Deserialize)]
    struct Token {
        surface: String,
        lemmas: Vec<Lemma>,
        morphemes: Vec<Morpheme>,
    }
    #[derive(Deserialize)]
    struct Sources {
        direct_token_paths: Vec<Token>,
    }
    let sources: Sources =
        serde_json::from_str(include_str!("fixtures/ryeogo-license-sources.json")).unwrap();
    assert_eq!(sources.direct_token_paths.len(), 15);
    let engine = Lemmatizer::new();
    for token in sources.direct_token_paths {
        let word = engine.analyze_word(&token.surface).unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas == token.lemmas && a.morphemes == token.morphemes),
            "{}",
            token.surface
        );
    }
}

#[test]
fn intention_class_assessments_preserve_homonyms_and_component_ownership() {
    let fixture = Fixture::new("judgments");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let cases = cases();
    assert_eq!(cases.len(), 45);
    let mut ids = std::collections::BTreeSet::new();
    for case in cases {
        assert!(ids.insert(case.id.clone()));
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
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for path in &word.analyses {
            assert!(path.breakdown().is_some());
            assert!(
                path.rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
        }
        let annotation = dictionary.annotate(&word).unwrap();
        let assessed = annotation.assess(a);
        let mut judgment_ids = std::collections::BTreeSet::new();
        for j in &case.judgments {
            assert!(judgment_ids.insert(&j.id));
            let entry = assessed.lemmas[j.lemma_index]
                .entries
                .iter()
                .find(|e| e.id == j.entry_id)
                .unwrap();
            assert_eq!(entry.status, j.status, "{}: {}", case.id, j.entry_id);
            assert_eq!(entry.conflicts, j.conflicts, "{}: {}", case.id, j.entry_id);
        }
        // Unknown is preserved by both filters; annotations still align with
        // complete paths after filtering and across small-cache eviction.
        for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut filtered = word.clone();
            let mut annotated = annotation.clone();
            annotated.filter(&mut filtered, policy);
            assert!(filtered.analyses.contains(a), "{}", case.id);
            for (a, r) in filtered.analyses.iter().zip(&annotated.readings) {
                assert_eq!(*r, annotated.assess(a));
            }
            assert_eq!(filtered.analyses.len(), annotated.readings.len());
        }
        assert!(dictionary.cache_bytes() <= 4096);
    }
}

#[test]
fn intention_unknowns_are_retained_with_exact_cli_annotation_parity() {
    let fixture = Fixture::new("cli");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    for case in cases() {
        for (flag, policy) in [
            ("--dict-only", DictionaryFilter::Headword),
            ("--dict-compatible", DictionaryFilter::Compatible),
        ] {
            let mut word = engine.analyze_word(&case.surface).unwrap();
            let mut annotation = dictionary.annotate(&word).unwrap();
            annotation.filter(&mut word, policy);
            reading(&word, &case);
            let cli = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", &case.surface, "--dictionary"])
                .arg(&fixture.0)
                .arg(flag)
                .output()
                .unwrap();
            assert!(
                cli.status.success(),
                "{}",
                String::from_utf8_lossy(&cli.stderr)
            );
            let json: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(json.clone()).unwrap(),
                word
            );
            assert_eq!(
                json["dictionary"],
                serde_json::to_value(annotation).unwrap()
            );
        }
    }
}

#[test]
fn intention_uncertainty_does_not_replace_known_role_conflicts_or_unknown_provider_pos() {
    let fixture = Fixture::new("provider");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 0);
    let word = Lemmatizer::new().analyze_word("크려고한다").unwrap();
    let case = cases()
        .into_iter()
        .find(|c| c.surface == "크려고한다")
        .unwrap();
    let a = reading(&word, &case);
    let annotation = dictionary.annotate(&word).unwrap();
    assert_eq!(
        annotation.assess(a).lemmas[0].status,
        Compatibility::Compatible
    );
    let mut adjective_only = annotation.clone();
    let head = adjective_only
        .lemmas
        .iter_mut()
        .find(|l| l.lemma == a.lemmas[0])
        .unwrap();
    head.entries.retain(|e| e.entry.id == "krdict:66586");
    assert_eq!(
        adjective_only.assess(a).lemmas[0].status,
        Compatibility::Unknown
    );
    let head = adjective_only
        .lemmas
        .iter_mut()
        .find(|l| l.lemma == a.lemmas[0])
        .unwrap();
    head.entries[0].entry.pos = "unclassified-provider-pos".into();
    head.entries[0].pos_compatibility = Compatibility::Unknown;
    assert_eq!(
        adjective_only.assess(a).lemmas[0].status,
        Compatibility::Unknown
    );
    let head = adjective_only
        .lemmas
        .iter_mut()
        .find(|l| l.lemma == a.lemmas[0])
        .unwrap();
    head.entries[0].entry.pos = "명사".into();
    head.entries[0].pos_compatibility = Compatibility::Incompatible;
    assert_eq!(
        adjective_only.assess(a).lemmas[0].status,
        Compatibility::Incompatible
    );
}
