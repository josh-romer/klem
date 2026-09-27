//! COV-021g: per-entry 르/러 written paradigms.
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
    s.cases.retain(|c| c.id.starts_with("reu-compat-"));
    s
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!("klem-reu-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-reu.json")],
            &path,
            "reu",
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
fn reu_constraints_preserve_raw_headword_and_cli_contracts() {
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
        .unwrap_or_else(|| panic!("{}: missing {ls:?} {ms:?}", word.normalized))
}

#[test]
fn every_native_entry_keeps_its_own_written_class() {
    let f = Fixture::new("profiles");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/reu-sources.json")).unwrap();
    let entries = source["source_entries"].as_array().unwrap();
    assert_eq!(entries.len(), 149);
    let mut counts = std::collections::BTreeMap::new();
    for profile in source["profiles"].as_array().unwrap() {
        let id = profile["entry"].as_str().unwrap();
        let expected = entries.iter().find(|e| e["id"] == id).unwrap();
        let entry = db.entry(id).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        let classes = profile["classes"].as_array().unwrap();
        *counts
            .entry(
                classes
                    .first()
                    .and_then(|c| c.as_str())
                    .unwrap_or("unknown"),
            )
            .or_insert(0) += 1;
        for (spelling, surface) in profile["variants"].as_object().unwrap() {
            let Some(surface) = surface.as_str() else {
                continue;
            };
            let word = Lemmatizer::new().analyze_word(surface).unwrap();
            let a = path(&word, &[&entry.summary.headword], &["어"]);
            let annotation = dict.annotate(&word).unwrap();
            let reading = annotation.assess(a);
            let assessment = reading.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == id)
                .unwrap();
            let expected = if classes.is_empty() {
                Compatibility::Unknown
            } else if classes.iter().any(|c| c == spelling) {
                Compatibility::Compatible
            } else {
                Compatibility::Incompatible
            };
            assert_eq!(assessment.status, expected, "{id} {surface} {spelling}");
            let matched = annotation
                .lemmas
                .iter()
                .flat_map(|l| &l.entries)
                .find(|e| e.entry.id == id)
                .unwrap();
            assert!(
                matched.hieut.is_none()
                    && matched.digeut.is_none()
                    && matched.siot.is_none()
                    && matched.bieup.is_none()
            );
            if classes.is_empty() {
                assert!(matched.reu.is_none());
            } else {
                let evidence = serde_json::to_value(matched.reu.as_ref().unwrap()).unwrap();
                for (class, forms) in evidence.as_object().unwrap() {
                    let expected: Vec<_> = entry
                        .forms
                        .iter()
                        .filter(|f| {
                            f.kind == "활용"
                                && f.written.trim()
                                    == profile["variants"][class].as_str().unwrap_or("")
                        })
                        .map(|f| f.written.clone())
                        .collect();
                    assert_eq!(
                        serde_json::from_value::<Vec<String>>(forms.clone()).unwrap(),
                        expected,
                        "{id} {class}"
                    );
                }
            }
        }
    }
    assert_eq!(
        counts,
        std::collections::BTreeMap::from([
            ("eu_deletion", 8),
            ("rieul_doubling", 126),
            ("reo", 6),
            ("unknown", 9)
        ])
    );
    for (surface, head) in [
        ("일러", "이르다"),
        ("이르러", "이르다"),
        ("눌러", "누르다"),
        ("누르러", "누르다"),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let reading = dict
            .annotate(&word)
            .unwrap()
            .assess(path(&word, &[head], &["어"]));
        assert_eq!(reading.status, Compatibility::Compatible);
        let statuses: Vec<_> = reading.lemmas[0].entries.iter().map(|e| e.status).collect();
        assert!(
            statuses.contains(&Compatibility::Compatible)
                && statuses.contains(&Compatibility::Incompatible)
        );
    }
}

#[test]
fn reu_requirements_follow_their_component_through_composition() {
    use SpellingClass::{
        HieutRegular as H, ReoAddition as O, ReuDoubling as D, ReuEuDeletion as E,
        ReuUncontracted as U,
    };
    let f = Fixture::new("owners");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    for (surface, ls, ms, requirements, status) in [
        (
            "치러놓으니",
            vec!["치르다", "놓다"],
            vec!["어", "으니"],
            vec![(0, E), (1, H)],
            Compatibility::Compatible,
        ),
        (
            "칠러놓으니",
            vec!["치르다", "놓다"],
            vec!["어", "으니"],
            vec![(0, D), (1, H)],
            Compatibility::Incompatible,
        ),
        (
            "치르어놓으니",
            vec!["치르다", "놓다"],
            vec!["어", "으니"],
            vec![(0, U), (1, H)],
            Compatibility::Incompatible,
        ),
        (
            "푸르러졌어요",
            vec!["푸르다", "지다"],
            vec!["어", "었", "어요"],
            vec![(0, O)],
            Compatibility::Compatible,
        ),
        (
            "몰라보았어요",
            vec!["모르다", "보다"],
            vec!["어", "었", "어요"],
            vec![(0, D)],
            Compatibility::Compatible,
        ),
        (
            "치렀음이었다",
            vec!["치르다", "이다"],
            vec!["었", "음", "었", "다"],
            vec![(0, E)],
            Compatibility::Compatible,
        ),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = path(&word, &ls, &ms);
        assert_eq!(
            a.spelling_paths,
            vec![
                requirements
                    .into_iter()
                    .map(|(morpheme_index, class)| SpellingRecovery {
                        morpheme_index,
                        class
                    })
                    .collect::<Vec<_>>()
            ],
            "{surface}"
        );
        assert_eq!(
            dict.annotate(&word).unwrap().assess(a).status,
            status,
            "{surface}"
        );
        assert_eq!(
            serde_json::from_str::<Analysis>(&serde_json::to_string(a).unwrap()).unwrap(),
            *a
        );
    }
    for (surface, forms) in [
        ("치르니", vec!["으니"]),
        ("치르시니", vec!["시", "으니"]),
        ("치르고", vec!["고"]),
        ("치른", vec!["은"]),
        ("치름", vec!["음"]),
        ("치르리라", vec!["으리라"]),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = path(&word, &["치르다"], &forms);
        assert!(a.spelling_paths.is_empty(), "{surface}");
        assert_ne!(
            dict.annotate(&word).unwrap().assess(a).status,
            Compatibility::Incompatible,
            "{surface}"
        );
    }
}

