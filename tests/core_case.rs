//! COV-018t/019n: core cases, emphatic case forms and auxiliary particles.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("core-case-"));
    suite
}

#[test]
fn core_case_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (69, 36));
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
fn core_case_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-core-case-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-core-case.json")],
        &path,
        "core_case",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let mut missing = engine.analyze_word("곧이를").unwrap();
        assert!(missing.analyses.iter().any(|a| a.lemmas[0].text == "곧이"));
        let mut annotation = dictionary.annotate(&missing).unwrap();
        annotation.filter(&mut missing, policy);
        assert!(
            !missing
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.text == "곧이"))
        );
        let mut filtered_suite = suite();
        filtered_suite
            .cases
            .retain(|c| c.id != "core-case-adverb-곧이");
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
fn core_case_annotated_paths_and_compound_alternatives() {
    let gsd = include_str!("fixtures/gsd-core-case.conllu");
    let kaist = include_str!("fixtures/kaist-core-case.conllu");
    assert_eq!(gsd.matches("# sent_id =").count(), 4);
    assert_eq!(kaist.matches("# sent_id =").count(), 2);
    for (source, surface, gold, lemma) in [
        (gsd, "속이지를", "속이+지+를", "속이다"),
        (gsd, "질리지가", "질리+지+가", "질리다"),
        (kaist, "적지가", "적+지+가", "적다"),
        (kaist, "작가에게로", "작가+에게로", "작가"),
    ] {
        assert!(
            source
                .lines()
                .any(|l| l.contains(&format!("\t{surface}\t{gold}\t")))
        );
        let result = Lemmatizer::new().analyze_word(surface).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == lemma)
        );
    }
    for (surface, base, inner, bundle) in [
        ("내게로", "내", "게", "게로"),
        ("친구에게로", "친구", "에게", "에게로"),
        ("친구한테로", "친구", "한테", "한테로"),
    ] {
        let result = Lemmatizer::new().analyze_word(surface).unwrap();
        for forms in [vec![bundle], vec![inner, "로"]] {
            assert!(result.analyses.iter().any(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == base
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            }));
        }
    }
}

#[test]
fn core_case_emphatic_adverbs_are_finite_and_auxiliary_links_stay_bounded() {
    let engine = Lemmatizer::new();
    for surface in [
        "맘껏을",
        "매번을",
        "매일을",
        "도대체가",
        "곧이를",
        "빨리를",
        "빨릴",
    ] {
        assert!(
            engine
                .analyze_word(surface)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "particle.adverbial_case"))
        );
    }
    // These are unsupported inventory members, not categorical judgments
    // that every Korean context would forbid the same adverb + particle.
    for surface in ["천천히를", "아주가", "빨리이", "맘껏가", "책을"] {
        assert!(
            !engine
                .analyze_word(surface)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "particle.adverbial_case"))
        );
    }
    for (full, short) in [
        ("먹지를않았다", "먹질않았다"),
        ("물어를봐야지", "물얼봐야지"),
    ] {
        let full = engine.analyze_word(full).unwrap();
        let short = engine.analyze_word(short).unwrap();
        let full_paths: Vec<_> = full
            .analyses
            .iter()
            .filter(|a| {
                a.lemmas
                    .iter()
                    .any(|l| l.kind == klem::LemmaKind::Auxiliary)
                    && a.morphemes
                        .iter()
                        .any(|m| m.form == "를" && m.kind == klem::MorphemeKind::Particle)
            })
            .collect();
        assert!(!full_paths.is_empty());
        for a in full_paths {
            assert!(short.analyses.iter().any(|b| a.lemmas == b.lemmas
                && a.morphemes == b.morphemes
                && b.rules.iter().any(|r| r == "particle.contraction.l")));
        }
    }
}

#[test]
fn core_case_corpus_observations_do_not_replace_lexical_alternatives() {
    let source = include_str!("fixtures/gsd-core-case.conllu");
    assert!(source.contains("\t강원체고를\t강원+체+이+고+를\t"));
    assert!(source.contains("\t잘해서\t잘+하+아서\t"));
    // Matching an annotated copula in a school name does not establish
    // its intended analysis; retain the ordinary nominal alternative.
    let engine = Lemmatizer::new();
    assert!(
        engine
            .analyze_word("강원체고를")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "강원체고"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "를")
    );
    assert!(
        engine
            .analyze_word("잘해서")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "잘하다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "어서")
    );
}
