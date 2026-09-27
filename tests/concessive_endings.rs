//! COV-017ak: concessive predicate endings.
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
        .retain(|c| c.id.starts_with("concessive-endings-"));
    suite
}

#[test]
fn concessive_endings_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (106, 24));
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
fn concessive_endings_dictionary_filters_preserve_roles_and_cli_parity() {
    let path =
        std::env::temp_dir().join(format!("klem-concessive-endings-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-concessive-endings.json",
        )],
        &path,
        "concessive_endings",
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
fn annotated_concessives_preserve_predicate_copula_and_tense_groups() {
    use klem::{LemmaKind, MorphemeKind};
    let kaist = include_str!("fixtures/kaist-concessive-endings.conllu");
    let gsd = include_str!("fixtures/gsd-concessive-endings.conllu");
    assert_eq!(kaist.matches("# sent_id =").count(), 5);
    assert_eq!(gsd.matches("# sent_id =").count(), 1);
    for (source, surface, gold, heads, forms, kinds) in [
        (
            kaist,
            "한들",
            "하+ㄴ들",
            vec!["하다"],
            vec!["은들"],
            vec![LemmaKind::Predicate],
        ),
        (
            gsd,
            "할망정",
            "하+ㄹ망정",
            vec!["하다"],
            vec!["을망정"],
            vec![LemmaKind::Predicate],
        ),
        (
            kaist,
            "될지언정",
            "되+ㄹ지언정",
            vec!["되다"],
            vec!["을지언정"],
            vec![LemmaKind::Predicate],
        ),
        (
            kaist,
            "것일지언정",
            "것+이+ㄹ지언정",
            vec!["것", "이다"],
            vec!["을지언정"],
            vec![LemmaKind::Nominal, LemmaKind::Copula],
        ),
        (
            kaist,
            "있었을지언정",
            "있+었+ㄹ지언정",
            vec!["있다"],
            vec!["었", "을지언정"],
            vec![LemmaKind::Predicate],
        ),
    ] {
        assert!(
            source
                .lines()
                .any(|l| l.contains(&format!("\t{surface}\t{gold}\t")))
        );
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(heads.iter().copied())
                    && a.lemmas.iter().map(|l| l.kind).eq(kinds.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending.concessive"));
        assert!(a.breakdown().is_some());
    }
}
