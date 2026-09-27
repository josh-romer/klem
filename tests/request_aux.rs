//! COV-019q: restricted request auxiliary across quoted-command endings.
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
    suite.cases.retain(|c| c.id.starts_with("request-aux-"));
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
        let path =
            std::env::temp_dir().join(format!("klem-request-aux-{}-{name}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-request-aux.json")],
            &path,
            "request-aux",
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
fn request_sources_preserve_full_entries_and_exact_examples() {
    let review: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/request-aux-sources.json")).unwrap();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    let sources = review["source_entries"].as_array().unwrap();
    assert_eq!(sources.len(), 54);
    for expected in sources {
        let entry = db.entry(expected["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(entry).unwrap(), *expected);
    }
    let suite = suite();
    let attestations = review["attestations"].as_array().unwrap();
    assert_eq!(attestations.len(), 29);
    for a in attestations {
        let entry = db.entry(a["entry"].as_str().unwrap()).unwrap().unwrap();
        let sense = entry.senses.iter().find(|s| a["sense"] == s.id).unwrap();
        let group = &sense.examples[a["example_group"].as_u64().unwrap() as usize];
        let excerpt = a["excerpt"].as_str().unwrap();
        assert!(group.iter().any(|s| s.contains(excerpt)));
        assert_eq!(a["examples"], serde_json::to_value(group).unwrap());
        let case = suite.cases.iter().find(|c| a["case"] == c.id).unwrap();
        assert_eq!(case.surface, excerpt.replace(' ', ""));
    }
    let full = review["fully_sampled_entries"].as_array().unwrap();
    assert_eq!(full.len(), 4);
    let mut examples = 0;
    for id in full {
        let entry = db.entry(id.as_str().unwrap()).unwrap().unwrap();
        for sense in entry.senses {
            for i in 0..sense.examples.len() {
                assert_eq!(
                    attestations
                        .iter()
                        .filter(|a| {
                            a["entry"] == *id && a["sense"] == sense.id && a["example_group"] == i
                        })
                        .count(),
                    1
                );
                examples += 1;
            }
        }
    }
    assert_eq!(examples, 17);
}

#[test]
fn request_paths_preserve_roles_boundaries_and_unicode() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (72, 46));
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
fn request_dictionary_filters_and_cli_preserve_exact_groups() {
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
fn request_auxiliary_evidence_does_not_borrow_lexical_homonyms() {
    let fixture = Fixture::new("homonyms");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let word = Lemmatizer::new().analyze_word("도와달라며").unwrap();
    let case = suite()
        .cases
        .into_iter()
        .find(|c| c.id == "request-aux-family-으라며")
        .unwrap();
    let path = word
        .analyses
        .iter()
        .find(|a| matches(a, &case.judgments[0]))
        .unwrap();
    let annotation = dictionary.annotate(&word).unwrap();
    let evidence = annotation.assess(path);
    let entries = &evidence.lemmas[1].entries;
    assert_eq!(entries.len(), db.lookup("달다").unwrap().len());
    assert!(entries.len() > 1);
    for entry in entries {
        assert_eq!(
            entry.status,
            if entry.id == "krdict:62361" {
                Compatibility::Compatible
            } else {
                Compatibility::Incompatible
            }
        );
    }
    let mut lexical_only = annotation.clone();
    lexical_only
        .lemmas
        .iter_mut()
        .find(|m| m.lemma == path.lemmas[1])
        .unwrap()
        .entries
        .retain(|e| e.entry.id != "krdict:62361");
    assert_eq!(
        lexical_only.assess(path).status,
        Compatibility::Incompatible
    );
    let mut headword = word.clone();
    lexical_only
        .clone()
        .filter(&mut headword, DictionaryFilter::Headword);
    assert!(headword.analyses.contains(path));
    let mut compatible = word.clone();
    lexical_only.filter(&mut compatible, DictionaryFilter::Compatible);
    assert!(!compatible.analyses.contains(path));
    // The ordinary, unfiltered candidate result remains available independently
    // of dictionary entry presence and role compatibility.
    assert!(word.analyses.contains(path));
}
