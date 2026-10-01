//! Full native -다가 groups extend the persistent inventory review.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
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
    s.cases.retain(|c| c.id.starts_with("daga-"));
    s
}
fn native() -> validity::Suite {
    let mut s = suite();
    s.cases.retain(|c| c.id.starts_with("daga-native-"));
    s
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let p =
            std::env::temp_dir().join(format!("klem-daga-source-{}-{name}.db", std::process::id()));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-daga.json"),
                PathBuf::from("tests/fixtures/krdict-daga-native.json"),
            ],
            &p,
            "daga-native-source-fixture",
        )
        .unwrap();
        Self(p)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn arr(v: &serde_json::Value) -> Vec<&serde_json::Value> {
    if let Some(a) = v.as_array() {
        a.iter().collect()
    } else if v.is_object() {
        vec![v]
    } else {
        vec![]
    }
}
fn feature<'a>(v: &'a serde_json::Value, name: &str) -> Option<&'a str> {
    arr(&v["feat"])
        .into_iter()
        .find(|f| f["att"] == name)
        .and_then(|f| f["val"].as_str())
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
fn daga_complete_native_groups_keep_every_target_and_source_turn() {
    let m: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/daga-native-sources.json")).unwrap();
    let f: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-daga.json")).unwrap();
    let e = f["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["val"] == "85740")
        .unwrap();
    assert_eq!(feature(e, "partOfSpeech"), Some("어미"));
    assert_eq!(feature(&e["Lemma"], "writtenForm"), Some("-다가"));
    let senses = arr(&e["Sense"]);
    assert_eq!(senses.len(), 4);
    let groups = m["source_groups"].as_array().unwrap();
    assert_eq!(groups.len(), 15);
    assert_eq!(
        senses
            .iter()
            .map(|s| arr(&s["SenseExample"]).len())
            .sum::<usize>(),
        groups.len()
    );
    let cases = native();
    let mut seen = std::collections::BTreeSet::new();
    for g in groups {
        let sense = senses.iter().find(|s| s["val"] == g["sense_id"]).unwrap();
        let group = arr(&sense["SenseExample"])[g["example_group"].as_u64().unwrap() as usize - 1];
        assert_eq!(group, &g["native_group"]);
        let examples: Vec<_> = arr(&group["feat"])
            .into_iter()
            .filter(|f| f["att"] == "example")
            .map(|f| f["val"].as_str().unwrap())
            .collect();
        assert_eq!(serde_json::to_value(&examples).unwrap(), g["examples"]);
        let targets = g["targets"].as_array().unwrap();
        assert!(!targets.is_empty());
        for t in targets {
            let token = examples[t["turn"].as_u64().unwrap() as usize]
                .split_whitespace()
                .nth(t["token"].as_u64().unwrap() as usize)
                .unwrap()
                .trim_end_matches(['.', '?', '!', ',']);
            assert_eq!(token, t["surface"]);
            let id = t["case_id"].as_str().unwrap();
            assert!(seen.insert(id));
            let c = cases.cases.iter().find(|c| c.id == id).unwrap();
            assert_eq!(c.surface, token);
            assert_eq!(c.judgments.len(), 1);
            let j = &c.judgments[0];
            assert_eq!(j.source, "daga-native-primary");
            assert_eq!(serde_json::to_value(&j.lemmas).unwrap(), t["lemmas"]);
            assert_eq!(serde_json::to_value(&j.morphemes).unwrap(), t["morphemes"]);
        }
        let tokens: Vec<_> = examples
            .iter()
            .flat_map(|s| s.split_whitespace())
            .map(|s| s.trim_end_matches(['.', '?', '!', ',']))
            .filter(|s| s.ends_with("다가"))
            .collect();
        assert_eq!(tokens.len(), targets.len());
    }
    assert_eq!(seen.len(), 19);
    assert_eq!(cases.cases.len(), seen.len());
    assert_eq!(m["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn daga_native_paths_preserve_normalization_boundaries_and_all_alternatives() {
    let r = validity::evaluate(&suite()).unwrap();
    assert!(r.passed(), "{:?}", r.violations);
    assert_eq!((r.required_total, r.forbidden_total), (23, 4));
    let engine = Lemmatizer::new();
    for c in native().cases {
        let a = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            a,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(a.analyses.iter().any(|a| a.unchanged));
        for p in &a.analyses {
            let order = p.breakdown().unwrap();
            assert_eq!(order.len(), p.lemmas.len() + p.morphemes.len());
            assert!(p.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
        for j in c.judgments {
            let p = a.analyses.iter().find(|p| matches(p, &j)).unwrap();
            assert!(p.rules.iter().any(|r| r == "ending"));
        }
    }
    for (word, head, forms) in [
        ("가다가", "가다", vec!["다가"]),
        ("가다가", "가다", vec!["어다가"]),
        ("들었다가", "들다", vec!["었", "다가"]),
        ("들었다가", "듣다", vec!["었", "다가"]),
    ] {
        let a = engine.analyze_word(word).unwrap();
        assert!(
            a.analyses.iter().any(|p| p.lemmas.len() == 1
                && p.lemmas[0].text == head
                && p.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())),
            "{word}: {head}"
        );
    }
}
#[test]
fn daga_native_dictionary_paths_keep_entry_identity_under_both_filters() {
    let f = Fixture::new("dictionary");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let entry = db.entry("krdict:85740").unwrap().unwrap();
    assert_eq!(entry.summary.headword, "-다가");
    assert_eq!(entry.summary.pos, "어미");
    assert_eq!(entry.senses.len(), 4);
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
        let report = validity::evaluate_with(&native(), |w| {
            let mut a = engine.analyze_word(w).unwrap();
            let mut an = d.annotate(&a).unwrap();
            an.filter(&mut a, filter);
            Ok(a)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
        assert_eq!(report.required_present, 19);
    }
    let a = engine.analyze_word("들었다가").unwrap();
    let mut an = d.annotate(&a).unwrap();
    let mut kept = a.clone();
    an.filter(&mut kept, DictionaryFilter::Compatible);
    for head in ["들다", "듣다"] {
        assert!(kept.analyses.iter().any(|p| {
            p.lemmas.len() == 1
                && p.lemmas[0].text == head
                && p.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["었", "다가"])
        }));
    }
    assert!(d.cache_bytes() <= 4096);
}
#[test]
fn daga_native_word_and_text_exports_match_library_and_ordered_components() {
    let f = Fixture::new("cli");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    for filter in [
        None,
        Some(DictionaryFilter::Headword),
        Some(DictionaryFilter::Compatible),
    ] {
        let cases = native().cases;
        let mut expected = vec![];
        for c in &cases {
            let mut a = engine.analyze_word(&c.surface).unwrap();
            let mut an = d.annotate(&a).unwrap();
            if let Some(f) = filter {
                an.filter(&mut a, f);
            }
            for j in &c.judgments {
                let p = a.analyses.iter().find(|p| matches(p, j)).unwrap();
                let order = p.breakdown().unwrap();
                assert!(matches!(order[0], klem::breakdown::Component::Lemma(0)));
                assert!(
                    order[1..]
                        .iter()
                        .all(|c| matches!(c, klem::breakdown::Component::Morpheme(_)))
                );
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"]).arg(&f.0);
            if let Some(f) = filter {
                cmd.arg(if f == DictionaryFilter::Headword {
                    "--dict-only"
                } else {
                    "--dict-compatible"
                });
            }
            let output = cmd.output().unwrap();
            assert!(output.status.success());
            let actual: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            let mut without_dict = actual.clone();
            assert_eq!(
                without_dict
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(an).unwrap()
            );
            assert_eq!(without_dict, serde_json::to_value(a).unwrap());
            expected.push(actual);
        }
        let text = cases
            .iter()
            .map(|c| c.surface.as_str())
            .collect::<Vec<_>>()
            .join(" ");
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
        cmd.args(["text", "-", "--dictionary"]).arg(&f.0);
        if let Some(f) = filter {
            cmd.arg(if f == DictionaryFilter::Headword {
                "--dict-only"
            } else {
                "--dict-compatible"
            });
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
        let records: Vec<serde_json::Value> = String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .filter(|r: &serde_json::Value| !r["analysis"].is_null())
            .collect();
        assert_eq!(records.len(), cases.len());
        for ((record, expected), c) in records.iter().zip(expected).zip(cases) {
            assert_eq!(record["surface"], c.surface);
            let mut expected = expected;
            let dictionary = expected
                .as_object_mut()
                .unwrap()
                .remove("dictionary")
                .unwrap();
            assert_eq!(record["analysis"], expected);
            assert_eq!(record["dictionary"], dictionary);
        }
    }
}
