//! COV-018ab: future questions retain their endings before noun-clause particles.
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, Session, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "particle.future_question";
fn evidence() -> Value {
    let mut fixture: Value =
        serde_json::from_str(include_str!("fixtures/future-question-sources.json")).unwrap();
    let supplement: Value = serde_json::from_str(include_str!(
        "fixtures/future-question-corpus-supplement.json"
    ))
    .unwrap();
    for (surface, before) in supplement["before_words"].as_object().unwrap() {
        if let Some(original) = fixture["before_words"]
            .as_object_mut()
            .unwrap()
            .insert(surface.clone(), before.clone())
        {
            assert_eq!(
                original, *before,
                "{surface}: supplement rewrote its baseline"
            );
        }
    }
    for source in supplement["corpora"].as_array().unwrap() {
        for token in source["tokens"].as_array().unwrap() {
            fixture["corpora"].as_array_mut().unwrap().push(serde_json::json!({
                "source": source["source"],
                "sentences": [{"complete_sentence": token["complete_sentence"], "matched_tokens": [token["source_row"]]}]
            }));
        }
    }
    fixture
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-future-question-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-future-question.json"),
                PathBuf::from("tests/fixtures/krdict-future-question-additional.json"),
            ],
            &path,
            "future-question-test",
        )
        .unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn path(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == c["lemmas"]
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == c["lemma_kinds"]
        && serde_json::to_value(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()).unwrap()
            == c["morphemes"]
}

#[test]
fn complete_native_sources_survive_import_without_contextual_relabeling() {
    let file = Fixture::new("native");
    let db = file.open();
    let fixture = evidence();
    for entry in fixture["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    let additional: Value = serde_json::from_str(include_str!(
        "fixtures/future-question-additional-native.json"
    ))
    .unwrap();
    for (id, entry) in additional["complete_native_entries"].as_object().unwrap() {
        let mut expected = entry.clone();
        for sense in expected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            expected
        );
    }
    let cases = fixture["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 70);
    assert_eq!(
        cases.iter().filter(|c| c["verdict"] == "required").count(),
        58
    );
    for case in cases {
        assert_eq!(case["contextual_verdict"], "unjudged");
        assert_eq!(case["independent_review"], "pending");
    }
}

#[test]
fn individual_paths_unicode_cache_filters_and_cli_agree() {
    let file = Fixture::new("cases");
    let db = file.open();
    let engine = Arc::new(Lemmatizer::new());
    let fixture = evidence();
    for cache in [0, 1, 4096] {
        let mut words = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for case in fixture["cases"].as_array().unwrap() {
            for nfd in [false, true] {
                let surface = case["surface"].as_str().unwrap();
                let text = if nfd {
                    surface.nfd().collect()
                } else {
                    surface.to_owned()
                };
                let result = words.analyze_word(&text).unwrap();
                let annotation = dictionary.annotate(&result).unwrap();
                let matches: Vec<_> = result.analyses.iter().filter(|a| path(a, case)).collect();
                if case["verdict"] == "forbidden" {
                    assert!(matches.is_empty(), "{}: {matches:?}", case["id"]);
                } else {
                    assert!(!matches.is_empty(), "{}: {result:?}", case["id"]);
                    for a in matches {
                        assert!(a.breakdown().is_some(), "{}", case["id"]);
                        assert!(a.rules.iter().any(|r| r == RULE));
                        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
                        // A following particle must inherit the independent ending's
                        // owner judgments, including Unknowns and auxiliary ownership.
                        let mut core = a.clone();
                        core.morphemes.pop();
                        let core_surface = &surface[..surface.len()
                            - case["morphemes"]
                                .as_array()
                                .unwrap()
                                .last()
                                .unwrap()
                                .as_str()
                                .unwrap()
                                .len()];
                        let original: WordAnalysis = serde_json::from_value(
                            fixture["before_words"][core_surface]["analysis"].clone(),
                        )
                        .unwrap();
                        let owner = original
                            .analyses
                            .iter()
                            .position(|old| {
                                old.lemmas == core.lemmas && old.morphemes == core.morphemes
                            })
                            .unwrap_or_else(|| {
                                panic!("{}: no independent ending path", case["id"])
                            });
                        assert_eq!(
                            serde_json::to_value(annotation.assess(a)).unwrap(),
                            fixture["before_words"][core_surface]["dictionary"]["readings"][owner],
                            "{}",
                            case["id"]
                        );
                    }
                }
                for (flag, policy) in [
                    (None, None),
                    (Some("--dict-only"), Some(DictionaryFilter::Headword)),
                    (
                        Some("--dict-compatible"),
                        Some(DictionaryFilter::Compatible),
                    ),
                ] {
                    let mut filtered = (*result).clone();
                    let mut assessed = annotation.clone();
                    if let Some(policy) = policy {
                        assessed.filter(&mut filtered, policy);
                    }
                    if cache == 0 {
                        let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
                        cmd.args(["word", &text, "--dictionary"]).arg(&file.0);
                        if let Some(flag) = flag {
                            cmd.arg(flag);
                        }
                        let cli = cmd.output().unwrap();
                        assert!(cli.status.success());
                        let value: Value = serde_json::from_slice(&cli.stdout).unwrap();
                        assert_eq!(
                            serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                            filtered
                        );
                        assert_eq!(value["dictionary"], serde_json::to_value(assessed).unwrap());
                    }
                }
                assert!(dictionary.cache_bytes() <= cache);
            }
        }
    }
}

