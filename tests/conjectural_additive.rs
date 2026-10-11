//! Original sources and typed expectations are authored before the new rule.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, TokenKind, WordAnalysis};
use serde_json::Value;
use std::{
    collections::BTreeMap,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;
#[path = "../tools/validity.rs"]
mod validity;

struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-conjectural-additive-{test}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/conjectural-additive-native.json",
        )],
        &path,
        "complete-original-conjectural-additive",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), dictionary)
}

fn suite() -> validity::Suite {
    serde_json::from_str(include_str!("fixtures/conjectural-additive-validity.json")).unwrap()
}

fn source() -> Value {
    serde_json::from_str(include_str!("fixtures/conjectural-additive-sources.json")).unwrap()
}

fn is_new(a: &Analysis) -> bool {
    a.rules
        .iter()
        .any(|rule| rule == "ending.conjectural_additive")
}

#[test]
fn independently_authored_source_paths_and_allomorph_boundaries_pass_in_both_encodings() {
    let mut suite = suite();
    assert_eq!(suite.cases.len(), 35);
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        (report.cases, report.required_total, report.forbidden_total),
        (35, 28, 7)
    );
    assert!(!report.review_queue.is_empty());
    for case in &mut suite.cases {
        case.surface = case.surface.nfd().collect();
    }
    let nfd = validity::evaluate(&suite).unwrap();
    assert!(nfd.passed(), "{:?}", nfd.violations);
    assert_eq!(nfd.required_present, 28);
}

#[test]
fn original_native_import_preserves_all_34_owners_and_every_field() {
    let (_cleanup, dictionary) = dictionary("native");
    let owners: BTreeMap<String, Value> = serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-native-entries.json"
    ))
    .unwrap();
    assert_eq!(owners.len(), 34);
    for (id, expected) in &owners {
        assert_eq!(
            serde_json::to_value(dictionary.entry(id).unwrap().unwrap()).unwrap(),
            *expected,
            "{id}"
        );
    }
    for id in ["krdict:86083", "krdict:86084"] {
        assert_eq!(owners[id]["homonym"], "0");
        assert_eq!(owners[id]["pos"], "어미");
        assert_eq!(owners[id]["lexical_unit"], "단어");
        assert_eq!(owners[id]["senses"].as_array().unwrap().len(), 2);
    }
}

