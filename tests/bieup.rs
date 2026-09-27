//! COV-021f: per-entry ㅂ paradigms and finite written 오 exceptions.
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
    s.cases.retain(|c| c.id.starts_with("bieup-compat-"));
    s
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!("klem-bieup-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-bieup.json")],
            &path,
            "bieup",
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
fn bieup_constraints_preserve_raw_headword_and_cli_contracts() {
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
        serde_json::from_str(include_str!("fixtures/bieup-sources.json")).unwrap();
    let entries = source["source_entries"].as_array().unwrap();
    assert_eq!(entries.len(), 443);
    let mut counts = std::collections::BTreeMap::new();
    for profile in source["profiles"].as_array().unwrap() {
        let id = profile["entry"].as_str().unwrap();
        let expected = entries.iter().find(|e| e["id"] == id).unwrap();
        let entry = db.entry(id).unwrap().unwrap();
        assert_eq!(serde_json::to_value(&entry).unwrap(), *expected);
        let class = profile["class_from_written_forms"].as_str().unwrap();
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
            assert!(matched.digeut.is_none());
            assert!(matched.siot.is_none());
            let evidence = &matched.bieup;
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
        std::collections::BTreeMap::from([("regular", 56), ("irregular", 377), ("unknown", 10)])
    );

    for surface in ["고우니", "곱으니", "구우니", "굽으니"] {
        let head = if surface.starts_with(['고', '곱']) {
            "곱다"
        } else {
            "굽다"
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
fn bieup_owners_stay_separate_from_auxiliaries_copulas_and_fixed_suffixes() {
    use SpellingClass::{BieupIrregular as I, BieupRegular as R, HieutRegular as H};
    let f = Fixture::new("owners");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    for (surface, ls, ms, requirements) in [
        (
            "입어놓으니",
            vec!["입다", "놓다"],
            vec!["어", "으니"],
            vec![(0, R), (1, H)],
        ),
        (
            "가까워졌어요",
            vec!["가깝다", "지다"],
            vec!["어", "었", "어요"],
            vec![(0, I)],
        ),
        (
            "어려움이었다",
            vec!["어렵다", "이다"],
            vec!["음", "었", "다"],
            vec![(0, I)],
        ),
        (
            "듣자와놓으니",
            vec!["듣잡다", "놓다"],
            vec!["어", "으니"],
            vec![(0, I), (1, H)],
        ),
        (
            "학생다워놓으니",
            vec!["학생", "놓다"],
            vec!["답다", "어", "으니"],
            vec![(2, H)],
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
            Compatibility::Compatible,
            "{surface}"
        );
    }
}

#[test]
fn finite_o_spellings_preserve_exact_source_forms_and_reject_wrong_u_paths() {
    let all: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    let mut scoped = all;
    scoped.cases.retain(|c| c.id.starts_with("bieup-written-"));
    let report = validity::evaluate(&scoped).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (18, 18));
}

#[test]
fn native_written_forms_preserve_the_explicit_source_spelling_conflict() {
    let f = Fixture::new("all-forms");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/bieup-sources.json")).unwrap();
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
    assert_eq!(count, 1674);
    // Preserve the primary source's mismatched written stem. Do not silently
    // rewrite the fixture or add arbitrary spelling repair to recover 얕잡다.
    assert_eq!(missing, [("krdict:67256", "얕잡다", "얃잡는")]);
}
