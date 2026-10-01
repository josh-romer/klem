//! COV-022k: prefixed bases and competing compound/suffix noun readings.
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
    s.cases.retain(|c| c.id.starts_with("noun-internal-"));
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
fn feature<'a>(v: &'a Value, name: &str) -> Option<&'a str> {
    arr(&v["feat"])
        .into_iter()
        .find(|f| f["att"] == name)
        .and_then(|f| f["val"].as_str())
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
fn internal_sources_retain_every_group_and_competing_boundary() {
    let m: Value =
        serde_json::from_str(include_str!("fixtures/noun-internal-sources.json")).unwrap();
    let f: Value =
        serde_json::from_str(include_str!("fixtures/krdict-noun-internal.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 27);
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
    assert_eq!((groups, targets), (44, 4));
    let bagi = entries.iter().find(|e| e["val"] == "92109").unwrap();
    assert_eq!(arr(&bagi["Sense"]).len(), 2);
    assert!(
        arr(&bagi["Sense"])[0]["SenseExample"]
            .to_string()
            .contains("점박이")
    );
    assert_eq!(
        entries
            .iter()
            .filter(|e| feature(&e["Lemma"], "writtenForm") == Some("왕-"))
            .count(),
        2
    );
    assert!(
        arr(&m["corpus_training_search"])
            .iter()
            .all(|c| c["matching_tokens"] == 0)
    );
}
#[test]
fn internal_paths_preserve_unicode_prefix_and_shared_base_ownership() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (68, 12));
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
            "왕눈이들이었다",
            "derivation.nominal.prefix_wang",
            vec![M(0), L(0), M(1), M(2), L(1), M(3), M(4)],
        ),
        (
            "왕눈이들이었다",
            "suffix.nominal.i",
            vec![L(0), M(0), M(1), L(1), M(2), M(3)],
        ),
        (
            "점박이들이었다",
            "derivation.nominal.compound",
            vec![L(0), L(1), M(0), M(1), L(2), M(2), M(3)],
        ),
        (
            "점박이들이었다",
            "suffix.nominal.bagi",
            vec![L(0), M(0), M(1), L(1), M(2), M(3)],
        ),
    ] {
        let a = engine.analyze_word(word).unwrap();
        let p = a
            .analyses
            .iter()
            .find(|p| {
                p.rules.iter().any(|r| r == rule)
                    && p.lemmas
                        .last()
                        .is_some_and(|l| l.kind == klem::LemmaKind::Copula)
                    && (rule != "suffix.nominal.i" || p.lemmas[0].kind == klem::LemmaKind::Root)
            })
            .unwrap();
        assert_eq!(p.breakdown().unwrap(), wanted);
    }
    for word in ["왕눈이를", "왕눈이들쯤에는", "왕눈이였다"] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|p| p.lemmas.iter().all(|l| l.text != "왕"))
        );
    }
    // Prefix stripping and 박이 separation are finite, not arbitrary tail rules.
    for word in [
        "왕눈",
        "왕귀이",
        "왕눈이님",
        "점박이적",
        "금니박이",
        "왕눈이다이",
        "점박어이",
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|p| p.rules.iter().all(|r| ![
                    "derivation.nominal.prefix_wang",
                    "suffix.nominal.bagi"
                ]
                .contains(&r.as_str()))),
            "{word}"
        );
    }
}
#[test]
fn external_prefix_and_bagi_shapes_require_correct_provenance() {
    let e = Lemmatizer::new();
    let a = e.analyze_word("왕눈이").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| {
            p.rules
                .iter()
                .any(|r| r == "derivation.nominal.prefix_wang")
        })
        .unwrap();
    let mut wrong = p.clone();
    wrong
        .rules
        .retain(|r| r != "derivation.nominal.prefix_wang");
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.morphemes[0].kind = klem::MorphemeKind::Suffix;
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.lemmas[0].text = "왕".into();
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.morphemes.push(wrong.morphemes[0].clone());
    assert!(wrong.breakdown().is_none());
    let a = e.analyze_word("점박이").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| p.rules.iter().any(|r| r == "suffix.nominal.bagi"))
        .unwrap();
    let mut wrong = p.clone();
    wrong.rules.push("suffix.nominal.i".into());
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.lemmas[0].text = "금니".into();
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.morphemes[0].form = "이".into();
    assert!(wrong.breakdown().is_none());
    assert_eq!(
        serde_json::to_string(&klem::MorphemeKind::Prefix).unwrap(),
        "\"prefix\""
    );
}
struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn dictionary(tag: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-noun-internal-{tag}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-internal.json")],
        &path,
        "noun-internal",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), db)
}
#[test]
fn internal_homonyms_filters_and_cli_exports_preserve_every_alternative() {
    let (cleanup, db) = dictionary("cli");
    assert_eq!(db.lookup("눈").unwrap().len(), 5);
    assert_eq!(db.lookup("점").unwrap().len(), 3);
    assert_eq!(db.lookup("왕-").unwrap().len(), 2);
    assert!(db.lookup("왕눈").unwrap().is_empty());
    assert_eq!(db.entry("krdict:92109").unwrap().unwrap().senses.len(), 2);
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
                if path
                    .rules
                    .iter()
                    .any(|r| r == "derivation.nominal.prefix_wang")
                {
                    assert_eq!(reading.lemmas[0].entries.len(), 5);
                    assert!(
                        reading.lemmas[0]
                            .entries
                            .iter()
                            .all(|e| e.status == klem::dictionary::Compatibility::Compatible)
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
fn internal_noun_spacing_preserves_prefix_and_compound_roles() {
    let (_cleanup, db) = dictionary("spacing");
    let mut session = klem::Session::new(Lemmatizer::new().into(), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    for noun in ["왕눈이", "점박이"] {
        for (tail, spaced, allowed) in [("먹는다", "먹는다", true), (noun, noun, false)] {
            let surface = format!("{noun}를{tail}");
            let wanted = format!("{noun}를 {spaced}");
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
                if noun == "왕눈이" {
                    assert!(forms.iter().any(|p| {
                        p.rules
                            .iter()
                            .any(|r| r == "derivation.nominal.prefix_wang")
                    }));
                } else {
                    assert!(
                        forms
                            .iter()
                            .any(|p| p.rules.iter().any(|r| r == "suffix.nominal.bagi"))
                    );
                    assert!(
                        forms
                            .iter()
                            .any(|p| p.rules.iter().any(|r| r == "derivation.nominal.compound"))
                    );
                }
            }
        }
    }
    assert!(dictionary.cache_bytes() <= 4096);
}
