//! COV-019u: native negative sources and lexical class ownership.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    AttachmentRule, Compatibility, Dictionary, DictionaryFilter, DictionarySession,
    SqliteDictionary, import_krdict, pos_compatibility,
};
use klem::{Analysis, LemmaKind, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let p = std::env::temp_dir().join(format!(
            "klem-negative-classes-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-negative-classes.json")],
            &p,
            "negative-classes",
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
fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/negative-class-sources.json")).unwrap()
}
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("negative-class-"));
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
}

#[test]
fn negative_sources_preserve_all_six_entries_seven_senses_and_74_groups() {
    let m = sources();
    let f = Fixture::new("sources");
    let db = f.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let suite = suite();
    assert_eq!(suite.cases.len(), 74);
    let mut groups = 0;
    let mut senses = 0;
    for e in m["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
        for sense in e["senses"].as_array().unwrap() {
            senses += 1;
            for (i, example) in sense["examples"].as_array().unwrap().iter().enumerate() {
                groups += 1;
                let rows: Vec<_> = m["attestations"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .filter(|r| {
                        r["entry"] == e["id"]
                            && r["sense"] == sense["id"]
                            && r["example_group"] == i
                    })
                    .collect();
                assert_eq!(rows.len(), 1);
                let r = rows[0];
                assert_eq!(r["examples"], *example);
                let excerpt = r["excerpt"].as_str().unwrap();
                assert!(
                    example
                        .as_array()
                        .unwrap()
                        .iter()
                        .any(|line| line.as_str().unwrap().contains(excerpt))
                );
                let c = suite.cases.iter().find(|c| c.id == r["case"]).unwrap();
                assert_eq!(c.surface, excerpt.replace(' ', ""));
                let word = Lemmatizer::new().analyze_word(&c.surface).unwrap();
                let a = word
                    .analyses
                    .iter()
                    .find(|a| matches(a, &c.judgments[0]))
                    .unwrap();
                let assessment = dictionary.annotate(&word).unwrap().assess(a);
                let source = assessment.lemmas[1]
                    .entries
                    .iter()
                    .find(|v| v.id == e["id"].as_str().unwrap())
                    .unwrap();
                assert_eq!(
                    source.status,
                    Compatibility::Compatible,
                    "{} {:?}",
                    c.id,
                    source
                );
            }
        }
    }
    assert_eq!((senses, groups), (7, 74));
}

#[test]
fn negative_raw_unicode_cached_dictionary_and_cli_keep_native_paths() {
    let suite = suite();
    let r = validity::evaluate(&suite).unwrap();
    assert!(r.passed());
    assert_eq!((r.required_total, r.forbidden_total), (74, 0));
    let f = Fixture::new("cli");
    let db = f.open();
    let mut cached = DictionarySession::new(&db, 1 << 20);
    let mut uncached = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    for c in &suite.cases {
        let word = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in &word.analyses {
            assert_eq!(
                a.breakdown().unwrap().len(),
                a.lemmas.len() + a.morphemes.len()
            );
        }
        let annotation = cached.annotate(&word).unwrap();
        assert_eq!(annotation, uncached.annotate(&word).unwrap());
        for (flag, policy) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut filtered = word.clone();
            let mut ann = annotation.clone();
            if let Some(p) = policy {
                ann.filter(&mut filtered, p);
            }
            assert!(
                filtered
                    .analyses
                    .iter()
                    .any(|a| matches(a, &c.judgments[0])),
                "{} {flag:?}",
                c.id
            );
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", &c.surface, "--dictionary"]).arg(&f.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let mut cli: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                cli.as_object_mut().unwrap().remove("dictionary").unwrap(),
                serde_json::to_value(ann).unwrap()
            );
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(cli).unwrap(),
                filtered
            );
        }
    }
}

