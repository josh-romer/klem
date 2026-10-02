//! COV-021k: all native ㅡ/ㅑ paradigms, source identity and local ownership.
#[path = "support/written_vowel_history.rs"]
mod history;
use klem::dictionary::{
    Annotation, Compatibility, Dictionary, DictionaryFilter, DictionaryMetadata, DictionarySession,
    Entry, EntrySummary, SqliteDictionary, WordForm, import_krdict,
};
use klem::{Analysis, Lemmatizer, SpellingClass, SpellingRecovery, WordAnalysis};
use serde_json::Value;
use std::{collections::HashMap, fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-written-vowel-compat-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-written-vowel-compat.json",
            )],
            &path,
            "written-vowel-compat",
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
fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/written-vowel-compat-sources.json")).unwrap()
}
fn matches(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}
fn path<'a>(w: &'a WordAnalysis, head: &str, forms: &[&str]) -> &'a Analysis {
    w.analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == head
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        })
        .unwrap()
}
#[test]
fn every_native_vowel_entry_retains_all_sources_and_its_own_positive_forms() {
    let fixture = Fixture::new("sources");
    let db = fixture.open();
    let f = sources();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&db, 4096);
    assert_eq!(f["source_entries"].as_array().unwrap().len(), 135);
    assert_eq!(f["owner_ids"].as_array().unwrap().len(), 80);
    for source in f["source_entries"].as_array().unwrap() {
        let entry = db.entry(source["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *source);
        if !f["owner_ids"].as_array().unwrap().contains(&source["id"]) {
            continue;
        }
        let stem = entry.summary.headword.strip_suffix('다').unwrap();
        let word = engine.analyze_word(&(stem.to_owned() + "고")).unwrap();
        let annotation = session.annotate(&word).unwrap();
        let matched = annotation
            .lemmas
            .iter()
            .find(|l| l.lemma.text == entry.summary.headword)
            .unwrap()
            .entries
            .iter()
            .find(|e| e.entry.id == entry.summary.id)
            .unwrap();
        let evidence = matched.written_vowel.as_ref().unwrap();
        assert_eq!(
            evidence.a.len() + evidence.eo.len(),
            1,
            "{}",
            entry.summary.id
        );
        assert!(evidence.uncontracted.is_empty());
        for form in evidence.a.iter().chain(&evidence.eo) {
            assert!(
                entry
                    .forms
                    .iter()
                    .any(|f| f.kind == "활용" && f.written == *form)
            );
            let w = engine.analyze_word(form).unwrap();
            let a = path(&w, &entry.summary.headword, &["어"]);
            let assessment = session.annotate(&w).unwrap().assess(a);
            let e = assessment.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == entry.summary.id)
                .unwrap();
            assert_eq!(e.status, Compatibility::Compatible);
            assert!(e.conflicts.is_empty());
            assert_eq!(
                a.spelling_paths,
                vec![vec![SpellingRecovery {
                    morpheme_index: 0,
                    class: if evidence.a.is_empty() {
                        SpellingClass::WrittenVowelEo
                    } else {
                        SpellingClass::WrittenVowelA
                    }
                }]]
            );
        }
    }
    for id in f["excluded_hieut_ids"].as_array().unwrap() {
        let entry = db.entry(id.as_str().unwrap()).unwrap().unwrap();
        let w = engine.analyze_word(&entry.summary.headword).unwrap();
        let a = session.annotate(&w).unwrap();
        assert!(
            a.lemmas
                .iter()
                .flat_map(|l| &l.entries)
                .filter(|e| e.entry.id == entry.summary.id)
                .all(|e| e.written_vowel.is_none())
        );
    }
}
#[test]
fn every_frozen_probe_keeps_raw_order_and_checks_the_actual_vowel_owner() {
    let f = sources();
    let engine = Lemmatizer::new();
    let fixture = Fixture::new("probes");
    let db = fixture.open();
    let mut session = DictionarySession::new(&db, 4096);
    let mut uncached = DictionarySession::new(&db, 0);
    let mut words = HashMap::new();
    for (surface, before) in f["before_words"].as_object().unwrap() {
        let w = engine.analyze_word(surface).unwrap();
        let b: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
        assert_eq!(
            history::project_word(&w),
            b,
            "{surface}: original candidate order or provenance changed"
        );
        assert_eq!(
            w,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        let annotation = session.annotate(&w).unwrap();
        assert_eq!(annotation, uncached.annotate(&w).unwrap());
        assert!(session.cache_bytes() <= 4096);
        assert_eq!(uncached.cache_bytes(), 0);
        words.insert(surface.clone(), (w, annotation));
    }
    let mut present = 0;
    let mut conflicts = 0;
    for c in f["cases"].as_array().unwrap() {
        let (word, annotation) = &words[c["surface"].as_str().unwrap()];
        let indices: Vec<_> = word
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, a)| matches(a, c))
            .map(|(i, _)| i)
            .collect();
        assert_eq!(
            serde_json::to_value(&indices).unwrap(),
            c["before_candidate_indices"]
        );
        for i in indices {
            present += 1;
            let a = &word.analyses[i];
            let assessment = annotation.assess(a);
            let e = assessment.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == c["owner_id"].as_str().unwrap())
                .unwrap();
            assert_eq!(
                serde_json::to_value(e.status).unwrap(),
                c["expected_entry_status"],
                "{}",
                c["id"]
            );
            if e.status == Compatibility::Incompatible {
                conflicts += 1;
                assert_eq!(
                    serde_json::to_value(&e.conflicts).unwrap(),
                    serde_json::json!([{"rule":"lexical_spelling","morpheme_index":0}])
                );
            } else {
                assert!(e.conflicts.is_empty());
            }
            for (filter, keep) in [
                (DictionaryFilter::Headword, true),
                (
                    DictionaryFilter::Compatible,
                    e.status != Compatibility::Incompatible,
                ),
            ] {
                let mut filtered = word.clone();
                let mut annotated = annotation.clone();
                annotated.filter(&mut filtered, filter);
                assert_eq!(
                    filtered.analyses.contains(a),
                    keep,
                    "{} {filter:?}",
                    c["id"]
                );
                assert_eq!(annotated.readings.len(), filtered.analyses.len());
            }
            if c["owner_morpheme_index"].is_null() {
                assert!(
                    a.spelling_paths.is_empty(),
                    "{}: a later prefinal borrowed the lexical vowel",
                    c["id"]
                );
            }
        }
    }
    assert_eq!((present, conflicts), (1761, 801));
}
struct Custom<'a> {
    base: &'a SqliteDictionary,
    entries: Vec<Entry>,
}
impl Dictionary for Custom<'_> {
    fn metadata(&self) -> &DictionaryMetadata {
        self.base.metadata()
    }
    fn fingerprint(&self) -> &str {
        self.base.fingerprint()
    }
    fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
        if head == "받아쓰다" {
            Ok(self.entries.iter().map(|e| e.summary.clone()).collect())
        } else {
            self.base.lookup(head)
        }
    }
    fn entry(&self, id: &str) -> klem::dictionary::Result<Option<Entry>> {
        if let Some(e) = self.entries.iter().find(|e| e.summary.id == id) {
            Ok(Some(e.clone()))
        } else {
            self.base.entry(id)
        }
    }
}
fn form(written: &str) -> WordForm {
    WordForm {
        kind: "활용".into(),
        written: written.nfd().collect(),
        pronunciations: vec![],
    }
}
#[test]
fn alternate_homonyms_sparse_sources_legacy_annotations_and_pronunciations_stay_conservative() {
    let fixture = Fixture::new("unknown");
    let db = fixture.open();
    let original = db.entry("krdict:56546").unwrap().unwrap();
    let engine = Lemmatizer::new();
    let mut regular = original.clone();
    regular.summary.id = "synthetic:eo".into();
    let mut alternate = original.clone();
    alternate.summary.id = "synthetic:a".into();
    alternate.forms = vec![form(" 받아싸 ")];
    let mut unknown = original.clone();
    unknown.summary.id = "synthetic:unknown".into();
    unknown.forms = vec![
        WordForm {
            kind: "발음".into(),
            written: "받아싸".into(),
            pronunciations: vec!["받아싸".into()],
        },
        WordForm {
            kind: "활용".into(),
            written: String::new(),
            pronunciations: vec!["받아싸".into()],
        },
    ];
    let source = Custom {
        base: &db,
        entries: vec![regular.clone(), alternate.clone(), unknown.clone()],
    };
    let mut session = DictionarySession::new(&source, 4096);
    let w = engine.analyze_word("받아싸버렸다").unwrap();
    let a = w
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["받아쓰다", "버리다"])
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["어", "었", "다"])
        })
        .unwrap();
    let annotation = session.annotate(&w).unwrap();
    assert_eq!(
        a.spelling_paths,
        vec![vec![SpellingRecovery {
            morpheme_index: 0,
            class: SpellingClass::WrittenVowelA
        }]]
    );
    let statuses: Vec<_> = annotation.assess(a).lemmas[0]
        .entries
        .iter()
        .map(|e| e.status)
        .collect();
    assert_eq!(
        statuses,
        vec![
            Compatibility::Incompatible,
            Compatibility::Compatible,
            Compatibility::Unknown
        ]
    );
    for extra in ["받아싸", "받아쓰어"] {
        let mut both = regular.clone();
        both.forms.push(form(extra));
        let source = Custom {
            base: &db,
            entries: vec![both],
        };
        let mut session = DictionarySession::new(&source, 0);
        let w = engine.analyze_word(extra).unwrap();
        let a = path(&w, "받아쓰다", &["어"]);
        assert_eq!(
            session.annotate(&w).unwrap().assess(a).status,
            Compatibility::Compatible
        );
    }
    let mut legacy = serde_json::to_value(&annotation).unwrap();
    for l in legacy["lemmas"].as_array_mut().unwrap() {
        for e in l["entries"].as_array_mut().unwrap() {
            e.as_object_mut().unwrap().remove("written_vowel");
        }
    }
    let legacy: Annotation = serde_json::from_value(legacy).unwrap();
    assert_eq!(legacy.assess(a).lemmas[0].status, Compatibility::Unknown);
    let source = Custom {
        base: &db,
        entries: vec![regular, unknown],
    };
    let mut session = DictionarySession::new(&source, 0);
    let annotation = session.annotate(&w).unwrap();
    let mut filtered = w.clone();
    let mut annotation = annotation;
    annotation.filter(&mut filtered, DictionaryFilter::Compatible);
    assert!(filtered.analyses.contains(a));
}
#[test]
fn cli_and_library_filters_keep_auxiliary_owners_and_original_indices() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let mut session = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for surface in [
        "받아싸",
        "받아써",
        "받아쌌어요",
        "받아썼어요",
        "받아쓰어",
        "가냘퍼",
        "가냘파",
        "약어",
        "약아",
        "크나카",
        "크나커",
        "본따버렸다",
        "본떠버렸다",
        "손썼다",
        "얇아봤다",
        "얇어봤다",
        "받아쓰셨어요",
        "가냘프셨어요",
    ] {
        for (flag, filter) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut expected = engine.analyze_word(surface).unwrap();
            let mut annotation = session.annotate(&expected).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut expected, filter);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(actual.clone()).unwrap(),
                expected
            );
            assert_eq!(
                serde_json::from_value::<Annotation>(actual["dictionary"].clone()).unwrap(),
                annotation
            );
        }
    }
}
