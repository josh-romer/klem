//! COV-021e: per-entry ㄷ/ㅅ paradigms and homonym preservation.
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
    s.cases.retain(|c| c.id.starts_with("ds-compat-"));
    s
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-digeut-siot-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-digeut-siot.json")],
            &path,
            "digeut-siot",
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
fn digeut_siot_constraints_preserve_raw_headword_and_cli_contracts() {
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
fn complete_native_paradigms_keep_homonym_evidence_separate() {
    let f = Fixture::new("native");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/digeut-siot-sources.json")).unwrap();
    let entries = source["source_entries"].as_array().unwrap();
    assert_eq!(entries.len(), 124);
    let mut counts = std::collections::BTreeMap::new();
    for profile in source["profiles"].as_array().unwrap() {
        let id = profile["entry"].as_str().unwrap();
        let expected = entries.iter().find(|e| e["id"] == id).unwrap();
        let entry = db.entry(id).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        let class = profile["class_from_written_ni"].as_str().unwrap();
        *counts.entry(class).or_insert(0) += 1;
        for spelling in ["regular", "irregular"] {
            let word = Lemmatizer::new()
                .analyze_word(profile[spelling].as_str().unwrap())
                .unwrap();
            let a = path(&word, &[&entry.summary.headword], &["으니"]);
            let annotation = dict.annotate(&word).unwrap();
            let reading = annotation.assess(a);
            let assessment = reading.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == id)
                .unwrap();
            let expected = if class == "unknown" {
                Compatibility::Unknown
            } else if class == spelling {
                Compatibility::Compatible
            } else {
                Compatibility::Incompatible
            };
            assert_eq!(assessment.status, expected, "{id} {spelling}");
            let matched = annotation
                .lemmas
                .iter()
                .flat_map(|l| &l.entries)
                .find(|e| e.entry.id == id)
                .unwrap();
            assert!(matched.hieut.is_none());
            let evidence = if profile["family"] == "digeut" {
                assert!(matched.siot.is_none());
                &matched.digeut
            } else {
                assert!(matched.digeut.is_none());
                &matched.siot
            };
            if class == "unknown" {
                assert!(evidence.is_none());
            } else {
                let evidence = evidence.as_ref().unwrap();
                assert_eq!(!evidence.regular.is_empty(), class == "regular");
                assert_eq!(!evidence.irregular.is_empty(), class == "irregular");
            }
        }
    }
    assert_eq!(
        counts,
        std::collections::BTreeMap::from([("regular", 65), ("irregular", 54), ("unknown", 5)])
    );
    // Actual native homonyms share lemma strings but not inflection paradigms.
    for surface in ["걸으니", "걷으니", "물으니", "묻으니"] {
        let head = if surface.starts_with(['걸', '걷']) {
            "걷다"
        } else {
            "묻다"
        };
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = path(&word, &[head], &["으니"]);
        let reading = dict.annotate(&word).unwrap().assess(a);
        assert_eq!(reading.status, Compatibility::Compatible);
        let statuses: Vec<_> = reading.lemmas[0].entries.iter().map(|e| e.status).collect();
        assert!(statuses.contains(&Compatibility::Compatible));
        assert!(statuses.contains(&Compatibility::Incompatible));
    }
}

#[test]
fn mixed_spelling_classes_keep_prefinal_auxiliary_and_copular_owners() {
    use SpellingClass::{
        DigeutIrregular as D, HieutIrregular as I, HieutRegular as H, SiotIrregular as S,
        SiotRegular as R,
    };
    let f = Fixture::new("owners");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    for (surface, ls, ms, requirements, status) in [
        (
            "들어놓으니",
            vec!["듣다", "놓다"],
            vec!["어", "으니"],
            vec![(0, D), (1, H)],
            Compatibility::Compatible,
        ),
        (
            "들어놀라고",
            vec!["듣다", "놓다"],
            vec!["어", "을라고"],
            vec![(0, D), (1, I)],
            Compatibility::Incompatible,
        ),
        (
            "지어놔요",
            vec!["짓다", "놓다"],
            vec!["어", "어요"],
            vec![(0, S), (1, H)],
            Compatibility::Compatible,
        ),
        (
            "벗어놓으니",
            vec!["벗다", "놓다"],
            vec!["어", "으니"],
            vec![(0, R), (1, H)],
            Compatibility::Compatible,
        ),
        (
            "들음이었다",
            vec!["듣다", "이다"],
            vec!["음", "었", "다"],
            vec![(0, D)],
            Compatibility::Compatible,
        ),
        (
            "들으셨으니",
            vec!["듣다"],
            vec!["시", "었", "으니"],
            vec![(0, D)],
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
    }
    for surface in ["듣고", "듣겠어요", "짓습니다", "웃다"] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let head = if surface.starts_with('듣') {
            "듣다"
        } else if surface.starts_with('짓') {
            "짓다"
        } else {
            "웃다"
        };
        assert!(
            word.analyses
                .iter()
                .filter(|a| a.lemmas.len() == 1 && a.lemmas[0].text == head)
                .all(|a| a.spelling_paths.is_empty())
        );
    }
}
