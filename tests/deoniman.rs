#[path = "copula_expectation_support/parent.rs"]
mod copula_expectation_parent;
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;
fn family(a: &Analysis) -> bool {
    a.rules
        .iter()
        .any(|r| matches!(r.as_str(), "ending.deoniman" | "ending.reported_deoni"))
}
fn heads(a: &Analysis, expected: &[&str]) -> bool {
    a.lemmas
        .iter()
        .map(|l| l.text.as_str())
        .eq(expected.iter().copied())
}

#[test]
fn every_original_emphatic_example_keeps_its_grouped_lexical_head() {
    let source: Value =
        serde_json::from_str(include_str!("fixtures/deoniman-sources.json")).unwrap();
    assert_eq!(
        source["primary_original_groups"].as_array().unwrap().len(),
        25
    );
    let engine = Lemmatizer::new();
    for (word, head) in source["expected_heads"].as_object().unwrap() {
        let expected = if word == "난리더니만" {
            vec!["난리", "이다"]
        } else {
            vec![head.as_str().unwrap()]
        };
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| family(a) && heads(a, &expected)),
            "{word}"
        );
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
        assert!(
            result
                .analyses
                .iter()
                .flat_map(|a| &a.rules)
                .all(|r| klem::rule_explanation(r).is_some())
        );
    }
}

#[test]
fn every_original_source_word_retains_all_previous_candidates_in_order() {
    let source: Value =
        serde_json::from_str(include_str!("fixtures/deoniman-sources.json")).unwrap();
    let before = source["source_before_analyses"].as_object().unwrap();
    assert_eq!(before.len(), 7215);
    let engine = Lemmatizer::new();
    for (word, old) in before {
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
            if !family(a) && a.rules.iter().any(|r| r == "copula.omitted_ending") {
                copula_expectation_parent::assert_omission_parent(word, a);
                continue;
            }
            assert!(family(a), "{word}: {a:?}");
            assert!(a.breakdown().is_some());
        }
    }
}

#[test]
fn quoted_verb_allomorphs_do_not_borrow_attached_hieut_recovery() {
    let engine = Lemmatizer::new();
    for (word, head, form) in [
        ("간다더니만", "가다", "는다더니만"),
        ("먹는다더니마는", "먹다", "는다더니마는"),
        ("산다더니만", "살다", "는다더니만"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| family(a)
                    && heads(a, &[head])
                    && a.morphemes.iter().any(|m| m.form == form)),
            "{word}"
        );
    }
    for (word, head) in [
        ("공부한다더니만", "공부핳다"),
        ("공부한다더니마는", "공부핳다"),
        ("살는다더니만", "살다"),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| family(a) && heads(a, &[head])),
            "{word}"
        );
    }
}

