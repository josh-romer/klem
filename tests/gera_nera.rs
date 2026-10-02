//! COV-021l: modern direct commands, original misses and local owners.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-gera-nera-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-gera-nera.json")],
            &path,
            "gera-nera",
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
fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/gera-nera-sources.json")).unwrap()
}
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("gera-nera-"));
    s
}
fn path<'a>(word: &'a WordAnalysis, head: &str, forms: &[&str]) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == head
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        })
        .unwrap_or_else(|| panic!("{}: {head} + {forms:?}", word.normalized))
}

#[test]
fn modern_commands_recover_every_native_miss_and_keep_all_original_hypotheses() {
    let engine = Lemmatizer::new();
    let source = sources();
    assert_eq!(source["native_forms"].as_array().unwrap().len(), 46);
    assert_eq!(source["cases"].as_array().unwrap().len(), 88);
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (84, 8));
    for (surface, before) in source["before_words"].as_object().unwrap() {
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        let original: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
        let mut remaining = word.analyses.iter();
        for old in &original.analyses {
            assert!(
                remaining.any(|new| new == old),
                "{surface}: original hypothesis, metadata or relative order changed: {old:?}"
            );
        }
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in &word.analyses {
            assert!(a.breakdown().is_some(), "{surface}: {a:?}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            if a.morphemes
                .iter()
                .any(|m| matches!(m.form.as_str(), "거라" | "너라"))
            {
                assert!(a.rules.iter().any(|r| r == "ending.direct_command"));
            }
        }
    }
    for n in source["native_forms"].as_array().unwrap() {
        let word = engine.analyze_word(n["written"].as_str().unwrap()).unwrap();
        let ending = if word.normalized.ends_with("너라") {
            "너라"
        } else {
            "거라"
        };
        let a = path(&word, n["headword"].as_str().unwrap(), &[ending]);
        assert!(!a.rules.iter().any(|r| r == "deletion.rieul"));
    }
}

#[test]
fn command_sources_keep_complete_entries_and_distinct_lexical_auxiliary_homonyms() {
    let source = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&db, 4096);
    assert_eq!(source["source_entries"].as_array().unwrap().len(), 101);
    for e in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    for n in source["native_forms"].as_array().unwrap() {
        let word = engine.analyze_word(n["written"].as_str().unwrap()).unwrap();
        let ending = if word.normalized.ends_with("너라") {
            "너라"
        } else {
            "거라"
        };
        let a = path(&word, n["headword"].as_str().unwrap(), &[ending]);
        let annotation = session.annotate(&word).unwrap();
        let assessment = annotation.assess(a);
        let entry = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == n["entry_id"].as_str().unwrap())
            .unwrap();
        assert_eq!(
            entry.status,
            if n["pos"] == "보조 동사" {
                Compatibility::Unknown
            } else {
                Compatibility::Compatible
            },
            "{n}"
        );
        assert!(entry.conflicts.is_empty());
    }
}

#[test]
fn commands_leave_unreviewed_prefinals_wishes_and_existential_senses_unknown() {
    let fixture = Fixture::new("unknown");
    let db = fixture.open();
    let mut session = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (surface, head, forms) in [
        ("가시거라", "가다", vec!["시", "거라"]),
        ("먹었거라", "먹다", vec!["었", "거라"]),
        ("가겠거라", "가다", vec!["겠", "거라"]),
        ("가더거라", "가다", vec!["더", "거라"]),
        ("예쁘거라", "예쁘다", vec!["거라"]),
        ("행복하거라", "행복하다", vec!["거라"]),
        ("싶거라", "싶다", vec!["거라"]),
    ] {
        let w = engine.analyze_word(surface).unwrap();
        let a = path(&w, head, &forms);
        let annotation = session.annotate(&w).unwrap();
        let assessment = annotation.assess(a);
        assert_eq!(assessment.status, Compatibility::Unknown, "{surface}");
        assert!(
            assessment.lemmas[0]
                .entries
                .iter()
                .all(|e| e.conflicts.is_empty())
        );
    }
    let w = engine.analyze_word("있거라").unwrap();
    let a = path(&w, "있다", &["거라"]);
    let annotation = session.annotate(&w).unwrap();
    let assessment = annotation.assess(a);
    let owner = &assessment.lemmas[0];
    for e in &owner.entries {
        let entry = db.entry(&e.id).unwrap().unwrap();
        assert_eq!(
            e.status,
            if entry.summary.pos == "동사" {
                Compatibility::Compatible
            } else {
                Compatibility::Unknown
            }
        );
    }
}

#[test]
fn commands_preserve_local_auxiliary_owners_and_all_cli_filter_modes() {
    let fixture = Fixture::new("parity");
    let db = fixture.open();
    let mut session = DictionarySession::new(&db, 4096);
    let mut uncached = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let report = validity::evaluate_with(&suite(), |surface| {
            let mut w = engine.analyze_word(surface).unwrap();
            let mut a = session.annotate(&w).unwrap();
            assert_eq!(a, uncached.annotate(&w).unwrap());
            assert!(session.cache_bytes() <= 4096);
            assert_eq!(uncached.cache_bytes(), 0);
            if let Some(filter) = filter {
                a.filter(&mut w, filter);
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", surface, "--dictionary"]).arg(&fixture.0);
            if let Some(flag) = flag {
                cmd.arg(flag);
            }
            let output = cmd.output().unwrap();
            assert!(output.status.success(), "{:?}", output.stderr);
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(actual.clone()).unwrap(),
                w
            );
            assert_eq!(actual["dictionary"], serde_json::to_value(&a).unwrap());
            Ok(w)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
    }
}
