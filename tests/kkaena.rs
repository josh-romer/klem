//! COV-018s: nominal degree particle 깨나.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("kkaena-"));
    suite
}

#[test]
fn kkaena_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (17, 10));
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
fn kkaena_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-kkaena-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-kkaena.json")],
        &path,
        "kkaena",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let mut missing = engine.analyze_word("아씨들깨나").unwrap();
        assert!(missing.analyses.iter().any(|a| a.lemmas[0].text == "아씨"));
        let mut annotation = dictionary.annotate(&missing).unwrap();
        assert!(
            annotation
                .lemmas
                .iter()
                .filter(|m| m.lemma.text == "아씨")
                .all(|m| m.entries.is_empty())
        );
        annotation.filter(&mut missing, policy);
        assert!(
            !missing
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.text == "아씨"))
        );
        let mut filtered_suite = suite();
        // 아씨 is absent from KRDict; the source-attested path remains raw-only.
        filtered_suite
            .cases
            .retain(|c| c.id != "kkaena-plural-source");
        let report = validity::evaluate_with(&filtered_suite, |word| {
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
fn annotated_kkaena_preserves_nominal_group() {
    let source = include_str!("fixtures/kaist-kkaena.conllu");
    assert_eq!(source.matches("# sent_id =").count(), 1);
    assert!(source.contains("\t족보깨나\t족보+깨나\tADV\tncn+jxc\t"));
    let word = Lemmatizer::new().analyze_word("족보깨나").unwrap();
    assert!(word.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "족보"
        && a.lemmas[0].kind == klem::LemmaKind::Nominal
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "깨나"
        && a.morphemes[0].kind == klem::MorphemeKind::Particle));
}

#[test]
fn kkaena_keeps_unknown_bases_and_requires_a_nonempty_head() {
    let engine = Lemmatizer::new();
    for surface in ["쀍깨나", "ABC깨나", "2026깨나"] {
        let word = engine.analyze_word(surface).unwrap();
        assert!(word.analyses.iter().any(|a| a.lemmas[0].text
            == surface.strip_suffix("깨나").unwrap()
            && a.morphemes.len() == 1
            && a.morphemes[0].form == "깨나"));
    }
    let word = engine.analyze_word("깨나").unwrap();
    assert!(
        word.analyses
            .iter()
            .all(|a| a.lemmas.iter().all(|l| !l.text.is_empty()))
    );
    assert!(
        !word
            .analyses
            .iter()
            .any(|a| a.morphemes.iter().any(|m| m.form == "깨나"))
    );
}
