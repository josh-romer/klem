//! COV-017bb: background connective bundles, not bound noun 바.
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
    suite.cases.retain(|c| c.id.starts_with("ba-"));
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
        let path = std::env::temp_dir().join(format!("klem-ba-{}-{name}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-ba.json")],
            &path,
            "ba",
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
fn background_ba_preserves_local_boundaries_prefinals_and_component_owners() {
    let suite = raw_suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (78, 20));
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
    for (surface, head, class) in [
        ("들은바", "듣다", Some(SpellingClass::DigeutIrregular)),
        ("산바", "살다", None),
    ] {
        let result = engine.analyze_word(surface).unwrap();
        let path = result
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == "은바"
            })
            .unwrap();
        if let Some(class) = class {
            assert!(
                path.spelling_paths
                    .iter()
                    .flatten()
                    .any(|r| r.morpheme_index == 0 && r.class == class)
            );
        } else {
            assert!(path.rules.iter().any(|r| r == "deletion.rieul"));
        }
        assert!(path.rules.iter().any(|r| r == "ending.background_ba"));
    }
    // Lexicalized adverb and ambiguous 사다/살다 readings coexist.
    let san = engine.analyze_word("산바").unwrap();
    for head in ["사다", "살다"] {
        assert!(san.analyses.iter().any(|a| a.lemmas.len() == 1
            && a.lemmas[0].text == head
            && a.morphemes.len() == 1
            && a.morphemes[0].form == "은바"));
    }
    assert!(
        engine
            .analyze_word("이른바")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.unchanged)
    );
}

#[test]
fn background_ba_sources_preserve_all_senses_and_complete_example_groups() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/ba-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-ba.json")).unwrap();
    let entries = fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(entries.len(), 84);
    assert_eq!(source["entry_ids"].as_array().unwrap().len(), entries.len());
    let examples = source["primary_examples"].as_array().unwrap();
    assert_eq!(examples.len(), 24);
    let mut seen = std::collections::BTreeSet::new();
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
        assert!(seen.insert((id, example["sense_id"].as_str().unwrap(), group)));
        let feats = &sense["SenseExample"][group - 1]["feat"];
        let features = if let Some(array) = feats.as_array() {
            array.clone()
        } else {
            vec![feats.clone()]
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
    for id in [87110, 87111, 87112, 87113] {
        let entry = entries
            .iter()
            .find(|e| e["val"].as_str() == Some(&id.to_string()))
            .unwrap();
        for sense in entry["Sense"].as_array().unwrap() {
            for group in 1..=sense["SenseExample"].as_array().unwrap().len() {
                assert!(seen.contains(&(id, sense["val"].as_str().unwrap(), group)));
            }
        }
    }
    let labels: serde_json::Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    for (form, count) in [("-은바", 2), ("-는바", 1), ("-던바", 1)] {
        assert_eq!(labels[form]["kind"], "ending");
        assert_eq!(labels[form]["sources"].as_array().unwrap().len(), count);
    }
}

#[test]
fn background_ba_dictionary_filters_preserve_source_paths_and_cli_parity() {
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
            if filter == DictionaryFilter::Headword && suite.cases[0].id.starts_with("ba-policy-") {
                assert_eq!((report.required_present, report.forbidden_present), (8, 5));
            } else {
                assert!(report.passed(), "{:?}", report.violations);
            }
        }
    }
}

#[test]
fn background_ba_checks_each_bare_entry_and_preserves_verb_homonyms() {
    let fixture = Fixture::new("classes");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let analysis = engine.analyze_word("크는바").unwrap();
    let annotation = dictionary.annotate(&analysis).unwrap();
    let path = analysis
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "크다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "는바"
        })
        .unwrap();
    let assessment = annotation.assess(path);
    let entries = &assessment.lemmas[0].entries;
    assert_eq!(
        entries
            .iter()
            .find(|e| e.id == "krdict:66584")
            .unwrap()
            .status,
        Compatibility::Compatible
    );
    let adjective = entries.iter().find(|e| e.id == "krdict:66586").unwrap();
    assert_eq!(adjective.status, Compatibility::Incompatible);
    assert!(
        adjective
            .conflicts
            .iter()
            .any(|c| c.rule == AttachmentRule::BareBackgroundVerb && c.morpheme_index == Some(0))
    );
    assert_eq!(assessment.status, Compatibility::Compatible);
    for surface in ["있는바", "없는바", "재미있는바", "맛없는바", "좋았는바"] {
        let analysis = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&analysis).unwrap();
        let head = if surface == "좋았는바" {
            "좋다"
        } else {
            match surface {
                "있는바" => "있다",
                "없는바" => "없다",
                "재미있는바" => "재미있다",
                _ => "맛없다",
            }
        };
        let path = analysis
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes.last().is_some_and(|m| m.form == "는바")
            })
            .unwrap();
        assert_eq!(
            annotation.assess(path).status,
            Compatibility::Compatible,
            "{surface}"
        );
    }
}
