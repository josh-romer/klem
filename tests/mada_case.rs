//! COV-018l: modern nominal 마다 + 에, independently sourced from Lee (2025).
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Analysis, Lemmatizer};
use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;
const RULE: &str = "particle.mada_case";
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("mada-case-"));
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
struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn dictionary(tag: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!("klem-mada-case-{tag}-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-mada-case.json")],
        &path,
        "mada-case",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), db)
}
#[test]
fn mada_case_sources_preserve_full_native_senses_and_original_observation() {
    let m: Value = serde_json::from_str(include_str!("fixtures/mada-case-sources.json")).unwrap();
    let f: Value = serde_json::from_str(include_str!("fixtures/krdict-mada-case.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 57);
    let mada = entries.iter().find(|e| e["val"] == "70331").unwrap();
    assert_eq!(arr(&mada["Sense"]).len(), 2);
    let mut groups = 0;
    for s in arr(&mada["Sense"]) {
        for (i, g) in arr(&s["SenseExample"]).iter().enumerate() {
            groups += 1;
            let recorded = arr(&m["mada_native_groups"])
                .into_iter()
                .find(|r| r["sense_id"] == s["val"] && r["example_group"] == i + 1)
                .unwrap();
            assert_eq!(&recorded["native_group"], *g);
        }
    }
    assert_eq!(groups, 20);
    assert_eq!(
        m["primary_consultation"]["consulted_pages"],
        serde_json::json!([70])
    );
    assert_eq!(
        m["primary_consultation"]["pdf_sha256"],
        "45333ce81286d92a8e9daf13ac3b198f0a18ef8cf54dab436dc00f9e8387a5a1"
    );
    assert_eq!(m["corpus_observation"]["matching_rows"], 1);
    let hit = &m["corpus_observation"]["files"][3]["hits"][0]["rows"][0];
    assert_eq!(hit[1], "편마다에도");
    assert_eq!(hit[2], "편+마다+에+도");
    assert!(
        include_str!("fixtures/kaist-range-case.conllu")
            .contains("15\t편마다에도\t편+마다+에+도\tADV\tncn+jxc+jca+jxc")
    );
}
#[test]
fn mada_case_paths_preserve_boundaries_ambiguity_unicode_and_component_ownership() {
    let s = suite();
    assert_eq!(s.cases.len(), 20);
    let report = validity::evaluate(&s).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (13, 7));
    let engine = Lemmatizer::new();
    for c in &s.cases {
        let word = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in &word.analyses {
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            let order = a.breakdown().unwrap();
            assert_eq!(order.len(), a.lemmas.len() + a.morphemes.len());
            if a.rules.iter().any(|r| r == RULE) {
                assert!(
                    a.morphemes
                        .windows(2)
                        .any(|p| p[0].form == "마다" && p[1].form == "에")
                );
            }
        }
    }
    // Existing following-genitive paths and ordinary noun/focus alternatives survive.
    for (word, forms) in [
        ("사람마다의", vec!["마다", "의"]),
        ("편마다도", vec!["마다", "도"]),
    ] {
        assert!(engine.analyze_word(word).unwrap().analyses.iter().any(|a| {
            a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(forms.iter().copied())
        }));
    }
}
#[test]
fn mada_case_dictionary_and_cli_filters_preserve_all_lexical_slots_and_unknown_heads() {
    let (cleanup, db) = dictionary("parity");
    let engine = Lemmatizer::new();
    let mut uncached = DictionarySession::new(&db, 0);
    let mut cached = DictionarySession::new(&db, 1 << 20);
    for c in suite().cases {
        let raw = engine.analyze_word(&c.surface).unwrap();
        let annotation = uncached.annotate(&raw).unwrap();
        assert_eq!(annotation, cached.annotate(&raw).unwrap());
        for (i, a) in raw.analyses.iter().enumerate() {
            assert_eq!(
                annotation.readings[i]
                    .lemmas
                    .iter()
                    .map(|l| l.lemma_index)
                    .collect::<Vec<_>>(),
                (0..a.lemmas.len()).collect::<Vec<_>>()
            );
        }
        for (flag, mode) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let (word, dict) = if let Some(mode) = mode {
                {
                    let mut word = raw.clone();
                    let mut dict = annotation.clone();
                    dict.filter(&mut word, mode);
                    (word, dict)
                }
            } else {
                (raw.clone(), annotation.clone())
            };
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"])
                .arg(&cleanup.0);
            if let Some(flag) = flag {
                cmd.arg(flag);
            }
            let out = cmd.output().unwrap();
            assert!(out.status.success());
            let mut expected = serde_json::to_value(&word).unwrap();
            expected["dictionary"] = serde_json::to_value(&dict).unwrap();
            assert_eq!(
                serde_json::from_slice::<Value>(&out.stdout).unwrap(),
                expected,
                "{} {flag:?}",
                c.id
            );
            if c.id == "mada-case-unknown-head" && mode.is_some() {
                assert!(
                    word.analyses
                        .iter()
                        .all(|a| !a.rules.iter().any(|r| r == RULE))
                );
            }
            if c.id == "mada-case-observed-에도" {
                assert!(
                    word.analyses
                        .iter()
                        .any(|a| matches(a, &suite().cases[1].judgments[0]))
                );
            }
        }
    }
}
#[test]
fn mada_case_text_cli_matches_word_api_with_original_spelling_and_offsets() {
    let (cleanup, db) = dictionary("text");
    let engine = Lemmatizer::new();
    let text = suite()
        .cases
        .iter()
        .map(|c| c.surface.clone())
        .collect::<Vec<_>>()
        .join(" ");
    for (flag, mode) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
        cmd.args(["text", "-", "--dictionary"])
            .arg(&cleanup.0)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped());
        if let Some(flag) = flag {
            cmd.arg(flag);
        }
        let mut child = cmd.spawn().unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(text.as_bytes())
            .unwrap();
        let out = child.wait_with_output().unwrap();
        assert!(out.status.success());
        let records = String::from_utf8(out.stdout)
            .unwrap()
            .lines()
            .map(|s| serde_json::from_str::<Value>(s).unwrap())
            .collect::<Vec<_>>();
        let words = records
            .iter()
            .filter(|r| !r["analysis"].is_null())
            .collect::<Vec<_>>();
        assert_eq!(words.len(), 20);
        for (c, r) in suite().cases.iter().zip(words) {
            let raw = engine.analyze_word(&c.surface).unwrap();
            let ann = DictionarySession::new(&db, 0).annotate(&raw).unwrap();
            let (a, d) = if let Some(mode) = mode {
                {
                    let mut word = raw.clone();
                    let mut dict = ann.clone();
                    dict.filter(&mut word, mode);
                    (word, dict)
                }
            } else {
                (raw, ann)
            };
            assert_eq!(r["analysis"], serde_json::to_value(a).unwrap());
            assert_eq!(r["dictionary"], serde_json::to_value(d).unwrap());
            let start = r["span"]["start"].as_u64().unwrap() as usize;
            let end = r["span"]["end"].as_u64().unwrap() as usize;
            assert_eq!(&text[start..end], c.surface);
        }
    }
}
