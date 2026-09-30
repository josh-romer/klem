//! COV-017be: exact primary comparative expressions, not general particle licenses.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    AttachmentRule, Compatibility, DictionaryFilter, DictionarySession, SqliteDictionary,
    import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;
fn suite(file: &str) -> validity::Suite {
    let mut s: validity::Suite = serde_json::from_str(file).unwrap();
    s.cases.retain(|c| c.id.starts_with("comparative-neuni-"));
    s
}
fn raw() -> validity::Suite {
    suite(include_str!("fixtures/validity.json"))
}
fn policy() -> validity::Suite {
    suite(include_str!("fixtures/dictionary-attachments.json"))
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let p = std::env::temp_dir().join(format!(
            "klem-comparative-neuni-{}-{name}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-neuni-comparison.json")],
            &p,
            "neuni-comparison",
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
fn path<'a>(w: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> &'a Analysis {
    w.analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(heads.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        })
        .unwrap_or_else(|| panic!("{}: {heads:?} + {forms:?}", w.normalized))
}
#[test]
fn comparative_expressions_preserve_local_owners_spelling_and_alternatives() {
    let s = raw();
    let report = validity::evaluate(&s).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (48, 10));
    let engine = Lemmatizer::new();
    for c in s.cases {
        let w = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            w,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(w.analyses.iter().any(|a| a.unchanged));
        for a in w.analyses {
            assert!(a.breakdown().is_some());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    for f in ["느니보다", "느니보다는"] {
        let w = engine.analyze_word(&format!("사{f}")).unwrap();
        for h in ["사다", "살다"] {
            let a = path(&w, &[h], &[f]);
            assert!(a.rules.iter().any(|r| r == "ending.neuni"));
            if h == "살다" {
                assert!(a.rules.iter().any(|r| r == "deletion.rieul"));
            }
        }
    }
}
#[test]
fn comparative_sources_preserve_complete_groups_and_expression_identity() {
    let s: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/neuni-comparison-sources.json")).unwrap();
    let n: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-neuni-comparison.json")).unwrap();
    let entries = n["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 43);
    let examples = s["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 10);
    let raw = raw();
    let mut groups = std::collections::BTreeSet::new();
    for e in examples {
        let id = e["entry_id"].as_u64().unwrap();
        let entry_id = id.to_string();
        let entry = entries
            .iter()
            .find(|n| n["val"].as_str() == Some(entry_id.as_str()))
            .unwrap();
        let sense = &entry["Sense"][0];
        assert_eq!(sense["val"], e["sense_id"]);
        let g = e["example_group"].as_u64().unwrap() as usize;
        groups.insert((id, g));
        let f = &sense["SenseExample"][g - 1]["feat"];
        let features = if let Some(a) = f.as_array() {
            a.clone()
        } else {
            vec![f.clone()]
        };
        assert!(features.iter().any(|f| {
            f["att"] == "example"
                && f["val"]
                    .as_str()
                    .unwrap()
                    .contains(e["original"].as_str().unwrap())
        }));
        let c = raw
            .cases
            .iter()
            .find(|c| c.id == e["case_id"].as_str().unwrap())
            .unwrap();
        assert_eq!(c.surface, e["surface"]);
        assert_eq!(c.judgments[0].verdict, validity::Verdict::Required);
        assert_eq!(
            raw.sources[&c.judgments[0].source],
            format!("https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo={id}")
        );
    }
    assert_eq!(groups.len(), 8);
    let labels: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    for (form, id) in [("느니보다", 85729), ("느니보다는", 85731)] {
        let entry_id = id.to_string();
        let e = entries
            .iter()
            .find(|e| e["val"].as_str() == Some(entry_id.as_str()))
            .unwrap();
        let feats = e["feat"].as_array().unwrap();
        assert!(
            feats
                .iter()
                .any(|f| f["att"] == "partOfSpeech" && f["val"] == "품사 없음")
        );
        assert!(
            feats
                .iter()
                .any(|f| f["att"] == "lexicalUnit" && f["val"] == "문법‧표현")
        );
        assert_eq!(labels[format!("-{form}")]["sources"][0]["id"], id);
        assert_eq!(labels[format!("-{form}")]["sources"][0]["pos"], "품사 없음");
        assert_eq!(e["Sense"][0]["SenseExample"].as_array().unwrap().len(), 4);
    }
}
#[test]
fn comparative_filters_preserve_library_cli_parity_and_unknown_prefinals() {
    let fixture = Fixture::new("filters");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dict = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, filter) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        for s in [raw(), policy()] {
            let is_policy = s.cases[0].id.starts_with("comparative-neuni-policy-");
            let report = validity::evaluate_with(&s, |surface| {
                let mut w = engine.analyze_word(surface).unwrap();
                let mut d = dict.annotate(&w).unwrap();
                d.filter(&mut w, filter);
                let output = Command::new(env!("CARGO_BIN_EXE_klem"))
                    .args(["word", surface, "--dictionary"])
                    .arg(&fixture.0)
                    .arg(flag)
                    .output()
                    .unwrap();
                assert!(output.status.success());
                let v: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
                assert_eq!(
                    serde_json::from_value::<WordAnalysis>(v.clone()).unwrap(),
                    w
                );
                assert_eq!(v["dictionary"], serde_json::to_value(&d).unwrap());
                assert!(dict.cache_bytes() <= 4096);
                Ok(w)
            })
            .unwrap();
            if is_policy && filter == DictionaryFilter::Headword {
                assert_eq!((report.required_present, report.forbidden_present), (8, 4));
            } else {
                assert!(report.passed(), "{:?}", report.violations);
            }
        }
        for f in ["느니보다", "느니보다는"] {
            for (stem, pf) in [
                ("먹었", "었"),
                ("먹겠", "겠"),
                ("먹더", "더"),
                ("먹사오", "사옵"),
            ] {
                let mut w = engine.analyze_word(&format!("{stem}{f}")).unwrap();
                let a = path(&w, &["먹다"], &[pf, f]).clone();
                let idx = w.analyses.iter().position(|p| p == &a).unwrap();
                let mut d = dict.annotate(&w).unwrap();
                assert_eq!(d.readings[idx].status, Compatibility::Unknown);
                d.filter(&mut w, filter);
                assert!(w.analyses.contains(&a));
            }
        }
    }
}
#[test]
fn comparative_policy_checks_each_homonym_independently() {
    let fixture = Fixture::new("homonyms");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dict = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for f in ["느니보다", "느니보다는"] {
        let w = engine.analyze_word(&format!("크{f}")).unwrap();
        let a = path(&w, &["크다"], &[f]);
        let idx = w.analyses.iter().position(|p| p == a).unwrap();
        let d = dict.annotate(&w).unwrap();
        let r = &d.readings[idx];
        assert_eq!(r.status, Compatibility::Compatible);
        for (id, status) in [
            ("krdict:66584", Compatibility::Compatible),
            ("krdict:66586", Compatibility::Incompatible),
        ] {
            let e = r.lemmas[0].entries.iter().find(|e| e.id == id).unwrap();
            assert_eq!(e.status, status);
            if status == Compatibility::Incompatible {
                assert!(
                    e.conflicts
                        .iter()
                        .any(|c| c.rule == AttachmentRule::BareNeuniVerb)
                );
            }
        }
    }
}
