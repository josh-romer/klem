use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{
    io::Write,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "ending.friendly_hortative.sena";
fn observation() -> Value {
    serde_json::from_str(include_str!(
        "fixtures/friendly-hortative-sena-corpus-observation.json"
    ))
    .unwrap()
}
fn sentence() -> String {
    include_str!("fixtures/friendly-hortative-sena-corpus.conllu")
        .lines()
        .find_map(|l| l.strip_prefix("# text = "))
        .unwrap()
        .into()
}
struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
fn dictionary(test: &str) -> (Cleanup, SqliteDictionary) {
    let path =
        std::env::temp_dir().join(format!("klem-sena-corpus-{test}-{}.db", std::process::id()));
    import_krdict(
        &["tests/fixtures/friendly-hortative-sena-corpus-native.json".into()],
        &path,
        "complete-original-kaist-sena-corpus",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), dictionary)
}
fn noun(path: &Analysis) -> bool {
    path.lemmas.len() == 1
        && path.lemmas[0].text == "중세"
        && path.lemmas[0].kind == klem::LemmaKind::Nominal
        && path.morphemes.len() == 1
        && path.morphemes[0].form == "나"
        && path.morphemes[0].kind == klem::MorphemeKind::Particle
}

#[test]
fn original_corpus_case_keeps_full_sentence_token_gold_and_unjudged_hypothesis() {
    let source = observation();
    assert_eq!(
        source["source_sha256"],
        "fd94dc89afb01d1f7f340a46d567e0f27ae6903a70d7b6f650b49f7427f83b97"
    );
    assert_eq!(source["historical_fixture_words_changed"], 0);
    assert_eq!(source["historical_allowances_assigned"], false);
    let item = &source["items"][0];
    assert_eq!(item["id"], "friendly-hortative-sena-kaist-MH2_0180-s63-5");
    assert_eq!(item["sentence_byte_start"], 2_000_347);
    assert_eq!(item["contextual_verdict"], "unjudged");
    assert_eq!(item["independent_korean_review"], "pending");
    let block = item["complete_original_conllu_block"].as_str().unwrap();
    assert_eq!(
        include_str!("fixtures/friendly-hortative-sena-corpus.conllu"),
        format!("{block}\n")
    );
    assert_eq!(
        format!("{:x}", Sha256::digest(block.as_bytes())),
        "ba761c57a4ca369a15c8095a5cb399b6e7834cb5f4315912a38072a123eab8a9"
    );
    let fields = item["complete_original_token_fields"].as_array().unwrap();
    assert_eq!(fields.len(), 10);
    assert_eq!(
        &fields[..5],
        &[
            Value::from("5"),
            Value::from("중세나"),
            Value::from("중세+나"),
            Value::from("CCONJ"),
            Value::from("ncn+jcj")
        ]
    );
    assert_eq!(
        item["original_gold_row"],
        serde_json::json!({
            "id":"id:MH2_0180-s63/5","surface":"중세나","expected":["중세"],
            "matched":true,"recovered":1,"recovered_sets":[[0]]
        })
    );
}

