//! COV-020m: source-attested adverbs before copulas.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("adverb-copula-"));
    suite
}

#[test]
fn adverb_copulas_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (61, 11));
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
fn adverb_copulas_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-adverb-copulas-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-adverb-copulas.json")],
        &path,
        "adverb_copulas",
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
fn annotated_adverb_copulas_preserve_roles_beside_nominal_homonyms() {
    use klem::{LemmaKind, MorphemeKind, breakdown::Component};
    let kaist = include_str!("fixtures/kaist-adverb-copulas.conllu");
    let gsd = include_str!("fixtures/gsd-adverb-copulas.conllu");
    assert_eq!(kaist.matches("# sent_id =").count(), 1);
    assert_eq!(gsd.matches("# sent_id =").count(), 8);
    for (source, surface, head, forms) in [
        (kaist, "왜냐고", "왜", vec!["냐고"]),
        (gsd, "별로입니다", "별로", vec!["습니다"]),
        (gsd, "그대로이다", "그대로", vec!["다"]),
        (gsd, "딱입니다", "딱", vec!["습니다"]),
        (gsd, "그만큼이라는", "그만큼", vec!["라는"]),
        (gsd, "먼저니", "먼저", vec!["니"]),
        (gsd, "그럭저럭이다", "그럭저럭", vec!["다"]),
        (gsd, "그만이다", "그만", vec!["다"]),
        (gsd, "물론이며", "물론", vec!["으며"]),
    ] {
        let row = source
            .lines()
            .find(|l| l.contains(&format!("\t{surface}\t")))
            .unwrap();
        assert!(row.contains(&format!("\t{head}+이+")));
        assert!(row.contains("MAG+VCP") || row.contains("mag+jp"));
        let result = Lemmatizer::new().analyze_word(surface).unwrap();
        let analysis = result
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| (l.text.as_str(), l.kind))
                    .eq([(head, LemmaKind::Adverbial), ("이다", LemmaKind::Copula)])
                    && a.morphemes
                        .iter()
                        .map(|m| (m.form.as_str(), m.kind))
                        .eq(forms.iter().map(|f| (*f, MorphemeKind::Ending)))
            })
            .expect(surface);
        assert!(analysis.rules.iter().any(|r| r == "copula.adverbial_base"));
        assert!(!analysis.rules.iter().any(|r| r == "nominalization"));
        assert_eq!(
            analysis.breakdown().unwrap(),
            [
                Component::Lemma(0),
                Component::Lemma(1),
                Component::Morpheme(0)
            ]
        );
    }
}
