//! COV-021p: source-head discrepancies, written bases and truncated fields.
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionaryMetadata, DictionarySession, Entry, EntrySummary,
    SqliteDictionary, WordForm, import_krdict,
};
use klem::{LemmaKind, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/source-head-sources.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-source-head-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-source-head.json")],
            &path,
            "source-head-review",
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
fn has_path(word: &WordAnalysis, head: &str, ending: &str) -> bool {
    word.analyses.iter().any(|a| {
        a.lemmas.len() == 1
            && a.morphemes.len() == 1
            && a.lemmas[0].text == head
            && a.lemmas[0].kind == LemmaKind::Predicate
            && a.morphemes[0].form == ending
            && a.morphemes[0].kind == MorphemeKind::Ending
    })
}

#[test]
fn native_import_preserves_every_conflicting_form_and_the_separate_heads() {
    let source = sources();
    let fixture = Fixture::new("native");
    let dictionary = fixture.open();
    for expected in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(
                dictionary
                    .entry(expected["id"].as_str().unwrap())
                    .unwrap()
                    .unwrap()
            )
            .unwrap(),
            *expected
        );
    }
    for review in source["reviews"].as_array().unwrap() {
        let original = &review["original_observation"];
        let entry = dictionary
            .entry(original["entry_id"].as_str().unwrap())
            .unwrap()
            .unwrap();
        let form = &entry.forms[original["form_index"].as_u64().unwrap() as usize];
        assert_eq!(form.written, original["written"].as_str().unwrap());
        assert_eq!(
            serde_json::to_value(&entry.forms).unwrap(),
            source["complete_native_entries"][&entry.summary.id]["forms"]
        );
    }
    assert!(dictionary.lookup("삐뚤빼뚤하다").unwrap().is_empty());
    assert_eq!(dictionary.lookup("삐뚤삐뚤하다").unwrap().len(), 1);
    assert_eq!(
        dictionary
            .entry("krdict:600930")
            .unwrap()
            .unwrap()
            .summary
            .pos,
        "동사"
    );
    assert_eq!(source["separate_pos_observation"]["primary_pos"], "형용사");
}

#[test]
fn individually_bound_judgments_preserve_candidates_unicode_and_breakdowns() {
    let source = sources();
    let ledger: Value = serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    let engine = Lemmatizer::new();
    for (surface, frozen) in source["before_words"].as_object().unwrap() {
        let before: WordAnalysis = serde_json::from_value(frozen.clone()).unwrap();
        let word = engine.analyze_word(surface).unwrap();
        let retained: Vec<_> = word
            .analyses
            .iter()
            .filter(|a| before.analyses.contains(a))
            .cloned()
            .collect();
        assert_eq!(retained, before.analyses, "{surface}");
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().all(|a| a.breakdown().is_some()));
    }
    for case in source["cases"].as_array().unwrap() {
        assert_eq!(
            ledger["cases"]
                .as_array()
                .unwrap()
                .iter()
                .find(|c| c["id"] == case["id"])
                .unwrap(),
            case
        );
        let judgment = &case["judgments"][0];
        let word = engine
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        assert_eq!(
            has_path(
                &word,
                judgment["lemmas"][0].as_str().unwrap(),
                judgment["morphemes"][0].as_str().unwrap()
            ),
            judgment["verdict"] == "required",
            "{}",
            case["id"]
        );
        if judgment["verdict"] == "forbidden" {
            assert!(word.analyses.iter().any(|a| a.unchanged));
        }
    }
}

#[test]
fn dictionary_gaps_remain_separate_from_validity_and_cli_filters_match_the_library() {
    let source = sources();
    let fixture = Fixture::new("cli");
    let dictionary = fixture.open();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 4096);
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        for surface in source["before_words"].as_object().unwrap().keys() {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = session.annotate(&word).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut word, filter);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let output = command.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let mut actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(annotation).unwrap()
            );
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(actual).unwrap(),
                word
            );
            for case in source["cases"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|c| c["surface"] == surface.as_str())
            {
                let expectation = source["dictionary_expectations"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .find(|e| e["case"] == case["id"])
                    .unwrap();
                let expected = expectation[if flag.is_none() {
                    "raw_required"
                } else {
                    "filtered_required"
                }]
                .as_bool()
                .unwrap();
                let judgment = &case["judgments"][0];
                assert_eq!(
                    has_path(
                        &word,
                        judgment["lemmas"][0].as_str().unwrap(),
                        judgment["morphemes"][0].as_str().unwrap()
                    ),
                    expected,
                    "{flag:?} {}",
                    case["id"]
                );
            }
        }
    }
}

