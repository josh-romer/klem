//! COV-017aw: relational copulas, full-expression uncertainty and polite path parity.
#[path = "../tools/validity.rs"]
mod validity;
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
    let mut cases =
        serde_json::from_str::<Ledger>(include_str!("fixtures/ryeogo-expansion-assessments.json"))
            .unwrap()
            .cases;
    // COV-019u supplies a known negative POS conflict independently of the
    // still-unknown intention tense license. Retain the historical fixture.
    let reviews: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/negative-class-entry-judgments.json")).unwrap();
    let revisions = reviews["expanded_intention_revisions"].as_array().unwrap();
    assert_eq!(revisions.len(), 2);
    for revision in revisions {
        let case = cases
            .iter_mut()
            .find(|c| c.id == revision["case_id"])
            .unwrap();
        let judgment = case
            .judgments
            .iter_mut()
            .find(|j| j.id == revision["judgment_id"])
            .unwrap();
        assert_eq!(judgment.entry_id, revision["entry_id"]);
        assert_eq!(judgment.lemma_index, revision["lemma_index"]);
        assert_eq!(
            serde_json::to_value(judgment.status).unwrap(),
            revision["before"]["status"]
        );
        assert_eq!(
            serde_json::to_value(&judgment.conflicts).unwrap(),
            revision["before"]["conflicts"]
        );
        judgment.status = serde_json::from_value(revision["after"]["status"].clone()).unwrap();
        judgment.conflicts =
            serde_json::from_value(revision["after"]["conflicts"].clone()).unwrap();
    }
    cases
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-ryeogo-expansions-{}-{name}.db",
            std::process::id()
        ));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-ryeogo-expansions.json"),
                PathBuf::from("tests/fixtures/krdict-ryeogo-licenses.json"),
            ],
            &path,
            "ryeogo-expansions",
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
fn expanded_intention_assessments_keep_tense_with_its_owner() {
    let fixture = Fixture::new("judgments");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let cases = cases();
    assert_eq!(cases.len(), 57);
    assert_eq!(cases.iter().map(|c| c.judgments.len()).sum::<usize>(), 119);
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
fn expanded_intention_unknowns_are_retained_with_exact_cli_annotation_parity() {
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
fn relational_intention_and_polite_alternatives_obey_the_reviewed_boundaries() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("intention-expanded-raw-"));
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (21, 9));
    let engine = Lemmatizer::new();
    for case in &suite.cases {
        let word = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        for a in &word.analyses {
            assert!(a.breakdown().is_some());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    for word in [
        "인간적이려고한다",
        "인간적이려고해요",
        "인간적이지않으려고한다",
    ] {
        let word = engine.analyze_word(word).unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "copula.intention_relational"))
        );
    }
}

#[test]
fn unknown_expansion_evidence_does_not_override_conflicting_provider_roles() {
    let fixture = Fixture::new("provider");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 0);
    let case = cases()
        .into_iter()
        .find(|c| c.surface == "학생이려고하니까")
        .unwrap();
    let word = Lemmatizer::new().analyze_word(&case.surface).unwrap();
    let a = reading(&word, &case);
    let mut annotation = dictionary.annotate(&word).unwrap();
    assert_eq!(
        annotation.assess(a).lemmas[1].status,
        Compatibility::Unknown
    );
    let slot = annotation
        .lemmas
        .iter_mut()
        .find(|l| l.lemma == a.lemmas[1])
        .unwrap();
    for e in &mut slot.entries {
        e.entry.pos = "unclassified-provider-pos".into();
        e.pos_compatibility = Compatibility::Unknown;
    }
    assert_eq!(
        annotation.assess(a).lemmas[1].status,
        Compatibility::Unknown
    );
    let slot = annotation
        .lemmas
        .iter_mut()
        .find(|l| l.lemma == a.lemmas[1])
        .unwrap();
    for e in &mut slot.entries {
        e.entry.pos = "명사".into();
        e.pos_compatibility = Compatibility::Incompatible;
    }
    assert_eq!(
        annotation.assess(a).lemmas[1].status,
        Compatibility::Incompatible
    );
}

#[test]
fn relational_raw_judgments_have_both_dictionary_filters_and_cli_parity() {
    let fixture = Fixture::new("raw-filters");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("intention-expanded-raw-"));
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let report = validity::evaluate_with(&suite, |surface| {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = dictionary.annotate(&word).unwrap();
            annotation.filter(&mut word, policy);
            let cli = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0)
                .arg(flag)
                .output()
                .unwrap();
            assert!(cli.status.success());
            let json: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(json.clone()).unwrap(),
                word
            );
            assert_eq!(
                json["dictionary"],
                serde_json::to_value(annotation).unwrap()
            );
            Ok(word)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
    }
}
