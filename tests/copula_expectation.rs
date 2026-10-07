//! Authored structural probes: primary omission rule plus source ending notes.
//! These are not directly attested sentence judgments or corpus gold.
use klem::breakdown::Component;
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

fn path(a: &Analysis, noun: &str, ending: &str) -> bool {
    a.lemmas.len() == 2
        && a.lemmas[0].text == noun
        && a.lemmas[0].kind == LemmaKind::Nominal
        && a.lemmas[1].text == "이다"
        && a.lemmas[1].kind == LemmaKind::Copula
        && a.morphemes.len() == 1
        && a.morphemes[0].form == ending
        && a.morphemes[0].kind == MorphemeKind::Ending
}

#[test]
fn frozen_old_candidates_and_explicit_parents_are_preserved() {
    let source: Value =
        serde_json::from_str(include_str!("copula-expectation-before.json")).unwrap();
    let engine = Lemmatizer::new();
    for r in source["records"].as_array().unwrap() {
        let word = r["surface"].as_str().unwrap();
        let old: WordAnalysis = serde_json::from_value(r["before"].clone()).unwrap();
        let new = engine.analyze_word(word).unwrap();
        assert_eq!(
            new,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            new.analyses
                .iter()
                .filter(|a| old.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            old.analyses,
            "{word}"
        );
        let parent: WordAnalysis = serde_json::from_value(
            source["explicit_parents"][r["explicit_parent"].as_str().unwrap()].clone(),
        )
        .unwrap();
        for a in new.analyses.iter().filter(|a| !old.analyses.contains(a)) {
            let mut inverse = a.clone();
            inverse.rules.retain(|r| r != "copula.omitted_ending");
            inverse.rules.push("boundary.eu".into());
            inverse.rules.sort();
            inverse.rules.dedup();
            assert!(parent.analyses.contains(&inverse), "{word}: {a:?}");
            assert_eq!(
                a.breakdown().unwrap(),
                vec![
                    Component::Lemma(0),
                    Component::Lemma(1),
                    Component::Morpheme(0)
                ]
            );
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            assert!(!a.rules.iter().any(|r| r.starts_with("irregular.")
                || r == "deletion.rieul"
                || r == "deletion.eu"));
        }
    }
}

#[test]
fn omission_respects_nominal_coda_and_preserves_explicit_copulas() {
    let engine = Lemmatizer::new();
    for (suffix, canonical) in [
        ("리만큼", "으리만큼"),
        ("련만", "으련만"),
        ("련마는", "으련마는"),
    ] {
        for noun in ["친구", "학교", "의사", "어디"] {
            let word = format!("{noun}{suffix}");
            assert!(
                engine
                    .analyze_word(&word)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| path(a, noun, canonical)),
                "{word}"
            );
        }
        for noun in ["학생", "서울", "먹음", "책"] {
            let word = format!("{noun}{suffix}");
            assert!(
                !engine
                    .analyze_word(&word)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| path(a, noun, canonical)),
                "{word}"
            );
            let full = format!("{noun}이{suffix}");
            assert!(
                engine
                    .analyze_word(&full)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| path(a, noun, canonical)),
                "{full}"
            );
        }
    }
}

#[test]
fn past_contractions_do_not_become_omission_of_a_nominal_ending() {
    let engine = Lemmatizer::new();
    for (suffix, canonical) in [
        ("으리만큼", "으리만큼"),
        ("으련만", "으련만"),
        ("으련마는", "으련마는"),
    ] {
        let valid = engine.analyze_word(&format!("학교였{suffix}")).unwrap();
        assert!(valid.analyses.iter().any(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["학교", "이다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["었", canonical])
        }));
        let invalid = engine.analyze_word(&format!("학교었{suffix}")).unwrap();
        assert!(!invalid.analyses.iter().any(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["학교", "이다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["었", canonical])
        }));
    }
}

#[test]
fn source_spans_remain_original_utf8_with_normalized_analysis() {
    let engine = Lemmatizer::new();
    for text in [
        "친구련만, 학교리만큼!".to_owned(),
        "친구련만, 학교리만큼!".nfd().collect(),
    ] {
        let tokens: Vec<_> = engine.analyze_text(&text).collect();
        assert_eq!(
            tokens
                .iter()
                .map(|t| t.surface.as_str())
                .collect::<String>(),
            text
        );
        let mut end = 0;
        for token in tokens {
            assert_eq!(token.span.start, end);
            assert_eq!(&text[token.span.clone()], token.surface);
            end = token.span.end;
            if let Some(result) = token.analysis {
                assert_eq!(*result, engine.analyze_word(&token.surface).unwrap());
            }
        }
        assert_eq!(end, text.len());
    }
}

