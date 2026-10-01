//! COV-022j: finite 까불이 relationship without selecting a verb homonym.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use serde_json::{Value, json};
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("noun-predicate-"));
    s
}
fn arr(v: &Value) -> Vec<&Value> {
    if let Some(a) = v.as_array() {
        a.iter().collect()
    } else if v.is_object() {
        vec![v]
    } else {
        vec![]
    }
}
fn feature<'a>(v: &'a Value, name: &str) -> Option<&'a str> {
    arr(&v["feat"])
        .into_iter()
        .find(|f| f["att"] == name)
        .and_then(|f| f["val"].as_str())
}
fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
        && j.lemma_kinds
            .as_ref()
            .is_none_or(|k| a.lemmas.iter().map(|l| l.kind).eq(k.iter().copied()))
        && j.morphemes
            .as_ref()
            .is_none_or(|m| a.morphemes.iter().map(|x| &x.form).eq(m.iter()))
        && j.morpheme_kinds
            .as_ref()
            .is_none_or(|k| a.morphemes.iter().map(|m| m.kind).eq(k.iter().copied()))
        && j.required_rules
            .as_ref()
            .is_none_or(|r| r.iter().all(|r| a.rules.contains(r)))
}
#[test]
fn native_class_homonyms_and_all_suffix_groups_remain_complete() {
    let m: Value =
        serde_json::from_str(include_str!("fixtures/noun-predicate-sources.json")).unwrap();
    let f: Value =
        serde_json::from_str(include_str!("fixtures/krdict-noun-predicate.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 15);
    let suffix = entries.iter().find(|e| e["val"] == "88924").unwrap();
    assert_eq!(feature(suffix, "partOfSpeech"), Some("접사"));
    assert_eq!(arr(&suffix["Sense"]).len(), 3);
    let mut groups = 0;
    let mut targets = 0;
    for sense in arr(&suffix["Sense"]) {
        for (i, group) in arr(&sense["SenseExample"]).iter().enumerate() {
            groups += 1;
            let recorded = arr(&m["source_groups"])
                .into_iter()
                .find(|g| g["sense_id"] == sense["val"] && g["example_group"] == i + 1)
                .unwrap();
            assert_eq!(&recorded["native_group"], *group);
            for t in arr(&recorded["targets"]) {
                targets += 1;
                assert_eq!(sense["val"], "3");
                assert_eq!(t["surface"], "까불이");
                assert_eq!(t["base"], "까불다");
                let cases = suite();
                let c = cases.cases.iter().find(|c| c.id == t["case_id"]).unwrap();
                assert_eq!(c.surface, t["surface"]);
            }
        }
    }
    assert_eq!((groups, targets), (44, 1));
    let verbs: Vec<_> = entries
        .iter()
        .filter(|e| feature(&e["Lemma"], "writtenForm") == Some("까불다"))
        .collect();
    assert_eq!(verbs.len(), 2);
    assert!(
        verbs
            .iter()
            .all(|e| feature(e, "partOfSpeech") == Some("동사"))
    );
    assert_eq!(m["representation"]["native_sense"], "3");
    assert_eq!(m["representation"]["class_note_preserved"], true);
    assert!(
        arr(&m["corpus_training_search"])
            .iter()
            .all(|c| c["matching_tokens"] == 0)
    );
}
#[test]
fn predicate_noun_boundary_keeps_unicode_and_later_copula_ownership() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (17, 3));
    let engine = Lemmatizer::new();
    for c in suite().cases {
        let a = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            a,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(a.analyses.iter().any(|p| p.unchanged));
        for p in &a.analyses {
            assert!(p.breakdown().is_some(), "{}: {p:?}", c.surface);
            assert!(p.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            if p.rules.iter().any(|r| r == "suffix.nominal.i") {
                assert_eq!(p.lemmas[0].text, "까불다");
                assert_eq!(p.lemmas[0].kind, klem::LemmaKind::Predicate);
                assert!(
                    !p.rules
                        .iter()
                        .any(|r| r == "derivation.nominal.related_root")
                );
                assert_eq!(p.morphemes[0].form, "이");
                assert_eq!(
                    p.breakdown().unwrap()[..2],
                    [
                        klem::breakdown::Component::Lemma(0),
                        klem::breakdown::Component::Morpheme(0)
                    ]
                );
            }
        }
    }
    let a = engine.analyze_word("까불이들이었다").unwrap();
    let p = a
        .analyses
        .iter()
        .find(|p| p.rules.iter().any(|r| r == "suffix.nominal.i") && p.lemmas.len() == 2)
        .unwrap();
    assert_eq!(
        p.breakdown().unwrap(),
        vec![
            klem::breakdown::Component::Lemma(0),
            klem::breakdown::Component::Morpheme(0),
            klem::breakdown::Component::Morpheme(1),
            klem::breakdown::Component::Lemma(1),
            klem::breakdown::Component::Morpheme(2),
            klem::breakdown::Component::Morpheme(3)
        ]
    );
    for word in [
        "까불이님",
        "까불이적",
        "까불이답다",
        "까불이이",
        "까불이다이",
        "까불어이",
        "까불아이",
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|p| !p.rules.iter().any(|r| r == "suffix.nominal.i")),
            "{word}"
        );
    }
    let repeated = engine.analyze_word("까불이들들").unwrap();
    for p in repeated
        .analyses
        .iter()
        .filter(|p| p.rules.iter().any(|r| r == "suffix.nominal.i"))
    {
        assert!(
            p.morphemes
                .iter()
                .filter(|m| m.form == "들" && m.kind == klem::MorphemeKind::Suffix)
                .count()
                <= 1
        );
    }
    let legal = engine
        .analyze_word("까불이")
        .unwrap()
        .analyses
        .into_iter()
        .find(|p| p.rules.iter().any(|r| r == "suffix.nominal.i"))
        .unwrap();
    for (form, kind) in [
        ("이", klem::MorphemeKind::Particle),
        ("었", klem::MorphemeKind::Prefinal),
    ] {
        let mut invalid = legal.clone();
        invalid.morphemes[0].form = form.into();
        invalid.morphemes[0].kind = kind;
        assert!(invalid.breakdown().is_none());
    }
}
struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn dictionary(tag: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!(
        "klem-noun-predicate-{tag}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-predicate.json")],
        &path,
        "noun-predicate",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), db)
}
#[test]
fn both_verb_homonyms_and_whole_noun_survive_filters_and_cli_exports() {
    let (cleanup, db) = dictionary("cli");
    assert_eq!(db.lookup("까불다").unwrap().len(), 2);
    assert_eq!(db.lookup("까불이").unwrap().len(), 1);
    assert!(db.lookup("까불").unwrap().is_empty());
    assert_eq!(db.entry("krdict:88924").unwrap().unwrap().senses.len(), 3);
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let cases = suite().cases;
    let text = cases
        .iter()
        .map(|c| c.surface.as_str())
        .collect::<Vec<_>>()
        .join(" ");
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let mut expected = vec![];
        for c in &cases {
            let mut a = engine.analyze_word(&c.surface).unwrap();
            let mut annotation = dictionary.annotate(&a).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut a, filter);
            }
            for j in &c.judgments {
                assert_eq!(
                    a.analyses.iter().any(|a| matches(a, j)),
                    matches!(j.verdict, validity::Verdict::Required),
                    "{} {flag:?}",
                    c.id
                );
            }
            if c.surface == "까불이" {
                assert!(a.analyses.iter().any(|p| p.unchanged));
                let lookup = annotation
                    .lemmas
                    .iter()
                    .find(|l| l.lemma.text == "까불다")
                    .unwrap();
                assert_eq!(lookup.entries.len(), 2);
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"])
                .arg(&cleanup.0);
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
                serde_json::to_value(&annotation).unwrap()
            );
            assert_eq!(actual, serde_json::to_value(&a).unwrap());
            expected.push((actual, serde_json::to_value(annotation).unwrap()));
        }
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
        cmd.args(["text", "-", "--dictionary"]).arg(&cleanup.0);
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
        let records: Vec<Value> = String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .filter(|r: &Value| !r["analysis"].is_null())
            .collect();
        assert_eq!(records.len(), cases.len());
        for (r, (a, d)) in records.iter().zip(expected) {
            assert_eq!(r["analysis"], a);
            assert_eq!(r["dictionary"], d);
        }
        assert!(dictionary.cache_bytes() <= 4096);
    }
}
#[test]
fn noun_suffix_does_not_turn_a_case_marked_noun_into_a_spacing_predicate() {
    let (_cleanup, db) = dictionary("spacing");
    let mut session = klem::Session::new(Lemmatizer::new().into(), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    for (surface, wanted, allowed) in [
        ("까불이를먹는다", "까불이를 먹는다", true),
        ("까불이를까불이", "까불이를 까불이", false),
    ] {
        let result = klem::spacing::suggest(
            &mut session,
            &mut dictionary,
            surface,
            0,
            Default::default(),
        )
        .unwrap();
        assert_eq!(
            result.alternatives.iter().any(|a| a.spaced == wanted),
            allowed
        );
        if allowed {
            let a = result
                .alternatives
                .iter()
                .find(|a| a.spaced == wanted)
                .unwrap();
            assert!(
                a.records[0]
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|p| p.rules.iter().any(|r| r == "suffix.nominal.i"))
            );
            assert!(
                a.records
                    .iter()
                    .all(|r| r.breakdowns.iter().all(Option::is_some))
            );
        }
    }
    assert!(dictionary.cache_bytes() <= 4096);
    // Keep canonical lookup text, rather than inventing a new root lemma kind.
    assert_eq!(
        json!(
            Lemmatizer::new()
                .analyze_word("까불이")
                .unwrap()
                .analyses
                .into_iter()
                .find(|p| p.rules.iter().any(|r| r == "suffix.nominal.i"))
                .unwrap()
                .lemmas[0]
                .text
        ),
        "까불다"
    );
}
