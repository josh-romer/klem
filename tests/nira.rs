//! COV-017ai / COV-020j: literary assertions and omitted copulas.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("nira-"));
    suite
}

#[test]
fn nira_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (37, 17));
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
    // An unknown lexical head remains a hypothesis, not a dictionary assertion.
    assert!(
        engine
            .analyze_word("쀍으니라")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "쀍다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "으니라")
    );
}

#[test]
fn nira_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-nira-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-nira.json")],
        &path,
        "nira",
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
fn annotated_nira_preserves_lexical_and_omitted_copula_groups() {
    let source = include_str!("fixtures/kaist-nira.conllu");
    assert_eq!(source.matches("# sent_id =").count(), 3);
    let engine = Lemmatizer::new();
    for (surface, gold, lemmas, forms) in [
        (
            "사랑하느니라",
            "사랑+하+느니라",
            vec!["사랑하다"],
            vec!["느니라"],
        ),
        (
            "그림자니라",
            "그림자+이+니라",
            vec!["그림자", "이다"],
            vec!["으니라"],
        ),
        ("같으니라", "같+으니라", vec!["같다"], vec!["으니라"]),
    ] {
        assert!(
            source
                .lines()
                .any(|l| l.contains(&format!("\t{surface}\t{gold}\t")))
        );
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        assert!(a.rules.iter().any(|r| r == "ending.literary_assertion"));
        if surface == "그림자니라" {
            assert_eq!(a.lemmas[1].kind, klem::LemmaKind::Copula);
            assert!(a.rules.iter().any(|r| r == "copula.omitted_ending"));
        }
    }
}

#[test]
fn nira_lexical_evidence_preserves_homonyms_unknowns_and_ownership() {
    use klem::dictionary::{AttachmentRule, Compatibility, pos_compatibility};
    let path = std::env::temp_dir().join(format!("klem-nira-evidence-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-nira.json")],
        &path,
        "nira",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (surface, ending, conflicting) in [
        ("크니라", "으니라", "krdict:66584"),
        ("크느니라", "느니라", "krdict:66586"),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == "크다"
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == ending
            })
            .unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let assessed = annotation.assess(a);
        assert_eq!(assessed.status, Compatibility::Compatible);
        let entry = assessed.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == conflicting)
            .unwrap();
        assert_eq!(entry.status, Compatibility::Incompatible);
        assert_eq!(entry.conflicts.len(), 1);
        assert_eq!(
            entry.conflicts[0].rule,
            AttachmentRule::LiteraryAssertionClass
        );
        assert_eq!(entry.conflicts[0].morpheme_index, Some(0));
    }
    let word = engine.analyze_word("읽으니라").unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "읽다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "으니라"
        })
        .unwrap();
    let mut annotation = dictionary.annotate(&word).unwrap();
    assert_eq!(annotation.assess(a).status, Compatibility::Incompatible);
    let slot = annotation
        .lemmas
        .iter_mut()
        .find(|m| m.lemma == a.lemmas[0])
        .unwrap();
    for e in &mut slot.entries {
        e.entry.pos = "unmapped provider class".into();
        e.pos_compatibility = pos_compatibility(&slot.lemma, &e.entry);
    }
    assert_eq!(annotation.assess(a).status, Compatibility::Unknown);
    let mut filtered = word.clone();
    annotation.filter(&mut filtered, DictionaryFilter::Compatible);
    assert!(filtered.analyses.contains(a));
    let mut word = engine.analyze_word("좋아하느니라").unwrap();
    let mut annotation = dictionary.annotate(&word).unwrap();
    annotation.filter(&mut word, DictionaryFilter::Compatible);
    assert!(word.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["좋다", "하다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["어", "느니라"])
    }));
}
