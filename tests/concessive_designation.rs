//! COV-018v: concessive and designation particles.
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
        .retain(|c| c.id.starts_with("concessive-designation-"));
    suite
}

#[test]
fn concessive_designation_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (68, 30));
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
fn concessive_designation_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!(
        "klem-concessive-designation-{}.db",
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
            "tests/fixtures/krdict-concessive-designation.json",
        )],
        &path,
        "concessive_designation",
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
fn emphatic_compounds_preserve_split_paths_and_lexical_ambiguity() {
    use klem::{Morpheme, MorphemeKind};
    let engine = Lemmatizer::new();
    let mut surfaces = Vec::new();
    for base in [
        "학교",
        "집",
        "말",
        "아이",
        "ABC",
        "2026",
        "쀍",
        "먹기",
        "먹고",
        "먹어",
        "먹어서",
        "먹고서",
    ] {
        for tail in ["을랑은", "일랑은", "설랑은", "에설랑은"] {
            for outer in ["", "요", "이다"] {
                surfaces.push(format!("{base}{tail}{outer}"));
            }
        }
    }
    surfaces.extend(
        [
            "얘길랑은",
            "널랑은요",
            "곳엘랑은",
            "먹질랑은",
            "먹고있어설랑은",
        ]
        .map(str::to_owned),
    );
    let mut compared = 0;
    for surface in surfaces {
        let word = engine.analyze_word(&surface).unwrap();
        for a in &word.analyses {
            for (i, m) in a.morphemes.iter().enumerate() {
                if m.kind != MorphemeKind::Particle {
                    continue;
                }
                for short in ["ㄹ랑", "을랑", "일랑", "설랑"] {
                    let long = format!("{short}은");
                    let mut forms = a.morphemes.clone();
                    if m.form == long {
                        forms.splice(
                            i..=i,
                            [short, "은"].map(|form| Morpheme {
                                form: form.into(),
                                kind: MorphemeKind::Particle,
                            }),
                        );
                    } else if m.form == short
                        && a.morphemes
                            .get(i + 1)
                            .is_some_and(|n| n.form == "은" && n.kind == MorphemeKind::Particle)
                    {
                        forms.splice(
                            i..i + 2,
                            [Morpheme {
                                form: long,
                                kind: MorphemeKind::Particle,
                            }],
                        );
                    } else {
                        continue;
                    }
                    compared += 1;
                    assert!(
                        word.analyses
                            .iter()
                            .any(|b| b.lemmas == a.lemmas && b.morphemes == forms),
                        "{surface}: {:?} -> {forms:?}",
                        a.morphemes
                    );
                }
            }
        }
    }
    assert!(compared > 100, "vacuous comparison: {compared}");
    for (surface, lexical, particle) in [("샌들", "새", "ㄴ들"), ("학자인들", "학자", "인들")]
    {
        let word = engine.analyze_word(surface).unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.unchanged && a.lemmas[0].text == surface)
        );
        assert!(word.analyses.iter().any(|a| a.lemmas.len() == 1
            && a.lemmas[0].text == lexical
            && a.morphemes.len() == 1
            && a.morphemes[0].form == particle));
    }
    let word = engine.analyze_word("먹고있어설랑은").unwrap();
    for forms in [["고", "어서", "ㄹ랑은"], ["고", "어", "설랑은"]] {
        assert!(word.analyses.iter().any(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).collect::<Vec<_>>() == ["먹다", "있다"]
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .collect::<Vec<_>>()
                    == forms
        }));
    }
}
