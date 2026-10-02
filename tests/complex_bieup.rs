//! COV-021o: complete native ㄼ paradigms and lexical spelling ownership.
#[path = "support/complex_bieup_history.rs"]
mod history;
use klem::dictionary::{
    Annotation, Compatibility, Dictionary, DictionaryFilter, DictionaryMetadata, DictionarySession,
    Entry, EntrySummary, SqliteDictionary, WordForm, import_krdict,
};
use klem::{Analysis, Lemmatizer, SpellingClass, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/complex-bieup-sources.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-complex-bieup-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-complex-bieup.json")],
            &path,
            "complex-bieup",
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
fn matches(a: &Analysis, case: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == case["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == case["morphemes"]
}
fn path<'a>(word: &'a WordAnalysis, head: &str, forms: &[String]) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == head
                && a.morphemes.iter().map(|m| &m.form).eq(forms.iter())
        })
        .unwrap_or_else(|| panic!("{} {head} {forms:?}", word.normalized))
}

#[test]
fn full_native_entries_and_written_paradigms_keep_identity() {
    let f = sources();
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    assert_eq!(f["source_entries"].as_array().unwrap().len(), 26);
    for entry in f["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    assert_eq!(f["primary_entry_ids"].as_array().unwrap().len(), 12);
    let mut regular = 0;
    let mut irregular = 0;
    let mut session = DictionarySession::new(&db, 4096);
    for profile in f["profiles"].as_array().unwrap() {
        let id = profile["entry"].as_str().unwrap();
        let entry = db.entry(id).unwrap().unwrap();
        let word = Lemmatizer::new()
            .analyze_word(&entry.summary.headword)
            .unwrap();
        let annotation = session.annotate(&word).unwrap();
        let matched = annotation
            .lemmas
            .iter()
            .flat_map(|l| &l.entries)
            .find(|e| e.entry.id == id)
            .unwrap();
        let evidence = matched.bieup.as_ref().unwrap();
        let expected = profile["class_from_written_forms"].as_str().unwrap();
        assert_eq!(!evidence.regular.is_empty(), expected == "regular", "{id}");
        assert_eq!(
            !evidence.irregular.is_empty(),
            expected == "irregular",
            "{id}"
        );
        regular += usize::from(expected == "regular");
        irregular += usize::from(expected == "irregular");
    }
    assert_eq!((regular, irregular), (11, 1));
    let corpus = include_str!("fixtures/kaist-complex-bieup.conllu");
    for row in f["corpus_rows"].as_array().unwrap() {
        assert!(corpus.contains(row["original_sentence"].as_str().unwrap()));
        assert!(corpus.lines().any(|line| line == row["original_row"]));
    }
}

#[test]
fn recovery_preserves_prior_candidates_and_unicode() {
    let f = sources();
    let engine = Lemmatizer::new();
    for (surface, before) in f["before_words"].as_object().unwrap() {
        let old: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
        let current = engine.analyze_word(surface).unwrap();
        assert_eq!(
            current,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        let projected: Vec<_> = current
            .analyses
            .iter()
            .map(history::project_analysis)
            .collect();
        assert_eq!(
            projected
                .into_iter()
                .filter(|a| old.analyses.contains(a))
                .collect::<Vec<_>>(),
            old.analyses,
            "{surface}"
        );
        assert!(current.analyses.iter().all(|a| a.breakdown().is_some()));
        for analysis in &current.analyses {
            assert!(
                analysis
                    .rules
                    .iter()
                    .all(|rule| klem::rule_explanation(rule).is_some())
            );
            for requirement in analysis.spelling_paths.iter().flatten() {
                assert!(requirement.morpheme_index < analysis.morphemes.len());
            }
        }
    }
    for case in f["cases"].as_array().unwrap() {
        let word = engine
            .analyze_word(case["surface"].as_str().unwrap())
            .unwrap();
        assert!(
            word.analyses.iter().any(|a| matches(a, case)),
            "{} {}",
            case["id"],
            case["surface"]
        );
    }
    for surface in ["설와", "설오니", "설오어", "널와", "발와"] {
        assert!(
            !engine
                .analyze_word(surface)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a
                    .lemmas
                    .iter()
                    .any(|l| matches!(l.text.as_str(), "섧다" | "넓다" | "밟다"))
                    && a.rules.iter().any(|r| r == "irregular.bieup")),
            "{surface}"
        );
    }
    for (surface, expected) in [("서러워", "서럽다"), ("설워", "섧다")] {
        let word = engine.analyze_word(surface).unwrap();
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == expected)
        );
        let other = if expected == "서럽다" {
            "섧다"
        } else {
            "서럽다"
        };
        assert!(
            !word
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == other)
        );
    }
}

