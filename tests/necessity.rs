//! COV-017am: necessity endings, distinct from particle 밖에.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("necessity-"));
    suite
}

#[test]
fn necessity_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (53, 13));
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
fn necessity_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-necessity-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-necessity.json")],
        &path,
        "necessity",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        // The pinned KRDict has no 되돌려받다 headword. It remains a raw
        // source-backed candidate, and dictionary filters must remove it.
        let mut covered = suite();
        covered
            .cases
            .retain(|c| c.id != "necessity-final-correction");
        let report = validity::evaluate_with(&covered, |word| {
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
fn necessity_missing_headword_is_unknown_and_filtered() {
    use klem::dictionary::Compatibility;
    let path =
        std::env::temp_dir().join(format!("klem-necessity-missing-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-necessity.json")],
        &path,
        "necessity",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let raw = Lemmatizer::new().analyze_word("되돌려받을밖에").unwrap();
    let annotation = dictionary.annotate(&raw).unwrap();
    let index = raw
        .analyses
        .iter()
        .position(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).eq(["되돌려받다"])
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["을밖에"])
        })
        .unwrap();
    assert_eq!(annotation.readings[index].status, Compatibility::Unknown);
    for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
        let mut analysis = raw.clone();
        let mut filtered = annotation.clone();
        filtered.filter(&mut analysis, policy);
        assert!(
            !analysis
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.text == "되돌려받다"))
        );
    }
    drop(dictionary);
    drop(db);
    fs::remove_file(path).unwrap();
}

#[test]
fn necessity_and_restrictive_particle_have_distinct_sources() {
    let catalog: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    assert_eq!(catalog["-을밖에"]["kind"], "ending");
    for id in [85762, 85772] {
        assert!(
            catalog["-을밖에"]["sources"]
                .as_array()
                .unwrap()
                .iter()
                .any(|s| s["id"] == id && s["pos"] == "어미")
        );
    }
    assert_eq!(catalog["밖에"]["kind"], "particle");
    assert!(
        catalog["밖에"]["sources"]
            .as_array()
            .unwrap()
            .iter()
            .any(|s| s["id"] == 70070 && s["pos"] == "조사")
    );
    // This search hit is a quoted clause plus particle, not an annotated
    // example of the necessity ending. Preserve its literal source reading.
    let corpus = include_str!("fixtures/kaist-necessity-search.conllu");
    assert!(corpus.contains("# sent_id = MH2_0072-s236"));
    assert!(corpus.contains("8\t못하다고밖에\t못하+다고+밖에\tADV\tpx+ecs+jxc"));
}
