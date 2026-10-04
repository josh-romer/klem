//! COV-017br: source-listed -랴 + concessive particles and own-owner uncertainty.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, MorphemeKind, Session, WordAnalysis};
use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;

fn fixture() -> Value {
    serde_json::from_str(include_str!("fixtures/rya-boundary-sources.json")).unwrap()
}
fn regressions() -> Value {
    serde_json::from_str(include_str!("fixtures/rya-boundary-regressions.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-rya-boundary-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-rya-boundary.json")],
            &path,
            "rya-boundary-test",
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
fn path(a: &Analysis, case: &Value) -> bool {
    serde_json::to_value(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()).unwrap()
        == case["lemmas"]
        && serde_json::to_value(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()).unwrap()
            == case["lemma_kinds"]
        && serde_json::to_value(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()).unwrap()
            == case["morphemes"]
}

#[test]
fn every_native_ending_and_particle_owner_survives_fixture_import() {
    let file = Fixture::new("native");
    let db = file.open();
    let native = regressions();
    assert_eq!(native["source_entries"].as_array().unwrap().len(), 99);
    for entry in native["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
}

#[test]
fn source_cases_preserve_ending_particle_roles_irregulars_auxiliaries_and_spans() {
    let engine = Lemmatizer::new();
    let ledger = fixture();
    assert_eq!(ledger["cases"].as_array().unwrap().len(), 63);
    for case in ledger["cases"].as_array().unwrap() {
        for nfd in [false, true] {
            let surface = case["surface"].as_str().unwrap();
            let surface = if nfd {
                surface.nfd().collect::<String>()
            } else {
                surface.to_owned()
            };
            let word = engine.analyze_word(&surface).unwrap();
            if case["verdict"] == "required" {
                let a = word
                    .analyses
                    .iter()
                    .find(|a| path(a, case))
                    .unwrap_or_else(|| panic!("{}: {:?}", case["id"], word));
                assert!(a.rules.iter().any(|r| r == "ending.rya"));
                assert!(a.breakdown().is_some());
                let has_particle = case["morphemes"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|m| m == "마는" || m == "만");
                if has_particle {
                    assert!(a.rules.iter().any(|r| r == "particle.concessive"));
                    assert!(
                        a.morphemes
                            .iter()
                            .any(|m| m.kind == MorphemeKind::Ending && m.form == "으랴")
                    );
                    assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Particle);
                }
            } else if case["verdict"] == "forbidden" {
                let head = case["lemma"].as_str().unwrap();
                assert!(
                    !word.analyses.iter().any(|a| {
                        a.lemmas.iter().any(|l| l.text == head)
                            && ((a.morphemes.iter().any(|m| m.form == "으랴")
                                && a.morphemes
                                    .last()
                                    .is_some_and(|m| m.form == "마는" || m.form == "요"))
                                || a.morphemes
                                    .iter()
                                    .any(|m| m.kind == MorphemeKind::Particle && m.form == "마는"))
                    }),
                    "{}",
                    case["id"]
                );
            }
        }
    }
}

#[test]
fn original_raw_paths_and_known_conflicts_survive_with_unreviewed_prefinals_unknown() {
    let file = Fixture::new("before");
    let db = file.open();
    let evidence = regressions();
    let engine = Arc::new(Lemmatizer::new());
    for cache in [0, 1, 4096] {
        let mut words = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for (surface, before) in evidence["before_words"].as_object().unwrap() {
            let old: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
            for text in [surface.clone(), surface.nfd().collect()] {
                let new = words.analyze_word(&text).unwrap();
                assert_eq!(new.normalized, old.normalized);
                assert_eq!(
                    new.analyses
                        .iter()
                        .filter(|a| old.analyses.contains(a))
                        .collect::<Vec<_>>(),
                    old.analyses.iter().collect::<Vec<_>>(),
                    "{surface}"
                );
                for a in new.analyses.iter().filter(|a| !old.analyses.contains(a)) {
                    assert!(
                        a.rules.iter().any(|r| r == "ending.rya")
                            && a.rules.iter().any(|r| r == "particle.concessive"),
                        "{surface}: {a:?}"
                    );
                }
                let annotation = dictionary.annotate(&new).unwrap();
                for (index, a) in old.analyses.iter().enumerate() {
                    let actual = serde_json::to_value(annotation.assess(a)).unwrap();
                    let previous = &before["dictionary"]["readings"][index];
                    for (b, now) in previous["lemmas"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .zip(actual["lemmas"].as_array().unwrap())
                    {
                        assert_eq!(b["lemma_index"], now["lemma_index"]);
                        assert_eq!(
                            b["entries"].as_array().unwrap().len(),
                            now["entries"].as_array().unwrap().len()
                        );
                        for (be, ae) in b["entries"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .zip(now["entries"].as_array().unwrap())
                        {
                            assert_eq!(be["id"], ae["id"]);
                            assert_eq!(be["conflicts"], ae["conflicts"]);
                            if be != ae {
                                assert_eq!(be["status"], "compatible");
                                assert_eq!(ae["status"], "unknown");
                                assert!(
                                    a.morphemes.iter().any(|m| m.kind == MorphemeKind::Prefinal
                                        && !matches!(m.form.as_str(), "시" | "었" | "겠")),
                                    "{surface}"
                                );
                            }
                        }
                    }
                }
            }
        }
    }
    let ledger = fixture();
    let mut dictionary = DictionarySession::new(&db, 4096);
    for case in ledger["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["verdict"] == "unknown_entry")
    {
        let word = engine
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let mut found = false;
        for a in &word.analyses {
            if !a.rules.iter().any(|r| r == "ending.rya") {
                continue;
            }
            let Some(slot) = a.lemmas.iter().position(|l| l.text == case["lemma"]) else {
                continue;
            };
            let assessment = annotation.assess(a);
            let entries = &assessment.lemmas[slot].entries;
            if entries.iter().any(|e| e.status == Compatibility::Unknown) {
                found = true;
            }
            assert!(
                !entries
                    .iter()
                    .any(|e| e.status == Compatibility::Compatible),
                "{}",
                case["id"]
            );
        }
        assert!(found, "{}", case["id"]);
    }
    // A retrospective marker on the connector owner cannot uncertify bare 보랴.
    let word = engine.analyze_word("먹었어보랴").unwrap();
    let annotation = dictionary.annotate(&word).unwrap();
    let mut found = false;
    for a in word.analyses.iter().filter(|a| {
        a.lemmas.len() == 2
            && a.lemmas[1].text == "보다"
            && a.rules.iter().any(|r| r == "ending.rya")
    }) {
        found = true;
        assert!(
            annotation.assess(a).lemmas[1]
                .entries
                .iter()
                .any(|e| e.status == Compatibility::Compatible)
        );
    }
    assert!(
        found,
        "the prior-owner composition must actually be represented"
    );
}

#[test]
fn cli_filters_cache_sizes_and_unicode_offsets_match_library_annotations() {
    let file = Fixture::new("cli");
    let db = file.open();
    let evidence = regressions();
    let engine = Arc::new(Lemmatizer::new());
    let input = evidence["before_words"]
        .as_object()
        .unwrap()
        .keys()
        .cloned()
        .collect::<Vec<_>>()
        .join(" ");
    for nfd in [false, true] {
        let text = format!(
            "前🙂「{}」",
            if nfd {
                input.nfd().collect::<String>()
            } else {
                input.clone()
            }
        );
        for cache in [0, 1, 4096] {
            let mut words = Session::new(engine.clone(), cache);
            let mut dictionary = DictionarySession::new(&db, cache);
            for (flag, policy) in [
                (None, None),
                (Some("--dict-only"), Some(DictionaryFilter::Headword)),
                (
                    Some("--dict-compatible"),
                    Some(DictionaryFilter::Compatible),
                ),
            ] {
                let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
                cmd.args(["text", "-", "--dictionary"])
                    .arg(&file.0)
                    .args(["--cache-bytes", &cache.to_string()]);
                if let Some(flag) = flag {
                    cmd.arg(flag);
                }
                let mut child = cmd
                    .stdin(Stdio::piped())
                    .stdout(Stdio::piped())
                    .spawn()
                    .unwrap();
                child
                    .stdin
                    .take()
                    .unwrap()
                    .write_all(text.as_bytes())
                    .unwrap();
                let output = child.wait_with_output().unwrap();
                assert!(output.status.success());
                for line in String::from_utf8(output.stdout).unwrap().lines() {
                    let record: Value = serde_json::from_str(line).unwrap();
                    let start = record["span"]["start"].as_u64().unwrap() as usize;
                    let end = record["span"]["end"].as_u64().unwrap() as usize;
                    assert_eq!(&text[start..end], record["surface"].as_str().unwrap());
                    if record["kind"] != "word" {
                        continue;
                    }
                    let mut word = words
                        .analyze_word(record["surface"].as_str().unwrap())
                        .unwrap()
                        .as_ref()
                        .clone();
                    let mut annotation = dictionary.annotate(&word).unwrap();
                    if let Some(policy) = policy {
                        annotation.filter(&mut word, policy);
                    }
                    assert_eq!(record["analysis"], serde_json::to_value(&word).unwrap());
                    assert_eq!(
                        record["dictionary"],
                        serde_json::to_value(&annotation).unwrap()
                    );
                }
            }
        }
    }
}
