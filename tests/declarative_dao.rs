use klem::{Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn individual_source_and_boundary_judgments_are_executable() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/declarative-dao-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 33);
    assert_eq!(report.forbidden_total, 3);
}

fn dictionary(name: &str) -> (klem::dictionary::SqliteDictionary, Cleanup) {
    use klem::dictionary::{SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!("klem-dao-{name}-{}.db", std::process::id()));
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/krdict-declarative-dao-english.json",
        )],
        &path,
        "declarative-dao-source",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (db, Cleanup(path))
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn complete_source_proposals_gain_paths_and_preserve_prior_hypotheses() {
    let rows: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/declarative-dao-proposals.json")).unwrap();
    assert_eq!(rows.len(), 26);
    let engine = Lemmatizer::new();
    for row in rows {
        let word = row["surface"].as_str().unwrap();
        let lemma = row["proposed_lemma"].as_str().unwrap();
        let before: WordAnalysis =
            serde_json::from_value(row["baseline_records"]["raw"]["analysis"].clone()).unwrap();
        let now = engine.analyze_word(word).unwrap();
        assert_eq!(
            now,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            now.analyses
                .iter()
                .filter(|a| before.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            before.analyses,
            "{word}"
        );
        assert!(
            now.analyses.iter().any(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.rules.iter().any(|r| r == "ending.declarative_dao")
            }),
            "{word}: {now:?}"
        );
        for added in now.analyses.iter().filter(|a| !before.analyses.contains(a)) {
            assert!(added.rules.iter().any(|r| r == "ending.declarative_dao"));
            assert!(added.breakdown().is_some());
            assert!(
                added
                    .rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
        }
    }
}

#[test]
fn tense_modal_and_retrospective_boundaries_belong_to_the_immediate_owner() {
    let engine = Lemmatizer::new();
    for (word, lemma, allowed) in [
        ("먹는다오", "먹다", true),
        ("먹으신다오", "먹다", true),
        ("먹으시다오", "먹다", true),
        ("먹었다오", "먹다", true),
        ("먹겠다오", "먹다", true),
        ("먹었는다오", "먹다", false),
        ("먹겠는다오", "먹다", false),
        ("먹더다오", "먹다", false),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert_eq!(
            result.analyses.iter().any(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.rules.iter().any(|r| r == "ending.declarative_dao")
            }),
            allowed,
            "{word}: {result:?}"
        );
    }
}

#[test]
fn source_lexical_profiles_survive_actual_dictionary_filtering() {
    use klem::dictionary::{Compatibility, DictionarySession};
    let (db, _cleanup) = dictionary("profiles");
    let mut session = DictionarySession::new(&db, 1048576);
    let engine = Lemmatizer::new();
    for (word, lemma, ending, expected) in [
        ("안다오", "안다", "다오", Compatibility::Incompatible),
        ("안다오", "알다", "는다오", Compatibility::Compatible),
        ("간다오", "가다", "는다오", Compatibility::Compatible),
        ("간다오", "갈다", "는다오", Compatibility::Compatible),
        ("먹는다오", "먹다", "는다오", Compatibility::Compatible),
        ("먹다오", "먹다", "다오", Compatibility::Incompatible),
        ("먹었다오", "먹다", "다오", Compatibility::Compatible),
        ("먹겠다오", "먹다", "다오", Compatibility::Compatible),
        ("먹으시다오", "먹다", "다오", Compatibility::Compatible),
        ("먹으신다오", "먹다", "는다오", Compatibility::Compatible),
        ("예쁘다오", "예쁘다", "다오", Compatibility::Compatible),
        ("예쁜다오", "예쁘다", "는다오", Compatibility::Incompatible),
        ("바쁘시다오", "바쁘다", "다오", Compatibility::Compatible),
        (
            "바쁘신다오",
            "바쁘다",
            "는다오",
            Compatibility::Incompatible,
        ),
        ("많으시다오", "많다", "다오", Compatibility::Compatible),
        ("많으신다오", "많다", "는다오", Compatibility::Incompatible),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let annotated = session.annotate(&result).unwrap();
        let indices: Vec<_> = result
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, a)| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.morphemes.last().is_some_and(|m| m.form == ending)
                    && a.rules.iter().any(|r| r == "ending.declarative_dao")
            })
            .map(|(i, _)| i)
            .collect();
        assert!(!indices.is_empty(), "{word}: {result:?}");
        for index in indices {
            assert_eq!(
                annotated.readings[index].lemmas[0].status, expected,
                "{word}"
            );
        }
    }
}

#[test]
fn every_original_occurrence_survives_both_dictionary_filters_and_cache_sizes() {
    use klem::dictionary::{DictionaryFilter, DictionarySession};
    let rows: Vec<Value> =
        serde_json::from_str(include_str!("fixtures/declarative-dao-proposals.json")).unwrap();
    let (db, _cleanup) = dictionary("occurrences");
    let engine = Lemmatizer::new();
    for cache in [0, 4096] {
        for (mode, policy) in [
            ("headword", DictionaryFilter::Headword),
            ("compatible", DictionaryFilter::Compatible),
        ] {
            let mut session = DictionarySession::new(&db, cache);
            for row in &rows {
                let word = row["surface"].as_str().unwrap();
                let lemma = row["proposed_lemma"].as_str().unwrap();
                let before: WordAnalysis =
                    serde_json::from_value(row["baseline_records"][mode]["analysis"].clone())
                        .unwrap();
                let mut now = engine.analyze_word(word).unwrap();
                let mut annotation = session.annotate(&now).unwrap();
                annotation.filter(&mut now, policy);
                assert_eq!(
                    now.analyses
                        .iter()
                        .filter(|a| before.analyses.contains(a))
                        .cloned()
                        .collect::<Vec<_>>(),
                    before.analyses,
                    "{word}/{mode}/{cache}"
                );
                assert!(
                    now.analyses.iter().any(|a| a.lemmas.len() == 1
                        && a.lemmas[0].text == lemma
                        && a.rules.iter().any(|r| r == "ending.declarative_dao")),
                    "{word}/{mode}/{cache}: {now:?}"
                );
            }
        }
    }
}

#[test]
fn imported_native_entries_preserve_all_source_identities_and_complete_groups() {
    use klem::dictionary::Dictionary;
    let expected: Value =
        serde_json::from_str(include_str!("fixtures/declarative-dao-native.json")).unwrap();
    let (db, _cleanup) = dictionary("native");
    for (id, original) in expected.as_object().unwrap() {
        let mut english = original.clone();
        for sense in english["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            english
        );
    }
    for (id, pos) in [
        ("krdict:77931", "어미"),
        ("krdict:79421", "어미"),
        ("krdict:79419", "어미"),
        ("krdict:88935", "품사 없음"),
        ("krdict:88936", "품사 없음"),
        ("krdict:88937", "품사 없음"),
    ] {
        assert_eq!(db.entry(id).unwrap().unwrap().summary.pos, pos);
    }
}

#[test]
fn shared_ledger_retains_every_source_and_boundary_judgment() {
    let batch: Value =
        serde_json::from_str(include_str!("fixtures/declarative-dao-validity.json")).unwrap();
    let ledger: Value = serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    for (key, source) in batch["sources"].as_object().unwrap() {
        assert_eq!(&ledger["sources"][key], source, "source {key}");
    }
    for case in batch["cases"].as_array().unwrap() {
        let matches: Vec<_> = ledger["cases"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|stored| stored["id"] == case["id"])
            .collect();
        assert_eq!(matches, vec![case], "case {}", case["id"]);
    }
}