#[test]
fn per_entry_spelling_filters_cache_and_cli_agree() {
    let f = sources();
    let fixture = Fixture::new("filters");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let mut cached = DictionarySession::new(&db, 4096);
    let mut uncached = DictionarySession::new(&db, 0);
    for contrast in f["contrasts"].as_array().unwrap() {
        let word = engine
            .analyze_word(contrast["surface"].as_str().unwrap())
            .unwrap();
        let forms: Vec<String> = serde_json::from_value(contrast["forms"].clone()).unwrap();
        let analysis = path(&word, contrast["headword"].as_str().unwrap(), &forms);
        let class = if contrast["spelling"] == "regular" {
            SpellingClass::BieupRegular
        } else {
            SpellingClass::BieupIrregular
        };
        assert!(
            analysis
                .spelling_paths
                .iter()
                .all(|p| p.iter().any(|r| r.class == class && r.morpheme_index == 0)),
            "{contrast}"
        );
        assert!(!analysis.spelling_paths.is_empty());
        let annotation = cached.annotate(&word).unwrap();
        let assessment = annotation.assess(analysis);
        let entry = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == contrast["entry"])
            .unwrap();
        assert_eq!(
            entry.status,
            if contrast["compatible"] == true {
                Compatibility::Compatible
            } else {
                Compatibility::Incompatible
            },
            "{contrast}"
        );
        let mut filtered = word.clone();
        let mut annotated = annotation.clone();
        annotated.filter(&mut filtered, DictionaryFilter::Headword);
        assert!(filtered.analyses.contains(analysis));
        let mut filtered = word.clone();
        let mut annotated = annotation;
        annotated.filter(&mut filtered, DictionaryFilter::Compatible);
        assert_eq!(
            filtered.analyses.contains(analysis),
            contrast["compatible"] == true,
            "{contrast}"
        );
    }
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        for surface in f["before_words"].as_object().unwrap().keys() {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = cached.annotate(&word).unwrap();
            assert_eq!(annotation, uncached.annotate(&word).unwrap());
            assert!(cached.cache_bytes() <= 4096);
            assert_eq!(uncached.cache_bytes(), 0);
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
            let mut value: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                value.as_object_mut().unwrap().remove("dictionary").unwrap(),
                serde_json::to_value(annotation).unwrap()
            );
            assert_eq!(serde_json::from_value::<WordAnalysis>(value).unwrap(), word);
            for case in f["cases"]
                .as_array()
                .unwrap()
                .iter()
                .filter(|c| c["surface"] == surface.as_str())
            {
                assert!(
                    word.analyses.iter().any(|a| matches(a, case)),
                    "{flag:?} {}",
                    case["id"]
                );
            }
        }
    }
}

#[test]
fn auxiliary_spelling_requirements_belong_to_the_recovered_root() {
    use klem::breakdown::Component;
    for (surface, head, class) in [
        ("설워졌다", "섧다", SpellingClass::BieupIrregular),
        ("설워봤다", "섧다", SpellingClass::BieupIrregular),
        ("넓어졌다", "넓다", SpellingClass::BieupRegular),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let paths: Vec<_> = word
            .analyses
            .iter()
            .filter(|a| a.lemmas.len() == 2 && a.lemmas[0].text == head)
            .collect();
        assert!(!paths.is_empty(), "{surface}");
        for analysis in paths {
            let components = analysis.breakdown().unwrap();
            for requirement in analysis
                .spelling_paths
                .iter()
                .flatten()
                .filter(|r| r.class == class)
            {
                let boundary = components
                    .iter()
                    .position(|c| *c == Component::Morpheme(requirement.morpheme_index))
                    .unwrap();
                let owner = components[..boundary]
                    .iter()
                    .rev()
                    .find_map(|c| {
                        if let Component::Lemma(i) = c {
                            Some(*i)
                        } else {
                            None
                        }
                    })
                    .unwrap();
                assert_eq!(owner, 0, "{surface}: {analysis:?}");
            }
            assert!(
                analysis
                    .spelling_paths
                    .iter()
                    .all(|p| p.iter().any(|r| r.class == class))
            );
            assert!(!analysis.spelling_paths.is_empty());
        }
    }
}

