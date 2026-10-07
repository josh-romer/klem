//! Source-owned reported copula and command boundaries; contextual sense stays unjudged.
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

fn source() -> Value {
    serde_json::from_str(include_str!("fixtures/reported-command-deoni-sources.json")).unwrap()
}
fn family(a: &Analysis) -> bool {
    a.rules.iter().any(|r| r == "ending.reported_command_deoni")
}
fn heads(a: &Analysis, words: &[&str]) -> bool {
    a.lemmas
        .iter()
        .map(|l| l.text.as_str())
        .eq(words.iter().copied())
}

#[test]
fn all_original_groups_keep_old_paths_and_exact_companion_provenance() {
    let source = source();
    assert_eq!(source["all_original_groups"].as_array().unwrap().len(), 20);
    let rows = source["literal_observations"].as_array().unwrap();
    assert_eq!(rows.len(), 20);
    let engine = Lemmatizer::new();
    for row in rows {
        let word = row["surface"].as_str().unwrap();
        let old: WordAnalysis =
            serde_json::from_value(source["actual_word_analyses"][word].clone()).unwrap();
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
                .filter(|a| old.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            old.analyses,
            "{word}"
        );
        let added: Vec<_> = now
            .analyses
            .iter()
            .filter(|a| !old.analyses.contains(a))
            .collect();
        assert!(!added.is_empty(), "{word}");
        for a in added {
            assert!(family(a), "{word}: {a:?}");
            assert!(a.breakdown().is_some());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            assert!(
                row["structural_proposals"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(
                        |p| serde_json::from_value::<Analysis>(p["proposal"].clone()).unwrap()
                            == *a
                    ),
                "new path without exact old companion {word}: {a:?}"
            );
        }
    }
}

#[test]
fn source_lexical_heads_preserve_factual_and_command_roles() {
    let engine = Lemmatizer::new();
    for (word, noun) in [
        ("건물이라더니", "건물"),
        ("유학생이라더니", "유학생"),
        ("오른손이라더니", "오른손"),
        ("상품이라더니", "상품"),
        ("장날이라더니", "장날"),
        ("다홍치마라더니", "다홍치마"),
        ("식이라더니", "식"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| family(a)
                    && heads(a, &[noun, "이다"])
                    && a.lemmas[0].kind == LemmaKind::Nominal
                    && a.lemmas[1].kind == LemmaKind::Copula
                    && a.morphemes.iter().any(|m| m.form == "라더니")),
            "{word}"
        );
    }
    for (word, head) in [
        ("아니라더니", "아니다"),
        ("말라더니", "말다"),
        ("달라더니", "달다"),
        ("검토하라더니", "검토하다"),
        ("가라더니", "가다"),
        ("치우라더니", "치우다"),
        ("찾으라더니", "찾다"),
        ("부으라더니", "붓다"),
        ("먹으라더니", "먹다"),
        ("잡으라더니", "잡다"),
        ("뻗으라더니", "뻗다"),
        ("같으라더니", "같다"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| family(a)
                    && heads(a, &[head])
                    && a.lemmas[0].kind == LemmaKind::Predicate),
            "{word}"
        );
    }
}

#[test]
fn command_allomorphs_and_unlisted_tense_slots_do_not_borrow_factual_paths() {
    let engine = Lemmatizer::new();
    for (word, head) in [
        ("가으라더니", "가다"),
        ("살으라더니", "살다"),
        ("아니라더니", "아니다"),
        ("먹었으라더니", "먹다"),
        ("먹겠으라더니", "먹다"),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| family(a)
                    && heads(a, &[head])
                    && a.morphemes.iter().any(|m| m.form == "으라더니")),
            "{word}"
        );
    }
    let honorific = engine.analyze_word("먹으시라더니").unwrap();
    assert!(
        honorific.analyses.iter().any(|a| family(a)
            && heads(a, &["먹다"])
            && a.morphemes
                .iter()
                .any(|m| m.kind == MorphemeKind::Prefinal && m.form == "시")),
        "honorific command"
    );
    assert!(
        !engine
            .analyze_word("학교였라더니")
            .unwrap()
            .analyses
            .iter()
            .any(|a| family(a)
                && heads(a, &["학교", "이다"])
                && a.morphemes
                    .iter()
                    .any(|m| m.kind == MorphemeKind::Prefinal && m.form == "었"))
    );
}

