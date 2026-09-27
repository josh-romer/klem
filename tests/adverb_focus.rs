//! COV-018n: distinguish adverbial focus attachment from nominal case marking.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{LemmaKind, Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("adverb-focus-"));
    suite
}

#[test]
fn adverbial_focus_roles_preserve_sources_unicode_order_and_unknown_heads() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (38, 17));
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
    for (word, base, form) in [
        ("쀍도", "쀍", "도"),
        ("쀍은", "쀍", "은"),
        ("쀍부터", "쀍", "부터"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        for kind in [LemmaKind::Nominal, LemmaKind::Adverbial] {
            assert!(result.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == base
                && a.lemmas[0].kind == kind
                && a.morphemes.len() == 1
                && a.morphemes[0].form == form));
        }
    }
}

#[test]
fn adverbial_focus_dictionary_filters_keep_lexical_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-adverb-focus-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-adverb-focus.json")],
        &path,
        "adverb-focus",
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
    for (word, base, expected) in [
        ("학교도", "학교", vec![LemmaKind::Nominal]),
        ("아직도", "아직", vec![LemmaKind::Adverbial]),
        (
            "오늘은",
            "오늘",
            vec![LemmaKind::Nominal, LemmaKind::Adverbial],
        ),
    ] {
        let mut analysis = engine.analyze_word(word).unwrap();
        let mut annotation = dictionary.annotate(&analysis).unwrap();
        assert!(analysis.analyses.iter().any(|a| a.lemmas.len() == 1
            && a.lemmas[0].text == base
            && a.lemmas[0].kind == LemmaKind::Adverbial));
        annotation.filter(&mut analysis, DictionaryFilter::Compatible);
        let mut roles: Vec<_> = analysis
            .analyses
            .iter()
            .filter(|a| a.lemmas.len() == 1 && a.lemmas[0].text == base)
            .map(|a| a.lemmas[0].kind)
            .collect();
        roles.sort();
        roles.dedup();
        assert_eq!(roles, expected, "{word}");
    }
}

#[test]
fn annotated_adverb_particle_tokens_have_an_adverbial_analysis() {
    let engine = Lemmatizer::new();
    let mut checked = 0;
    for source in [
        include_str!("fixtures/kaist-adverb-focus.conllu"),
        include_str!("fixtures/gsd-adverb-focus.conllu"),
    ] {
        for line in source
            .lines()
            .filter(|line| !line.starts_with('#') && !line.is_empty())
        {
            let fields: Vec<_> = line.split('\t').collect();
            if !matches!(fields[1], "아직도" | "아직까지" | "너무도" | "일찍부터")
                || fields[3] != "ADV"
                || !fields[2].contains('+')
            {
                continue;
            }
            let components: Vec<_> = fields[2].split('+').collect();
            assert_eq!(components.len(), 2);
            assert!(matches!(fields[4], "mag+jxc" | "MAG+JX"));
            let result = engine.analyze_word(fields[1]).unwrap();
            assert!(
                result.analyses.iter().any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == components[0]
                    && a.lemmas[0].kind == LemmaKind::Adverbial
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == components[1]
                    && a.morphemes[0].kind == klem::MorphemeKind::Particle),
                "{}",
                fields[1]
            );
            checked += 1;
        }
    }
    assert_eq!(checked, 6);
}
