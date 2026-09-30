//! COV-017bd: source-reviewed quoted listing bundles and local owners.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    AttachmentRule, Compatibility, DictionaryFilter, DictionarySession, SqliteDictionary,
    import_krdict,
};
use klem::{Lemmatizer, SpellingClass, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;
fn suite(file: &str) -> validity::Suite {
    let mut s: validity::Suite = serde_json::from_str(file).unwrap();
    s.cases.retain(|c| c.id.starts_with("quoted-neuni-"));
    s
}
fn raw_suite() -> validity::Suite {
    suite(include_str!("fixtures/validity.json"))
}
fn policy_suite() -> validity::Suite {
    suite(include_str!("fixtures/dictionary-attachments.json"))
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-quoted-neuni-{}-{name}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-quoted-neuni.json")],
            &path,
            "neuni",
        )
        .unwrap();
        Self(path)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn path<'a>(word: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> &'a klem::Analysis {
    word.analyses
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
        .unwrap_or_else(|| panic!("missing {heads:?} {forms:?}: {word:?}"))
}
#[test]
fn quoted_neuni_bundles_preserve_spelling_and_immediate_owners() {
    let report = validity::evaluate(&raw_suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (133, 43));
    let engine = Lemmatizer::new();
    for c in raw_suite().cases {
        let word = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in word.analyses {
            assert!(a.breakdown().is_some(), "{}: {a:?}", c.surface);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    let word = engine.analyze_word("산다느니").unwrap();
    for head in ["사다", "살다"] {
        let a = path(&word, &[head], &["는다느니"]);
        assert!(a.rules.iter().any(|r| r == "ending.quoted_neuni"));
        if head == "살다" {
            assert!(a.rules.iter().any(|r| r == "deletion.rieul"));
        }
    }
    let word = engine.analyze_word("먹으시라느니").unwrap();
    for ending in ["라느니", "으라느니"] {
        path(&word, &["먹다"], &["시", ending]);
    }
    let word = engine.analyze_word("먹더라느니").unwrap();
    path(&word, &["먹다"], &["더라느니"]);
    path(&word, &["먹다"], &["더", "라느니"]);
    let word = engine.analyze_word("먹으리라느니").unwrap();
    let a = path(&word, &["먹다"], &["으리", "라느니"]);
    assert!(a.rules.iter().any(|r| r == "ending.quoted_neuni"));
    let word = engine.analyze_word("나으냐느니").unwrap();
    let a = path(&word, &["낫다"], &["으냐느니"]);
    assert!(
        a.spelling_paths
            .iter()
            .flatten()
            .any(|p| p.morpheme_index == 0 && p.class == SpellingClass::SiotIrregular)
    );
    let word = engine.analyze_word("사달라느니").unwrap();
    path(&word, &["사다", "달다"], &["어", "으라느니"]);
    for (surface, forms) in [
        ("사달시라느니", vec!["어", "시", "으라느니"]),
        ("사달더라느니", vec!["어", "더", "라느니"]),
    ] {
        let w = engine.analyze_word(surface).unwrap();
        assert!(!w.analyses.iter().any(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["사다", "달다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        }));
    }
}
#[test]
fn quoted_neuni_sources_preserve_every_sense_group_and_expression_identity() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/quoted-neuni-sources.json")).unwrap();
    let native: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-quoted-neuni.json")).unwrap();
    let entries = native["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 143);
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 93);
    assert_eq!(
        examples
            .iter()
            .filter(|e| e["input_kind"] == "direct")
            .count(),
        90
    );
    assert_eq!(
        examples
            .iter()
            .filter(|e| e["input_kind"] == "joined")
            .count(),
        3
    );
    let mut groups = std::collections::BTreeSet::new();
    let mut cases = std::collections::BTreeSet::new();
    let suite = raw_suite();
    for e in examples {
        let id = e["entry_id"].as_u64().unwrap();
        let entry = entries
            .iter()
            .find(|n| n["val"].as_str() == Some(&id.to_string()))
            .unwrap();
        let sense = entry["Sense"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["val"] == e["sense_id"])
            .unwrap();
        let group = e["example_group"].as_u64().unwrap() as usize;
        groups.insert((id, e["sense_id"].as_str().unwrap(), group));
        assert!(cases.insert(e["case_id"].as_str().unwrap()));
        let f = &sense["SenseExample"][group - 1]["feat"];
        let fs = if let Some(a) = f.as_array() {
            a.clone()
        } else {
            vec![f.clone()]
        };
        assert!(fs.iter().any(|f| {
            f["att"] == "example"
                && f["val"]
                    .as_str()
                    .unwrap()
                    .contains(e["original"].as_str().unwrap())
        }));
        let c = suite
            .cases
            .iter()
            .find(|c| Some(c.id.as_str()) == e["case_id"].as_str())
            .unwrap();
        assert_eq!(c.surface, e["surface"].as_str().unwrap());
        assert_eq!(c.judgments[0].verdict, validity::Verdict::Required);
        assert_eq!(
            suite.sources[&c.judgments[0].source],
            format!("https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo={id}")
        );
    }
    assert_eq!(groups.len(), 49);
    let mut senses = 0;
    for id in [
        86068, 86069, 86911, 86079, 86080, 86070, 88983, 88986, 88987, 86074,
    ] {
        let e = entries
            .iter()
            .find(|e| e["val"].as_str() == Some(&id.to_string()))
            .unwrap();
        for s in e["Sense"].as_array().unwrap() {
            senses += 1;
            for g in 1..=s["SenseExample"].as_array().unwrap().len() {
                assert!(groups.contains(&(id, s["val"].as_str().unwrap(), g)));
            }
        }
    }
    assert_eq!(senses, 11);
    let labels: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    for (form, count) in [
        ("다느니", 1),
        ("는다느니", 2),
        ("라느니", 1),
        ("으라느니", 2),
        ("자느니", 1),
        ("냐느니", 1),
        ("느냐느니", 1),
        ("으냐느니", 1),
        ("더라느니", 1),
    ] {
        assert_eq!(labels[format!("-{form}")]["kind"], "ending");
        assert_eq!(
            labels[format!("-{form}")]["sources"]
                .as_array()
                .unwrap()
                .len(),
            count
        );
    }
    for (form, id) in [("느냐느니", 88986), ("더라느니", 86074)] {
        assert_eq!(labels[format!("-{form}")]["sources"][0]["id"], id);
        assert_eq!(labels[format!("-{form}")]["sources"][0]["pos"], "품사 없음");
    }
    let observations = source["source_observations"].as_array().unwrap();
    assert_eq!(observations.len(), 1);
    assert_eq!(observations[0]["original"], "결혼을하라느니");
    assert_eq!(observations[0]["checklist"], "COV-020p");
}
#[test]
fn quoted_neuni_dictionary_filters_preserve_source_paths_unicode_and_cli_parity() {
    let fixture = Fixture::new("filters");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, filter) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        for suite in [raw_suite(), policy_suite()] {
            let report = validity::evaluate_with(&suite, |surface| {
                let mut analysis = engine.analyze_word(surface).unwrap();
                let mut annotation = dictionary.annotate(&analysis).unwrap();
                annotation.filter(&mut analysis, filter);
                let cli = Command::new(env!("CARGO_BIN_EXE_klem"))
                    .args(["word", surface, "--dictionary"])
                    .arg(&fixture.0)
                    .arg(flag)
                    .output()
                    .unwrap();
                assert!(
                    cli.status.success(),
                    "{}",
                    String::from_utf8_lossy(&cli.stderr)
                );
                let value: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
                assert_eq!(
                    serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                    analysis
                );
                assert_eq!(
                    value["dictionary"],
                    serde_json::to_value(&annotation).unwrap()
                );
                assert!(dictionary.cache_bytes() <= 4096);
                Ok(analysis)
            })
            .unwrap();
            if filter == DictionaryFilter::Headword
                && suite.cases[0].id.starts_with("quoted-neuni-policy-")
            {
                assert_eq!((report.required_present, report.forbidden_present), (9, 7));
            } else {
                assert!(report.passed(), "{:?}", report.violations);
            }
        }
    }
}

#[test]
fn quoted_neuni_checks_each_homonym_and_keeps_unknown_prefinal_roles() {
    let fixture = Fixture::new("homonyms");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dict = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (surface, forms, verb_status, adj_status, rule) in [
        (
            "크다느니",
            vec!["다느니"],
            Compatibility::Incompatible,
            Compatibility::Compatible,
            AttachmentRule::BareAdjectivalReport,
        ),
        (
            "큰다느니",
            vec!["는다느니"],
            Compatibility::Compatible,
            Compatibility::Incompatible,
            AttachmentRule::PresentDeclarativeVerb,
        ),
        (
            "크느냐느니",
            vec!["느냐느니"],
            Compatibility::Compatible,
            Compatibility::Incompatible,
            AttachmentRule::BareVerbalQuestion,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let p = path(&word, &["크다"], &forms);
        let index = word.analyses.iter().position(|a| a == p).unwrap();
        let annotated = dict.annotate(&word).unwrap();
        let reading = &annotated.readings[index];
        assert_eq!(reading.status, Compatibility::Compatible);
        for (entry, status) in [("krdict:66584", verb_status), ("krdict:66586", adj_status)] {
            let e = reading.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == entry)
                .unwrap();
            assert_eq!(e.status, status);
            if status == Compatibility::Incompatible {
                assert!(e.conflicts.iter().any(|c| c.rule == rule));
            }
        }
    }
    for (surface, heads, forms) in [
        ("먹사옵다느니", vec!["먹다"], vec!["사옵", "다느니"]),
        ("먹더냐느니", vec!["먹다"], vec!["더", "냐느니"]),
        ("않다느니", vec!["않다"], vec!["다느니"]),
    ] {
        let mut word = engine.analyze_word(surface).unwrap();
        let target = path(&word, &heads, &forms).clone();
        let index = word.analyses.iter().position(|a| a == &target).unwrap();
        let mut annotated = dict.annotate(&word).unwrap();
        assert_eq!(
            annotated.readings[index].status,
            Compatibility::Unknown,
            "{surface}"
        );
        annotated.filter(&mut word, DictionaryFilter::Compatible);
        assert!(word.analyses.contains(&target));
    }
    let malformed = engine.analyze_word("결혼을하라느니").unwrap();
    assert!(malformed.analyses.iter().any(|a| a.unchanged));
}
