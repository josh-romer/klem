//! COV-017az: literary questions with separately owned polite components.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("rikka-"));
    suite
}

#[test]
fn rikka_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (137, 35));
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
fn rikka_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-rikka-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-rikka.json")],
        &path,
        "rikka",
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
fn rikka_primary_examples_keep_external_sense_identity() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/rikka-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-rikka.json")).unwrap();
    let entries = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 64);
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), entries.len());
    let suite = suite();
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 11);
    for example in examples {
        let case = suite
            .cases
            .iter()
            .find(|c| c.id == example["case_id"])
            .unwrap();
        assert_eq!(case.surface, example["surface"]);
        assert_eq!(suite.sources[&case.judgments[0].source], example["url"]);
        assert_eq!(case.judgments[0].verdict, validity::Verdict::Required);
    }
    let labels: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    assert_eq!(labels["-으리까"]["kind"], "ending");
    assert!(labels["-으리까"]["sources"].as_array().unwrap().is_empty());
    let references = labels["-으리까"]["references"].as_array().unwrap();
    assert_eq!(references.len(), 4);
    for (reference, sense) in references.iter().zip([1, 39911, 20153, 51276]) {
        assert_eq!(
            reference["url"],
            format!("https://opendict.korean.go.kr/dictionary/view?sense_no={sense}")
        );
    }
}

#[test]
fn rikka_spelling_owners_do_not_move_into_nominal_or_auxiliary_components() {
    use klem::SpellingClass;
    let engine = Lemmatizer::new();
    for (word, heads, forms, class, index) in [
        (
            "들으리까",
            vec!["듣다"],
            vec!["으리까"],
            SpellingClass::DigeutIrregular,
            0,
        ),
        (
            "들어주오리까",
            vec!["듣다", "주다"],
            vec!["어", "으옵", "으리까"],
            SpellingClass::DigeutIrregular,
            0,
        ),
        (
            "먹어놓으리까",
            vec!["먹다", "놓다"],
            vec!["어", "으리까"],
            SpellingClass::HieutRegular,
            1,
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let analysis = result
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(heads.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        assert!(
            analysis
                .spelling_paths
                .iter()
                .flatten()
                .any(|s| s.class == class && s.morpheme_index == index),
            "{word}: {analysis:?}"
        );
        assert!(
            analysis
                .rules
                .iter()
                .any(|r| r == "ending.literary_question_ri")
        );
    }
    for (word, heads, forms) in [
        ("친구리까", vec!["친구", "이다"], vec!["으리까"]),
        ("학생다우리까", vec!["학생"], vec!["답다", "으리까"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let analysis = result
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(heads.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        assert!(analysis.spelling_paths.is_empty(), "{word}: {analysis:?}");
        assert!(analysis.breakdown().is_some());
    }
}

#[test]
fn rikka_substrings_inside_lexical_particle_bases_preserve_baseline_outputs() {
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/rikka-corpus-targets.json")).unwrap();
    let engine = Lemmatizer::new();
    let cases = fixture["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 10);
    for case in cases {
        let before: WordAnalysis =
            serde_json::from_value(case["baseline_analysis"].clone()).unwrap();
        assert_eq!(
            engine
                .analyze_word(case["surface"].as_str().unwrap())
                .unwrap(),
            before,
            "{}",
            case["case_id"]
        );
        assert!(
            case["raw_row"]
                .as_str()
                .unwrap()
                .split('\t')
                .nth(2)
                .unwrap()
                .ends_with("+까지")
        );
    }
}
