//! COV-017bw: emphatic purpose and affirmation source boundaries.
#[path = "../tools/hada_nominal_preservation.rs"]
mod hada_preservation;
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, Session};
use serde_json::Value;
use std::{collections::HashSet, fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;
fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/emphatic-ending-sources.json")).unwrap()
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == c["lemmas"]
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == c["lemma_kinds"]
        && serde_json::to_value(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()).unwrap()
            == c["morphemes"]
        && serde_json::to_value(a.morphemes.iter().map(|m| m.kind).collect::<Vec<_>>()).unwrap()
            == c["morpheme_kinds"]
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-emphatic-ending-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-emphatic-ending.json")],
            &path,
            "emphatic-ending-test",
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
fn complete_native_entries_and_labels_preserve_source_identity() {
    let file = Fixture::new("native");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let f = evidence();
    assert_eq!(f["cases"].as_array().unwrap().len(), 132);
    for entry in f["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    let catalog: Value =
        serde_json::from_str(include_str!("../web/src/grammar-labels.json")).unwrap();
    for (form, id) in [("-게끔", 88382), ("-고말고", 66991), ("-다마다", 75968)] {
        assert_eq!(catalog[form]["sources"][0]["id"], id);
        assert_eq!(catalog[form]["sources"][0]["pos"], "어미");
    }
    for c in f["cases"].as_array().unwrap() {
        assert_eq!(c["contextual_verdict"], "unjudged");
        assert_eq!(c["independent_review"], "pending");
    }
}
#[test]
fn all_named_paths_unicode_cache_and_ordered_components_agree() {
    let f = evidence();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        for c in f["cases"].as_array().unwrap() {
            let surface = c["surface"].as_str().unwrap();
            let word = session.analyze_word(surface).unwrap();
            assert_eq!(
                word,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
            let paths: Vec<_> = word.analyses.iter().filter(|a| matches(a, c)).collect();
            assert_eq!(
                !paths.is_empty(),
                c["verdict"] == "required",
                "{} {surface}: {word:?}",
                c["id"]
            );
            for a in paths {
                if c["verdict"] == "required" {
                    for r in c["required_rules"].as_array().unwrap() {
                        assert!(a.rules.iter().any(|rule| rule == r.as_str().unwrap()));
                    }
                }
            }
            for a in &word.analyses {
                assert!(a.breakdown().is_some(), "{surface}: {a:?}");
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            }
        }
    }
}
#[test]
fn central_paths_survive_dictionary_filters() {
    let f = evidence();
    let ids: HashSet<_> = f["cases"]
        .as_array()
        .unwrap()
        .iter()
        .map(|c| c["id"].as_str().unwrap())
        .collect();
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| ids.contains(c.id.as_str()));
    let report = validity::evaluate(&suite).unwrap();
    assert_eq!((report.required_total, report.forbidden_total), (109, 23));
    assert!(report.passed(), "{:?}", report.violations);
    let file = Fixture::new("policy");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let mut dict = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let policy_ids: HashSet<_> = ids.iter().map(|id| format!("{id}-policy")).collect();
    let mut policy: validity::Suite =
        serde_json::from_str(include_str!("fixtures/dictionary-attachments.json")).unwrap();
    policy.cases.retain(|c| policy_ids.contains(&c.id));
    for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
        let report = validity::evaluate_with(&policy, |surface| {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut native = dict.annotate(&word).unwrap();
            native.filter(&mut word, filter);
            Ok(word)
        })
        .unwrap();
        assert_eq!((report.required_total, report.forbidden_total), (107, 25));
        assert_eq!(
            report.required_present, 107,
            "{filter:?}: {:?}",
            report.violations
        );
        // KRDict lists 되다 as a verb, while the raw parser uses a legacy
        // auxiliary role. Preserve that known policy conflict explicitly;
        // headword matches do not certify the auxiliary-role representation.
        assert_eq!(
            report.forbidden_present,
            if filter == DictionaryFilter::Headword {
                2
            } else {
                0
            },
            "{filter:?}: {:?}",
            report.violations
        );
    }
    for (surface, head, forms) in [
        ("먹었게끔", "먹다", vec!["었", "게끔"]),
        ("먹겠게끔", "먹다", vec!["겠", "게끔"]),
        ("먹겠고말고", "먹다", vec!["겠", "고말고"]),
        ("먹겠다마다", "먹다", vec!["겠", "다마다"]),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let native = dict.annotate(&word).unwrap();
        let mut found = 0;
        for (a, r) in word.analyses.iter().zip(&native.readings) {
            if a.lemmas.len() == 1
                && a.lemmas[0].text == head
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
            {
                assert_eq!(
                    r.status,
                    klem::dictionary::Compatibility::Unknown,
                    "{surface}: {r:?}"
                );
                found += 1;
            }
        }
        assert!(found > 0, "{surface}");
    }
}
#[test]
fn every_frozen_candidate_retains_its_native_reading_and_cli_filters_agree() {
    let file = Fixture::new("retention");
    let db = SqliteDictionary::open(&file.0).unwrap();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, before) in evidence()["before_words"].as_object().unwrap() {
        let word = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let original: Vec<Analysis> =
            serde_json::from_value(before["analysis"]["analyses"].clone()).unwrap();
        let readings = before["dictionary"]["readings"].as_array().unwrap();
        let mut cursor = 0;
        for (i, prior) in original.iter().enumerate() {
            let position = word.analyses[cursor..]
                .iter()
                .position(|a| a == prior)
                .unwrap_or_else(|| panic!("{surface}: prior path lost: {prior:?}"))
                + cursor;
            assert_eq!(
                serde_json::to_value(&annotation.readings[position]).unwrap(),
                readings[i],
                "{surface}"
            );
            cursor = position + 1;
        }
        for a in &hada_preservation::project_remaining(&word).analyses {
            if !original.contains(a) {
                assert!(
                    a.rules.iter().any(|r| matches!(
                        r.as_str(),
                        "ending.emphatic_purpose" | "ending.emphatic_affirmation"
                    )),
                    "{surface}: {a:?}"
                );
            }
        }
        for filter in [
            None,
            Some(DictionaryFilter::Headword),
            Some(DictionaryFilter::Compatible),
        ] {
            let mut expected = word.clone();
            let mut native = annotation.clone();
            if let Some(f) = filter {
                native.filter(&mut expected, f);
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", surface, "--dictionary"]).arg(&file.0);
            if let Some(f) = filter {
                cmd.arg(if f == DictionaryFilter::Headword {
                    "--dict-only"
                } else {
                    "--dict-compatible"
                });
            }
            let result = cmd.output().unwrap();
            assert!(result.status.success());
            let mut actual: Value = serde_json::from_slice(&result.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(native).unwrap()
            );
            assert_eq!(actual, serde_json::to_value(expected).unwrap());
        }
    }
}
