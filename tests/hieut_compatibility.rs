//! COV-021d: written inflection evidence, per-entry classes and recovery ownership.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, SpellingClass, SpellingRecovery, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/dictionary-attachments.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("hieut-compat-"));
    s
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!("klem-hieut-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-hieut-compatibility.json",
            )],
            &path,
            "hieut",
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

#[test]
fn written_spelling_constraints_preserve_raw_headword_and_cli_contracts() {
    let f = Fixture::new("policies");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let s = suite();
    let raw = validity::evaluate(&s).unwrap();
    assert_eq!(raw.required_present, raw.required_total);
    assert_eq!(raw.forbidden_present, raw.forbidden_total);
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let report = validity::evaluate_with(&s, |word| {
            let mut a = engine.analyze_word(word).unwrap();
            assert_eq!(
                a,
                engine
                    .analyze_word(&word.nfd().collect::<String>())
                    .unwrap()
            );
            for reading in &a.analyses {
                assert!(reading.breakdown().is_some());
                for path in &reading.spelling_paths {
                    assert!(!path.is_empty());
                    for r in path {
                        assert!(r.morpheme_index < reading.morphemes.len());
                    }
                }
            }
            let mut annotation = dict.annotate(&a).unwrap();
            annotation.filter(&mut a, policy);
            let output = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", word, "--dictionary"])
                .arg(&f.0)
                .arg(flag)
                .output()
                .unwrap();
            assert!(output.status.success());
            let value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                a
            );
            assert_eq!(
                value["dictionary"],
                serde_json::to_value(&annotation).unwrap()
            );
            assert!(dict.cache_bytes() <= 4096);
            Ok(a)
        })
        .unwrap();
        assert_eq!(report.required_present, raw.required_total);
        if policy == DictionaryFilter::Compatible {
            assert!(report.passed(), "{:?}", report.violations);
        } else {
            assert_eq!(report.forbidden_present, raw.forbidden_total);
        }
    }
}

fn path<'a>(word: &'a WordAnalysis, ls: &[&str], ms: &[&str]) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(ls.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(ms.iter().copied())
        })
        .unwrap()
}

#[test]
fn recovery_requirements_belong_to_each_owner_through_auxiliaries_and_copulas() {
    use SpellingClass::{HieutIrregular as I, HieutRegular as R};
    let f = Fixture::new("owners");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    for (surface, ls, ms, expected, status) in [
        (
            "노래져놓으니",
            vec!["노랗다", "지다", "놓다"],
            vec!["어", "어", "으니"],
            vec![(0, I), (2, R)],
            Compatibility::Compatible,
        ),
        (
            "노래져놀라고",
            vec!["노랗다", "지다", "놓다"],
            vec!["어", "어", "을라고"],
            vec![(0, I), (2, I)],
            Compatibility::Incompatible,
        ),
        (
            "먹어놓으셨으니",
            vec!["먹다", "놓다"],
            vec!["어", "시", "었", "으니"],
            vec![(1, R)],
            Compatibility::Compatible,
        ),
        (
            "하얘짐이었다",
            vec!["하얗다", "지다", "이다"],
            vec!["어", "음", "었", "다"],
            vec![(0, I)],
            Compatibility::Compatible,
        ),
        (
            "먹어놓음이었다",
            vec!["먹다", "놓다", "이다"],
            vec!["어", "음", "었", "다"],
            vec![(1, R)],
            Compatibility::Compatible,
        ),
        (
            "놔놀라고",
            vec!["놓다", "놓다"],
            vec!["어", "을라고"],
            vec![(0, R), (1, I)],
            Compatibility::Incompatible,
        ),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = path(&word, &ls, &ms);
        let annotation = dict.annotate(&word).unwrap();
        assert_eq!(
            a.spelling_paths,
            vec![
                expected
                    .into_iter()
                    .map(|(morpheme_index, class)| SpellingRecovery {
                        morpheme_index,
                        class
                    })
                    .collect::<Vec<_>>()
            ],
            "{surface}"
        );
        assert_eq!(annotation.assess(a).status, status, "{surface}");
        assert_eq!(
            serde_json::from_str::<Analysis>(&serde_json::to_string(a).unwrap()).unwrap(),
            *a
        );
    }
}

