//! COV-017ac / COV-019h: bare-adjective question family licenses.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("adjectival-question-"));
    suite
}

#[test]
fn adjectival_question_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (120, 49));
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
    // Dictionary-free lexical heads are unknown, unlike represented auxiliaries.
    // Preserve the whole lexical hypotheses and explicit question families.
    for (word, lemma, form) in [
        ("쀍으냐", "쀍다", "으냐"),
        ("먹으냐", "먹다", "으냐"),
        ("있으냐", "있다", "으냐"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == form)
        );
    }
}

#[test]
fn annotated_question_keeps_its_lexical_reading_and_general_ending() {
    let source = include_str!("fixtures/gsd-adjectival-question.conllu");
    let fields: Vec<_> = source
        .lines()
        .find(|l| l.starts_with("12\t"))
        .unwrap()
        .split('\t')
        .collect();
    assert_eq!(
        (&fields[1..3], fields[4]),
        (&["뭐하냐는", "뭐+하+냐는"][..], "NP+XSA+ETM")
    );
    let result = Lemmatizer::new().analyze_word(fields[1]).unwrap();
    assert!(result.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "뭐하다"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "냐는"));
    assert!(!result.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["무다", "하다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["어", "으냐는"])
    }));
}

#[test]
fn adjectival_question_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!(
        "klem-adjectival-question-{}.db",
        std::process::id()
    ));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-adjectival-question.json",
        )],
        &path,
        "adjectival-question",
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
