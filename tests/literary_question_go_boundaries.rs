//! Finite source-note derivations and unjudged spacing composition regressions.
use klem::dictionary::{Dictionary, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Analysis, Lemmatizer, Session, WordAnalysis};
use serde_json::Value;
use std::{path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;
#[path = "../tools/validity.rs"]
mod validity;

fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
        && a.lemmas
            .iter()
            .map(|l| l.kind)
            .eq(j.lemma_kinds.as_ref().unwrap().iter().copied())
        && a.morphemes
            .iter()
            .map(|m| &m.form)
            .eq(j.morphemes.as_ref().unwrap().iter())
        && a.morphemes
            .iter()
            .map(|m| m.kind)
            .eq(j.morpheme_kinds.as_ref().unwrap().iter().copied())
        && j.required_rules
            .as_ref()
            .unwrap()
            .iter()
            .all(|r| a.rules.contains(r))
}
fn suite() -> validity::Suite {
    serde_json::from_str(include_str!(
        "fixtures/literary-question-go-boundaries.json"
    ))
    .unwrap()
}
#[test]
fn individual_boundary_ids_check_19_required_and_four_path_specific_exclusions() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.cases, 23);
    assert_eq!(report.required_total, 19);
    assert_eq!(report.forbidden_total, 4);
}
#[test]
fn boundary_paths_keep_unicode_earlier_order_spelling_recovery_and_explanations() {
    let before: Value = serde_json::from_str(include_str!(
        "fixtures/literary-question-go-boundary-before.json"
    ))
    .unwrap();
    let engine = Lemmatizer::new();
    for case in suite().cases {
        let old: WordAnalysis = serde_json::from_value(before[&case.surface].clone()).unwrap();
        let raw = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            raw,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            raw.analyses
                .iter()
                .filter(|a| old.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            old.analyses
        );
        for j in case.judgments {
            for a in raw.analyses.iter().filter(|a| matches(a, &j)) {
                assert!(a.breakdown().is_some(), "{}: {a:?}", case.id);
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
                if case.id.ends_with("bieup-descriptive") || case.id.ends_with("bieup-cold") {
                    assert!(a.rules.iter().any(|r| r == "irregular.bieup"));
                    assert!(!a.spelling_paths.is_empty());
                }
                if case.id.ends_with("hieut-demonstrative") || case.id.ends_with("hieut-color") {
                    assert!(a.rules.iter().any(|r| r == "irregular.hieut"));
                    assert!(!a.spelling_paths.is_empty());
                }
            }
        }
    }
}
struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
fn dictionary(name: &str) -> (SqliteDictionary, Cleanup) {
    let p = std::env::temp_dir().join(format!(
        "klem-question-go-boundaries-{name}-{}.db",
        std::process::id()
    ));
    assert!(!p.exists());
    let cleanup = Cleanup(p.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/literary-question-go-spelling-spacing-english.json",
        )],
        &p,
        "literary-question-go-boundaries",
    )
    .unwrap();
    (SqliteDictionary::open(p).unwrap(), cleanup)
}
#[test]
fn all_128_original_entries_and_same_head_homonyms_survive_the_real_importer() {
    let (db, _cleanup) = dictionary("native");
    let native: Value = serde_json::from_str(include_str!(
        "fixtures/literary-question-go-spelling-spacing-native.json"
    ))
    .unwrap();
    assert_eq!(native.as_object().unwrap().len(), 128);
    for (id, expected) in native.as_object().unwrap() {
        let mut english = expected.clone();
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
        let e = db.entry(id).unwrap().unwrap();
        assert!(
            db.lookup(&e.summary.headword)
                .unwrap()
                .iter()
                .any(|s| s.id == *id)
        );
    }
}
#[test]
fn new_spacing_hypotheses_keep_native_owners_unicode_and_original_boundaries() {
    // These are conditional raw hypotheses, not judgments about the novel's
    // intended reading. Original complete-line captures remain unjudged.
    let (db, _cleanup) = dictionary("spacing");
    let mut dict = DictionarySession::new(&db, 1024);
    let engine = Arc::new(Lemmatizer::new());
    let mut words = Session::new(engine, 1024);
    for (whole, left, right, head) in [
        ("돌아갔는고", "돌아", "갔는고", "가다"),
        ("살아왔는고", "살아", "왔는고", "오다"),
    ] {
        for encoding in [false, true] {
            let original = if encoding {
                whole.nfd().collect::<String>()
            } else {
                whole.to_owned()
            };
            let lhs = if encoding {
                left.nfd().collect::<String>()
            } else {
                left.to_owned()
            };
            let rhs = if encoding {
                right.nfd().collect::<String>()
            } else {
                right.to_owned()
            };
            let value = serde_json::to_value(
                klem::spacing::suggest(
                    &mut words,
                    &mut dict,
                    &original,
                    37,
                    klem::spacing::SpacingLimits::default(),
                )
                .unwrap(),
            )
            .unwrap();
            assert_eq!(value["complete"], true);
            let alternative = value["alternatives"]
                .as_array()
                .unwrap()
                .iter()
                .find(|h| h["spaced"] == format!("{lhs} {rhs}"))
                .unwrap();
            assert_eq!(
                alternative["inserted_at"],
                serde_json::json!([37 + lhs.len()])
            );
            assert_eq!(alternative["records"][0]["surface"], lhs);
            assert_eq!(alternative["records"][1]["surface"], rhs);
            assert_eq!(
                alternative["records"][0]["span"],
                serde_json::json!({"start":37,"end":37+lhs.len()})
            );
            assert_eq!(
                alternative["records"][1]["span"],
                serde_json::json!({"start":37+lhs.len(),"end":37+original.len()})
            );
            let segment = &alternative["records"][1];
            assert!(
                segment["analysis"]["analyses"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|a| a["lemmas"][0]["text"] == head
                        && a["rules"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .any(|r| r == "ending.literary_question_go"))
            );
        }
    }
}