#[test]
fn complete_original_source_words_preserve_order_and_attribute_each_addition() {
    let source: Value =
        serde_json::from_str(include_str!("copula-expectation-full-source.json")).unwrap();
    assert_eq!(source["before_analyses"].as_object().unwrap().len(), 7071);
    assert_eq!(source["individual_additions"].as_array().unwrap().len(), 28);
    let engine = Lemmatizer::new();
    let mut additions = 0;
    for (word, old) in source["before_analyses"].as_object().unwrap() {
        let old: WordAnalysis = serde_json::from_value(old.clone()).unwrap();
        let new = engine.analyze_word(word).unwrap();
        assert_eq!(
            new.analyses
                .iter()
                .filter(|a| old.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            old.analyses,
            "{word}"
        );
        for a in new.analyses.iter().filter(|a| !old.analyses.contains(a)) {
            additions += 1;
            assert!(a.rules.iter().any(|r| r == "copula.omitted_ending"));
            assert!(a.breakdown().is_some());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            let row = source["individual_additions"]
                .as_array()
                .unwrap()
                .iter()
                .find(|r| {
                    r["surface"] == word.as_str()
                        && serde_json::from_value::<Analysis>(r["after"].clone()).unwrap() == *a
                })
                .expect("missing individual attribution");
            let mut inverse = a.clone();
            inverse.rules.retain(|r| r != "copula.omitted_ending");
            inverse.rules.push("boundary.eu".into());
            inverse.rules.sort();
            inverse.rules.dedup();
            assert!(
                row["explicit_parents"].as_array().unwrap().iter().any(|p| {
                    let parent: WordAnalysis = serde_json::from_value(
                        source["explicit_parents"][p.as_str().unwrap()].clone(),
                    )
                    .unwrap();
                    parent.analyses.contains(&inverse)
                }),
                "missing exact explicit parent {word}: {a:?}"
            );
        }
    }
    assert_eq!(additions, 28);
}

#[test]
fn imported_native_copula_entries_preserve_source_uncertainty_and_known_conflicts() {
    use klem::dictionary::{Compatibility, DictionarySession, SqliteDictionary, import_krdict};
    use std::path::PathBuf;
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let engine = Lemmatizer::new();
    for (family, suffix, form, expected) in [
        (
            "counterfactual-ryeon",
            "련만",
            "으련만",
            Compatibility::Compatible,
        ),
        (
            "counterfactual-ryeon",
            "련마는",
            "으련마는",
            Compatibility::Compatible,
        ),
        (
            "degree-rimankeum",
            "리만큼",
            "으리만큼",
            Compatibility::Unknown,
        ),
    ] {
        let db_path = std::env::temp_dir().join(format!(
            "klem-copula-expectation-{}-{suffix}.db",
            std::process::id()
        ));
        let _cleanup = Cleanup(db_path.clone());
        import_krdict(
            &[PathBuf::from(format!(
                "tests/fixtures/krdict-{family}-english.json"
            ))],
            &db_path,
            "copula-expectation-source",
        )
        .unwrap();
        let dictionary = SqliteDictionary::open(db_path).unwrap();
        let mut session = DictionarySession::new(&dictionary, 1048576);
        let result = engine.analyze_word(&format!("친구{suffix}")).unwrap();
        let i = result
            .analyses
            .iter()
            .position(|a| path(a, "친구", form))
            .unwrap();
        let annotated = session.annotate(&result).unwrap();
        let owner = annotated.readings[i]
            .lemmas
            .iter()
            .find(|l| l.lemma_index == 1)
            .unwrap();
        assert_eq!(owner.status, expected, "{suffix}");
        for id in ["krdict:86118", "krdict:86232"] {
            assert_eq!(
                owner.entries.iter().find(|e| e.id == id).unwrap().status,
                expected,
                "{suffix}: {id}"
            );
        }
        let conflict = owner
            .entries
            .iter()
            .find(|e| e.id == "krdict:92457")
            .unwrap();
        assert_eq!(conflict.status, Compatibility::Incompatible);
        assert!(!conflict.conflicts.is_empty());
    }
}

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn individually_identified_source_rule_boundary_judgments_pass() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("copula-expectation-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 21);
    assert_eq!(report.forbidden_total, 9);
}
