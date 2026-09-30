//! COV-017bc: comparison, listing/assertion and reason bundles.
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
    suite.cases.retain(|c| c.id.starts_with("neuni-"));
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
            std::env::temp_dir().join(format!("klem-neuni-{}-{name}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-neuni.json")],
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

#[test]
fn neuni_bundles_preserve_local_boundaries_and_ordered_owners() {
    let suite = raw_suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (111, 40));
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
    let result = engine.analyze_word("사느니").unwrap();
    for head in ["살다", "사다"] {
        let path = result
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == "느니"
            })
            .unwrap();
        assert!(path.rules.iter().any(|r| r == "ending.neuni"));
        if head == "살다" {
            assert!(path.rules.iter().any(|r| r == "deletion.rieul"));
        }
    }
    let result = engine.analyze_word("그랬느니").unwrap();
    let path = result
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "그렇다"
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["었", "느니"])
        })
        .unwrap();
    assert!(
        path.spelling_paths
            .iter()
            .flatten()
            .any(|r| r.morpheme_index == 0 && r.class == SpellingClass::HieutIrregular)
    );
}

#[test]
fn neuni_sources_preserve_all_native_senses_groups_and_exact_expression_identity() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/neuni-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-neuni.json")).unwrap();
    let entries = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 103);
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), entries.len());
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 39);
    let mut groups = std::collections::BTreeSet::new();
    let mut tokens = std::collections::BTreeSet::new();
    let suite = raw_suite();
    for example in examples {
        let id = example["entry_id"].as_u64().unwrap();
        let entry = entries
            .iter()
            .find(|e| e["val"].as_str() == Some(&id.to_string()))
            .unwrap();
        let sense = entry["Sense"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["val"] == example["sense_id"])
            .unwrap();
        let group = example["example_group"].as_u64().unwrap() as usize;
        groups.insert((id, example["sense_id"].as_str().unwrap(), group));
        assert!(tokens.insert((id, group, example["surface"].as_str().unwrap())));
        let features = &sense["SenseExample"][group - 1]["feat"];
        let features = if let Some(a) = features.as_array() {
            a.clone()
        } else {
            vec![features.clone()]
        };
        assert!(features.iter().any(|f| {
            f["att"] == "example"
                && f["val"]
                    .as_str()
                    .unwrap()
                    .contains(example["original"].as_str().unwrap())
        }));
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
    assert_eq!(groups.len(), 34);
    for id in [85722, 85723, 80839, 85725, 85726, 85824, 85727, 85728] {
        let entry = entries
            .iter()
            .find(|e| e["val"].as_str() == Some(&id.to_string()))
            .unwrap();
        for sense in entry["Sense"].as_array().unwrap() {
            for group in 1..=sense["SenseExample"].as_array().unwrap().len() {
                assert!(groups.contains(&(id, sense["val"].as_str().unwrap(), group)));
            }
        }
    }
    let labels: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    for (form, count) in [
        ("-느니", 3),
        ("-느니만", 1),
        ("-느니만큼", 1),
        ("-니만", 1),
        ("-으니만큼", 2),
    ] {
        assert_eq!(labels[form]["kind"], "ending");
        assert_eq!(labels[form]["sources"].as_array().unwrap().len(), count);
    }
    assert_eq!(labels["-니만"]["sources"][0]["id"], 85824);
    assert_eq!(labels["-니만"]["sources"][0]["pos"], "품사 없음");
    assert!(labels.get("-으니만").is_none());
}

#[test]
fn neuni_dictionary_filters_preserve_source_paths_unicode_and_cli_parity() {
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
                && suite.cases[0].id.starts_with("neuni-policy-")
            {
                assert_eq!((report.required_present, report.forbidden_present), (10, 6));
            } else {
                assert!(report.passed(), "{:?}", report.violations);
            }
        }
    }
}

#[test]
fn neuni_homonyms_and_unreviewed_distributions_remain_independent() {
    let fixture = Fixture::new("classes");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (word, form, verb, adjective, rule) in [
        (
            "크느니",
            "느니",
            Compatibility::Compatible,
            Compatibility::Incompatible,
            AttachmentRule::BareNeuniVerb,
        ),
        (
            "크니만",
            "니만",
            Compatibility::Incompatible,
            Compatibility::Compatible,
            AttachmentRule::BareNimanAdjective,
        ),
        (
            "크니만큼",
            "으니만큼",
            Compatibility::Unknown,
            Compatibility::Compatible,
            AttachmentRule::BareNimanAdjective,
        ),
    ] {
        let analysis = engine.analyze_word(word).unwrap();
        let annotation = dictionary.annotate(&analysis).unwrap();
        let path = analysis
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == "크다"
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == form
            })
            .unwrap();
        let assessment = annotation.assess(path);
        let entries = &assessment.lemmas[0].entries;
        let v = entries.iter().find(|e| e.id == "krdict:66584").unwrap();
        let a = entries.iter().find(|e| e.id == "krdict:66586").unwrap();
        assert_eq!(v.status, verb, "{word}");
        assert_eq!(a.status, adjective, "{word}");
        if verb == Compatibility::Incompatible {
            assert!(
                v.conflicts
                    .iter()
                    .any(|c| c.rule == rule && c.morpheme_index == Some(0))
            );
        }
        if adjective == Compatibility::Incompatible {
            assert!(
                a.conflicts
                    .iter()
                    .any(|c| c.rule == rule && c.morpheme_index == Some(0))
            );
        }
        assert_eq!(assessment.status, Compatibility::Compatible);
    }
    for (word, head, forms, status) in [
        (
            "아니만큼",
            "알다",
            vec!["으니만큼"],
            Compatibility::Compatible,
        ),
        ("하니만큼", "하다", vec!["으니만큼"], Compatibility::Unknown),
        ("가니만", "가다", vec!["니만"], Compatibility::Unknown),
        (
            "맛없느니만",
            "맛없다",
            vec!["느니만"],
            Compatibility::Unknown,
        ),
        (
            "먹었느니만",
            "먹다",
            vec!["었", "느니만"],
            Compatibility::Unknown,
        ),
        (
            "먹겠느니만큼",
            "먹다",
            vec!["겠", "느니만큼"],
            Compatibility::Unknown,
        ),
        (
            "좋으시니만",
            "좋다",
            vec!["시", "니만"],
            Compatibility::Unknown,
        ),
        (
            "먹어야겠느니",
            "먹다",
            vec!["어야겠", "느니"],
            Compatibility::Unknown,
        ),
    ] {
        let mut analysis = engine.analyze_word(word).unwrap();
        let mut annotation = dictionary.annotate(&analysis).unwrap();
        let path = analysis
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap()
            .clone();
        assert_eq!(annotation.assess(&path).status, status, "{word}: {path:?}");
        annotation.filter(&mut analysis, DictionaryFilter::Compatible);
        assert!(analysis.analyses.contains(&path), "{word}");
    }
}
