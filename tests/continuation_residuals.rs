//! COV-019af: source differences are tracked without repairing original gold.
#[path = "../tools/validity.rs"]
mod validity;

use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/continuation-residual-sources.json")).unwrap()
}

fn preflight() -> Value {
    serde_json::from_str(include_str!(
        "../docs/continuation-gold-residual-preflight.json"
    ))
    .unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-continuation-residual-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-continuation-residual.json",
            )],
            &path,
            "continuation-residual",
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

fn named<'a>(word: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> (usize, &'a Analysis) {
    word.analyses
        .iter()
        .enumerate()
        .find(|(_, a)| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(heads.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        })
        .unwrap()
}

#[test]
fn complete_native_entries_preserve_homonyms_and_all_source_fields() {
    let source = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    assert_eq!(source["source_entries"].as_array().unwrap().len(), 28);
    for entry in source["source_entries"].as_array().unwrap() {
        let id = entry["id"].as_str().unwrap();
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            *entry
        );
        let mut projected = source["complete_native_entries"][id].clone();
        for sense in projected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(projected, *entry);
    }
    for head in ["짜증내다", "짜증나다"] {
        assert!(db.lookup(head).unwrap().is_empty());
    }
    let lexical = db.entry("krdict:89906").unwrap().unwrap();
    let auxiliary = db.entry("krdict:60625").unwrap().unwrap();
    assert_eq!(lexical.summary.headword, auxiliary.summary.headword);
    assert_eq!(lexical.summary.pos, "동사");
    assert_eq!(lexical.summary.homonym, "1");
    assert_eq!(auxiliary.summary.pos, "보조 동사");
    assert_eq!(auxiliary.summary.homonym, "2");
    assert_eq!(lexical.senses.len(), 31);
}

#[test]
fn scoped_written_boundaries_preserve_original_gold_and_nfd_candidates() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/continuation-residual-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (11, 2));
    let engine = Lemmatizer::new();
    let source = sources();
    assert_eq!(source["observed_words"].as_object().unwrap().len(), 17);
    for (surface, words) in source["observed_words"].as_object().unwrap() {
        let mut value = words["all"].clone();
        value.as_object_mut().unwrap().remove("dictionary");
        value.as_object_mut().unwrap().remove("spacing");
        let original: WordAnalysis = serde_json::from_value(value).unwrap();
        let actual = engine.analyze_word(surface).unwrap();
        assert_eq!(actual.normalized, original.normalized);
        let mut cursor = 0;
        for prior in &original.analyses {
            let relative = actual.analyses[cursor..]
                .iter()
                .position(|a| a == prior)
                .unwrap_or_else(|| panic!("Lost or changed original path in {surface}: {prior:?}"));
            cursor += relative + 1;
        }
        assert_eq!(
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap(),
            actual
        );
        for analysis in &actual.analyses {
            assert_eq!(
                analysis.breakdown().unwrap().len(),
                analysis.lemmas.len() + analysis.morphemes.len()
            );
        }
    }
    let preflight = preflight();
    assert_eq!(preflight["cases"].as_array().unwrap().len(), 6);
    for case in preflight["cases"].as_array().unwrap() {
        let row = &case["original_gold_row"];
        let surface = row["surface"].as_str().unwrap();
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(word.normalized, surface);
        // Historical misses describe the frozen observation, not a requirement
        // that future source-backed implementations must keep failing.
        assert_eq!(row["matched"], false);
        assert_eq!(case["verdict"], "unjudged");
    }
}

