//! COV-019ad: source-scoped immediate-left classes, independent of raw generation.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    AttachmentRule, Compatibility, Dictionary, DictionaryFilter, DictionarySession,
    SqliteDictionary, import_krdict, pos_compatibility,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    serde_json::from_str(include_str!("fixtures/continuation-left-sources.json")).unwrap()
}
fn judgments() -> Value {
    serde_json::from_str(include_str!(
        "fixtures/continuation-left-entry-judgments.json"
    ))
    .unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-continuation-left-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-continuation-left.json",
            )],
            &path,
            "continuation-left",
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
fn named<'a>(word: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| {
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
fn path(a: &Analysis, c: &Value) -> bool {
    serde_json::to_value(&a.lemmas).unwrap() == c["lemmas"]
        && serde_json::to_value(&a.morphemes).unwrap() == c["morphemes"]
}

#[test]
fn complete_sources_and_prechange_raw_paths_are_preserved() {
    let source = sources();
    let f = Fixture::new("source");
    let db = f.open();
    assert_eq!(source["source_entries"].as_array().unwrap().len(), 55);
    for e in source["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(e["id"].as_str().unwrap()).unwrap().unwrap()).unwrap(),
            *e
        );
        let mut full = source["complete_native_entries"][e["id"].as_str().unwrap()].clone();
        for sense in full["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(full, *e);
    }
    let preflight: Value = serde_json::from_str(include_str!(
        "../docs/continuation-left-source-preflight.json"
    ))
    .unwrap();
    for (s, w) in preflight["words"].as_object().unwrap() {
        assert_eq!(source["before_words"][s], *w);
    }
    let engine = Lemmatizer::new();
    assert_eq!(source["before_words"].as_object().unwrap().len(), 160);
    for (surface, modes) in source["before_words"].as_object().unwrap() {
        let mut frozen = modes["all"].clone();
        frozen.as_object_mut().unwrap().remove("dictionary");
        let frozen: WordAnalysis = serde_json::from_value(frozen).unwrap();
        let actual = engine.analyze_word(surface).unwrap();
        assert_eq!(actual, frozen, "{surface}");
        assert_eq!(
            actual,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        for a in &actual.analyses {
            assert_eq!(
                a.breakdown().unwrap().len(),
                a.lemmas.len() + a.morphemes.len()
            );
        }
    }
}

#[test]
fn individual_entry_classes_filter_only_the_authored_paths() {
    let fixture = Fixture::new("policy");
    let db = fixture.open();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let cases = judgments();
    assert_eq!(cases["cases"].as_array().unwrap().len(), 56);
    let mut entry_count = 0;
    for c in cases["cases"].as_array().unwrap() {
        let word = engine.analyze_word(c["surface"].as_str().unwrap()).unwrap();
        let analysis = word.analyses.iter().find(|a| path(a, c)).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let reading = annotation.assess(analysis);
        for j in c["judgments"].as_array().unwrap() {
            entry_count += 1;
            let slot = reading
                .lemmas
                .iter()
                .find(|s| s.lemma_index == j["lemma_index"].as_u64().unwrap() as usize)
                .unwrap();
            let entry = slot
                .entries
                .iter()
                .find(|e| e.id == j["entry_id"].as_str().unwrap())
                .unwrap();
            assert_eq!(
                serde_json::to_value(entry.status).unwrap(),
                j["status"],
                "{} {}",
                c["id"],
                entry.id
            );
            assert_eq!(
                serde_json::to_value(&entry.conflicts).unwrap(),
                j["conflicts"],
                "{} {}",
                c["id"],
                entry.id
            );
        }
        for policy in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut filtered = word.clone();
            let mut ann = annotation.clone();
            ann.filter(&mut filtered, policy);
            assert_eq!(
                filtered.analyses.iter().any(|a| path(a, c)),
                policy == DictionaryFilter::Headword || c["filter_retained"] == true,
                "{}",
                c["id"]
            );
        }
    }
    assert_eq!(entry_count, 276);
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/dictionary-attachments.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("continuation-left-"));
    let raw = validity::evaluate(&suite).unwrap();
    assert_eq!((raw.required_present, raw.forbidden_present), (21, 35));
    let report = validity::evaluate_with(&suite, |s| {
        let mut w = engine.analyze_word(s).unwrap();
        dictionary
            .annotate(&w)
            .unwrap()
            .filter(&mut w, DictionaryFilter::Compatible);
        Ok(w)
    })
    .unwrap();
    assert_eq!((report.required_total, report.forbidden_total), (21, 35));
    assert!(report.passed(), "{:?}", report.violations);
}

