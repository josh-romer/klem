//! Full native examples and per-entry uncertainty for formal proposals.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;
fn suite(file: &str, previous: bool) -> validity::Suite {
    let mut s: validity::Suite = serde_json::from_str(file).unwrap();
    s.cases.retain(|c| {
        c.id.starts_with("proposal-audit-") || (previous && c.id.starts_with("propositive-"))
    });
    s
}
fn raw() -> validity::Suite {
    suite(include_str!("fixtures/validity.json"), true)
}
fn policy() -> validity::Suite {
    suite(include_str!("fixtures/dictionary-attachments.json"), false)
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let p = std::env::temp_dir().join(format!(
            "klem-proposal-review-{}-{name}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-proposal-audit.json")],
            &p,
            "proposal-review-fixture",
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
fn path<'a>(a: &'a klem::WordAnalysis, heads: &[&str], forms: &[&str]) -> &'a Analysis {
    a.analyses
        .iter()
        .find(|p| {
            p.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(heads.iter().copied())
                && p.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        })
        .unwrap()
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
#[test]
fn proposal_all_native_groups_keep_exact_source_examples_and_identities() {
    let manifest: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/proposal-audit-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-proposal-audit.json")).unwrap();
    let groups = manifest["source_groups"].as_array().unwrap();
    assert_eq!(groups.len(), 8);
    let cases = raw();
    for ident in ["68880", "68883"] {
        let native = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["val"] == ident && feature(e, "lexicalUnit") == Some("단어"))
            .unwrap();
        let sources = arr(&native["Sense"]);
        assert_eq!(sources.len(), 1);
        assert_eq!(feature(native, "partOfSpeech"), Some("어미"));
        assert_eq!(arr(&sources[0]["SenseExample"]).len(), 4);
        for g in groups
            .iter()
            .filter(|g| g["entry_id"] == format!("krdict:{ident}"))
        {
            let sense = sources.iter().find(|s| s["val"] == g["sense_id"]).unwrap();
            let native_group =
                arr(&sense["SenseExample"])[g["example_group"].as_u64().unwrap() as usize - 1];
            assert_eq!(native_group, &g["native_group"]);
            let examples: Vec<_> = arr(&native_group["feat"])
                .into_iter()
                .filter(|f| f["att"] == "example")
                .map(|f| f["val"].as_str().unwrap())
                .collect();
            assert_eq!(serde_json::to_value(&examples).unwrap(), g["examples"]);
            let token = examples[g["turn"].as_u64().unwrap() as usize]
                .split_whitespace()
                .nth(g["token"].as_u64().unwrap() as usize)
                .unwrap()
                .trim_end_matches(['.', '?', '!', ',']);
            assert_eq!(token, g["surface"]);
            assert!(
                cases
                    .cases
                    .iter()
                    .any(|c| Some(c.id.as_str()) == g["case_id"].as_str() && c.surface == token)
            );
            assert!(
                policy()
                    .cases
                    .iter()
                    .any(|c| Some(c.id.as_str()) == g["policy_case_id"].as_str()
                        && c.surface == token)
            );
        }
    }
    assert_eq!(manifest["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn proposal_source_paths_preserve_boundaries_normalization_and_ambiguity() {
    let r = validity::evaluate(&raw()).unwrap();
    assert!(r.passed(), "{:?}", r.violations);
    assert_eq!((r.required_total, r.forbidden_total), (15, 5));
    let engine = Lemmatizer::new();
    for c in raw().cases {
        let a = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            a,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(a.analyses.iter().any(|p| p.unchanged));
        for p in &a.analyses {
            assert!(p.breakdown().is_some());
            assert!(p.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    let a = engine.analyze_word("갑시다").unwrap();
    for h in ["가다", "갈다"] {
        let p = path(&a, &[h], &["읍시다"]);
        assert!(p.rules.iter().any(|r| r == "ending"));
    }
    let a = engine.analyze_word("도와줍시다").unwrap();
    path(&a, &["도와주다"], &["읍시다"]);
    path(&a, &["돕다", "주다"], &["어", "읍시다"]);
}
#[test]
fn proposal_uncertainty_is_per_entry_and_immediate_owner() {
    let f = Fixture::new("classes");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    for (word, heads, forms, owner, id, expected) in [
        (
            "좋읍시다",
            vec!["좋다"],
            vec!["읍시다"],
            0,
            "krdict:79033",
            Compatibility::Unknown,
        ),
        (
            "건강합시다",
            vec!["건강하다"],
            vec!["읍시다"],
            0,
            "krdict:17317",
            Compatibility::Unknown,
        ),
        (
            "행복합시다",
            vec!["행복하다"],
            vec!["읍시다"],
            0,
            "krdict:72481",
            Compatibility::Unknown,
        ),
        (
            "고릅시다",
            vec!["고르다"],
            vec!["읍시다"],
            0,
            "krdict:19935",
            Compatibility::Compatible,
        ),
        (
            "고릅시다",
            vec!["고르다"],
            vec!["읍시다"],
            0,
            "krdict:19938",
            Compatibility::Compatible,
        ),
        (
            "고릅시다",
            vec!["고르다"],
            vec!["읍시다"],
            0,
            "krdict:25632",
            Compatibility::Unknown,
        ),
        (
            "좋지않읍시다",
            vec!["좋다", "않다"],
            vec!["지", "읍시다"],
            0,
            "krdict:79033",
            Compatibility::Compatible,
        ),
        (
            "좋지않읍시다",
            vec!["좋다", "않다"],
            vec!["지", "읍시다"],
            1,
            "krdict:71581",
            Compatibility::Unknown,
        ),
        (
            "먹지않읍시다",
            vec!["먹다", "않다"],
            vec!["지", "읍시다"],
            1,
            "krdict:71581",
            Compatibility::Unknown,
        ),
        (
            "먹고싶읍시다",
            vec!["먹다", "싶다"],
            vec!["고", "읍시다"],
            1,
            "krdict:62657",
            Compatibility::Unknown,
        ),
        (
            "먹어보지않읍시다",
            vec!["먹다", "보다", "않다"],
            vec!["어", "지", "읍시다"],
            2,
            "krdict:71581",
            Compatibility::Compatible,
        ),
        (
            "먹어봅시다",
            vec!["먹다", "보다"],
            vec!["어", "읍시다"],
            1,
            "krdict:62171",
            Compatibility::Compatible,
        ),
    ] {
        let a = engine.analyze_word(word).unwrap();
        let p = path(&a, &heads, &forms);
        let an = d.annotate(&a).unwrap();
        let assessment = an.assess(p);
        let e = assessment.lemmas[owner]
            .entries
            .iter()
            .find(|e| e.id == id)
            .unwrap();
        assert_eq!(e.status, expected, "{word}: {id}");
        if expected == Compatibility::Unknown {
            assert!(e.conflicts.is_empty());
        }
    }
    for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
        let r = validity::evaluate_with(&policy(), |w| {
            let mut a = engine.analyze_word(w).unwrap();
            let mut an = d.annotate(&a).unwrap();
            an.filter(&mut a, filter);
            Ok(a)
        })
        .unwrap();
        assert_eq!(r.required_total, 16);
        assert!(r.passed(), "{:?}", r.violations);
    }
    assert!(d.cache_bytes() <= 4096);
}
#[test]
fn proposal_source_and_uncertain_paths_match_cli_library_and_ordered_exports() {
    let f = Fixture::new("cli");
    let db = SqliteDictionary::open(&f.0).unwrap();
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    for c in policy().cases {
        for filter in [
            None,
            Some(DictionaryFilter::Headword),
            Some(DictionaryFilter::Compatible),
        ] {
            let mut a = engine.analyze_word(&c.surface).unwrap();
            let mut an = d.annotate(&a).unwrap();
            if let Some(f) = filter {
                an.filter(&mut a, f);
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
            let mut actual: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(&an).unwrap()
            );
            assert_eq!(actual, serde_json::to_value(&a).unwrap());
            for p in &a.analyses {
                assert!(p.breakdown().is_some());
            }
        }
    }
}