#[test]
fn diagnostic_companions_keep_main_verb_auxiliary_and_copula_roles_separate() {
    let fixture = Fixture::new("roles");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, heads, forms, source_id, slot) in [
        (
            "드러난다",
            vec!["드러나다"],
            vec!["는다"],
            "krdict:15034",
            0,
        ),
        (
            "잘하시네요",
            vec!["잘하다"],
            vec!["시", "네요"],
            "krdict:70073",
            0,
        ),
        (
            "편이네요",
            vec!["편", "이다"],
            vec!["네요"],
            "krdict:86232",
            1,
        ),
        (
            "잘하셔내요",
            vec!["잘하다", "내다"],
            vec!["시", "어", "어", "요"],
            "krdict:60625",
            1,
        ),
        ("낼", vec!["내다"], vec!["을"], "krdict:89906", 0),
        ("내시네", vec!["내다"], vec!["시", "네"], "krdict:89906", 0),
        ("내요", vec!["내다"], vec!["어", "요"], "krdict:89906", 0),
    ] {
        let raw = engine.analyze_word(surface).unwrap();
        let (index, _) = named(&raw, &heads, &forms);
        let mut annotation = dictionary.annotate(&raw).unwrap();
        let entry = annotation.readings[index].lemmas[slot]
            .entries
            .iter()
            .find(|e| e.id == source_id)
            .unwrap();
        assert_eq!(entry.status, Compatibility::Compatible, "{surface}");
        assert!(entry.conflicts.is_empty());
        let mut filtered = raw;
        annotation.filter(&mut filtered, DictionaryFilter::Compatible);
        named(&filtered, &heads, &forms);
    }
    for case in preflight()["cases"].as_array().unwrap() {
        let surface = case["original_gold_row"]["surface"].as_str().unwrap();
        let mut word = engine.analyze_word(surface).unwrap();
        let mut annotation = dictionary.annotate(&word).unwrap();
        annotation.filter(&mut word, DictionaryFilter::Compatible);
        if matches!(surface, "드러난다" | "드러나며") {
            assert!(
                word.analyses
                    .iter()
                    .any(|a| { a.lemmas.len() == 1 && a.lemmas[0].text == "드러나다" })
            );
        } else {
            assert!(word.analyses.is_empty(), "{surface}");
        }
    }
}

#[test]
fn cli_streaming_preserves_original_inputs_and_companion_library_parity() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let source = sources();
    let surfaces: Vec<_> = source["observed_words"]
        .as_object()
        .unwrap()
        .keys()
        .collect();
    for cache in [0, 4096] {
        for nfd in [false, true] {
            let words: Vec<String> = surfaces
                .iter()
                .map(|s| if nfd { s.nfd().collect() } else { (*s).clone() })
                .collect();
            let input = words.join(" ");
            for (mode, flags) in [
                (None, vec![]),
                (Some(DictionaryFilter::Headword), vec!["--dict-only"]),
                (
                    Some(DictionaryFilter::Compatible),
                    vec!["--dict-compatible"],
                ),
            ] {
                let mut child = Command::new(env!("CARGO_BIN_EXE_klem"))
                    .args(["text", "-", "--dictionary"])
                    .arg(&fixture.0)
                    .args(["--cache-bytes", &cache.to_string()])
                    .args(flags)
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .stderr(Stdio::piped())
                    .spawn()
                    .unwrap();
                child
                    .stdin
                    .take()
                    .unwrap()
                    .write_all(input.as_bytes())
                    .unwrap();
                let output = child.wait_with_output().unwrap();
                assert!(output.status.success(), "{:?}", output.stderr);
                let records: Vec<Value> = String::from_utf8(output.stdout)
                    .unwrap()
                    .lines()
                    .map(|line| serde_json::from_str(line).unwrap())
                    .collect();
                let word_records: Vec<_> = records.iter().filter(|r| r["kind"] == "word").collect();
                assert_eq!(word_records.len(), words.len());
                let mut dictionary = DictionarySession::new(&db, cache);
                for (surface, record) in words.iter().zip(word_records) {
                    assert_eq!(record["surface"], surface.as_str());
                    let start = record["span"]["start"].as_u64().unwrap() as usize;
                    let end = record["span"]["end"].as_u64().unwrap() as usize;
                    assert_eq!(&input[start..end], surface);
                    let mut word = engine.analyze_word(surface).unwrap();
                    let mut annotation = dictionary.annotate(&word).unwrap();
                    if let Some(mode) = mode {
                        annotation.filter(&mut word, mode);
                    }
                    assert_eq!(record["analysis"], serde_json::to_value(word).unwrap());
                    assert_eq!(
                        record["dictionary"],
                        serde_json::to_value(annotation).unwrap()
                    );
                }
            }
        }
    }
}