#[test]
fn all_original_candidates_are_preserved_without_rewriting_the_baseline() {
    let originals: BTreeMap<String, WordAnalysis> =
        serde_json::from_str(include_str!("fixtures/conjectural-additive-before.json")).unwrap();
    let engine = Lemmatizer::new();
    assert_eq!(originals.len(), 16);
    for (surface, before) in originals {
        assert!(!before.analyses.iter().any(is_new));
        let after = engine.analyze_word(&surface).unwrap();
        for path in &before.analyses {
            assert!(
                after.analyses.contains(path),
                "lost original {surface}: {path:?}"
            );
        }
        for path in after
            .analyses
            .iter()
            .filter(|a| !before.analyses.contains(a))
        {
            assert!(is_new(path), "unrelated addition {surface}: {path:?}");
        }
        assert_eq!(
            after,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
    }
}

#[test]
fn compatible_filter_retains_all_16_original_typed_paths_with_correct_component_owners() {
    let mut suite = suite();
    suite.cases.truncate(16);
    let (_cleanup, dictionary) = dictionary("compatible");
    let engine = Lemmatizer::new();
    for cache in [0, 4096] {
        let mut session = DictionarySession::new(&dictionary, cache);
        let report = validity::evaluate_with(&suite, |surface| {
            let mut word = engine.analyze_word(surface).map_err(|e| e.to_string())?;
            let mut annotation = session.annotate(&word).map_err(|e| e.to_string())?;
            annotation.filter(&mut word, DictionaryFilter::Compatible);
            Ok(word)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
        assert_eq!(report.required_present, 16);
    }
    let word = engine.analyze_word("어두워지려니와").unwrap();
    let path = word
        .analyses
        .iter()
        .find(|a| {
            is_new(a)
                && a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(["어둡다", "지다"])
        })
        .unwrap();
    let order = path.breakdown().unwrap();
    assert_eq!(order.len(), 4);
    assert!(matches!(order[0], klem::breakdown::Component::Lemma(0)));
    assert!(matches!(order[1], klem::breakdown::Component::Morpheme(0)));
    assert!(matches!(order[2], klem::breakdown::Component::Lemma(1)));
    assert!(matches!(order[3], klem::breakdown::Component::Morpheme(1)));
    let mut session = DictionarySession::new(&dictionary, 4096);
    let annotation = session.annotate(&word).unwrap();
    assert_ne!(annotation.assess(path).status, Compatibility::Incompatible);
}

#[test]
fn attachment_licenses_belong_to_the_immediate_owner_and_unlisted_markers_stay_unknown() {
    let policy: Value = serde_json::from_str(include_str!(
        "fixtures/conjectural-additive-attachment-policy.json"
    ))
    .unwrap();
    let (_cleanup, dictionary) = dictionary("prefinal-policy");
    let engine = Lemmatizer::new();
    for cache in [0, 4096] {
        let mut session = DictionarySession::new(&dictionary, cache);
        for case in policy["cases"].as_array().unwrap() {
            let word = engine
                .analyze_word(case["surface"].as_str().unwrap())
                .unwrap();
            let path = word
                .analyses
                .iter()
                .find(|a| {
                    is_new(a)
                        && serde_json::to_value(
                            a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>(),
                        )
                        .unwrap()
                            == case["lemmas"]
                        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>())
                            .unwrap()
                            == case["kinds"]
                        && serde_json::to_value(
                            a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>(),
                        )
                        .unwrap()
                            == case["forms"]
                })
                .unwrap_or_else(|| {
                    panic!("missing independently authored attachment path: {case}")
                });
            let annotation = session.annotate(&word).unwrap();
            assert_eq!(
                serde_json::to_value(annotation.assess(path).status).unwrap(),
                case["status"],
                "{case}"
            );
        }
    }
}

#[test]
fn cli_library_complete_contexts_unicode_filters_caches_and_original_bytes_agree() {
    let (cleanup, dictionary) = dictionary("cli");
    let source = source();
    let original_text = source["complete_source_text"].as_str().unwrap();
    let targets = suite()
        .cases
        .into_iter()
        .take(16)
        .map(|c| c.surface)
        .collect::<Vec<_>>()
        .join(" ");
    let engine = Lemmatizer::new();
    for text in [original_text, targets.as_str()] {
        for encoding in ["NFC", "NFD"] {
            let text = if encoding == "NFD" {
                text.nfd().collect::<String>()
            } else {
                text.to_owned()
            };
            for (mode, filter) in [
                ("raw", None),
                ("headword", Some(DictionaryFilter::Headword)),
                ("compatible", Some(DictionaryFilter::Compatible)),
            ] {
                let mut uncached = None;
                for cache in [0, 4096] {
                    let mut session = DictionarySession::new(&dictionary, cache);
                    let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
                    command.args(["text", "-", "--dictionary"]).arg(&cleanup.0);
                    if mode == "headword" {
                        command.arg("--dict-only");
                    }
                    if mode == "compatible" {
                        command.arg("--dict-compatible");
                    }
                    command.args(["--cache-bytes", &cache.to_string()]);
                    let mut child = command
                        .stdin(Stdio::piped())
                        .stdout(Stdio::piped())
                        .stderr(Stdio::piped())
                        .spawn()
                        .unwrap();
                    child
                        .stdin
                        .take()
                        .unwrap()
                        .write_all(text.as_bytes())
                        .unwrap();
                    let output = child.wait_with_output().unwrap();
                    assert!(output.status.success(), "{:?}", output.stderr);
                    assert!(output.stderr.is_empty());
                    if let Some(before) = &uncached {
                        assert_eq!(before, &output.stdout);
                    } else {
                        uncached = Some(output.stdout.clone());
                    }
                    let rows: Vec<Value> = String::from_utf8(output.stdout)
                        .unwrap()
                        .lines()
                        .map(|line| serde_json::from_str(line).unwrap())
                        .collect();
                    let tokens: Vec<_> = engine.analyze_text(&text).collect();
                    assert_eq!(rows.len(), tokens.len());
                    let mut cursor = 0;
                    for (row, token) in rows.iter().zip(tokens) {
                        assert_eq!(row["span"]["start"], cursor);
                        cursor = row["span"]["end"].as_u64().unwrap() as usize;
                        assert_eq!(row["surface"], &text[token.span.clone()]);
                        let mut expected = serde_json::to_value(&token).unwrap();
                        expected["dictionary"] = Value::Null;
                        if token.kind == TokenKind::Word {
                            let raw = token.analysis.as_ref().unwrap();
                            let mut annotation = session.annotate(raw).unwrap();
                            let mut filtered = raw.as_ref().clone();
                            if let Some(policy) = filter {
                                annotation.filter(&mut filtered, policy);
                            }
                            expected["analysis"] = serde_json::to_value(&filtered).unwrap();
                            expected["dictionary"] = serde_json::to_value(&annotation).unwrap();
                            for path in &filtered.analyses {
                                assert!(path.breakdown().is_some());
                            }
                        }
                        assert_eq!(*row, expected, "{mode} {encoding} {cache}");
                    }
                    assert_eq!(cursor, text.len());
                }
            }
        }
    }
}