#[test]
fn negative_entry_conflicts_keep_homonyms_chains_and_owner_resets() {
    let f = Fixture::new("classes");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    for (surface, heads, rejected, rule, connector) in [
        (
            "개운하지않다",
            vec!["개운하다", "않다"],
            Some("보조 동사"),
            AttachmentRule::NegativeLexicalClass,
            "지",
        ),
        (
            "가지않다",
            vec!["가다", "않다"],
            Some("보조 형용사"),
            AttachmentRule::NegativeLexicalClass,
            "지",
        ),
        (
            "예쁘지못했다",
            vec!["예쁘다", "못하다"],
            Some("보조 동사"),
            AttachmentRule::NegativeLexicalClass,
            "지",
        ),
        (
            "먹지아니했다",
            vec!["먹다", "아니하다"],
            Some("보조 형용사"),
            AttachmentRule::NegativeLexicalClass,
            "지",
        ),
        (
            "예쁘지않지못했다",
            vec!["예쁘다", "않다", "못하다"],
            Some("보조 동사"),
            AttachmentRule::NegativeLexicalClass,
            "지",
        ),
        (
            "크지않다",
            vec!["크다", "않다"],
            None,
            AttachmentRule::NegativeLexicalClass,
            "지",
        ),
        (
            "먹고싶지않다",
            vec!["먹다", "싶다", "않다"],
            Some("보조 동사"),
            AttachmentRule::AuxiliaryClass,
            "지",
        ),
        (
            "예쁘지않아보지못했다",
            vec!["예쁘다", "않다", "보다", "못하다"],
            Some("보조 형용사"),
            AttachmentRule::AuxiliaryClass,
            "지",
        ),
        (
            "학생답지않다",
            vec!["학생", "않다"],
            Some("보조 동사"),
            AttachmentRule::AuxiliaryClass,
            "지",
        ),
        (
            "학생이지않다",
            vec!["학생", "이다", "않다"],
            None,
            AttachmentRule::NegativeLexicalClass,
            "지",
        ),
        (
            "견디다못한",
            vec!["견디다", "못하다"],
            Some("보조 동사"),
            AttachmentRule::AuxiliaryClass,
            "다",
        ),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(heads.iter().copied())
                    && a.lemmas.last().unwrap().kind == LemmaKind::Auxiliary
            })
            .unwrap();
        let ann = dict.annotate(&word).unwrap();
        let assessment = ann.assess(a);
        let last = assessment.lemmas.last().unwrap();
        for e in &last.entries {
            let source = db.entry(&e.id).unwrap().unwrap();
            if !matches!(source.summary.pos.as_str(), "보조 동사" | "보조 형용사") {
                continue;
            }
            if rejected == Some(source.summary.pos.as_str()) {
                assert_eq!(e.status, Compatibility::Incompatible, "{surface} {e:?}");
                let conflict = e.conflicts.iter().find(|c| c.rule == rule).unwrap();
                assert_eq!(
                    a.morphemes[conflict.morpheme_index.unwrap()].form,
                    connector
                );
            } else {
                assert_eq!(e.status, Compatibility::Compatible, "{surface} {e:?}");
                assert!(
                    !e.conflicts
                        .iter()
                        .any(|c| c.rule == AttachmentRule::NegativeLexicalClass)
                );
            }
        }
        assert_eq!(assessment.status, Compatibility::Compatible, "{surface}");
    }
}

#[test]
fn negative_unknown_classes_and_standalone_owners_do_not_borrow_pos() {
    let f = Fixture::new("unknown");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let word = Lemmatizer::new().analyze_word("개운하지않다").unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["개운하다", "않다"])
        })
        .unwrap();
    let mut annotation = dict.annotate(&word).unwrap();
    for entry in &mut annotation
        .lemmas
        .iter_mut()
        .find(|m| m.lemma == a.lemmas[0])
        .unwrap()
        .entries
    {
        entry.entry.pos = "unreviewed-provider-class".into();
        entry.pos_compatibility = pos_compatibility(&a.lemmas[0], &entry.entry);
    }
    let assessed = annotation.assess(a);
    assert_eq!(assessed.status, Compatibility::Unknown);
    assert!(assessed.lemmas[1].entries.iter().all(|e| {
        !e.conflicts
            .iter()
            .any(|c| c.rule == AttachmentRule::NegativeLexicalClass)
    }));
    let mut filtered = word.clone();
    annotation.filter(&mut filtered, DictionaryFilter::Compatible);
    assert!(filtered.analyses.contains(a));
    // An additional unknown homonym prevents a categorical class exclusion,
    // even when a known adjective entry is also present.
    let mut mixed = dict.annotate(&word).unwrap();
    let slot = mixed
        .lemmas
        .iter_mut()
        .find(|m| m.lemma == a.lemmas[0])
        .unwrap();
    let mut unknown = slot.entries[0].clone();
    unknown.entry.id = "provider:unknown-homonym".into();
    unknown.entry.pos = "unreviewed-provider-class".into();
    unknown.pos_compatibility = Compatibility::Unknown;
    slot.entries.push(unknown);
    assert!(mixed.assess(a).lemmas[1].entries.iter().all(|e| {
        !e.conflicts
            .iter()
            .any(|c| c.rule == AttachmentRule::NegativeLexicalClass)
    }));
    for surface in ["않다", "아니하다", "못하다", "않지못했다"] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let ann = dict.annotate(&word).unwrap();
        for a in &word.analyses {
            assert!(
                ann.assess(a)
                    .lemmas
                    .iter()
                    .flat_map(|l| &l.entries)
                    .flat_map(|e| &e.conflicts)
                    .all(|c| c.rule != AttachmentRule::NegativeLexicalClass)
            );
        }
    }
}
