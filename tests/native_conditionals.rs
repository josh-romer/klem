//! Complete native intention/concessive entries supplement the inventory audit.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use std::{
    collections::BTreeSet,
    fs,
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("native-conditionals-"));
    s
}
fn arr(v: &serde_json::Value) -> Vec<&serde_json::Value> {
    if let Some(a) = v.as_array() {
        a.iter().collect()
    } else if v.is_object() {
        vec![v]
    } else {
        vec![]
    }
}
fn feature<'a>(v: &'a serde_json::Value, name: &str) -> Option<&'a str> {
    arr(&v["feat"])
        .into_iter()
        .find(|f| f["att"] == name)
        .and_then(|f| f["val"].as_str())
}
fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
        && a.lemmas
            .iter()
            .map(|l| l.kind)
            .eq(j.lemma_kinds.as_ref().unwrap().iter().copied())
        && a.morphemes
            .iter()
            .map(|m| &m.form)
            .eq(j.morphemes.as_ref().unwrap().iter())
        && a.morphemes
            .iter()
            .map(|m| m.kind)
            .eq(j.morpheme_kinds.as_ref().unwrap().iter().copied())
}
#[test]
fn native_conditionals_preserve_all_source_groups_and_exact_turn_tokens() {
    let manifest: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/native-conditionals-sources.json")).unwrap();
    let fixture: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-native-conditionals.json")).unwrap();
    let entries = arr(&fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    let groups = arr(&manifest["source_groups"]);
    assert_eq!(groups.len(), 14);
    let cases = suite();
    let mut seen = BTreeSet::new();
    for (id, head, count) in [
        ("80338", "-자면", 4),
        ("80167", "-나마", 6),
        ("80164", "-으나마", 4),
    ] {
        let e = entries.iter().find(|e| e["val"] == id).unwrap();
        assert_eq!(feature(e, "partOfSpeech"), Some("어미"));
        assert_eq!(feature(&e["Lemma"], "writtenForm"), Some(head));
        let senses = arr(&e["Sense"]);
        assert_eq!(senses.len(), 1);
        let native = arr(&senses[0]["SenseExample"]);
        assert_eq!(native.len(), count);
        let linked: Vec<_> = groups
            .iter()
            .filter(|g| g["entry_id"] == format!("krdict:{id}"))
            .collect();
        assert_eq!(linked.len(), count);
        for (index, group) in native.iter().enumerate() {
            let g = linked
                .iter()
                .find(|g| g["example_group"] == index + 1)
                .unwrap();
            assert_eq!(g["sense_id"], senses[0]["val"]);
            assert_eq!(&g["native_group"], *group);
            let examples: Vec<_> = arr(&group["feat"])
                .into_iter()
                .filter(|f| f["att"] == "example")
                .map(|f| f["val"].as_str().unwrap())
                .collect();
            assert_eq!(serde_json::to_value(&examples).unwrap(), g["examples"]);
            let targets = arr(&g["targets"]);
            assert_eq!(targets.len(), 1);
            let t = targets[0];
            let word = examples[t["turn"].as_u64().unwrap() as usize]
                .split_whitespace()
                .nth(t["token"].as_u64().unwrap() as usize)
                .unwrap()
                .trim_end_matches(['.', '?', '!', ',']);
            assert_eq!(word, t["surface"]);
            let case_id = t["case_id"].as_str().unwrap();
            assert!(seen.insert(case_id));
            let c = cases.cases.iter().find(|c| c.id == case_id).unwrap();
            assert_eq!(c.surface, word);
            assert_eq!(c.judgments.len(), 1);
            let j = &c.judgments[0];
            assert_eq!(j.source, format!("native-conditionals-{id}"));
            assert_eq!(serde_json::to_value(&j.lemmas).unwrap(), t["lemmas"]);
            assert_eq!(
                serde_json::to_value(&j.lemma_kinds).unwrap(),
                t["lemma_kinds"]
            );
            assert_eq!(serde_json::to_value(&j.morphemes).unwrap(), t["morphemes"]);
            assert_eq!(
                examples
                    .iter()
                    .flat_map(|s| s.split_whitespace())
                    .filter(|w| w
                        .trim_end_matches(['.', '?', '!', ','])
                        .ends_with(if id == "80338" { "자면" } else { "나마" }))
                    .count(),
                1
            );
        }
    }
    assert_eq!(seen.len(), cases.cases.len());
    assert_eq!(seen.len(), 14);
    assert_eq!(manifest["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn native_conditionals_preserve_normalization_lexical_homonyms_and_particle_alternatives() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (14, 0));
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
            assert!(p.breakdown().is_some());
            assert!(p.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    let a = engine.analyze_word("조금이나마").unwrap();
    for kind in [klem::LemmaKind::Nominal, klem::LemmaKind::Adverbial] {
        assert!(a.analyses.iter().any(|p| p.lemmas.len() == 1
            && p.lemmas[0].text == "조금"
            && p.lemmas[0].kind == kind
            && p.morphemes.len() == 1
            && p.morphemes[0].form == "이나마"
            && p.morphemes[0].kind == klem::MorphemeKind::Particle));
    }
}
#[test]
fn native_conditionals_dictionary_and_cli_exports_keep_roles_source_ids_and_order() {
    let path = std::env::temp_dir().join(format!(
        "klem-native-conditionals-{}.db",
        std::process::id()
    ));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-native-conditionals.json",
        )],
        &path,
        "native-conditionals",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    for (id, head) in [("80338", "-자면"), ("80167", "-나마"), ("80164", "-으나마")] {
        let e = db.entry(&format!("krdict:{id}")).unwrap().unwrap();
        assert_eq!(e.summary.headword, head);
        assert_eq!(e.summary.pos, "어미");
        assert_eq!(e.senses.len(), 1);
    }
    for (head, ids) in [
        ("늦다", ["krdict:61181", "krdict:64526"]),
        ("적다", ["krdict:71234", "krdict:62051"]),
    ] {
        let mut d = DictionarySession::new(&db, 4096);
        let entries = d.lookup(head).unwrap();
        for id in ids {
            assert!(entries.iter().any(|e| e.id == id));
        }
    }
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    for (flag, filter) in [
        (None, None),
        (Some("--dict-only"), Some(DictionaryFilter::Headword)),
        (
            Some("--dict-compatible"),
            Some(DictionaryFilter::Compatible),
        ),
    ] {
        let mut expected = vec![];
        let cases = suite().cases;
        for c in &cases {
            let mut a = engine.analyze_word(&c.surface).unwrap();
            let mut an = d.annotate(&a).unwrap();
            if let Some(f) = filter {
                an.filter(&mut a, f);
            }
            let p = a
                .analyses
                .iter()
                .find(|a| matches(a, &c.judgments[0]))
                .unwrap();
            let order = p.breakdown().unwrap();
            let mut wanted: Vec<_> = (0..p.lemmas.len())
                .map(klem::breakdown::Component::Lemma)
                .collect();
            wanted.extend((0..p.morphemes.len()).map(klem::breakdown::Component::Morpheme));
            assert_eq!(order, wanted);
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"]).arg(&path);
            if let Some(f) = flag {
                cmd.arg(f);
            }
            let output = cmd.output().unwrap();
            assert!(output.status.success());
            let mut value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                value.as_object_mut().unwrap().remove("dictionary").unwrap(),
                serde_json::to_value(&an).unwrap()
            );
            assert_eq!(value, serde_json::to_value(&a).unwrap());
            expected.push((value, serde_json::to_value(&an).unwrap()));
        }
        let text = cases
            .iter()
            .map(|c| c.surface.as_str())
            .collect::<Vec<_>>()
            .join(" ");
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
        cmd.args(["text", "-", "--dictionary"]).arg(&path);
        if let Some(f) = flag {
            cmd.arg(f);
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
        let records: Vec<serde_json::Value> = String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .filter(|r: &serde_json::Value| !r["analysis"].is_null())
            .collect();
        assert_eq!(records.len(), 14);
        for ((r, (a, d)), c) in records.iter().zip(expected).zip(cases) {
            assert_eq!(r["surface"], c.surface);
            assert_eq!(r["analysis"], a);
            assert_eq!(r["dictionary"], d);
        }
        assert!(d.cache_bytes() <= 4096);
    }
}
