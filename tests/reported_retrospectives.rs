//! Contracted recalled reports retain native attachment distinctions and prior paths.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, Session, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "ending.reporting_retrospective";
fn evidence() -> Value {
    let mut fixture: Value =
        serde_json::from_str(include_str!("fixtures/reported-retrospective-sources.json")).unwrap();
    let followers: Value = serde_json::from_str(include_str!(
        "fixtures/reported-retrospective-followers.json"
    ))
    .unwrap();
    fixture["cases"]
        .as_array_mut()
        .unwrap()
        .extend(followers["cases"].as_array().unwrap().iter().cloned());
    let corrections: Value = serde_json::from_str(include_str!(
        "fixtures/reported-retrospective-corrections.json"
    ))
    .unwrap();
    for change in corrections["superseded"].as_array().unwrap() {
        let old = fixture["cases"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|c| c["id"] == change["original"]["id"])
            .unwrap();
        assert_eq!(*old, change["original"]);
        *old = change["replacement"].clone();
    }
    fixture["cases"]
        .as_array_mut()
        .unwrap()
        .extend(corrections["cases"].as_array().unwrap().iter().cloned());
    for (surface, before) in corrections["before_words"].as_object().unwrap() {
        if let Some(previous) = fixture["before_words"]
            .as_object_mut()
            .unwrap()
            .insert(surface.clone(), before.clone())
        {
            assert_eq!(previous, *before);
        }
    }
    for entry in corrections["complete_native_entries"]
        .as_object()
        .unwrap()
        .values()
    {
        let mut entry = entry.clone();
        for sense in entry["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        fixture["source_entries"]
            .as_array_mut()
            .unwrap()
            .push(entry);
    }
    let additional: Value = serde_json::from_str(include_str!(
        "fixtures/reported-retrospective-additional-native.json"
    ))
    .unwrap();
    for entry in additional["complete_native_entries"]
        .as_object()
        .unwrap()
        .values()
    {
        let mut entry = entry.clone();
        for sense in entry["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        fixture["source_entries"]
            .as_array_mut()
            .unwrap()
            .push(entry);
    }
    fixture
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-reported-retrospective-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-reported-retrospective.json"),
                PathBuf::from("tests/fixtures/krdict-reported-retrospective-corrections.json"),
                PathBuf::from("tests/fixtures/krdict-reported-retrospective-additional.json"),
            ],
            &path,
            "reported-retrospective-test",
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
    let cases = fixture["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 182);
    assert_eq!(
        cases.iter().filter(|c| c["verdict"] == "required").count(),
        135
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
                        let assessed = annotation.assess(a);
                        let status = match case["ending_owner_status"].as_str().unwrap() {
                            "compatible" => Compatibility::Compatible,
                            "incompatible" => Compatibility::Incompatible,
                            "unknown" => Compatibility::Unknown,
                            other => panic!("unexpected source judgment {other}"),
                        };
                        let owner = assessed.lemmas.last().unwrap();
                        assert!(
                            (owner.entries.is_empty() && status == Compatibility::Unknown)
                                || owner.entries.iter().any(|e| e.status == status),
                            "{}: {assessed:?}",
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
    assert_eq!(fixture["before_words"].as_object().unwrap().len(), 605);
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
                assert!(
                    a.morphemes
                        .iter()
                        .any(|m| m.kind == klem::MorphemeKind::Ending
                            && matches!(
                                m.form.as_str(),
                                "다던"
                                    | "다던데"
                                    | "는다던"
                                    | "는다던데"
                                    | "라던"
                                    | "라던데"
                                    | "으라던"
                                    | "으라던데"
                                    | "자던"
                                    | "자던데"
                                    | "냐던데"
                                    | "느냐던데"
                                    | "으냐던데"
                            ))
                );
            }
        }
    }
}

#[test]
fn tracked_native_announcement_dependency_gains_main_nada_spacing_with_utf8_spans() {
    let file = Fixture::new("spacing");
    let db = file.open();
    for cache in [0, 1, 4096] {
        let mut words = Session::new(Arc::new(Lemmatizer::new()), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for original in ["발표났다던데", "학교에서발표났다던데"] {
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
                    vec!["학교에서", "발표", "났다던데"]
                } else {
                    vec!["발표", "났다던데"]
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
                                .eq(["었", "다던데"])
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
fn original_annotations_preserve_existing_matches_and_expose_conversion_disagreements() {
    let fixture = evidence();
    let engine = Lemmatizer::new();
    let mut total = 0;
    let mut before_matches = 0;
    let mut after_matches = 0;
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
                    panic!("{fields:?}");
                };
                let old: WordAnalysis =
                    serde_json::from_value(fixture["before_words"][fields[1]]["analysis"].clone())
                        .unwrap();
                let new = engine.analyze_word(fields[1]).unwrap();
                let matches = |word: &WordAnalysis| {
                    word.analyses
                        .iter()
                        .any(|a| a.lemmas.iter().map(|l| &l.text).eq(gold.iter()))
                };
                let b = matches(&old);
                let a = matches(&new);
                assert!(!b || a, "lost original annotation: {fields:?}");
                println!("{}: {gold:?}: {b} -> {a}", fields[1]);
                total += 1;
                before_matches += usize::from(b);
                after_matches += usize::from(a);
            }
        }
    }
    assert_eq!(total, 12);
    assert_eq!(before_matches, 4);
    assert_eq!(after_matches, 11);
    println!(
        "Original annotation matches: {before_matches} before, {after_matches} after, {total} tokens"
    );
}

#[test]
fn closed_adjectival_report_retains_irregular_stems_without_open_or_rieul_aliases() {
    let fixture: Value = serde_json::from_str(include_str!(
        "fixtures/reported-retrospective-boundaries.json"
    ))
    .unwrap();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut session = Session::new(engine.clone(), cache);
        for case in fixture["cases"].as_array().unwrap() {
            for text in [
                case["surface"].as_str().unwrap().to_owned(),
                case["surface"].as_str().unwrap().nfd().collect(),
            ] {
                let word = session.analyze_word(&text).unwrap();
                let found = word.analyses.iter().any(|a| path(a, case));
                assert_eq!(
                    found,
                    case["verdict"] == "required",
                    "{}: {word:?}",
                    case["id"]
                );
            }
        }
    }
}
