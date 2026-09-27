//! COV-021c: complex-coda classes before shortened 하다.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("hada-complex-"));
    suite
}

#[test]
fn hada_complex_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (28, 26));
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
fn hada_complex_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-hada-complex-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-hada-complex.json")],
        &path,
        "hada_complex",
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

// These eight bases exercise phonological classes, including hypothetical
// 하다 words. They assert reversible spelling, not dictionary membership.
#[test]
fn fixed_complex_codas_preserve_full_form_paths_and_reject_opposite_shortening() {
    let engine = Lemmatizer::new();
    for (base, deletion) in [
        ("넋", true),
        ("흙", true),
        ("읊", true),
        ("값", true),
        ("앉", false),
        ("삶", false),
        ("외곬", false),
        ("핥", false),
    ] {
        for (plain, aspirated) in [
            ("기", "키"),
            ("기로", "키로"),
            ("기가", "키가"),
            ("기는", "키는"),
            ("기도", "키도"),
            ("기만", "키만"),
            ("기를", "키를"),
            ("기보다", "키보다"),
            ("게", "케"),
            ("게요", "케요"),
            ("지", "치"),
            ("지요", "치요"),
            ("지만", "치만"),
            ("지만요", "치만요"),
            ("다", "타"),
            ("다고", "타고"),
            ("다는", "타는"),
            ("다니", "타니"),
            ("다면", "타면"),
            ("도록", "토록"),
            ("고자", "코자"),
            ("건대", "컨대"),
        ] {
            let lemma = format!("{base}하다");
            let full = engine.analyze_word(&format!("{base}하{plain}")).unwrap();
            let (short, wrong, rule) = if deletion {
                (plain, aspirated, "deletion.ha")
            } else {
                (aspirated, plain, "contraction.ha_aspiration")
            };
            let short = format!("{base}{short}");
            let analysis = engine.analyze_word(&short).unwrap();
            let expected: Vec<_> = full
                .analyses
                .iter()
                .filter(|a| {
                    a.lemmas.len() == 1
                        && a.lemmas[0].text == lemma
                        && a.lemmas[0].kind == klem::LemmaKind::Predicate
                        && !a.unchanged
                })
                .collect();
            assert!(!expected.is_empty(), "{short}");
            for a in expected {
                let recovered = analysis
                    .analyses
                    .iter()
                    .find(|b| {
                        b.lemmas == a.lemmas
                            && b.morphemes == a.morphemes
                            && b.rules.iter().any(|r| r == rule)
                    })
                    .unwrap_or_else(|| panic!("{short}: {a:?}"));
                assert_eq!(recovered.breakdown(), a.breakdown());
            }
            assert_eq!(
                analysis,
                engine
                    .analyze_word(&short.nfd().collect::<String>())
                    .unwrap()
            );
            let wrong = engine.analyze_word(&format!("{base}{wrong}")).unwrap();
            assert!(
                !wrong
                    .analyses
                    .iter()
                    .any(|a| a.lemmas.iter().any(|l| l.text == lemma)),
                "{base}/{plain}"
            );
        }
    }
}

#[test]
fn complex_shortening_keeps_nominal_and_lexical_paths_and_scoped_exclusions() {
    use klem::{LemmaKind, MorphemeKind, breakdown::Component};
    let engine = Lemmatizer::new();
    let negative = engine.analyze_word("꼴값지않았다").unwrap();
    let restored = negative
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["꼴값하다", "않다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["지", "었", "다"])
        })
        .unwrap();
    assert!(restored.rules.iter().any(|r| r == "deletion.ha"));
    assert_eq!(
        restored.breakdown().unwrap(),
        [
            Component::Lemma(0),
            Component::Morpheme(0),
            Component::Lemma(1),
            Component::Morpheme(1),
            Component::Morpheme(2)
        ]
    );
    let value = engine.analyze_word("값진").unwrap();
    assert!(value.analyses.iter().any(|a| {
        a.lemmas.len() == 1
            && a.lemmas[0].text == "값지다"
            && a.lemmas[0].kind == LemmaKind::Predicate
            && a.morphemes
                .iter()
                .any(|m| m.form == "은" && m.kind == MorphemeKind::Ending)
    }));
    // Pending classes are not declared ungrammatical, but cannot silently
    // acquire a guessed pronunciation from this fixed-class extension.
    for base in ["넓", "많", "싫", "ABC", "3", ""] {
        for tail in ["지", "치", "기", "키"] {
            let result = engine.analyze_word(&format!("{base}{tail}")).unwrap();
            assert!(
                !result
                    .analyses
                    .iter()
                    .any(|a| a.lemmas.iter().any(|l| l.text == format!("{base}하다")))
            );
        }
    }
    let nominal = engine.analyze_word("값기다").unwrap();
    assert!(!nominal.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["값하", "이다"])
    }));
}
