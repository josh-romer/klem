//! COV-018q: emphatic 에야 and its explicit decomposition.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("eya-"));
    suite
}

#[test]
fn eya_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (26, 8));
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
fn eya_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-eya-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-eya.json")],
        &path,
        "eya",
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
fn annotated_eya_preserves_groups_and_split_alternatives() {
    let source = include_str!("fixtures/kaist-eya.conllu");
    assert_eq!(source.matches("# sent_id =").count(), 3);
    let engine = Lemmatizer::new();
    for (surface, base, gold, outer) in [
        ("때에야만", "때", "때+에+야만", true),
        ("전에야", "전", "전+에+야", false),
        ("다음에야", "다음", "다음+에+야", false),
    ] {
        assert!(
            source
                .lines()
                .any(|line| line.contains(&format!("\t{surface}\t{gold}\t")))
        );
        let word = engine.analyze_word(surface).unwrap();
        for mut forms in [vec!["에야"], vec!["에", "야"]] {
            if outer {
                forms.push("만");
            }
            assert!(word.analyses.iter().any(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == base
                    && a.lemmas[0].kind == klem::LemmaKind::Nominal
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
                    && a.morphemes
                        .iter()
                        .all(|m| m.kind == klem::MorphemeKind::Particle)
            }));
        }
    }
}

#[test]
fn eya_decomposition_preserves_outer_order_and_copula_ownership() {
    let engine = Lemmatizer::new();
    for surface in [
        "때에야만은",
        "집들에야",
        "죽음에야",
        "학생임에야",
        "때에야만이다",
        "Alex에야",
        "쀍에야",
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let mut checked = 0;
        for a in &word.analyses {
            let Some(slot) = a.morphemes.iter().position(|m| m.form == "에야") else {
                continue;
            };
            let mut split = a.clone();
            split.morphemes.splice(
                slot..=slot,
                [
                    klem::Morpheme {
                        form: "에".into(),
                        kind: klem::MorphemeKind::Particle,
                    },
                    klem::Morpheme {
                        form: "야".into(),
                        kind: klem::MorphemeKind::Particle,
                    },
                ],
            );
            assert!(
                word.analyses
                    .iter()
                    .any(|b| b.lemmas == split.lemmas && b.morphemes == split.morphemes),
                "{surface}: {a:?}"
            );
            assert!(split.breakdown().is_some());
            checked += 1;
        }
        assert!(checked > 0, "{surface}");
        assert!(word.analyses.iter().any(|a| a.unchanged));
    }
}
