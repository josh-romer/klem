//! Original ri-prefinal groups, common followers and exact spelling boundaries; contextual senses stay open.
use klem::Lemmatizer;
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn original_literary_ri_prefinal_structures_and_named_spelling_boundaries() {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/literary-ri-prefinal-validity.json")).unwrap();
    for encoding in ["NFC", "NFD"] {
        if encoding == "NFD" {
            for case in &mut suite.cases {
                case.surface = case.surface.nfd().collect();
            }
        }
        let report = validity::evaluate(&suite).unwrap();
        assert!(report.passed(), "{encoding}: {:?}", report.violations);
        assert_eq!((report.required_total, report.forbidden_total), (30, 6));
    }
}

struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn source_owned_irregular_profiles_reject_regular_hypotheses_only_in_compatible_mode() {
    use klem::dictionary::{AttachmentRule, Compatibility, DictionaryFilter, DictionarySession};
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("spelling");
    let mut session = DictionarySession::new(&db, 64);
    for (base, lemma) in [("듣으리", "듣다"), ("짓으리", "짓다"), ("돕으리", "돕다")]
    {
        for (suffix, ending) in [("니", "니"), ("니라", "으니라")] {
            for surface in [
                format!("{base}{suffix}"),
                format!("{base}{suffix}").nfd().collect(),
            ] {
                let raw = engine.analyze_word(&surface).unwrap();
                let index = raw
                    .analyses
                    .iter()
                    .position(|a| {
                        a.lemmas.iter().map(|l| l.text.as_str()).eq([lemma])
                            && a.morphemes
                                .iter()
                                .map(|m| m.form.as_str())
                                .eq(["으리", ending])
                    })
                    .unwrap();
                let selected = raw.analyses[index].clone();
                let annotation = session.annotate(&raw).unwrap();
                let reading = &annotation.readings[index];
                assert_eq!(reading.status, Compatibility::Incompatible, "{surface}");
                assert!(!reading.lemmas[0].entries.is_empty());
                for entry in &reading.lemmas[0].entries {
                    assert_eq!(entry.status, Compatibility::Incompatible);
                    assert!(
                        entry
                            .conflicts
                            .iter()
                            .any(|c| c.rule == AttachmentRule::LexicalSpelling
                                && c.morpheme_index == Some(0)),
                        "{surface}: {} retains its own spelling evidence",
                        entry.id
                    );
                }
                for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                    let mut filtered = raw.clone();
                    let mut assessment = annotation.clone();
                    assessment.filter(&mut filtered, mode);
                    assert_eq!(
                        filtered.analyses.contains(&selected),
                        mode == DictionaryFilter::Headword,
                        "{surface}: {mode:?}"
                    );
                }
            }
        }
    }
}

fn dictionary(name: &str) -> (klem::dictionary::SqliteDictionary, Cleanup) {
    use klem::dictionary::{SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!(
        "klem-literary-ri-prefinal-{name}-{}.db",
        std::process::id()
    ));
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/krdict-literary-ri-prefinal-english.json",
        )],
        &path,
        "literary-ri-prefinal-source",
    )
    .unwrap();
    (SqliteDictionary::open(path).unwrap(), cleanup)
}

#[test]
fn all_primary_ending_and_lexical_sources_survive_import() {
    use klem::dictionary::Dictionary;
    let expected: Value =
        serde_json::from_str(include_str!("fixtures/literary-ri-prefinal-native.json")).unwrap();
    assert_eq!(expected.as_object().unwrap().len(), 56);
    let (db, _cleanup) = dictionary("native");
    for (id, original) in expected.as_object().unwrap() {
        let mut english = original.clone();
        for sense in english["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|translation| translation["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            english,
            "{id}"
        );
    }
}

#[test]
fn dictionary_filter_retains_all_original_literary_ri_prefinal_structure_proposals() {
    use klem::dictionary::{DictionaryFilter, DictionarySession};
    let (db, _cleanup) = dictionary("policy");
    let mut session = DictionarySession::new(&db, 1048576);
    let engine = Lemmatizer::new();
    let mut suite: validity::Suite = serde_json::from_str(include_str!(
        "fixtures/literary-ri-prefinal-policy-validity.json"
    ))
    .unwrap();
    for encoding in ["NFC", "NFD"] {
        if encoding == "NFD" {
            for case in &mut suite.cases {
                case.surface = case.surface.nfd().collect();
            }
        }
        let report = validity::evaluate_with(&suite, |word| {
            let mut analysis = engine
                .analyze_word(word)
                .map_err(|error| error.to_string())?;
            let mut annotation = session
                .annotate(&analysis)
                .map_err(|error| error.to_string())?;
            annotation.filter(&mut analysis, DictionaryFilter::Compatible);
            Ok(analysis)
        })
        .unwrap();
        assert!(report.passed(), "{encoding}: {:?}", report.violations);
        assert_eq!((report.required_total, report.forbidden_total), (30, 12));
    }
}
