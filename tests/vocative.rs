//! COV-018p: nominal vocative particles and allomorphs.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("vocative-"));
    suite
}

#[test]
fn vocative_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (21, 13));
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
fn vocative_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-vocative-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-vocative.json")],
        &path,
        "vocative",
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
fn annotated_vocative_preserves_nominal_groups() {
    let source = include_str!("fixtures/kaist-vocative.conllu");
    assert_eq!(source.matches("# sent_id =").count(), 2);
    let engine = Lemmatizer::new();
    for (surface, base, particle) in [("검이여", "검", "이여"), ("젊은이여", "젊은이", "여")]
    {
        assert!(source.lines().any(|line| {
            line.contains(&format!("\t{surface}\t{base}+{particle}\tINTJ\tncn+jcv\t"))
        }));
        let word = engine.analyze_word(surface).unwrap();
        assert!(word.analyses.iter().any(|a| a.lemmas.len() == 1
            && a.lemmas[0].text == base
            && a.lemmas[0].kind == klem::LemmaKind::Nominal
            && a.morphemes.len() == 1
            && a.morphemes[0].form == particle
            && a.morphemes[0].kind == klem::MorphemeKind::Particle));
    }
}

#[test]
fn vocative_keeps_pronunciation_assumptions_and_homonymous_paths() {
    let engine = Lemmatizer::new();
    for (surface, rule) in [
        ("Alex이여", "pronunciation.assumed_consonant"),
        ("Alex시여", "pronunciation.assumed_vowel"),
        ("Alex이시여", "pronunciation.assumed_consonant"),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        assert!(word.analyses.iter().any(|a| a.lemmas.len() == 1
            && a.lemmas[0].text == "Alex"
            && a.rules.iter().any(|r| r == rule)));
    }
    // An unsupported lexical noun is a raw hypothesis; no foreign spelling
    // or noun POS identifies its referent or dictates a vocative interpretation.
    for surface in ["쀍이여", "쀍이시여", "아이야", "주여", "왕자시여"] {
        let word = engine.analyze_word(surface).unwrap();
        assert!(word.analyses.iter().any(|a| a.unchanged));
    }
    let word = engine.analyze_word("왕자시여").unwrap();
    assert!(
        word.analyses
            .iter()
            .any(|a| a.lemmas.iter().any(|l| l.kind == klem::LemmaKind::Copula))
    );
}