#[test]
fn complete_native_import_retains_all_notes_and_original_example_groups() {
    use klem::dictionary::{Dictionary, SqliteDictionary, import_krdict};
    use std::path::PathBuf;
    let path = std::env::temp_dir().join(format!(
        "klem-reported-command-deoni-{}.db",
        std::process::id()
    ));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-reported-command-deoni-english.json",
        )],
        &path,
        "reported-command-deoni-source",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let source = source();
    for (id, raw) in source["complete_native_entries"].as_object().unwrap() {
        let mut expected = raw.clone();
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
fn dictionary_assessments_keep_each_ending_owner_and_unlisted_extensions_separate() {
    use klem::dictionary::{Compatibility, DictionarySession, SqliteDictionary, import_krdict};
    use std::path::PathBuf;
    let path = std::env::temp_dir().join(format!(
        "klem-reported-command-policy-{}.db",
        std::process::id()
    ));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-deoniman-english.json"),
            PathBuf::from("tests/fixtures/krdict-reported-command-deoni-english.json"),
        ],
        &path,
        "reported-command-policy",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let mut session = DictionarySession::new(&dictionary, 1048576);
    let engine = Lemmatizer::new();
    for (word, head, form, expected) in [
        ("가라더니", "가다", "으라더니", Compatibility::Compatible),
        ("먹으라더니", "먹다", "으라더니", Compatibility::Compatible),
        ("살라더니", "살다", "으라더니", Compatibility::Compatible),
        ("가시라더니", "가다", "으라더니", Compatibility::Compatible),
        ("가시라더니", "가다", "라더니", Compatibility::Unknown),
        ("아니라더니", "아니다", "라더니", Compatibility::Compatible),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let annotated = session.annotate(&result).unwrap();
        let indices: Vec<_> = result
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, a)| {
                family(a) && heads(a, &[head]) && a.morphemes.iter().any(|m| m.form == form)
            })
            .map(|(i, _)| i)
            .collect();
        assert!(!indices.is_empty(), "{word} {form}");
        for index in indices {
            assert_eq!(
                annotated.readings[index].lemmas[0].status, expected,
                "{word} {form}"
            );
        }
    }
    let result = engine.analyze_word("학교라더니").unwrap();
    let annotated = session.annotate(&result).unwrap();
    let index = result
        .analyses
        .iter()
        .position(|a| {
            family(a)
                && heads(a, &["학교", "이다"])
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "라더니"
        })
        .unwrap();
    let owner = annotated.readings[index]
        .lemmas
        .iter()
        .find(|l| l.lemma_index == 1)
        .unwrap();
    for ident in ["krdict:86118", "krdict:86232"] {
        assert_eq!(
            owner.entries.iter().find(|e| e.id == ident).unwrap().status,
            Compatibility::Compatible,
            "{ident}"
        );
    }
    assert_eq!(
        owner
            .entries
            .iter()
            .find(|e| e.id == "krdict:92457")
            .unwrap()
            .status,
        Compatibility::Incompatible
    );

    // Supplied hypotheses still receive scoped dictionary checks even when
    // the runtime generator excludes their unlisted prefinal/follower slots.
    let mut a = engine
        .analyze_word("먹으라더니")
        .unwrap()
        .analyses
        .into_iter()
        .find(|a| {
            family(a)
                && heads(a, &["먹다"])
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "으라더니"
        })
        .unwrap();
    a.morphemes.insert(
        0,
        klem::Morpheme {
            form: "더".into(),
            kind: MorphemeKind::Prefinal,
        },
    );
    let supplied = WordAnalysis {
        normalized: "먹더으라더니".into(),
        analyses: vec![a.clone()],
    };
    assert_eq!(
        session.annotate(&supplied).unwrap().readings[0].lemmas[0].status,
        Compatibility::Unknown
    );
    a.morphemes.remove(0);
    a.morphemes.push(klem::Morpheme {
        form: "요".into(),
        kind: MorphemeKind::Particle,
    });
    let supplied = WordAnalysis {
        normalized: "먹으라더니요".into(),
        analyses: vec![a],
    };
    assert_eq!(
        session.annotate(&supplied).unwrap().readings[0].lemmas[0].status,
        Compatibility::Unknown
    );
}

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn stable_individual_source_rule_judgments_pass() {
    let suite: validity::Suite = serde_json::from_str(include_str!(
        "fixtures/reported-command-deoni-validity.json"
    ))
    .unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 25);
    assert_eq!(report.forbidden_total, 6);
}