// A deliberately partial external provider, never imported as KRDict or
// substituted for its complete native entry. Only reviewed head/POS/forms are
// supplied; all unknown fields remain empty.
struct ExpertProjection<'a> {
    base: &'a SqliteDictionary,
    metadata: DictionaryMetadata,
    fingerprint: String,
    entries: Vec<Entry>,
}
impl<'a> ExpertProjection<'a> {
    fn new(base: &'a SqliteDictionary, source: &Value) -> Self {
        let mut metadata = base.metadata().clone();
        metadata.source = "test-native-plus-expert-projection".into();
        metadata.source_url = source["primary_reviews"]["alternate_head"]["senses"][2]["url"]
            .as_str()
            .unwrap()
            .into();
        metadata.license = "Native fixture CC-BY-SA-2.0-KR; external facts only".into();
        metadata.attribution = "Partial expert-reviewed head/POS/form projection; complete KRDict entries retained independently.".into();
        let entries: Vec<_> = source["primary_reviews"]["alternate_head"]["senses"]
            .as_array()
            .unwrap()
            .iter()
            .map(|sense| Entry {
                summary: EntrySummary {
                    id: format!("opendict-sense:{}", sense["sense_no"].as_str().unwrap()),
                    headword: "삐뚤빼뚤하다".into(),
                    homonym: String::new(),
                    pos: sense["pos"].as_str().unwrap().into(),
                },
                url: sense["url"].as_str().unwrap().into(),
                level: String::new(),
                lexical_unit: "단어".into(),
                origins: Vec::new(),
                notes: Vec::new(),
                senses: Vec::new(),
                forms: source["primary_reviews"]["alternate_head"]["attested_written_forms"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|form| WordForm {
                        kind: "활용".into(),
                        written: form.as_str().unwrap().into(),
                        pronunciations: Vec::new(),
                    })
                    .collect(),
            })
            .collect();
        metadata.entries += entries.len();
        Self {
            base,
            metadata,
            fingerprint: format!(
                "{}+expert-projection:{}",
                base.fingerprint(),
                source["primary_review_sha256"].as_str().unwrap()
            ),
            entries,
        }
    }
}
impl Dictionary for ExpertProjection<'_> {
    fn metadata(&self) -> &DictionaryMetadata {
        &self.metadata
    }
    fn fingerprint(&self) -> &str {
        &self.fingerprint
    }
    fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
        let mut matches = self.base.lookup(head)?;
        matches.extend(
            self.entries
                .iter()
                .filter(|e| e.summary.headword == head)
                .map(|e| e.summary.clone()),
        );
        Ok(matches)
    }
    fn entry(&self, id: &str) -> klem::dictionary::Result<Option<Entry>> {
        if let Some(entry) = self.entries.iter().find(|e| e.summary.id == id) {
            Ok(Some(entry.clone()))
        } else {
            self.base.entry(id)
        }
    }
}

#[test]
fn independent_provider_retains_the_alternate_head_without_borrowing_native_identity() {
    let source = sources();
    let fixture = Fixture::new("external");
    let dictionary = fixture.open();
    let external = ExpertProjection::new(&dictionary, &source);
    assert_ne!(external.fingerprint(), dictionary.fingerprint());
    assert_eq!(external.lookup("삐뚤빼뚤하다").unwrap().len(), 3);
    assert_eq!(
        external.entry("krdict:601920").unwrap(),
        dictionary.entry("krdict:601920").unwrap()
    );
    let mut session = DictionarySession::new(&external, 4096);
    for (surface, ending) in [
        ("삐뚤빼뚤한", "은"),
        ("삐뚤빼뚤하여", "어"),
        ("삐뚤빼뚤하니", "으니"),
        ("삐뚤빼뚤합니다", "습니다"),
    ] {
        let raw = Lemmatizer::new().analyze_word(surface).unwrap();
        for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut word = raw.clone();
            let mut annotation = session.annotate(&word).unwrap();
            annotation.filter(&mut word, filter);
            assert!(has_path(&word, "삐뚤빼뚤하다", ending));
            assert!(!has_path(&word, "삐뚤삐뚤하다", ending));
            let matched = annotation
                .lemmas
                .iter()
                .find(|l| l.lemma.text == "삐뚤빼뚤하다")
                .unwrap();
            assert!(
                matched
                    .entries
                    .iter()
                    .all(|e| e.entry.id.starts_with("opendict-sense:"))
            );
        }
    }
}
