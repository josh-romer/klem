//! COV-019p: source-sense audit of continuation and completion auxiliaries.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("continuation-aux-"));
    suite
}

fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
        && a.lemmas
            .iter()
            .map(|l| &l.kind)
            .eq(j.lemma_kinds.as_ref().unwrap())
        && a.morphemes
            .iter()
            .map(|m| &m.form)
            .eq(j.morphemes.as_ref().unwrap())
        && a.morphemes
            .iter()
            .map(|m| &m.kind)
            .eq(j.morpheme_kinds.as_ref().unwrap())
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-continuation-aux-{}-{name}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-continuation-aux.json")],
            &path,
            "continuation-aux",
        )
        .unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

#[test]
fn continuation_sources_cover_every_sense_and_example_group() {
    let review: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/continuation-aux-sources.json")).unwrap();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let suite = suite();
    let sources = review["source_entries"].as_array().unwrap();
    assert_eq!(sources.len(), 7);
    let attestations = review["attestations"].as_array().unwrap();
    assert_eq!(attestations.len(), 44);
    let mut covered = std::collections::BTreeSet::new();
    for expected in sources {
        let id = expected["id"].as_str().unwrap();
        let entry = db.entry(id).unwrap().unwrap();
        // Full senses, notes, forms and examples survive the LMF fixture import.
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        for sense in &entry.senses {
            for (index, example) in sense.examples.iter().enumerate() {
                let rows: Vec<_> = attestations
                    .iter()
                    .filter(|a| {
                        a["entry"] == id && a["sense"] == sense.id && a["example_group"] == index
                    })
                    .collect();
                assert_eq!(rows.len(), 1, "{id}/{} example {index}", sense.id);
                let a = rows[0];
                let excerpt = a["excerpt"].as_str().unwrap();
                assert!(example.iter().any(|line| line.contains(excerpt)));
                assert_eq!(a["examples"], serde_json::to_value(example).unwrap());
                let case = suite.cases.iter().find(|c| a["case"] == c.id).unwrap();
                assert!(covered.insert(case.id.clone()));
                assert_eq!(case.surface, excerpt.replace(' ', ""));
                let word = Lemmatizer::new().analyze_word(&case.surface).unwrap();
                let path = word
                    .analyses
                    .iter()
                    .find(|p| matches(p, &case.judgments[0]))
                    .unwrap();
                let annotation = dictionary.annotate(&word).unwrap();
                let reading = annotation.assess(path);
                let slot = path
                    .lemmas
                    .iter()
                    .position(|l| {
                        l.kind == klem::LemmaKind::Auxiliary && l.text == entry.summary.headword
                    })
                    .unwrap();
                let evidence = reading.lemmas[slot]
                    .entries
                    .iter()
                    .find(|e| e.id == id)
                    .unwrap();
                assert_eq!(evidence.status, Compatibility::Compatible, "{}", case.id);
                assert!(evidence.conflicts.is_empty());
            }
        }
    }
    assert_eq!(covered.len(), 44);
}

#[test]
fn continuation_paths_preserve_roles_boundaries_and_unicode() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (70, 20));
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let word = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in &word.analyses {
            assert!(a.breakdown().is_some(), "{}: {a:?}", case.id);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            if matches(a, &case.judgments[0]) && a.lemmas.len() > 1 {
                assert!(a.rules.iter().any(|r| r == "auxiliary"));
            }
        }
    }
}

#[test]
fn continuation_dictionary_filters_and_cli_preserve_exact_groups() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
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
                .arg(&fixture.0)
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
        assert!(report.passed(), "{flag}: {:?}", report.violations);
    }
}

#[test]
fn continuation_dictionary_keeps_the_split_when_the_compound_is_missing() {
    let fixture = Fixture::new("missing");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let raw = Lemmatizer::new().analyze_word("번져나갔다").unwrap();
    let whole = raw
        .analyses
        .iter()
        .find(|a| a.lemmas.len() == 1 && a.lemmas[0].text == "번져나가다")
        .unwrap();
    assert!(db.lookup("번져나가다").unwrap().is_empty());
    for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
        let mut word = raw.clone();
        let mut annotation = dictionary.annotate(&word).unwrap();
        annotation.filter(&mut word, policy);
        assert!(!word.analyses.contains(whole));
        assert!(word.analyses.iter().any(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["번지다", "나가다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["어", "었", "다"])
        }));
    }
}