#[test]
fn derived_adjectives_preserve_plain_quoted_and_past_components() {
    let engine = Lemmatizer::new();
    for (word, forms) in [
        ("학생답더니만", vec!["답다", "더니만"]),
        ("학생답다더니만", vec!["답다", "다더니만"]),
        ("학생다웠다더니마는", vec!["답다", "었", "다더니마는"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| {
                family(a)
                    && heads(a, &["학생"])
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .expect(word);
        assert_eq!(a.lemmas[0].kind, LemmaKind::Nominal);
        assert_eq!(a.morphemes[0].kind, MorphemeKind::Suffix);
        assert!(a.breakdown().is_some());
    }
}

#[test]
fn full_native_import_preserves_notes_groups_homonyms_and_own_marker_assessments() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    use std::path::PathBuf;
    let path = std::env::temp_dir().join(format!("klem-deoniman-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-deoniman-english.json")],
        &path,
        "deoniman-source",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 1048576);
    let source: Value =
        serde_json::from_str(include_str!("fixtures/deoniman-sources.json")).unwrap();
    assert_eq!(
        source["complete_native_entries"].as_object().unwrap().len(),
        77
    );
    for (id, native) in source["complete_native_entries"].as_object().unwrap() {
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
    for (word, head, form, expected) in [
        ("가더니만", "가다", "더니만", Compatibility::Compatible),
        ("좋더니마는", "좋다", "더니마는", Compatibility::Compatible),
        ("가시더니만", "가다", "더니만", Compatibility::Compatible),
        ("갔더니마는", "가다", "더니마는", Compatibility::Compatible),
        ("가겠더니만", "가다", "더니만", Compatibility::Compatible),
        ("가더더니만", "가다", "더니만", Compatibility::Unknown),
        (
            "간다더니만",
            "가다",
            "는다더니만",
            Compatibility::Compatible,
        ),
        ("좋다더니만", "좋다", "다더니만", Compatibility::Compatible),
        (
            "가다더니만",
            "가다",
            "다더니만",
            Compatibility::Incompatible,
        ),
        ("갔다더니만", "가다", "다더니만", Compatibility::Compatible),
        (
            "가겠다더니만",
            "가다",
            "다더니만",
            Compatibility::Compatible,
        ),
        ("가시다더니만", "가다", "다더니만", Compatibility::Unknown),
        ("학생이더니만", "이다", "더니만", Compatibility::Compatible),
        ("학생이다더니만", "이다", "다더니만", Compatibility::Unknown),
        (
            "학생답다더니만",
            "학생",
            "다더니만",
            Compatibility::Compatible,
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let selected: Vec<_> = result
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, a)| {
                family(a)
                    && a.lemmas.last().is_some_and(|l| l.text == head)
                    && a.morphemes.last().is_some_and(|m| m.form == form)
                    && !a.morphemes.iter().any(|m| m.kind == MorphemeKind::Particle)
            })
            .collect();
        assert!(!selected.is_empty(), "{word}");
        for (i, a) in selected {
            let own = annotation.readings[i]
                .lemmas
                .iter()
                .find(|l| l.lemma_index == a.lemmas.len() - 1)
                .unwrap();
            assert_eq!(own.status, expected, "{word}: {a:?}");
        }
    }
}

#[test]
fn every_direct_report_group_recovers_its_frozen_companion_paths() {
    let source: Value =
        serde_json::from_str(include_str!("fixtures/deoniman-sources.json")).unwrap();
    assert_eq!(
        source["reported_original_groups"].as_array().unwrap().len(),
        23
    );
    let engine = Lemmatizer::new();
    for row in source["reported_literal_observations"].as_array().unwrap() {
        let word = row["surface"].as_str().unwrap();
        let old: WordAnalysis = serde_json::from_value(row["before"].clone()).unwrap();
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
        for proposal in row["structural_proposals"].as_array().unwrap() {
            let expected: Analysis = serde_json::from_value(proposal.clone()).unwrap();
            assert!(new.analyses.contains(&expected), "{word}: {expected:?}");
            assert!(expected.breakdown().is_some());
        }
        assert!(
            new.analyses
                .iter()
                .filter(|a| !old.analyses.contains(a))
                .all(family),
            "{word}"
        );
    }
}

#[test]
fn direct_report_allomorphs_preserve_boundaries_and_derived_adjectives() {
    let engine = Lemmatizer::new();
    for (word, head, form) in [
        ("간다더니", "가다", "는다더니"),
        ("먹는다더니", "먹다", "는다더니"),
        ("산다더니", "살다", "는다더니"),
        ("좋다더니", "좋다", "다더니"),
        ("갔다더니", "가다", "다더니"),
        ("가겠다더니", "가다", "다더니"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| family(a)
                    && heads(a, &[head])
                    && a.morphemes.iter().any(|m| m.form == form)),
            "{word}"
        );
    }
    for (word, head) in [("공부한다더니", "공부핳다"), ("살는다더니", "살다")] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| family(a) && heads(a, &[head])),
            "{word}"
        );
    }
    assert!(
        engine
            .analyze_word("학생답다더니")
            .unwrap()
            .analyses
            .iter()
            .any(|a| family(a)
                && heads(a, &["학생"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["답다", "다더니"])),
        "derived adjective"
    );
}

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn individually_identified_reported_source_judgments() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/reported-deoni-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 24);
    assert_eq!(report.forbidden_total, 2);
    assert!(!report.review_queue.is_empty());
}

#[test]
fn directly_reported_lexical_owners_keep_complete_native_imports() {
    use klem::dictionary::{Dictionary, SqliteDictionary, import_krdict};
    use std::path::PathBuf;
    let path = std::env::temp_dir().join(format!("klem-reported-native-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-reported-deoni-english.json",
        )],
        &path,
        "reported-native",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let source: Value =
        serde_json::from_str(include_str!("fixtures/reported-deoni-native.json")).unwrap();
    assert_eq!(source.as_object().unwrap().len(), 34);
    for (id, native) in source.as_object().unwrap() {
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
}

#[test]
fn direct_report_assessments_follow_their_own_allomorph_and_prefinals() {
    use klem::dictionary::{Compatibility, DictionarySession, SqliteDictionary, import_krdict};
    use std::path::PathBuf;
    let path = std::env::temp_dir().join(format!("klem-reported-policy-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-deoniman-english.json")],
        &path,
        "reported-policy",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let mut session = DictionarySession::new(&dictionary, 1048576);
    let engine = Lemmatizer::new();
    for (word, head, form, expected) in [
        ("간다더니", "가다", "는다더니", Compatibility::Compatible),
        ("먹는다더니", "먹다", "는다더니", Compatibility::Compatible),
        ("산다더니", "살다", "는다더니", Compatibility::Compatible),
        ("좋다더니", "좋다", "다더니", Compatibility::Compatible),
        ("가다더니", "가다", "다더니", Compatibility::Incompatible),
        (
            "좋는다더니",
            "좋다",
            "는다더니",
            Compatibility::Incompatible,
        ),
        ("갔다더니", "가다", "다더니", Compatibility::Compatible),
        ("가겠다더니", "가다", "다더니", Compatibility::Compatible),
        ("가신다더니", "가다", "는다더니", Compatibility::Compatible),
        ("가시다더니", "가다", "다더니", Compatibility::Unknown),
        ("가더다더니", "가다", "다더니", Compatibility::Unknown),
        ("학생답다더니", "학생", "다더니", Compatibility::Compatible),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let annotated = session.annotate(&result).unwrap();
        let selected = result
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, a)| {
                family(a) && heads(a, &[head]) && a.morphemes.iter().any(|m| m.form == form)
            })
            .collect::<Vec<_>>();
        assert!(!selected.is_empty(), "{word}");
        for (index, a) in selected {
            assert_eq!(
                annotated.readings[index].lemmas[0].status, expected,
                "{word}: {a:?}"
            );
        }
    }
}

#[test]
fn individually_identified_emphatic_source_judgments() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/deoniman-emphatic-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 25);
    assert_eq!(report.forbidden_total, 6);
}
