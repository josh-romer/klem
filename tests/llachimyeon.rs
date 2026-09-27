//! COV-017al: recurring-condition endings and lexical role boundaries.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("llachimyeon-"));
    suite
}

#[test]
fn llachimyeon_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (29, 13));
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let result = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            result,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for a in result.analyses {
            assert!(a.breakdown().is_some(), "{}: {a:?}", case.surface);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn llachimyeon_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-llachimyeon-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-llachimyeon.json")],
        &path,
        "llachimyeon",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let report = validity::evaluate_with(&suite(), |word| {
            let mut analysis = engine.analyze_word(word).unwrap();
            let mut annotation = dictionary.annotate(&analysis).unwrap();
            annotation.filter(&mut analysis, policy);
            let cli = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", word, "--dictionary"])
                .arg(&path)
                .arg(flag)
                .output()
                .unwrap();
            assert!(
                cli.status.success(),
                "{}",
                String::from_utf8_lossy(&cli.stderr)
            );
            let value: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                analysis
            );
            assert_eq!(
                value["dictionary"],
                serde_json::to_value(&annotation).unwrap()
            );
            assert!(dictionary.cache_bytes() <= 4096);
            Ok(analysis)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
    }
}

#[test]
fn llachimyeon_dictionary_assesses_homonyms_and_existential_exception() {
    use klem::dictionary::{AttachmentRule, Compatibility};
    let path = std::env::temp_dir().join(format!(
        "klem-llachimyeon-classes-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-llachimyeon.json")],
        &path,
        "llachimyeon",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (word, lemma) in [
        ("좋을라치면", "좋다"),
        ("예쁠라치면", "예쁘다"),
        ("아닐라치면", "아니다"),
        ("있을라치면", "있다"),
        ("늦을라치면", "늦다"),
    ] {
        let analysis = engine.analyze_word(word).unwrap();
        let annotation = dictionary.annotate(&analysis).unwrap();
        let index = analysis
            .analyses
            .iter()
            .position(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.morphemes.iter().map(|m| m.form.as_str()).eq(["을라치면"])
            })
            .unwrap();
        let reading = &annotation.readings[index];
        assert_eq!(
            reading.status,
            if matches!(lemma, "있다" | "늦다") {
                Compatibility::Compatible
            } else {
                Compatibility::Incompatible
            }
        );
        let matches = annotation
            .lemmas
            .iter()
            .find(|m| m.lemma == analysis.analyses[index].lemmas[0])
            .unwrap();
        for evidence in &reading.lemmas[0].entries {
            let entry = &matches
                .entries
                .iter()
                .find(|m| m.entry.id == evidence.id)
                .unwrap()
                .entry;
            if entry.pos == "형용사" && lemma != "있다" {
                assert_eq!(evidence.status, Compatibility::Incompatible);
                assert!(
                    evidence
                        .conflicts
                        .iter()
                        .any(|c| c.rule == AttachmentRule::HabitualConditionVerb
                            && c.morpheme_index == Some(0))
                );
            } else if entry.pos == "동사" || (entry.pos == "형용사" && lemma == "있다") {
                assert_eq!(evidence.status, Compatibility::Compatible);
            }
        }
        if lemma == "늦다" {
            assert!(
                reading.lemmas[0]
                    .entries
                    .iter()
                    .any(|e| e.status == Compatibility::Incompatible)
            );
            assert!(
                reading.lemmas[0]
                    .entries
                    .iter()
                    .any(|e| e.status == Compatibility::Compatible)
            );
        }
    }
    for (word, lemmas, expected) in [
        (
            "예쁘지않을라치면",
            ["예쁘다", "않다"],
            Compatibility::Incompatible,
        ),
        (
            "좋지못할라치면",
            ["좋다", "못하다"],
            Compatibility::Incompatible,
        ),
        (
            "먹지않을라치면",
            ["먹다", "않다"],
            Compatibility::Compatible,
        ),
        (
            "늦지않을라치면",
            ["늦다", "않다"],
            Compatibility::Compatible,
        ),
        ("좋아질라치면", ["좋다", "지다"], Compatibility::Compatible),
    ] {
        let analysis = engine.analyze_word(word).unwrap();
        let annotation = dictionary.annotate(&analysis).unwrap();
        let index = analysis
            .analyses
            .iter()
            .position(|a| {
                a.lemmas.iter().map(|l| l.text.as_str()).eq(lemmas)
                    && a.morphemes.last().is_some_and(|m| m.form == "을라치면")
            })
            .unwrap();
        let reading = &annotation.readings[index];
        assert_eq!(reading.status, expected, "{word}");
        if expected == Compatibility::Incompatible {
            assert!(reading.lemmas[0].entries.iter().any(|e| {
                e.conflicts.iter().any(|c| {
                    c.rule == AttachmentRule::HabitualConditionVerb && c.morpheme_index == Some(1)
                })
            }));
            let mut missing = annotation.clone();
            missing.lemmas.retain(|m| m.lemma.text != lemmas[0]);
            assert_eq!(
                missing.assess(&analysis.analyses[index]).status,
                Compatibility::Unknown
            );
        }
    }
    drop(dictionary);
    drop(db);
    fs::remove_file(path).unwrap();
    let catalog: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    assert_eq!(catalog["-을라치면"]["kind"], "ending");
    for id in [86489, 86616] {
        assert!(
            catalog["-을라치면"]["sources"]
                .as_array()
                .unwrap()
                .iter()
                .any(|s| s["id"] == id && s["pos"] == "어미")
        );
    }
}