#[test]
fn full_source_entries_and_all_written_ni_dispositions_are_preserved() {
    let f = Fixture::new("sources");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/hieut-compatibility-sources.json")).unwrap();
    let entries = source["source_entries"].as_array().unwrap();
    assert_eq!(entries.len(), 116);
    let mut unknown = 0;
    for expected in entries {
        let entry = db.entry(expected["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        let word = Lemmatizer::new()
            .analyze_word(&entry.summary.headword)
            .unwrap();
        let annotation = dict.annotate(&word).unwrap();
        let matched = annotation
            .lemmas
            .iter()
            .flat_map(|l| &l.entries)
            .find(|m| m.entry.id == entry.summary.id)
            .unwrap();
        let profile = source["profiles"]
            .as_array()
            .unwrap()
            .iter()
            .find(|p| p["entry"] == entry.summary.id)
            .unwrap();
        match profile["class_from_written_ni"].as_str().unwrap() {
            "regular" => {
                let h = matched.hieut.as_ref().unwrap();
                assert!(!h.regular.is_empty());
                assert!(h.irregular.is_empty());
            }
            "irregular" => {
                let h = matched.hieut.as_ref().unwrap();
                assert!(h.regular.is_empty());
                assert!(!h.irregular.is_empty());
            }
            "unknown" => {
                unknown += 1;
                assert!(matched.hieut.is_none());
            }
            _ => panic!("unknown disposition"),
        }
    }
    assert_eq!(unknown, 4);
}

#[test]
fn spelling_alternatives_cannot_mix_incompatible_owners_into_one_valid_path() {
    use SpellingClass::{HieutIrregular as I, HieutRegular as R};
    let f = Fixture::new("alternatives");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let word = Lemmatizer::new().analyze_word("놔놓으니").unwrap();
    let mut a = path(&word, &["놓다", "놓다"], &["어", "으니"]).clone();
    let annotation = dict.annotate(&word).unwrap();
    // Synthetic competing derivations: each path has a different bad owner.
    // Combining per-slot compatibility across paths would wrongly accept it.
    a.spelling_paths = [[(0, R), (1, I)], [(0, I), (1, R)]]
        .into_iter()
        .map(|p| {
            p.into_iter()
                .map(|(morpheme_index, class)| SpellingRecovery {
                    morpheme_index,
                    class,
                })
                .collect()
        })
        .collect();
    let assessment = annotation.assess(&a);
    assert_eq!(assessment.status, Compatibility::Incompatible);
    assert!(
        assessment
            .lemmas
            .iter()
            .all(|l| l.status == Compatibility::Compatible)
    );
    a.spelling_paths.push(vec![
        SpellingRecovery {
            morpheme_index: 0,
            class: R,
        },
        SpellingRecovery {
            morpheme_index: 1,
            class: R,
        },
    ]);
    assert_eq!(annotation.assess(&a).status, Compatibility::Compatible);
    // Older JSON has no owned spelling evidence. Preserve it conservatively.
    let mut legacy = serde_json::to_value(&a).unwrap();
    legacy.as_object_mut().unwrap().remove("spelling_paths");
    let legacy: Analysis = serde_json::from_value(legacy).unwrap();
    assert!(legacy.spelling_paths.is_empty());
    assert_ne!(
        annotation.assess(&legacy).status,
        Compatibility::Incompatible
    );
}

#[test]
fn synthetic_homonyms_keep_their_own_written_evidence_and_unknown_alternatives() {
    use klem::dictionary::{DictionaryMetadata, Entry, EntrySummary, WordForm};
    struct Homonyms {
        base: SqliteDictionary,
        entries: Vec<Entry>,
    }
    impl Dictionary for Homonyms {
        fn metadata(&self) -> &DictionaryMetadata {
            self.base.metadata()
        }
        fn fingerprint(&self) -> &str {
            "synthetic-hieut-homonyms"
        }
        fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
            if head == "놓다" {
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
    let f = Fixture::new("homonyms");
    let db = f.open();
    let regular = db.entry("krdict:89534").unwrap().unwrap();
    let mut irregular = regular.clone();
    irregular.summary.id = "synthetic:irregular".into();
    irregular.forms = vec![WordForm {
        kind: "활용".into(),
        written: "노니".into(),
        pronunciations: vec![],
    }];
    let mut unknown = regular.clone();
    unknown.summary.id = "synthetic:unknown".into();
    unknown.forms = vec![WordForm {
        kind: "활용".into(),
        written: String::new(),
        pronunciations: vec!["노니".into()],
    }];
    for (entries, status) in [
        (
            vec![regular.clone(), irregular, unknown.clone()],
            Compatibility::Compatible,
        ),
        (vec![regular.clone(), unknown], Compatibility::Unknown),
        (vec![regular], Compatibility::Incompatible),
    ] {
        let source = Homonyms {
            base: f.open(),
            entries,
        };
        let mut dict = DictionarySession::new(&source, 4096);
        let word = Lemmatizer::new().analyze_word("놀라고").unwrap();
        let a = path(&word, &["놓다"], &["을라고"]);
        let annotation = dict.annotate(&word).unwrap();
        let assessment = annotation.assess(a);
        assert_eq!(assessment.status, status);
        for e in &assessment.lemmas[0].entries {
            assert_eq!(
                e.status,
                match e.id.as_str() {
                    "krdict:89534" => Compatibility::Incompatible,
                    "synthetic:irregular" => Compatibility::Compatible,
                    "synthetic:unknown" => Compatibility::Unknown,
                    _ => panic!(),
                }
            );
        }
        let mut filtered = word.clone();
        let mut ann = annotation.clone();
        ann.filter(&mut filtered, DictionaryFilter::Compatible);
        assert_eq!(
            filtered.analyses.contains(a),
            status != Compatibility::Incompatible
        );
        assert!(dict.cache_bytes() <= 4096);
    }
}