#[test]
fn corpus_candidate_preserves_old_order_and_original_noun_dictionary_owner() {
    let item = observation()["items"][0].clone();
    let previous: WordAnalysis =
        serde_json::from_value(item["complete_original_word_analysis"].clone()).unwrap();
    let engine = Lemmatizer::new();
    let current = engine.analyze_word("중세나").unwrap();
    assert_eq!(current.normalized, previous.normalized);
    assert_eq!(
        current
            .analyses
            .iter()
            .filter(|a| previous.analyses.contains(a))
            .cloned()
            .collect::<Vec<_>>(),
        previous.analyses
    );
    let expected: Vec<Analysis> =
        serde_json::from_value(item["new_unjudged_paths"].clone()).unwrap();
    assert_eq!(
        current
            .analyses
            .iter()
            .filter(|a| a.rules.iter().any(|r| r == RULE))
            .cloned()
            .collect::<Vec<_>>(),
        expected
    );
    let (_cleanup, dictionary) = dictionary("owner");
    let entries: serde_json::Map<String, Value> = serde_json::from_str(include_str!(
        "fixtures/friendly-hortative-sena-corpus-native-entries.json"
    ))
    .unwrap();
    assert_eq!(entries.len(), 1);
    for (ident, expected) in entries {
        assert_eq!(
            serde_json::to_value(dictionary.entry(&ident).unwrap().unwrap()).unwrap(),
            expected
        );
    }
    assert!(dictionary.lookup("중다").unwrap().is_empty());
    for surface in ["중세나".into(), "중세나".nfd().collect::<String>()] {
        let word = engine.analyze_word(&surface).unwrap();
        assert_eq!(word, current);
        for cache in [0, 4096] {
            let annotation = DictionarySession::new(&dictionary, cache)
                .annotate(&word)
                .unwrap();
            let old_noun = word.analyses.iter().find(|a| noun(a)).unwrap();
            assert_eq!(
                annotation.assess(old_noun).status,
                Compatibility::Compatible
            );
            let hypothetical = word
                .analyses
                .iter()
                .find(|a| a.rules.iter().any(|r| r == RULE))
                .unwrap();
            assert_eq!(
                annotation.assess(hypothetical).status,
                Compatibility::Unknown
            );
            assert!(!annotation.has_match(&hypothetical.lemmas[0], false));
        }
    }
}

#[test]
fn whole_corpus_sentence_cli_matches_library_with_filters_unicode_cache_and_byte_spans() {
    let (cleanup, dictionary) = dictionary("cli");
    let engine = Lemmatizer::new();
    for text in [sentence(), sentence().nfd().collect::<String>()] {
        let mut previous = Vec::new();
        for (mode, flag) in [
            ("raw", None),
            ("headword", Some("--dict-only")),
            ("compatible", Some("--dict-compatible")),
        ] {
            let mut word = engine.analyze_word("중세나").unwrap();
            let mut annotation = DictionarySession::new(&dictionary, 0)
                .annotate(&word)
                .unwrap();
            if mode != "raw" {
                annotation.filter(
                    &mut word,
                    if mode == "headword" {
                        DictionaryFilter::Headword
                    } else {
                        DictionaryFilter::Compatible
                    },
                );
            }
            let expected = word.analyses;
            for cache in [0, 8_388_608] {
                let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
                command
                    .args(["text", "-", "--dictionary"])
                    .arg(&cleanup.0)
                    .args(["--cache-bytes", &cache.to_string()]);
                if let Some(flag) = flag {
                    command.arg(flag);
                }
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
                assert!(
                    output.status.success(),
                    "{}",
                    String::from_utf8_lossy(&output.stderr)
                );
                assert!(output.stderr.is_empty());
                let frames: Vec<Value> = String::from_utf8(output.stdout.clone())
                    .unwrap()
                    .lines()
                    .map(|l| serde_json::from_str(l).unwrap())
                    .collect();
                let mut cursor = 0;
                for frame in &frames {
                    let start = frame["span"]["start"].as_u64().unwrap() as usize;
                    let end = frame["span"]["end"].as_u64().unwrap() as usize;
                    assert_eq!(start, cursor);
                    assert_eq!(&text[start..end], frame["surface"].as_str().unwrap());
                    cursor = end;
                }
                assert_eq!(cursor, text.len());
                let target = frames
                    .iter()
                    .find(|f| {
                        f["surface"]
                            .as_str()
                            .is_some_and(|s| s.nfc().collect::<String>() == "중세나")
                    })
                    .unwrap();
                let paths: Vec<Analysis> =
                    serde_json::from_value(target["analysis"]["analyses"].clone()).unwrap();
                assert_eq!(paths, expected, "{mode}");
                assert!(paths.iter().any(noun));
                assert_eq!(
                    paths
                        .iter()
                        .filter(|a| a.rules.iter().any(|r| r == RULE))
                        .count(),
                    usize::from(mode == "raw")
                );
                if cache == 0 {
                    previous = output.stdout;
                } else {
                    assert_eq!(output.stdout, previous);
                }
            }
        }
    }
}