#[test]
fn class_dependencies_stop_at_other_owners_and_keep_unknown_providers() {
    let f = Fixture::new("owners");
    let db = f.open();
    let engine = Lemmatizer::new();
    let mut dict = DictionarySession::new(&db, 0);
    for (surface, heads, forms) in [
        (
            "좋아해내다",
            vec!["좋다", "하다", "내다"],
            vec!["어", "어", "다"],
        ),
        (
            "좋아보아내다",
            vec!["좋다", "보다", "내다"],
            vec!["어", "어", "다"],
        ),
        (
            "좋아지고나니",
            vec!["좋다", "지다", "나다"],
            vec!["어", "고", "으니"],
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = named(&word, &heads, &forms);
        let ann = dict.annotate(&word).unwrap();
        let r = ann.assess(a);
        assert!(
            r.lemmas[0].entries.iter().all(|e| e
                .conflicts
                .iter()
                .all(|c| c.rule != AttachmentRule::ContinuationVerb)),
            "{surface}"
        );
        // This only checks ownership; other lexical/sense restrictions remain unjudged.
    }
    for (surface, heads, forms) in [
        ("어두워가다", vec!["어둡다", "가다"], vec!["어", "다"]),
        ("깊어가다", vec!["깊다", "가다"], vec!["어", "다"]),
        ("밝아오다", vec!["밝다", "오다"], vec!["어", "다"]),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let ann = dict.annotate(&word).unwrap();
        let r = ann.assess(named(&word, &heads, &forms));
        assert!(r.lemmas.iter().flat_map(|s| &s.entries).all(|e| {
            e.conflicts
                .iter()
                .all(|c| c.rule != AttachmentRule::ContinuationVerb)
        }));
    }
    let word = engine.analyze_word("좋아내다").unwrap();
    for surface in ["학생들다워내다", "학생님다워내다", "학생님들다워내다"] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(["학생", "내다"])
                    && a.morphemes.iter().any(|m| m.form == "답다")
            })
            .unwrap();
        let ann = dict.annotate(&word).unwrap();
        let r = ann.assess(a);
        let entry = r.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == "krdict:31670")
            .unwrap();
        assert_eq!(entry.status, Compatibility::Incompatible, "{surface}");
        assert_eq!(entry.conflicts[0].rule, AttachmentRule::ContinuationVerb);
        assert_eq!(
            a.morphemes[entry.conflicts[0].morpheme_index.unwrap()].form,
            "어"
        );
    }
    let a = named(&word, &["좋다", "내다"], &["어", "다"]);
    let ann = dict.annotate(&word).unwrap();
    let mut unknown = ann.clone();
    for m in &mut unknown.lemmas {
        if m.lemma == a.lemmas[0] {
            for e in &mut m.entries {
                e.entry.pos = "provider-class-unreviewed".into();
                e.independent_pos = None;
                e.pos_compatibility = pos_compatibility(&m.lemma, &e.entry);
            }
        }
    }
    let r = unknown.assess(a);
    assert_eq!(r.status, Compatibility::Unknown);
    assert!(
        r.lemmas[0]
            .entries
            .iter()
            .all(|e| e.status == Compatibility::Unknown && e.conflicts.is_empty())
    );
    for field in ["id", "headword", "homonym", "pos"] {
        let mut other = ann.clone();
        for m in &mut other.lemmas {
            if m.lemma == a.lemmas[1] {
                for e in &mut m.entries {
                    if e.entry.id != "krdict:60625" {
                        continue;
                    }
                    match field {
                        "id" => e.entry.id = "other:60625".into(),
                        "headword" => e.entry.headword = "unreviewed-head".into(),
                        "homonym" => e.entry.homonym = "unreviewed".into(),
                        "pos" => e.entry.pos = "unreviewed".into(),
                        _ => unreachable!(),
                    }
                }
            }
        }
        assert!(
            other.assess(a).lemmas[0].entries.iter().all(|e| e
                .conflicts
                .iter()
                .all(|c| c.rule != AttachmentRule::ContinuationVerb)),
            "{field}"
        );
    }
    let unknown = engine.analyze_word("뮈어내다").unwrap();
    let r =
        dict.annotate(&unknown)
            .unwrap()
            .assess(named(&unknown, &["뮈다", "내다"], &["어", "다"]));
    assert_eq!(r.status, Compatibility::Unknown);
    let standalone = engine.analyze_word("내다").unwrap();
    let r = dict
        .annotate(&standalone)
        .unwrap()
        .assess(named(&standalone, &["내다"], &["다"]));
    assert_eq!(
        r.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == "krdict:60625")
            .unwrap()
            .status,
        Compatibility::Unknown
    );
}

#[test]
fn all_cli_modes_unicode_and_cache_budgets_agree() {
    let f = Fixture::new("cli");
    let db = f.open();
    let engine = Lemmatizer::new();
    for c in judgments()["cases"].as_array().unwrap() {
        for input in [
            c["surface"].as_str().unwrap().to_owned(),
            c["surface"].as_str().unwrap().nfd().collect::<String>(),
        ] {
            let word = engine.analyze_word(&input).unwrap();
            let mut reference = None;
            for budget in [0, 1, 4096] {
                let mut session = DictionarySession::new(&db, budget);
                let annotation = session.annotate(&word).unwrap();
                assert_eq!(annotation, session.annotate(&word).unwrap());
                assert!(session.cache_bytes() <= budget);
                if let Some(r) = &reference {
                    assert_eq!(&annotation, r);
                } else {
                    reference = Some(annotation);
                }
            }
            for (flag, policy) in [
                (None, None),
                (Some("--dict-only"), Some(DictionaryFilter::Headword)),
                (
                    Some("--dict-compatible"),
                    Some(DictionaryFilter::Compatible),
                ),
            ] {
                let mut expected = word.clone();
                let mut annotation = reference.clone().unwrap();
                if let Some(p) = policy {
                    annotation.filter(&mut expected, p);
                }
                let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
                cmd.args(["word", &input, "--dictionary"]).arg(&f.0);
                if let Some(flag) = flag {
                    cmd.arg(flag);
                }
                let output = cmd.output().unwrap();
                assert!(output.status.success());
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
                    expected
                );
            }
        }
    }
}
