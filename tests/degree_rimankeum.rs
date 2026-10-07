#[path = "copula_expectation_support/parent.rs"]
mod copula_expectation_parent;
#[path = "deoniman_support/parent.rs"]
mod deoniman_parent;
use klem::{Analysis, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

fn degree(a: &Analysis) -> bool {
    a.rules.iter().any(|r| r == "ending.degree_rimankeum")
}

#[test]
fn original_examples_recover_heads_and_preserve_every_old_candidate() {
    let source: Value =
        serde_json::from_str(include_str!("fixtures/degree-rimankeum-sources.json")).unwrap();
    assert_eq!(source["original_groups"].as_array().unwrap().len(), 9);
    let engine = Lemmatizer::new();
    for (word, head) in source["expected_heads"].as_object().unwrap() {
        let old: WordAnalysis =
            serde_json::from_value(source["before_analyses"][word].clone()).unwrap();
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
            old.analyses
        );
        assert!(new.analyses.iter().any(|a| degree(a)
            && a.lemmas.len() == 1
            && a.lemmas[0].text == head.as_str().unwrap()
            && a.morphemes.len() == 1
            && a.morphemes[0].form == "으리만큼"));
        let companion = format!("{}라", word.strip_suffix("만큼").unwrap());
        let parent: WordAnalysis =
            serde_json::from_value(source["companion_analyses"][&companion].clone()).unwrap();
        for a in new.analyses.iter().filter(|a| !old.analyses.contains(a)) {
            if a.rules
                .iter()
                .any(|r| matches!(r.as_str(), "ending.deoniman" | "ending.reported_deoni"))
            {
                deoniman_parent::assert_report_parent(word, a);
                continue;
            }
            if a.rules.iter().any(|r| r == "copula.omitted_ending") {
                copula_expectation_parent::assert_omission_parent(word, a);
                continue;
            }
            assert!(degree(a), "unattributed {word}: {a:?}");
            assert!(a.breakdown().is_some(), "{word}: {a:?}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            let mut inverse = a.clone();
            inverse.rules.retain(|r| r != "ending.degree_rimankeum");
            let endings: Vec<_> = inverse
                .morphemes
                .iter_mut()
                .filter(|m| m.kind == MorphemeKind::Ending && m.form == "으리만큼")
                .collect();
            assert_eq!(endings.len(), 1);
            for ending in endings {
                ending.form = "으리라".into();
            }
            assert!(
                parent.analyses.contains(&inverse),
                "missing exact parent {word}: {a:?}"
            );
        }
    }
}

#[test]
fn allomorphs_retain_lexical_rieul_and_irregular_stems() {
    let engine = Lemmatizer::new();
    for (word, head) in [
        ("가리만큼", "가다"),
        ("먹으리만큼", "먹다"),
        ("살리만큼", "살다"),
        ("들으리만큼", "듣다"),
        ("추우리만큼", "춥다"),
        ("좋으리만큼", "좋다"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| degree(a) && a.lemmas.len() == 1 && a.lemmas[0].text == head),
            "{word} -> {head}"
        );
    }
    // These assertions reject only the named lexical/allomorph path;
    // other possible lexical or nominal interpretations remain available.
    for (word, head) in [("먹리만큼", "먹다"), ("가으리만큼", "가다")] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| degree(a) && a.lemmas.len() == 1 && a.lemmas[0].text == head),
            "{word} -> {head}"
        );
    }
}

#[test]
fn source_listed_prefinals_and_derived_adjectives_keep_ordered_components() {
    let engine = Lemmatizer::new();
    for (word, head, prefinal) in [("가시리만큼", "가다", "시"), ("갔으리만큼", "가다", "었")]
    {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| degree(a)
                    && a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes
                        .iter()
                        .any(|m| m.kind == MorphemeKind::Prefinal && m.form == prefinal)
                    && a.breakdown().is_some()),
            "{word}"
        );
    }
    assert!(
        engine
            .analyze_word("학생다우리만큼")
            .unwrap()
            .analyses
            .iter()
            .any(|a| degree(a)
                && a.lemmas.iter().any(|l| l.text == "학생")
                && a.morphemes.iter().any(|m| m.form == "답다")
                && a.breakdown().is_some())
    );
}

#[test]
fn complete_native_import_and_uncertain_unlisted_attachments() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    use std::path::PathBuf;
    let path =
        std::env::temp_dir().join(format!("klem-degree-rimankeum-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-degree-rimankeum-english.json",
        )],
        &path,
        "degree-rimankeum-source",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let source: Value =
        serde_json::from_str(include_str!("fixtures/degree-rimankeum-sources.json")).unwrap();
    let entries = source["complete_native_entries"].as_object().unwrap();
    assert_eq!(entries.len(), 43);
    for (id, native) in entries {
        let mut expected = native.clone();
        for sense in expected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(dictionary.entry(id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 1048576);
    for (word, head, expected) in [
        ("가시리만큼", "가다", Compatibility::Compatible),
        ("갔으리만큼", "가다", Compatibility::Compatible),
        ("가겠으리만큼", "가다", Compatibility::Unknown),
        ("가더리만큼", "가다", Compatibility::Unknown),
        ("학생이리만큼", "이다", Compatibility::Unknown),
        ("싶으리만큼", "싶다", Compatibility::Unknown),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let selected: Vec<_> = result
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, a)| degree(a) && a.lemmas.last().is_some_and(|l| l.text == head))
            .collect();
        assert!(!selected.is_empty(), "missing {word} -> {head}");
        for (i, a) in selected {
            let owner = a.lemmas.len() - 1;
            let assessment = annotation.readings[i]
                .lemmas
                .iter()
                .find(|l| l.lemma_index == owner)
                .unwrap();
            assert_eq!(assessment.status, expected, "{word}: {a:?}");
        }
    }
}

#[test]
fn every_original_entry_example_has_a_stable_structural_judgment() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/degree-rimankeum-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 9);
    assert_eq!(report.forbidden_total, 3);
}

#[test]
fn full_source_cohort_retains_candidate_order_and_attributes_new_paths() {
    let source: Value =
        serde_json::from_str(include_str!("fixtures/degree-rimankeum-sources.json")).unwrap();
    assert_eq!(
        source["source_cohort_original_groups"]
            .as_array()
            .unwrap()
            .len(),
        2073
    );
    let old_words = source["source_cohort_before_analyses"].as_object().unwrap();
    assert_eq!(old_words.len(), 5019);
    let engine = Lemmatizer::new();
    for (word, old) in old_words {
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
            if a.rules
                .iter()
                .any(|r| matches!(r.as_str(), "ending.deoniman" | "ending.reported_deoni"))
            {
                deoniman_parent::assert_report_parent(word, a);
                continue;
            }
            if a.rules.iter().any(|r| r == "copula.omitted_ending") {
                copula_expectation_parent::assert_omission_parent(word, a);
                continue;
            }
            assert!(degree(a), "unattributed {word}: {a:?}");
            assert!(a.breakdown().is_some(), "{word}: {a:?}");
            let companion = format!("{}라", word.strip_suffix("만큼").unwrap());
            let parent: WordAnalysis =
                serde_json::from_value(source["companion_analyses"][&companion].clone()).unwrap();
            let mut inverse = a.clone();
            inverse.rules.retain(|r| r != "ending.degree_rimankeum");
            for m in &mut inverse.morphemes {
                if m.kind == MorphemeKind::Ending && m.form == "으리만큼" {
                    m.form = "으리라".into();
                }
            }
            assert!(parent.analyses.contains(&inverse), "{word}: {a:?}");
        }
    }
}
