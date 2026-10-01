//! Finite opaque roots retain lexical adverbs and separate lookup hypotheses.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, EntrySummary, SqliteDictionary,
    import_krdict, pos_compatibility,
};
use klem::{Analysis, LemmaKind, Lemmatizer};
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
    s.cases.retain(|c| c.id.starts_with("opaque-"));
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
fn matched(a: &Analysis, j: &validity::Judgment) -> bool {
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
fn opaque_adverbs_keep_complete_native_entries_and_all_original_groups() {
    let m: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/opaque-adverb-sources.json")).unwrap();
    let f: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-opaque-adverbs.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 4);
    let groups = arr(&m["source_groups"]);
    assert_eq!(groups.len(), 84);
    let cases = suite();
    let mut seen = BTreeSet::new();
    let mut total_groups = 0;
    for (id, head, pos, sense_count) in [
        ("26902", "천천히", "부사", 2),
        ("60522", "분연히", "부사", 1),
        ("60708", "분연히", "부사", 1),
        ("88504", "-히", "접사", 1),
    ] {
        let e = entries.iter().find(|e| e["val"] == id).unwrap();
        assert_eq!(feature(&e["Lemma"], "writtenForm"), Some(head));
        assert_eq!(feature(e, "partOfSpeech"), Some(pos));
        let senses = arr(&e["Sense"]);
        assert_eq!(senses.len(), sense_count);
        for s in senses {
            for (index, native) in arr(&s["SenseExample"]).iter().enumerate() {
                total_groups += 1;
                let g = groups
                    .iter()
                    .find(|g| {
                        g["entry_id"] == format!("krdict:{id}")
                            && g["sense_id"] == s["val"]
                            && g["example_group"] == index + 1
                    })
                    .unwrap();
                assert_eq!(&g["native_group"], *native);
                let examples: Vec<_> = arr(&native["feat"])
                    .into_iter()
                    .filter(|f| f["att"] == "example")
                    .map(|f| f["val"].as_str().unwrap())
                    .collect();
                assert_eq!(serde_json::to_value(&examples).unwrap(), g["examples"]);
                let targets = arr(&g["targets"]);
                assert_eq!(
                    examples
                        .iter()
                        .flat_map(|s| s.split_whitespace())
                        .filter(|w| matches!(
                            w.trim_end_matches(['.', '?', '!', ',']),
                            "천천히" | "분연히"
                        ))
                        .count(),
                    targets.len()
                );
                for t in targets {
                    let word = examples[t["turn"].as_u64().unwrap() as usize]
                        .split_whitespace()
                        .nth(t["token"].as_u64().unwrap() as usize)
                        .unwrap()
                        .trim_end_matches(['.', '?', '!', ',']);
                    assert_eq!(word, t["surface"]);
                    let ident = t["case_id"].as_str().unwrap();
                    assert!(seen.insert(ident));
                    let c = cases.cases.iter().find(|c| c.id == ident).unwrap();
                    assert_eq!(c.surface, word);
                    assert_eq!(c.judgments.len(), 1);
                    assert_eq!(c.judgments[0].source, format!("opaque-krdict-{id}"));
                    assert_eq!(c.judgments[0].lemmas, [t["root"].as_str().unwrap()]);
                    assert_eq!(
                        c.judgments[0].lemma_kinds.as_ref().unwrap(),
                        &[LemmaKind::Root]
                    );
                }
            }
        }
    }
    assert_eq!(total_groups, groups.len());
    assert_eq!(seen.len(), 40);
    assert_eq!(m["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn opaque_adverbs_preserve_roles_spelling_boundaries_and_particle_order() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (61, 2));
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
            if p.lemmas[0].kind == LemmaKind::Root {
                assert!(p.rules.iter().any(|r| r == "derivation.adverbial.opaque"));
                assert_eq!(p.morphemes[0].form, "히");
                assert_eq!(
                    p.breakdown().unwrap(),
                    std::iter::once(klem::breakdown::Component::Lemma(0))
                        .chain((0..p.morphemes.len()).map(klem::breakdown::Component::Morpheme))
                        .collect::<Vec<_>>()
                );
                assert!(
                    p.morphemes[1..]
                        .iter()
                        .all(|m| m.kind == klem::MorphemeKind::Particle)
                );
            }
        }
    }
    for word in ["천천히히", "분연히히", "쀍히", "천천히요요"] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|p| p.lemmas[0].kind == LemmaKind::Root),
            "{word}"
        );
    }
    let mut root = engine
        .analyze_word("천천히")
        .unwrap()
        .analyses
        .into_iter()
        .find(|p| p.lemmas[0].kind == LemmaKind::Root)
        .unwrap();
    let serialized = serde_json::to_value(&root).unwrap();
    assert_eq!(serialized["lemmas"][0]["kind"], "root");
    assert_eq!(
        serde_json::from_value::<Analysis>(serialized).unwrap(),
        root
    );
    root.morphemes.clear();
    assert_eq!(root.breakdown(), None);
    root.morphemes.push(klem::Morpheme {
        form: "다".into(),
        kind: klem::MorphemeKind::Ending,
    });
    assert_eq!(root.breakdown(), None);
}
#[test]
fn opaque_adverbs_keep_corpus_lexical_gold_without_changing_its_segmentation() {
    let engine = Lemmatizer::new();
    for source in [
        include_str!("fixtures/kaist-opaque-adverbs.conllu"),
        include_str!("fixtures/gsd-opaque-adverbs.conllu"),
    ] {
        assert!(source.contains("# sent_id = ") && source.contains("# text = "));
        let row = source
            .lines()
            .filter(|l| !l.starts_with('#'))
            .find(|l| l.split('\t').nth(1) == Some("천천히"))
            .unwrap();
        let fields: Vec<_> = row.split('\t').collect();
        assert_eq!((fields[2], fields[3]), ("천천히", "ADV"));
        assert_eq!(fields[4].to_lowercase(), "mag");
        let result = engine.analyze_word(fields[1]).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.unchanged && a.lemmas[0].text == fields[2])
        );
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.lemmas[0].kind == LemmaKind::Root && a.lemmas[0].text == "천천")
        );
    }
}
#[test]
fn opaque_adverbs_keep_dictionary_misses_homonyms_and_cli_exports_distinct() {
    let path = std::env::temp_dir().join(format!("klem-opaque-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-opaque-adverbs.json")],
        &path,
        "opaque-adverbs",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    assert_eq!(db.entry("krdict:26902").unwrap().unwrap().senses.len(), 2);
    for id in ["krdict:60522", "krdict:60708"] {
        let e = db.entry(id).unwrap().unwrap();
        assert_eq!(e.summary.headword, "분연히");
        assert_eq!(e.senses.len(), 1);
    }
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    for (word, root) in [("천천히", "천천"), ("분연히", "분연")] {
        let a = engine.analyze_word(word).unwrap();
        let p = a
            .analyses
            .iter()
            .find(|p| p.lemmas[0].kind == LemmaKind::Root)
            .unwrap();
        for pos in ["명사", "부사", "형용사", "품사 없음"] {
            let e = EntrySummary {
                id: "synthetic:root-homonym".into(),
                headword: root.into(),
                homonym: "0".into(),
                pos: pos.into(),
            };
            assert_eq!(pos_compatibility(&p.lemmas[0], &e), Compatibility::Unknown);
        }
    }
    let cases = suite().cases;
    let words: Vec<_> = cases.iter().map(|c| c.surface.as_str()).collect();
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
            let mut an = d.annotate(&a).unwrap();
            if let Some(f) = filter {
                an.filter(&mut a, f);
            }
            if filter.is_none() {
                for j in &c.judgments {
                    if matches!(j.verdict, validity::Verdict::Required) {
                        assert!(a.analyses.iter().any(|p| matched(p, j)));
                    }
                }
            } else {
                assert!(!a.analyses.iter().any(|p| {
                    p.lemmas
                        .iter()
                        .any(|l| l.kind == LemmaKind::Root || l.text == "천천하다")
                }));
            }
            if c.surface == "분연히" {
                let entries = &an
                    .lemmas
                    .iter()
                    .find(|l| l.lemma.text == "분연히")
                    .unwrap()
                    .entries;
                assert_eq!(
                    entries
                        .iter()
                        .map(|e| e.entry.id.as_str())
                        .collect::<BTreeSet<_>>(),
                    BTreeSet::from(["krdict:60522", "krdict:60708"])
                );
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"]).arg(&path);
            if let Some(f) = flag {
                cmd.arg(f);
            }
            let output = cmd.output().unwrap();
            assert!(output.status.success());
            let mut value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            let annotation = value.as_object_mut().unwrap().remove("dictionary").unwrap();
            assert_eq!(annotation, serde_json::to_value(&an).unwrap());
            assert_eq!(value, serde_json::to_value(&a).unwrap());
            expected.push((value, annotation));
        }
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
            .write_all(words.join(" ").as_bytes())
            .unwrap();
        let output = child.wait_with_output().unwrap();
        assert!(output.status.success());
        let records: Vec<serde_json::Value> = String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|l| serde_json::from_str(l).unwrap())
            .filter(|r: &serde_json::Value| !r["analysis"].is_null())
            .collect();
        assert_eq!(records.len(), expected.len());
        for ((r, (a, an)), word) in records.iter().zip(expected).zip(&words) {
            assert_eq!(r["surface"], *word);
            assert_eq!(r["analysis"], a);
            assert_eq!(r["dictionary"], an);
        }
        assert!(d.cache_bytes() <= 4096);
    }
}