struct AlternateDictionary<'a> {
    base: &'a SqliteDictionary,
    entries: Vec<Entry>,
}
impl Dictionary for AlternateDictionary<'_> {
    fn metadata(&self) -> &DictionaryMetadata {
        self.base.metadata()
    }
    fn fingerprint(&self) -> &str {
        self.base.fingerprint()
    }
    fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
        if head == "섧다" {
            Ok(self.entries.iter().map(|e| e.summary.clone()).collect())
        } else {
            self.base.lookup(head)
        }
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
fn homonyms_sparse_pronunciations_and_legacy_annotations_keep_their_own_evidence() {
    let fixture = Fixture::new("alternate");
    let db = fixture.open();
    let original = db.entry("krdict:63307").unwrap().unwrap();
    let written = |text: &str| WordForm {
        kind: "활용".into(),
        written: text.nfd().collect(),
        pronunciations: vec![],
    };
    let mut regular = original.clone();
    regular.summary.id = "synthetic:regular".into();
    regular.forms = vec![written(" 섧으니 ")];
    let mut pronunciation = original.clone();
    pronunciation.summary.id = "synthetic:pronunciation".into();
    pronunciation.forms = vec![
        WordForm {
            kind: "발음".into(),
            written: "설우니".into(),
            pronunciations: vec!["설우니".into()],
        },
        WordForm {
            kind: "활용".into(),
            written: String::new(),
            pronunciations: vec!["설우니".into()],
        },
    ];
    let mut sparse = original.clone();
    sparse.summary.id = "synthetic:sparse".into();
    sparse.forms = vec![written("섧고")];
    let mut mixed = original.clone();
    mixed.summary.id = "synthetic:mixed".into();
    mixed.forms = vec![written("섧으니"), written("설우니")];
    let provider = AlternateDictionary {
        base: &db,
        entries: vec![original, regular, pronunciation, sparse, mixed],
    };
    let mut dictionary = DictionarySession::new(&provider, 4096);
    for (surface, regular) in [("섧으니", true), ("설우니", false)] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let analysis = path(&word, "섧다", &["으니".into()]);
        let annotation = dictionary.annotate(&word).unwrap();
        let reading = annotation.assess(analysis);
        for (id, expected) in [
            (
                "krdict:63307",
                if regular {
                    Compatibility::Incompatible
                } else {
                    Compatibility::Compatible
                },
            ),
            (
                "synthetic:regular",
                if regular {
                    Compatibility::Compatible
                } else {
                    Compatibility::Incompatible
                },
            ),
            ("synthetic:pronunciation", Compatibility::Unknown),
            ("synthetic:sparse", Compatibility::Unknown),
            ("synthetic:mixed", Compatibility::Compatible),
        ] {
            assert_eq!(
                reading.lemmas[0]
                    .entries
                    .iter()
                    .find(|e| e.id == id)
                    .unwrap()
                    .status,
                expected,
                "{id} {surface}"
            );
        }
        assert_eq!(reading.status, Compatibility::Compatible);
        let mut legacy = serde_json::to_value(&annotation).unwrap();
        for lemma in legacy["lemmas"].as_array_mut().unwrap() {
            for entry in lemma["entries"].as_array_mut().unwrap() {
                entry.as_object_mut().unwrap().remove("bieup");
            }
        }
        let legacy: Annotation = serde_json::from_value(legacy).unwrap();
        assert_eq!(legacy.assess(analysis).status, Compatibility::Unknown);
    }
}

#[test]
fn consonant_endings_and_honorific_prefinals_keep_the_boundary_scope() {
    let fixture = Fixture::new("boundaries");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let f = sources();
    let engine = Lemmatizer::new();
    for profile in f["profiles"].as_array().unwrap() {
        let entry = db
            .entry(profile["entry"].as_str().unwrap())
            .unwrap()
            .unwrap();
        let stem = entry.summary.headword.strip_suffix('다').unwrap();
        for ending in ["고", "지", "습니다"] {
            let word = engine.analyze_word(&(stem.to_owned() + ending)).unwrap();
            let analysis = path(&word, &entry.summary.headword, &[ending.into()]);
            assert!(!analysis.spelling_paths.iter().flatten().any(|r| matches!(
                r.class,
                SpellingClass::BieupRegular | SpellingClass::BieupIrregular
            )));
            assert_eq!(
                dictionary.annotate(&word).unwrap().assess(analysis).status,
                Compatibility::Compatible
            );
        }
        let regular = profile["class_from_written_forms"] == "regular";
        let base = if regular {
            stem.to_owned() + "으"
        } else {
            profile["irregular"]
                .as_str()
                .unwrap()
                .strip_suffix('니')
                .unwrap()
                .to_owned()
        };
        let word = engine.analyze_word(&(base + "셨어요")).unwrap();
        let analysis = path(
            &word,
            &entry.summary.headword,
            &["시".into(), "었".into(), "어요".into()],
        );
        let expected = if regular {
            SpellingClass::BieupRegular
        } else {
            SpellingClass::BieupIrregular
        };
        assert_eq!(
            analysis.spelling_paths,
            vec![vec![klem::SpellingRecovery {
                morpheme_index: 0,
                class: expected
            }]]
        );
        assert_eq!(
            dictionary.annotate(&word).unwrap().assess(analysis).status,
            Compatibility::Compatible
        );
    }
    for (surface, head, class) in [
        ("설워놓으니", "섧다", SpellingClass::BieupIrregular),
        ("넓어놓으니", "넓다", SpellingClass::BieupRegular),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let analysis = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.iter().map(|l| l.text.as_str()).eq([head, "놓다"])
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(["어", "으니"])
            })
            .unwrap();
        assert_eq!(
            analysis.spelling_paths,
            vec![vec![
                klem::SpellingRecovery {
                    morpheme_index: 0,
                    class
                },
                klem::SpellingRecovery {
                    morpheme_index: 1,
                    class: SpellingClass::HieutRegular
                }
            ]]
        );
        assert_eq!(
            history::project_analysis(analysis).spelling_paths,
            vec![vec![klem::SpellingRecovery {
                morpheme_index: 1,
                class: SpellingClass::HieutRegular
            }]]
        );
    }
}
