//! COV-013/019s: complete 가지다/갖다 source review, preserving lexical homonyms.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("carry-aux-"));
    s
}
fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
        && a.lemmas
            .iter()
            .map(|l| l.kind)
            .eq(j.lemma_kinds.as_ref().unwrap().iter().copied())
        && a.morphemes
            .iter()
            .map(|m| &m.form)
            .eq(j.morphemes.as_ref().unwrap().iter())
        && a.morphemes
            .iter()
            .map(|m| m.kind)
            .eq(j.morpheme_kinds.as_ref().unwrap().iter().copied())
        && j.required_rules
            .as_ref()
            .is_none_or(|r| r.iter().all(|r| a.rules.contains(r)))
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let p =
            std::env::temp_dir().join(format!("klem-carry-aux-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-carry-aux.json")],
            &p,
            "carry-aux",
        )
        .unwrap();
        Self(p)
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
fn carry_sources_keep_both_full_senses_every_group_and_lexical_homonyms() {
    let m: Value = serde_json::from_str(include_str!("fixtures/carry-aux-sources.json")).unwrap();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let sources = m["source_entries"].as_array().unwrap();
    assert_eq!(sources.len(), 4);
    for e in sources {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    let s = suite();
    let attestations = m["attestations"].as_array().unwrap();
    assert_eq!(attestations.len(), 16);
    let mut covered = std::collections::BTreeSet::new();
    for entry in &sources[..2] {
        let senses = entry["senses"].as_array().unwrap();
        assert_eq!(senses.len(), 2);
        for sense in senses {
            let examples = sense["examples"].as_array().unwrap();
            assert_eq!(examples.len(), 4);
            for (i, group) in examples.iter().enumerate() {
                let rows: Vec<_> = attestations
                    .iter()
                    .filter(|r| {
                        r["entry"] == entry["id"]
                            && r["sense"] == sense["id"]
                            && r["example_group"] == i
                    })
                    .collect();
                assert_eq!(rows.len(), 1);
                let r = rows[0];
                assert_eq!(r["examples"], *group);
                let excerpt = r["excerpt"].as_str().unwrap();
                assert!(
                    group
                        .as_array()
                        .unwrap()
                        .iter()
                        .any(|l| l.as_str().unwrap().contains(excerpt))
                );
                let c = s.cases.iter().find(|c| c.id == r["case"]).unwrap();
                assert!(covered.insert(c.id.clone()));
                assert_eq!(c.surface, excerpt.replace(' ', ""));
                let word = Lemmatizer::new().analyze_word(&c.surface).unwrap();
                let a = word
                    .analyses
                    .iter()
                    .find(|a| matches(a, &c.judgments[0]))
                    .unwrap();
                let annotation = dict.annotate(&word).unwrap();
                let assessment = annotation.assess(a);
                let e = assessment.lemmas[1]
                    .entries
                    .iter()
                    .find(|e| e.id == entry["id"].as_str().unwrap())
                    .unwrap();
                assert_eq!(e.status, Compatibility::Compatible, "{}", c.id);
                assert!(e.conflicts.is_empty());
            }
        }
    }
    assert_eq!(covered.len(), 16);
}
#[test]
fn carry_paths_preserve_unicode_order_roles_and_restricted_auxiliary_forms() {
    let s = suite();
    assert_eq!(s.cases.len(), 30);
    let r = validity::evaluate(&s).unwrap();
    assert!(r.passed(), "{:?}", r.violations);
    assert_eq!((r.required_total, r.forbidden_total), (22, 8));
    let engine = Lemmatizer::new();
    for c in s.cases {
        let word = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in &word.analyses {
            let order = a.breakdown().unwrap();
            assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    // The existing outer particle does not become an auxiliary inflection.
    for (word, head) in [("먹어가지고요", "가지다"), ("먹어갖고요", "갖다")] {
        let a = engine.analyze_word(word).unwrap();
        assert!(a.analyses.iter().any(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).eq(["먹다", head])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["어", "고", "요"])
        }));
    }
}
#[test]
fn carry_filters_cached_dictionary_and_cli_preserve_every_required_role() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let mut uncached = DictionarySession::new(&db, 0);
    let mut cached = DictionarySession::new(&db, 1 << 20);
    let s = suite();
    for c in &s.cases {
        let word = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            uncached.annotate(&word).unwrap(),
            cached.annotate(&word).unwrap()
        );
        for (flag, policy) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut filtered = word.clone();
            let mut annotation = cached.annotate(&filtered).unwrap();
            if let Some(p) = policy {
                annotation.filter(&mut filtered, p);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", &c.surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(f) = flag {
                command.arg(f);
            }
            let out = command.output().unwrap();
            assert!(
                out.status.success(),
                "{}: {}",
                c.id,
                String::from_utf8_lossy(&out.stderr)
            );
            let cli: Value = serde_json::from_slice(&out.stdout).unwrap();
            let mut bare = cli.clone();
            bare.as_object_mut().unwrap().remove("dictionary");
            let actual: WordAnalysis = serde_json::from_value(bare).unwrap();
            assert_eq!(actual, filtered, "{} {flag:?}", c.id);
            assert_eq!(cli["dictionary"], serde_json::to_value(annotation).unwrap());
            for j in &c.judgments {
                assert_eq!(
                    filtered.analyses.iter().any(|a| matches(a, j)),
                    j.verdict == validity::Verdict::Required,
                    "{} {flag:?}",
                    c.id
                );
            }
        }
    }
}