#[test]
fn native_written_conjugations_preserve_the_explicit_short_form_discrepancy() {
    let f = Fixture::new("all-forms");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/reu-sources.json")).unwrap();
    let mut missing = Vec::new();
    let mut count = 0;
    for e in source["source_entries"].as_array().unwrap() {
        for form in e["forms"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|f| f["kind"] == "활용")
        {
            count += 1;
            let surface = form["written"].as_str().unwrap().trim();
            let mut word = Lemmatizer::new().analyze_word(surface).unwrap();
            let mut annotation = dict.annotate(&word).unwrap();
            annotation.filter(&mut word, DictionaryFilter::Compatible);
            if !word
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == e["headword"].as_str().unwrap())
            {
                missing.push((
                    e["id"].as_str().unwrap(),
                    e["headword"].as_str().unwrap(),
                    surface,
                ));
            }
        }
    }
    assert_eq!(count, 404);
    // KRDict 29043 lists 서툰 under 서투르다, but NIKL Q&A 324385
    // (2025-12-01) assigns it to the separate shortened headword 서툴다.
    // Preserve both source evidence and lexical identity, not a general 르 deletion.
    assert_eq!(missing, [("krdict:29043", "서투르다", "서툰")]);
    let short = Lemmatizer::new().analyze_word("서툰").unwrap();
    assert!(
        short
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == "서툴다")
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
            "synthetic-reu-homonyms"
        }
        fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
            if head == "치르다" {
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
    let regular = db.entry("krdict:28130").unwrap().unwrap();
    // Exercise future/custom dictionaries too: multiple explicitly written
    // classes coexist, while pronunciations never supply written evidence.
    for (written, surface, class) in [
        (" 치러 ", "치러", SpellingClass::ReuEuDeletion),
        ("칠러", "칠러", SpellingClass::ReuDoubling),
        ("치르러", "치르러", SpellingClass::ReoAddition),
        ("치르어", "치르어", SpellingClass::ReuUncontracted),
    ] {
        let mut custom = regular.clone();
        custom.forms.push(WordForm {
            kind: "활용".into(),
            written: written.nfd().collect(),
            pronunciations: vec![],
        });
        let source = Homonyms {
            base: f.open(),
            entries: vec![custom],
        };
        let mut session = DictionarySession::new(&source, 4096);
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = path(&word, &["치르다"], &["어"]);
        assert_eq!(
            a.spelling_paths,
            vec![vec![SpellingRecovery {
                morpheme_index: 0,
                class
            }]]
        );
        let annotation = session.annotate(&word).unwrap();
        assert_eq!(annotation.assess(a).status, Compatibility::Compatible);
        let mut legacy = serde_json::to_value(&annotation).unwrap();
        for l in legacy["lemmas"].as_array_mut().unwrap() {
            for e in l["entries"].as_array_mut().unwrap() {
                e.as_object_mut().unwrap().remove("reu");
            }
        }
        let legacy: klem::dictionary::Annotation = serde_json::from_value(legacy).unwrap();
        assert_eq!(legacy.assess(a).status, Compatibility::Unknown);
        assert!(session.cache_bytes() <= 4096);
    }
    let mut irregular = regular.clone();
    irregular.summary.id = "synthetic:irregular".into();
    irregular.forms = vec![WordForm {
        kind: "활용".into(),
        written: "칠러".into(),
        pronunciations: vec![],
    }];
    let mut unknown = regular.clone();
    unknown.summary.id = "synthetic:unknown".into();
    unknown.forms = vec![WordForm {
        kind: "활용".into(),
        written: String::new(),
        pronunciations: vec!["칠러".into()],
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
        let word = Lemmatizer::new().analyze_word("칠러").unwrap();
        let a = path(&word, &["치르다"], &["어"]);
        let annotation = dict.annotate(&word).unwrap();
        let assessment = annotation.assess(a);
        assert_eq!(assessment.status, status);
        for e in &assessment.lemmas[0].entries {
            assert_eq!(
                e.status,
                match e.id.as_str() {
                    "krdict:28130" => Compatibility::Incompatible,
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
