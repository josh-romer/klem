//! COV-017ba: promise finals with a local ㅁ/음 boundary and verb owner.
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
    let mut suite: validity::Suite = serde_json::from_str(file).unwrap();
    suite.cases.retain(|c| c.id.starts_with("eumse-"));
    suite
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
        let path =
            std::env::temp_dir().join(format!("klem-eumse-{}-{name}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-eumse.json")],
            &path,
            "eumse",
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

#[test]
fn eumse_keeps_retained_rieul_allomorphs_and_ordered_auxiliary_owners() {
    let suite = raw_suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (37, 18));
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let analysis = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            analysis,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(analysis.analyses.iter().any(|a| a.unchanged));
        for a in analysis.analyses {
            assert!(a.breakdown().is_some(), "{}: {a:?}", case.surface);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    for (surface, heads, forms, index) in [
        ("들음세", vec!["듣다"], vec!["음세"], 0),
        ("들어줌세", vec!["듣다", "주다"], vec!["어", "음세"], 0),
    ] {
        let result = engine.analyze_word(surface).unwrap();
        let path = result
            .analyses
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
            .unwrap();
        assert!(
            path.spelling_paths.iter().flatten().any(|r| {
                r.morpheme_index == index && r.class == SpellingClass::DigeutIrregular
            })
        );
        assert!(path.rules.iter().any(|r| r == "ending.volitional_promise"));
    }
}

#[test]
fn eumse_native_examples_preserve_every_example_group_and_source_identity() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/eumse-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-eumse.json")).unwrap();
    let entries = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 87);
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), entries.len());
    let suite = raw_suite();
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 10);
    for example in examples {
        let id = example["entry_id"].as_u64().unwrap();
        let entry = entries
            .iter()
            .find(|e| e["val"].as_str() == Some(&id.to_string()))
            .unwrap();
        let groups = entry["Sense"][0]["SenseExample"].as_array().unwrap();
        assert_eq!(groups.len(), if id == 78483 { 6 } else { 4 });
        assert!((1..=groups.len() as u64).contains(&example["example_group"].as_u64().unwrap()));
        let group = &groups[example["example_group"].as_u64().unwrap() as usize - 1];
        let original = if example["joined"] == true {
            "시작해 봄세"
        } else {
            example["surface"].as_str().unwrap()
        };
        let features = group["feat"].as_array().unwrap();
        assert!(
            features
                .iter()
                .any(|f| f["att"] == "example" && f["val"].as_str().unwrap().contains(original))
        );
        let case = suite
            .cases
            .iter()
            .find(|c| c.id == example["case_id"])
            .unwrap();
        assert_eq!(case.surface, example["surface"]);
        assert_eq!(case.judgments[0].verdict, validity::Verdict::Required);
        assert_eq!(
            suite.sources[&case.judgments[0].source],
            format!("https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo={id}")
        );
    }
    let labels: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    assert_eq!(labels["-음세"]["kind"], "ending");
    assert_eq!(labels["-음세"]["sources"].as_array().unwrap().len(), 2);
}

#[test]
fn eumse_dictionary_filters_keep_source_paths_and_cli_parity() {
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
                && suite.cases[0].id.starts_with("eumse-policy-")
            {
                assert_eq!((report.required_present, report.forbidden_present), (8, 6));
            } else {
                assert!(report.passed(), "{:?}", report.violations);
            }
        }
    }
}

#[test]
fn eumse_per_entry_classes_do_not_reject_verbal_homonyms_or_certify_prefinals() {
    let fixture = Fixture::new("classes");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (surface, head, verb, adjective) in [
        ("큼세", "크다", "krdict:66584", "krdict:66586"),
        ("멂세", "멀다", "krdict:54855", "krdict:26833"),
        ("있음세", "있다", "krdict:68796", "krdict:68797"),
        ("씀세", "쓰다", "krdict:65172", "krdict:16488"),
    ] {
        let analysis = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&analysis).unwrap();
        let path = analysis
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == "음세"
            })
            .unwrap();
        let assessment = annotation.assess(path);
        let entries = &assessment.lemmas[0].entries;
        assert_eq!(
            entries.iter().find(|e| e.id == verb).unwrap().status,
            Compatibility::Compatible
        );
        let wrong = entries.iter().find(|e| e.id == adjective).unwrap();
        assert_eq!(wrong.status, Compatibility::Incompatible);
        assert_eq!(wrong.conflicts.len(), 1);
        assert_eq!(
            wrong.conflicts[0].rule,
            AttachmentRule::VolitionalPromiseVerb
        );
        assert_eq!(wrong.conflicts[0].morpheme_index, Some(0));
        assert_eq!(assessment.status, Compatibility::Compatible);
    }
    // Track policy uncertainty of already generated generic prefinal hypotheses.
    // These are not required/forbidden linguistic judgments about acceptability.
    for (surface, heads, forms) in [
        ("먹었음세", vec!["먹다"], vec!["었", "음세"]),
        ("먹겠음세", vec!["먹다"], vec!["겠", "음세"]),
        ("좋았음세", vec!["좋다"], vec!["었", "음세"]),
        ("학생이었음세", vec!["학생", "이다"], vec!["었", "음세"]),
        ("먹어봤음세", vec!["먹다", "보다"], vec!["어", "었", "음세"]),
    ] {
        let analysis = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&analysis).unwrap();
        let path = analysis
            .analyses
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
            .unwrap();
        assert_eq!(
            annotation.assess(path).status,
            Compatibility::Unknown,
            "{surface}"
        );
    }
}
