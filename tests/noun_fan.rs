//! COV-022l: finite 허풍 + 선(扇) + 이 and source-specific root evidence.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    AttachmentRule, Compatibility, Dictionary, DictionaryFilter, DictionarySession,
    SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use serde_json::Value;
use std::{
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;
const RULE: &str = "derivation.nominal.root_compound";
fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("noun-fan-"));
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
fn fan(a: &Analysis) -> bool {
    a.rules.iter().any(|r| r == RULE)
}
struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn dictionary(tag: &str) -> (Cleanup, SqliteDictionary) {
    let path = std::env::temp_dir().join(format!("klem-noun-fan-{tag}-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-fan.json")],
        &path,
        "noun-fan",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (Cleanup(path), db)
}
#[test]
fn fan_sources_keep_complete_origins_groups_and_training_observations() {
    let m: Value = serde_json::from_str(include_str!("fixtures/noun-fan-sources.json")).unwrap();
    let f: Value = serde_json::from_str(include_str!("fixtures/krdict-noun-fan.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 19);
    let suffix = entries.iter().find(|e| e["val"] == "88924").unwrap();
    assert_eq!(arr(&suffix["Sense"]).len(), 3);
    let mut groups = 0;
    let mut targets = 0;
    for s in arr(&suffix["Sense"]) {
        for (i, g) in arr(&s["SenseExample"]).iter().enumerate() {
            groups += 1;
            let recorded = arr(&m["source_groups"])
                .into_iter()
                .find(|r| r["sense_id"] == s["val"] && r["example_group"] == i + 1)
                .unwrap();
            assert_eq!(&recorded["native_group"], *g);
            targets += arr(&recorded["targets"]).len();
        }
    }
    assert_eq!((groups, targets), (44, 1));
    assert_eq!(suite().cases.len(), 20);
    let (_cleanup, db) = dictionary("sources");
    assert_eq!(db.lookup("선").unwrap().len(), 5);
    let origins = arr(&m["dictionary_origin_policy"]["native_origins"]);
    for r in origins {
        let full = db.entry(r["id"].as_str().unwrap()).unwrap().unwrap();
        assert_eq!(serde_json::to_value(full.origins).unwrap(), r["origins"]);
    }
    assert_eq!(
        db.entry("krdict:87945").unwrap().unwrap().origins,
        ["虛風扇이"]
    );
    assert_eq!(db.entry("krdict:87944").unwrap().unwrap().origins, ["虛風"]);
    let marriage = db.entry("krdict:63243").unwrap().unwrap();
    assert!(marriage.origins.is_empty());
    assert_eq!(marriage.senses.len(), 2);
    assert!(marriage.senses[0].definition.contains("결혼"));
    assert!(marriage.senses[1].definition.contains("처음 모습을"));
    assert!(
        arr(&m["corpus_training_search"])
            .iter()
            .all(|r| r["matching_tokens"] == 0 && arr(&r["observations"]).is_empty())
    );
}
#[test]
fn fan_paths_preserve_order_outer_ownership_and_finite_boundaries() {
    let s = suite();
    let report = validity::evaluate(&s).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (17, 3));
    let engine = Lemmatizer::new();
    for c in &s.cases {
        let nfc = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            nfc,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        for p in &nfc.analyses {
            assert!(p.breakdown().is_some(), "{} {p:?}", c.surface);
            assert!(p.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    use klem::breakdown::Component::{Lemma as L, Morpheme as M};
    let a = engine.analyze_word("허풍선이들이었다").unwrap();
    let p = a.analyses.iter().find(|p| fan(p)).unwrap();
    assert_eq!(
        p.breakdown().unwrap(),
        [L(0), L(1), M(0), M(1), L(2), M(2), M(3)]
    );
    let a = engine.analyze_word("허풍선이들쯤에는").unwrap();
    let p = a.analyses.iter().find(|p| fan(p)).unwrap();
    assert_eq!(
        p.breakdown().unwrap(),
        [L(0), L(1), M(0), M(1), M(2), M(3), M(4)]
    );
    assert!(
        a.analyses
            .iter()
            .any(|p| p.lemmas.len() == 1 && p.lemmas[0].text == "허풍선")
    );
    assert!(
        a.analyses
            .iter()
            .any(|p| p.lemmas.len() == 1 && p.lemmas[0].text == "허풍선이")
    );
    for word in ["허풍선", "허풍선았이", "풍선이", "허풍줄이", "허풍선이는다"]
    {
        assert!(
            !engine.analyze_word(word).unwrap().analyses.iter().any(fan),
            "{word}"
        );
    }
    for edit in 0..5 {
        let mut wrong = p.clone();
        match edit {
            0 => wrong.lemmas[0].text = "풍선".into(),
            1 => wrong.lemmas[1].kind = klem::LemmaKind::Nominal,
            2 => wrong.rules.push("derivation.nominal.compound".into()),
            3 => wrong.rules.retain(|r| r != "suffix.nominal.i"),
            _ => wrong.morphemes[0].form = "히".into(),
        }
        assert!(wrong.breakdown().is_none(), "{edit}");
    }
}
#[test]
fn fan_origin_conflicts_are_per_entry_per_root_and_cache_independent() {
    let (_cleanup, db) = dictionary("origins");
    let engine = Lemmatizer::new();
    let a = engine.analyze_word("허풍선이들이었다").unwrap();
    let index = a.analyses.iter().position(fan).unwrap();
    let p = &a.analyses[index];
    let mut snapshots = Vec::new();
    for budget in [0, 256, 1024 * 1024] {
        let mut session = DictionarySession::new(&db, budget);
        let annotated = session.annotate(&a).unwrap();
        assert_eq!(annotated, session.annotate(&a).unwrap());
        assert!(session.cache_bytes() <= budget);
        let r = &annotated.readings[index];
        assert_eq!(r.lemmas.len(), 3);
        assert_eq!(r.lemmas[1].entries.len(), 5);
        assert!(r.lemmas[1].entries.iter().all(|e| {
            e.status == Compatibility::Incompatible
                && e.conflicts.iter().any(|c| {
                    c.rule == AttachmentRule::DerivationalRoot && c.morpheme_index.is_none()
                })
        }));
        assert!(r.lemmas[2].entries.iter().all(|e| {
            e.conflicts
                .iter()
                .all(|c| c.rule != AttachmentRule::DerivationalRoot)
        }));
        for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut v = a.clone();
            let mut d = annotated.clone();
            d.filter(&mut v, filter);
            assert_eq!(
                v.analyses.iter().any(fan),
                filter == DictionaryFilter::Headword
            );
            assert!(v.analyses.iter().any(|a| a.lemmas[0].text == "허풍선이"));
        }
        let ordinary = session
            .annotate(&engine.analyze_word("선을").unwrap())
            .unwrap();
        assert!(
            ordinary
                .lemmas
                .iter()
                .flat_map(|l| &l.entries)
                .all(|e| e.origins.is_none())
        );
        assert!(
            ordinary
                .readings
                .iter()
                .flat_map(|r| &r.lemmas)
                .flat_map(|l| &l.entries)
                .all(|e| e
                    .conflicts
                    .iter()
                    .all(|c| c.rule != AttachmentRule::DerivationalRoot))
        );
        snapshots.push(annotated);
    }
    assert!(snapshots.windows(2).all(|w| w[0] == w[1]));
    let annotated = &snapshots[0];
    let mut old = serde_json::to_value(annotated).unwrap();
    for l in old["lemmas"].as_array_mut().unwrap() {
        for e in l["entries"].as_array_mut().unwrap() {
            e.as_object_mut().unwrap().remove("origins");
        }
    }
    let mut old: klem::dictionary::Annotation = serde_json::from_value(old).unwrap();
    // Unknown evidence in older annotations survives; the positively reviewed
    // matchmaking entry remains a conflict by its native lexical identity.
    let r = old.assess(p);
    assert_eq!(r.status, Compatibility::Unknown);
    assert_eq!(
        r.lemmas[1]
            .entries
            .iter()
            .filter(|e| e.status == Compatibility::Unknown)
            .count(),
        4
    );
    let root = old
        .lemmas
        .iter_mut()
        .find(|l| l.lemma == p.lemmas[1])
        .unwrap();
    for e in &mut root.entries {
        e.origins = Some(vec![]);
    }
    assert_eq!(old.assess(p).status, Compatibility::Unknown);
    let root = old
        .lemmas
        .iter_mut()
        .find(|l| l.lemma == p.lemmas[1])
        .unwrap();
    let mut mock = root.entries[0].clone();
    mock.entry.id = "mock:fan".into();
    mock.origins = Some(vec!["扇".into()]);
    root.entries.push(mock);
    let r = old.assess(p);
    assert_eq!(
        r.lemmas[1].entries.last().unwrap().status,
        Compatibility::Unknown
    );
    assert!(r.lemmas[1].entries.last().unwrap().conflicts.is_empty());
}
#[test]
fn fan_cli_word_text_and_filters_match_library_annotations() {
    let (cleanup, db) = dictionary("cli");
    let engine = Lemmatizer::new();
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
        let mut dictionary = DictionarySession::new(&db, 4096);
        let mut expected = Vec::new();
        for c in &cases {
            let mut a = engine.analyze_word(&c.surface).unwrap();
            let mut annotation = dictionary.annotate(&a).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut a, filter);
            }
            for j in &c.judgments {
                assert_eq!(
                    a.analyses.iter().any(|a| matches(a, j)),
                    matches!(j.verdict, validity::Verdict::Required)
                        && filter != Some(DictionaryFilter::Compatible),
                    "{} {flag:?}",
                    c.id
                );
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
    }
}
#[test]
fn fan_spacing_keeps_whole_noun_roles_and_does_not_borrow_conflicting_roots() {
    let (_cleanup, db) = dictionary("spacing");
    let mut session = klem::Session::new(Lemmatizer::new().into(), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    for tail in ["먹는다", "허풍선이"] {
        let surface = format!("허풍선이를{tail}");
        let wanted = format!("허풍선이를 {tail}");
        let r = klem::spacing::suggest(
            &mut session,
            &mut dictionary,
            &surface,
            0,
            Default::default(),
        )
        .unwrap();
        assert_eq!(
            r.alternatives.iter().any(|a| a.spaced == wanted),
            tail == "먹는다"
        );
        if tail == "먹는다" {
            let a = r.alternatives.iter().find(|a| a.spaced == wanted).unwrap();
            assert!(
                a.records[0]
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .iter()
                    .all(|p| !fan(p))
            );
            assert!(
                a.records
                    .iter()
                    .all(|r| r.breakdowns.iter().all(Option::is_some))
            );
        }
    }
}