#[test]
fn all_prior_words_retain_paths_order_and_dictionary_assessments() {
    let file = Fixture::new("prior");
    let db = file.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let fixture = evidence();
    assert_eq!(fixture["before_words"].as_object().unwrap().len(), 382);
    for (surface, before) in fixture["before_words"].as_object().unwrap() {
        let old: WordAnalysis = serde_json::from_value(before["analysis"].clone()).unwrap();
        for text in [surface.clone(), surface.nfd().collect::<String>()] {
            let new = engine.analyze_word(&text).unwrap();
            assert_eq!(
                new.analyses
                    .iter()
                    .filter(|a| old.analyses.contains(a))
                    .collect::<Vec<_>>(),
                old.analyses.iter().collect::<Vec<_>>(),
                "{surface}"
            );
            let annotation = dictionary.annotate(&new).unwrap();
            for (i, a) in old.analyses.iter().enumerate() {
                assert_eq!(
                    serde_json::to_value(annotation.assess(a)).unwrap(),
                    before["dictionary"]["readings"][i],
                    "{surface}"
                );
            }
            for a in new.analyses.iter().filter(|a| !old.analyses.contains(a)) {
                assert!(a.rules.iter().any(|r| r == RULE), "{surface}: {a:?}");
                let end = a.morphemes.iter().position(|m| m.form == "을지").unwrap();
                assert!(end + 1 < a.morphemes.len());
            }
        }
    }
}

#[test]
fn tracked_native_accident_dependency_gains_main_nada_spacing_with_utf8_spans() {
    let file = Fixture::new("spacing");
    let db = file.open();
    for cache in [0, 1, 4096] {
        let mut words = Session::new(Arc::new(Lemmatizer::new()), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for original in ["사고날지도", "학교에서사고날지도"] {
            for text in [original.to_owned(), original.nfd().collect()] {
                let prefix = "前🙂「";
                let input = format!("{prefix}{text}」");
                let suggestions = klem::spacing::suggest(
                    &mut words,
                    &mut dictionary,
                    &text,
                    prefix.len(),
                    klem::spacing::SpacingLimits::default(),
                )
                .unwrap();
                let expected = if original.starts_with("학교") {
                    vec!["학교에서", "사고", "날지도"]
                } else {
                    vec!["사고", "날지도"]
                };
                let option = suggestions
                    .alternatives
                    .iter()
                    .find(|h| {
                        h.rule == Some("spacing.bare_noun_main_nada")
                            && h.records
                                .iter()
                                .map(|s| s.record.analysis.as_ref().unwrap().normalized.as_str())
                                .eq(expected.iter().copied())
                    })
                    .unwrap_or_else(|| panic!("{text}: {suggestions:?}"));
                let right = option.records.last().unwrap();
                assert!(
                    right
                        .record
                        .analysis
                        .as_ref()
                        .unwrap()
                        .analyses
                        .iter()
                        .any(|a| a.lemmas[0].text == "나다"
                            && a.rules.iter().any(|r| r == RULE)
                            && a.morphemes
                                .iter()
                                .map(|m| m.form.as_str())
                                .eq(["을지", "도"])
                            && right.dictionary.assess(a).lemmas[0]
                                .entries
                                .iter()
                                .any(|e| e.id == "krdict:62210"))
                );
                for segment in &option.records {
                    assert_eq!(&input[segment.record.span.clone()], segment.record.surface);
                }
            }
        }
    }
}

#[path = "../tools/corpus.rs"]
#[allow(dead_code)]
mod corpus;

#[test]
fn original_annotated_question_tokens_keep_their_gold_and_gain_lexical_recovery() {
    let fixture = evidence();
    let engine = Lemmatizer::new();
    let mut total = 0;
    let mut old_matches = 0;
    let mut new_matches = 0;
    for source in fixture["corpora"].as_array().unwrap() {
        let kind = if source["source"].as_str().unwrap().contains("/kaist/") {
            corpus::Corpus::Kaist
        } else {
            corpus::Corpus::Gsd
        };
        for sentence in source["sentences"].as_array().unwrap() {
            for row in sentence["matched_tokens"].as_array().unwrap() {
                let fields: Vec<_> = row
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|v| v.as_str().unwrap())
                    .collect();
                assert!(
                    sentence["complete_sentence"]
                        .as_str()
                        .unwrap()
                        .lines()
                        .any(|line| line == fields.join("\t"))
                );
                let corpus::Conversion::Gold(gold) = corpus::convert(&fields, kind) else {
                    panic!("unsupported original annotation: {fields:?}");
                };
                let old: WordAnalysis =
                    serde_json::from_value(fixture["before_words"][fields[1]]["analysis"].clone())
                        .unwrap();
                let old_match = old
                    .analyses
                    .iter()
                    .any(|a| a.lemmas.iter().map(|l| &l.text).eq(gold.iter()));
                old_matches += usize::from(old_match);
                let new = engine.analyze_word(fields[1]).unwrap();
                let new_match = new
                    .analyses
                    .iter()
                    .any(|a| a.lemmas.iter().map(|l| &l.text).eq(gold.iter()));
                assert!(!old_match || new_match, "lost original gold: {fields:?}");
                new_matches += usize::from(new_match);
                total += 1;
            }
        }
    }
    assert_eq!(total, 50);
    assert_eq!(old_matches, 1);
    assert_eq!(new_matches, 50);
    println!(
        "Original annotation matches: {old_matches} before, {new_matches} after, {total} tokens"
    );
}
