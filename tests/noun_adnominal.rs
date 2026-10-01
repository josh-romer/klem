//! COV-022l: individual adnominal noun and competing bound-noun formations.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("noun-adnominal-"));
    s
}
fn arr(v: &Value) -> Vec<&Value> {
    if let Some(a) = v.as_array() {
        a.iter().collect()
    } else if v.is_object() {
        vec![v]
    } else {
        vec![]
    }
}
fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
        && j.lemma_kinds
            .as_ref()
            .is_none_or(|k| a.lemmas.iter().map(|l| l.kind).eq(k.iter().copied()))
        && j.morphemes
            .as_ref()
            .is_none_or(|m| a.morphemes.iter().map(|x| &x.form).eq(m.iter()))
        && j.morpheme_kinds
            .as_ref()
            .is_none_or(|k| a.morphemes.iter().map(|m| m.kind).eq(k.iter().copied()))
        && j.required_rules
            .as_ref()
            .is_none_or(|r| r.iter().all(|r| a.rules.contains(r)))
}
#[test]
fn adnominal_sources_preserve_conflicts_and_complete_native_groups() {
    let m: Value =
        serde_json::from_str(include_str!("fixtures/noun-adnominal-sources.json")).unwrap();
    let f: Value =
        serde_json::from_str(include_str!("fixtures/krdict-noun-adnominal.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 28);
    let suffix = entries.iter().find(|e| e["val"] == "88924").unwrap();
    assert_eq!(arr(&suffix["Sense"]).len(), 3);
    let mut groups = 0;
    let mut targets = 0;
    for sense in arr(&suffix["Sense"]) {
        for (i, g) in arr(&sense["SenseExample"]).iter().enumerate() {
            groups += 1;
            let recorded = arr(&m["source_groups"])
                .into_iter()
                .find(|r| r["sense_id"] == sense["val"] && r["example_group"] == i + 1)
                .unwrap();
            assert_eq!(&recorded["native_group"], *g);
            for t in arr(&recorded["targets"]) {
                targets += 1;
                assert_eq!(sense["val"], "3");
                assert!(suite().cases.iter().any(|c| c.id == t["case_id"]));
            }
        }
    }
    assert_eq!((groups, targets), (44, 5));
    let dungi = entries.iter().find(|e| e["val"] == "72336").unwrap();
    assert_eq!(arr(&dungi["Sense"]).len(), 1);
    assert_eq!(arr(&arr(&dungi["Sense"])[0]["SenseExample"]).len(), 5);
    assert!(
        arr(&m["primary_consultations"])
            .iter()
            .any(|c| c["answer_date"] == "2023-07-26")
    );
    assert!(
        arr(&m["primary_consultations"])
            .iter()
            .any(|c| c["answer_date"] == "2026-09-19")
    );
    assert!(
        arr(&m["corpus_training_search"])
            .iter()
            .all(|c| c["matching_tokens"] == 0)
    );
    assert!(entries.iter().any(|e| e["val"] == "71124"));
}
#[test]
fn adnominal_paths_preserve_unicode_and_noun_ownership() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (85, 15));
    let engine = Lemmatizer::new();
    for c in suite().cases {
        let a = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            a,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(a.analyses.iter().any(|p| p.unchanged));
        for p in a.analyses {
            assert!(p.breakdown().is_some(), "{}: {p:?}", c.surface);
            assert!(p.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    use klem::breakdown::Component::{Lemma as L, Morpheme as M};
    for (word, rule, wanted) in [
        (
            "못난이들이었다",
            "derivation.nominal.adnominal",
            vec![L(0), M(0), M(1), M(2), L(1), M(3), M(4)],
        ),
        (
            "못난이들이었다",
            "derivation.nominal.bound_i",
            vec![L(0), M(0), L(1), M(1), L(2), M(2), M(3)],
        ),
        (
            "못난이를",
            "derivation.nominal.bound_i",
            vec![L(0), M(0), L(1), M(1)],
        ),
        (
            "흰둥이들이었다",
            "suffix.nominal.dungi",
            vec![L(0), M(0), M(1), M(2), L(1), M(3), M(4)],
        ),
    ] {
        let a = engine.analyze_word(word).unwrap();
        let p = a
            .analyses
            .iter()
            .find(|p| {
                p.rules.iter().any(|r| r == rule)
                    && p.morphemes.last().is_some_and(|m| {
                        m.form == if word == "못난이를" { "를" } else { "다" }
                    })
            })
            .unwrap();
        assert_eq!(p.breakdown().unwrap(), wanted);
    }
    for word in [
        "못난이님",
        "흰둥이적",
        "검둥이",
        "못나는이",
        "흰둥이였다이",
        "희었둥이",
        "못났이",
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|p| p.rules.iter().all(|r| ![
                    "derivation.nominal.adnominal",
                    "derivation.nominal.bound_i",
                    "suffix.nominal.dungi"
                ]
                .contains(&r.as_str()))),
            "{word}"
        );
    }
}
#[test]
fn external_adnominal_shapes_require_individual_provenance() {
    let e = Lemmatizer::new();
    for (word, rule) in [
        ("못난이", "derivation.nominal.adnominal"),
        ("흰둥이", "suffix.nominal.dungi"),
        ("못난이", "derivation.nominal.bound_i"),
    ] {
        let a = e.analyze_word(word).unwrap();
        let p = a
            .analyses
            .iter()
            .find(|p| p.rules.iter().any(|r| r == rule))
            .unwrap();
        let mut wrong = p.clone();
        wrong.morphemes[0].form = "는".into();
        assert!(wrong.breakdown().is_none());
        let mut wrong = p.clone();
        wrong.morphemes[0].kind = klem::MorphemeKind::Prefinal;
        assert!(wrong.breakdown().is_none());
        let mut wrong = p.clone();
        wrong.lemmas[0].text = "먹다".into();
        assert!(wrong.breakdown().is_none());
        let mut wrong = p.clone();
        wrong.rules.push("derivation.nominal.compound".into());
        assert!(wrong.breakdown().is_none());
    }
    let a = e.analyze_word("흰둥이").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| p.rules.iter().any(|r| r == "suffix.nominal.dungi"))
        .unwrap();
    let mut wrong = p.clone();
    wrong.rules.retain(|r| r != "derivation.nominal.adnominal");
    assert!(wrong.breakdown().is_none());
    let a = e.analyze_word("못난이").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| p.rules.iter().any(|r| r == "derivation.nominal.bound_i"))
        .unwrap();
    let mut wrong = p.clone();
    wrong.lemmas[1].text = "사람".into();
    assert!(wrong.breakdown().is_none());
}
struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn dictionary(tag: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-noun-adnominal-{tag}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-adnominal.json")],
        &path,
        "noun-adnominal",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), db)
}
#[test]
fn adnominal_filters_cli_and_bound_noun_roles_preserve_all_paths() {
    let (cleanup, db) = dictionary("cli");
    assert_eq!(db.lookup("이").unwrap().len(), 9);
    assert!(db.lookup("못난").unwrap().is_empty());
    assert!(db.lookup("흰둥").unwrap().is_empty());
    assert_eq!(db.entry("krdict:72336").unwrap().unwrap().senses.len(), 1);
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let cases = suite().cases;
    let text = cases
        .iter()
        .map(|c| c.surface.as_str())
        .collect::<Vec<_>>()
        .join(" ");
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let mut expected = vec![];
        for c in &cases {
            let mut a = engine.analyze_word(&c.surface).unwrap();
            let mut annotation = dictionary.annotate(&a).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut a, filter);
            }
            for (path, reading) in a.analyses.iter().zip(&annotation.readings) {
                assert_eq!(
                    reading
                        .lemmas
                        .iter()
                        .map(|l| l.lemma_index)
                        .collect::<Vec<_>>(),
                    (0..path.lemmas.len()).collect::<Vec<_>>(),
                    "{} {flag:?}: {path:?}",
                    c.id
                );
                if path.rules.iter().any(|r| r == "derivation.nominal.bound_i") {
                    let bound = &reading.lemmas[1];
                    assert_eq!(bound.entries.len(), 9);
                    assert_eq!(
                        bound
                            .entries
                            .iter()
                            .filter(|e| e.status == klem::dictionary::Compatibility::Compatible)
                            .map(|e| e.id.as_str())
                            .collect::<Vec<_>>(),
                        vec!["krdict:71124"]
                    );
                    assert!(
                        bound
                            .entries
                            .iter()
                            .filter(|e| e.id != "krdict:71124")
                            .all(
                                |e| e.status == klem::dictionary::Compatibility::Incompatible
                                    && e.conflicts
                                        .iter()
                                        .any(|c| c.rule
                                            == klem::dictionary::AttachmentRule::LexicalRole)
                            )
                    );
                }
            }
            for j in &c.judgments {
                assert_eq!(
                    a.analyses.iter().any(|a| matches(a, j)),
                    matches!(j.verdict, validity::Verdict::Required)
                        && (filter.is_none()
                            || j.lemmas.iter().all(|l| !db.lookup(l).unwrap().is_empty())),
                    "{} {flag:?}",
                    c.id
                );
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"])
                .arg(&cleanup.0);
            if let Some(flag) = flag {
                cmd.arg(flag);
            }
            let output = cmd.output().unwrap();
            assert!(output.status.success());
            let mut actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(&annotation).unwrap()
            );
            assert_eq!(actual, serde_json::to_value(&a).unwrap());
            expected.push((actual, serde_json::to_value(annotation).unwrap()));
        }
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
        cmd.args(["text", "-", "--dictionary"]).arg(&cleanup.0);
        if let Some(flag) = flag {
            cmd.arg(flag);
        }
        let mut child = cmd
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(text.as_bytes())
            .unwrap();
        let output = child.wait_with_output().unwrap();
        assert!(output.status.success());
        let records: Vec<Value> = String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .filter(|r: &Value| !r["analysis"].is_null())
            .collect();
        assert_eq!(records.len(), cases.len());
        for (r, (a, d)) in records.iter().zip(expected) {
            assert_eq!(r["analysis"], a);
            assert_eq!(r["dictionary"], d);
        }
        assert!(dictionary.cache_bytes() <= 4096);
    }
}
#[test]
fn adnominal_nouns_do_not_become_spacing_predicates() {
    let (_cleanup, db) = dictionary("spacing");
    let mut session = klem::Session::new(Lemmatizer::new().into(), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    for noun in ["못난이", "흰둥이"] {
        for (tail, allowed) in [("먹는다", true), (noun, false)] {
            let surface = format!("{noun}를{tail}");
            let wanted = format!("{noun}를 {tail}");
            let r = klem::spacing::suggest(
                &mut session,
                &mut dictionary,
                &surface,
                0,
                Default::default(),
            )
            .unwrap();
            assert_eq!(r.alternatives.iter().any(|a| a.spaced == wanted), allowed);
            if allowed {
                let a = r.alternatives.iter().find(|a| a.spaced == wanted).unwrap();
                assert!(
                    a.records
                        .iter()
                        .all(|r| r.breakdowns.iter().all(Option::is_some))
                );
                let forms = &a.records[0].record.analysis.as_ref().unwrap().analyses;
                assert!(
                    forms
                        .iter()
                        .any(|p| p.rules.iter().any(|r| r == "derivation.nominal.adnominal"))
                );
                if noun == "못난이" {
                    assert!(
                        forms
                            .iter()
                            .any(|p| p.rules.iter().any(|r| r == "derivation.nominal.bound_i"))
                    );
                }
            }
        }
    }
    assert!(dictionary.cache_bytes() <= 4096);
}
