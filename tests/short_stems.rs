//! COV-021h: entry-specific short-stem restrictions.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/dictionary-attachments.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("short-stem-"));
    s
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-short-stems-{tag}-{}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-short-stems.json")],
            &path,
            "short-stems",
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
fn short_stem_constraints_preserve_raw_headword_and_cli_contracts() {
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
fn native_entry_identities_preserve_homonyms_and_source_conflicts() {
    use klem::dictionary::AttachmentRule;
    let f = Fixture::new("native");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/short-stem-sources.json")).unwrap();
    for e in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
    }
    for (surface, head, id, forbidden) in [
        ("까불어", "까불다", "krdict:38390", true),
        ("까불어", "까불다", "krdict:42138", false),
        ("건들어", "건들다", "krdict:23620", true),
        ("서툴어", "서툴다", "krdict:29045", true),
        ("굴어", "굴다", "krdict:37417", false),
        ("들까불어", "들까불다", "krdict:50569", false),
        ("썰어", "썰다", "krdict:29774", false),
        ("일어", "일다", "krdict:72214", false),
        ("부어", "붓다", "krdict:24536", false),
        ("부어", "붓다", "krdict:62054", false),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let annotation = dict.annotate(&word).unwrap();
        let reading = annotation.assess(path(&word, &[head], &["어"]));
        let entry = reading.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == id)
            .unwrap();
        assert_eq!(
            entry.status == Compatibility::Incompatible,
            forbidden,
            "{surface} {id}"
        );
        assert_eq!(
            entry
                .conflicts
                .iter()
                .any(|c| c.rule == AttachmentRule::ShortStemEnding && c.morpheme_index == Some(0)),
            forbidden
        );
        if surface == "까불어" {
            assert_eq!(reading.status, Compatibility::Compatible);
        }
    }
    // Check every listed form against its owning entry, not a helpful homonym.
    let mut discrepancies = Vec::new();
    let mut count = 0;
    for profile in source["profiles"].as_array().unwrap() {
        let id = profile["entry"].as_str().unwrap();
        let e = db.entry(id).unwrap().unwrap();
        for form in e.forms.iter().filter(|f| f.kind == "활용") {
            count += 1;
            let word = Lemmatizer::new().analyze_word(form.written.trim()).unwrap();
            let annotation = dict.annotate(&word).unwrap();
            let supported =
                word.analyses
                    .iter()
                    .filter(|a| a.lemmas.len() == 1 && a.lemmas[0].text == e.summary.headword)
                    .any(|a| {
                        annotation.assess(a).lemmas[0].entries.iter().any(|entry| {
                            entry.id == id && entry.status != Compatibility::Incompatible
                        })
                    });
            if !supported {
                discrepancies.push((id.to_owned(), form.written.clone()));
            }
        }
    }
    assert_eq!(count, 22);
    assert_eq!(
        discrepancies,
        [
            ("krdict:23620", "건들어"),
            ("krdict:38390", "까불어"),
            ("krdict:29045", "서툴어")
        ]
        .map(|(i, w)| (i.into(), w.into()))
    );
}

#[test]
fn restrictions_stop_at_the_first_owned_boundary() {
    use klem::dictionary::AttachmentRule;
    let f = Fixture::new("ownership");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    for (surface, ls, ms, conflict) in [
        (
            "딛어놓으니",
            vec!["딛다", "놓다"],
            vec!["어", "으니"],
            Some(0),
        ),
        (
            "딛고싶었어요",
            vec!["딛다", "싶다"],
            vec!["고", "었", "어요"],
            None,
        ),
        ("갖겠어요", vec!["갖다"], vec!["겠", "어요"], None),
        (
            "머묾이었다",
            vec!["머물다", "이다"],
            vec!["음", "었", "다"],
            None,
        ),
        (
            "딛음이었다",
            vec!["딛다", "이다"],
            vec!["음", "었", "다"],
            Some(0),
        ),
        ("서투시니", vec!["서툴다"], vec!["시", "으니"], None),
        ("뵙으시니", vec!["뵙다"], vec!["시", "으니"], Some(0)),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let a = path(&word, &ls, &ms);
        let reading = dict.annotate(&word).unwrap().assess(a);
        assert_eq!(
            reading.status == Compatibility::Incompatible,
            conflict.is_some(),
            "{surface}"
        );
        let conflicts: Vec<_> = reading
            .lemmas
            .iter()
            .flat_map(|l| &l.entries)
            .flat_map(|e| &e.conflicts)
            .filter(|c| c.rule == AttachmentRule::ShortStemEnding)
            .collect();
        assert_eq!(!conflicts.is_empty(), conflict.is_some(), "{surface}");
        assert!(conflicts.iter().all(|c| c.morpheme_index == conflict));
    }
}

#[test]
fn purpose_endings_do_not_turn_long_stem_forms_into_short_stem_aeo() {
    let f = Fixture::new("purpose");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    for (surface, short, long) in [
        ("머물러", "머물다", "머무르다"),
        ("서둘러", "서둘다", "서두르다"),
    ] {
        let word = Lemmatizer::new().analyze_word(surface).unwrap();
        let annotation = dict.annotate(&word).unwrap();
        for (head, ending) in [(short, "으러"), (long, "어")] {
            assert_eq!(
                annotation.assess(path(&word, &[head], &[ending])).status,
                Compatibility::Compatible,
                "{surface} {head} {ending}"
            );
        }
        assert!(!word.analyses.iter().any(|a| a.lemmas.len() == 1
            && a.lemmas[0].text == short
            && a.morphemes.len() == 1
            && a.morphemes[0].form == "어"));
    }
    // A third-party homonym cannot inherit a restriction by spelling alone.
    let word = Lemmatizer::new().analyze_word("서툴어").unwrap();
    let a = path(&word, &["서툴다"], &["어"]);
    let mut annotation = dict.annotate(&word).unwrap();
    assert_eq!(annotation.assess(a).status, Compatibility::Incompatible);
    for l in &mut annotation.lemmas {
        for e in &mut l.entries {
            if e.entry.id == "krdict:29045" {
                e.entry.id = "custom:unknown-short-form".into();
            }
        }
    }
    assert_eq!(annotation.assess(a).status, Compatibility::Compatible);
}

#[test]
fn lexical_gajeun_remains_when_its_unsupported_inflection_is_filtered() {
    let f = Fixture::new("lexical");
    let db = f.open();
    let mut dict = DictionarySession::new(&db, 4096);
    let mut word = Lemmatizer::new().analyze_word("갖은").unwrap();
    assert!(
        word.analyses
            .iter()
            .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == "갖다")
    );
    let mut annotation = dict.annotate(&word).unwrap();
    annotation.filter(&mut word, DictionaryFilter::Compatible);
    assert!(
        !word
            .analyses
            .iter()
            .any(|a| a.lemmas.iter().any(|l| l.text == "갖다"))
    );
    let a = path(&word, &["갖은"], &[]);
    assert!(a.unchanged);
    assert!(
        annotation
            .lemmas
            .iter()
            .any(|l| l.lemma.text == "갖은"
                && l.entries.iter().any(|e| e.entry.id == "krdict:22767"))
    );
}
