//! Partial COV-022l: primary noun/root bases and independently sourced prefix.
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
    s.cases.retain(|c| c.id.starts_with("noun-formation-"));
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
fn formation_sources_preserve_native_groups_and_independent_roles() {
    let m: Value =
        serde_json::from_str(include_str!("fixtures/noun-formation-sources.json")).unwrap();
    let f: Value =
        serde_json::from_str(include_str!("fixtures/krdict-noun-formation.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 22);
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
                assert!(suite().cases.iter().any(|c| c.id == t["case_id"]));
            }
        }
    }
    assert_eq!((groups, targets), (44, 5));
    assert_eq!(m["native_target_occurrences"], 4);
    let prefix = entries.iter().find(|e| e["val"] == "72496").unwrap();
    assert_eq!(arr(&prefix["Sense"]).len(), 2);
    assert!(
        arr(&prefix["Sense"])[0]["SenseExample"]
            .to_string()
            .contains("얼간")
    );
    assert!(entries.iter().any(|e| e["val"] == "93133"));
    let source_ids: Vec<_> = arr(&m["primary_consultations"])
        .iter()
        .map(|s| s["id"].as_str().unwrap())
        .collect();
    for id in [
        "formation-eolgan-noun",
        "formation-eol-prefix",
        "formation-heopung-kbs",
        "formation-reduplication-paper",
        "formation-eolgan-norm-data",
    ] {
        assert!(source_ids.contains(&id));
    }
    assert_eq!(m["corpus_training_search"][0]["matching_tokens"], 2);
    assert_eq!(m["corpus_training_search"][1]["matching_tokens"], 0);
    for observation in arr(&m["corpus_training_search"][0]["observations"]) {
        assert!(
            observation["sentence_body"]
                .as_str()
                .unwrap()
                .contains(observation["original_row"].as_str().unwrap())
        );
    }
}
#[test]
fn formation_paths_preserve_unicode_and_internal_ownership() {
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
    let a = engine.analyze_word("얼간이들쯤에는").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| {
            p.rules.iter().any(|r| r == "derivation.nominal.prefix_eol")
                && p.morphemes.last().is_some_and(|m| m.form == "는")
        })
        .unwrap();
    assert_eq!(
        p.breakdown().unwrap(),
        vec![M(0), L(0), M(1), M(2), M(3), M(4), M(5)]
    );
    let a = engine.analyze_word("얼간이들이었다").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| {
            p.rules.iter().any(|r| r == "derivation.nominal.prefix_eol")
                && p.morphemes.last().is_some_and(|m| m.form == "다")
        })
        .unwrap();
    assert_eq!(
        p.breakdown().unwrap(),
        vec![M(0), L(0), M(1), M(2), L(1), M(3), M(4)]
    );
    for word in [
        "얼간이님",
        "얼간이적",
        "쭉정이님",
        "됨됨이적",
        "허풍선이님",
        "얼간이다이",
        "얼간이이",
        "얼간다이",
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|p| !p.rules.iter().any(|r| r == "derivation.nominal.prefix_eol")),
            "{word}"
        );
    }
    for word in ["됨됨이", "쭉정이", "허풍선이", "얼간이"] {
        let a = engine.analyze_word(word).unwrap();
        assert!(a.analyses.iter().all(|p| {
            !p.rules
                .iter()
                .any(|r| r == "derivation.nominal.related_root")
        }));
        assert!(
            a.analyses
                .iter()
                .filter(|p| p.rules.iter().any(|r| r == "suffix.nominal.i"))
                .all(|p| p
                    .lemmas
                    .iter()
                    .all(|l| l.kind != klem::LemmaKind::Predicate))
        );
    }
}
#[test]
fn external_prefix_shapes_require_registered_source_identity() {
    let e = Lemmatizer::new();
    let a = e.analyze_word("얼간이").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| p.rules.iter().any(|r| r == "derivation.nominal.prefix_eol"))
        .unwrap();
    let mut wrong = p.clone();
    wrong.lemmas[0].text = "눈".into();
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.morphemes[0].form = "왕".into();
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.lemmas[0].kind = klem::LemmaKind::Root;
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.rules.push("derivation.nominal.prefix_wang".into());
    assert!(wrong.breakdown().is_none());
    let mut wrong = p.clone();
    wrong.rules.retain(|r| r != "derivation.nominal.prefix_eol");
    assert!(wrong.breakdown().is_none());
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
    assert!(p.breakdown().is_some());
    let mut wrong = p.clone();
    wrong.rules.push("derivation.nominal.prefix_eol".into());
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
        "klem-noun-formation-{tag}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-formation.json")],
        &path,
        "noun-formation",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), db)
}
#[test]
fn formation_filters_cli_and_prefix_slots_preserve_all_paths() {
    let (cleanup, db) = dictionary("cli");
    assert_eq!(db.lookup("간").unwrap().len(), 4);
    assert_eq!(db.lookup("얼-").unwrap().len(), 2);
    for word in ["얼간", "허풍선", "됨됨", "쭉정"] {
        assert!(db.lookup(word).unwrap().is_empty());
    }
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
                    .any(|r| r == "derivation.nominal.prefix_eol")
                {
                    assert_eq!(reading.lemmas[0].entries.len(), 4);
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
fn formation_nouns_keep_spacing_roles_without_invented_predicates() {
    let (_cleanup, db) = dictionary("spacing");
    let mut session = klem::Session::new(Lemmatizer::new().into(), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    for tail in ["먹는다", "얼간이"] {
        let surface = format!("얼간이를{tail}");
        let wanted = format!("얼간이를 {tail}");
        let r = klem::spacing::suggest(
            &mut session,
            &mut dictionary,
            &surface,
            0,
            Default::default(),
        )
        .unwrap();
        assert_eq!(
            r.alternatives.iter().any(|a| a.spaced == wanted),
            tail == "먹는다"
        );
        if tail == "먹는다" {
            let a = r.alternatives.iter().find(|a| a.spaced == wanted).unwrap();
            assert!(
                a.records[0]
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|p| p.rules.iter().any(|r| r == "derivation.nominal.prefix_eol"))
            );
            assert!(
                a.records
                    .iter()
                    .all(|r| r.breakdowns.iter().all(Option::is_some))
            );
        }
    }
    assert!(dictionary.cache_bytes() <= 4096);
}
