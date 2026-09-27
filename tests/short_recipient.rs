//! COV-018o: independent 게/게서 recipient and source particles.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("short-recipient-"));
    suite
}

#[test]
fn short_recipient_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (77, 16));
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
fn short_recipient_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-short-recipient-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-short-recipient.json")],
        &path,
        "short_recipient",
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
fn annotated_short_recipient_preserves_pronoun_bases_and_particle_roles() {
    let source = include_str!("fixtures/kaist-short-recipient.conllu");
    assert_eq!(source.matches("# sent_id =").count(), 4);
    let engine = Lemmatizer::new();
    let mut count = 0;
    for line in source.lines() {
        let fields: Vec<_> = line.split('\t').collect();
        if fields.len() != 10 || !matches!(fields[1], "내게" | "네게" | "제게" | "내게는")
        {
            continue;
        }
        assert!(fields[4].starts_with("npp+jca"));
        let parts: Vec<_> = fields[2].split('+').collect();
        let word = engine.analyze_word(fields[1]).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == parts[0]
                    && a.lemmas[0].kind == klem::LemmaKind::Nominal
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(parts[1..].iter().copied())
                    && a.morphemes
                        .iter()
                        .all(|m| m.kind == klem::MorphemeKind::Particle)
            })
            .unwrap_or_else(|| panic!("missing annotated path: {line}"));
        assert!(a.rules.iter().any(|r| r == "particle.recipient"));
        count += 1;
    }
    assert_eq!(count, 4);
    // Whole dictionary words and ending homonyms remain selectable.
    for surface in ["가게", "베개", "먹게", "크게"] {
        assert!(
            engine
                .analyze_word(surface)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.unchanged)
        );
    }
}
