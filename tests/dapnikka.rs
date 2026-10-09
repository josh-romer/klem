use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "ending.question_dapnikka";

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn stable_individual_source_and_boundary_judgments_pass() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/dapnikka-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 55);
    assert_eq!(report.forbidden_total, 7);
}

fn proposals() -> Vec<Value> {
    serde_json::from_str(include_str!("fixtures/dapnikka-proposals.json")).unwrap()
}

fn source_path(a: &klem::Analysis, expected: &[String]) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(expected)
        && a.rules.iter().any(|r| r == RULE)
        && a.breakdown().is_some()
}

#[test]
fn every_complete_source_target_recovers_and_keeps_all_original_paths() {
    let engine = Lemmatizer::new();
    let cases = proposals();
    assert_eq!(cases.len(), 46);
    for case in cases {
        let surface = case["surface"].as_str().unwrap();
        let expected: Vec<String> =
            serde_json::from_value(case["proposed_lemmas"].clone()).unwrap();
        let previous: WordAnalysis =
            serde_json::from_value(case["baseline_records"]["raw"]["analysis"].clone()).unwrap();
        let now = engine.analyze_word(surface).unwrap();
        assert_eq!(
            now,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(
            now.analyses.iter().any(|a| source_path(a, &expected)),
            "{} {surface}: {now:?}",
            case["id"]
        );
        assert_eq!(
            now.analyses
                .iter()
                .filter(|a| previous.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            previous.analyses
        );
        for added in now
            .analyses
            .iter()
            .filter(|a| !previous.analyses.contains(a))
        {
            assert!(added.rules.iter().any(|r| r == RULE));
            assert!(
                added
                    .rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
        }
    }
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(name: &str) -> (klem::dictionary::SqliteDictionary, Cleanup) {
    use klem::dictionary::{SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!("klem-dapnikka-{name}-{}.db", std::process::id()));
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/dapnikka-native.json",
        )],
        &path,
        "complete-original-native",
    )
    .unwrap();
    (SqliteDictionary::open(&path).unwrap(), Cleanup(path))
}

#[test]
fn every_native_owner_identity_and_complete_original_entry_survives_import() {
    use klem::dictionary::Dictionary;
    let (dictionary, _cleanup) = dictionary("native");
    let entries: std::collections::BTreeMap<String, Value> =
        serde_json::from_str(include_str!("fixtures/dapnikka-native-entries.json")).unwrap();
    assert_eq!(entries.len(), 90);
    for (id, expected) in entries {
        let actual = dictionary.entry(&id).unwrap().unwrap();
        assert_eq!(serde_json::to_value(actual).unwrap(), expected, "{id}");
    }
}

#[test]
fn each_original_source_lemma_survives_dictionary_filters_and_owned_assessment() {
    use klem::dictionary::{Compatibility, DictionarySession};
    let (db, _cleanup) = dictionary("sources");
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for case in proposals() {
        let surface = case["surface"].as_str().unwrap();
        let expected: Vec<String> =
            serde_json::from_value(case["proposed_lemmas"].clone()).unwrap();
        let word = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        assert!(
            word.analyses.iter().any(|a| {
                source_path(a, &expected)
                    && annotation.assess(a).status != Compatibility::Incompatible
                    && annotation
                        .assess(a)
                        .lemmas
                        .iter()
                        .all(|l| !l.entries.is_empty())
            }),
            "{} {surface}: {annotation:?}",
            case["id"]
        );
    }
}

#[test]
fn present_plain_command_and_factual_questions_keep_their_own_boundaries() {
    let engine = Lemmatizer::new();
    for (surface, lemma, allowed) in [
        ("읽는답니까", "읽다", true),
        ("읽으신답니까", "읽다", true),
        ("읽었답니까", "읽다", true),
        ("읽겠답니까", "읽다", true),
        ("읽었는답니까", "읽다", false),
        ("읽겠는답니까", "읽다", false),
        ("읽더답니까", "읽다", false),
        ("읽으랍니까", "읽다", true),
        ("읽랍니까", "읽다", false),
        ("읽었으랍니까", "읽다", false),
        ("읽으시랍니까", "읽다", true),
        ("아니랍니까", "아니다", true),
        ("아니으랍니까", "아니다", false),
        ("읽으리랍니까", "읽다", true),
        ("가리랍니까", "가다", true),
        ("읽더으리랍니까", "읽다", false),
    ] {
        let now = engine.analyze_word(surface).unwrap();
        assert_eq!(
            now.analyses
                .iter()
                .any(|a| source_path(a, &[lemma.to_owned()])),
            allowed,
            "{surface}: {now:?}"
        );
    }
}

#[test]
fn dictionary_homonyms_keep_their_own_present_and_plain_classes() {
    use klem::dictionary::{Compatibility, DictionarySession};
    let (db, _cleanup) = dictionary("classes");
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (surface, lemma, form, pos, expected) in [
        (
            "늦는답니까",
            "늦다",
            "는답니까",
            "동사",
            Compatibility::Compatible,
        ),
        (
            "늦는답니까",
            "늦다",
            "는답니까",
            "형용사",
            Compatibility::Incompatible,
        ),
        (
            "먹답니까",
            "먹다",
            "답니까",
            "동사",
            Compatibility::Incompatible,
        ),
        (
            "많답니까",
            "많다",
            "답니까",
            "형용사",
            Compatibility::Compatible,
        ),
        (
            "아니랍니까",
            "아니다",
            "랍니까",
            "형용사",
            Compatibility::Compatible,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let analysis = word
            .analyses
            .iter()
            .find(|a| {
                source_path(a, &[lemma.to_owned()])
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == form
            })
            .unwrap();
        let entry = annotation
            .lemmas
            .iter()
            .find(|l| l.lemma.text == lemma)
            .unwrap()
            .entries
            .iter()
            .find(|e| e.entry.pos == pos)
            .unwrap();
        let assessment = annotation.assess(analysis);
        let owned = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == entry.entry.id)
            .unwrap();
        assert_eq!(owned.status, expected, "{surface}/{pos}: {assessment:?}");
    }
}
