//! COV-022i: root boundaries and related predicate lookups keep distinct ownership.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use serde_json::{Value, json};
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
    s.cases.retain(|c| c.id.starts_with("noun-root-"));
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
fn root_base_source_retains_every_native_sense_group_and_target() {
    let m: Value = serde_json::from_str(include_str!("fixtures/noun-root-sources.json")).unwrap();
    let f: Value = serde_json::from_str(include_str!("fixtures/krdict-noun-root.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 29);
    let e = entries.iter().find(|e| e["val"] == "88924").unwrap();
    assert_eq!(feature(e, "partOfSpeech"), Some("접사"));
    assert_eq!(feature(&e["Lemma"], "writtenForm"), Some("-이"));
    assert_eq!(arr(&e["Sense"]).len(), 3);
    let cases = suite();
    let mut seen = BTreeSet::new();
    let mut count = 0;
    for s in arr(&e["Sense"]) {
        for (i, g) in arr(&s["SenseExample"]).iter().enumerate() {
            count += 1;
            let recorded = m["source_groups"]
                .as_array()
                .unwrap()
                .iter()
                .find(|x| x["sense_id"] == s["val"] && x["example_group"] == i + 1)
                .unwrap();
            assert_eq!(&recorded["native_group"], *g);
            let text: Vec<_> = arr(&g["feat"])
                .iter()
                .filter(|x| x["att"] == "example")
                .map(|x| x["val"].as_str().unwrap())
                .collect();
            assert_eq!(json!(text), recorded["examples"]);
            for t in arr(&recorded["targets"]) {
                let word = text[0];
                assert_eq!(word, t["surface"]);
                let id = t["case_id"].as_str().unwrap();
                assert!(seen.insert(id));
                let c = cases.cases.iter().find(|c| c.id == id).unwrap();
                assert_eq!(c.surface, word);
                assert_eq!(json!(c.judgments[0].lemmas), json!([t["base"]]));
                assert!(
                    c.judgments[0]
                        .required_rules
                        .as_ref()
                        .unwrap()
                        .iter()
                        .any(|r| r == "suffix.nominal.i")
                );
            }
        }
    }
    assert_eq!(count, 44);
    assert_eq!(seen.len(), 7);
    assert_eq!(m["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn root_base_paths_keep_homonym_identity_boundaries_and_order() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (226, 39));
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
                assert!(!p.rules.iter().any(|r| r == "suffix.adverbial.i"));
                assert_eq!(p.morphemes[0].form, "이");
                let order = p.breakdown().unwrap();
                assert_eq!(order[0], klem::breakdown::Component::Lemma(0));
                let compound = p.rules.iter().any(|r| r == "derivation.nominal.compound");
                if compound {
                    assert_eq!(order[1], klem::breakdown::Component::Lemma(1));
                }
                assert_eq!(
                    order[usize::from(compound) + 1],
                    klem::breakdown::Component::Morpheme(0)
                );
            }
        }
    }
    for word in [
        "끈끈이님",
        "누렁이적",
        "멍청이답다",
        "미치광이이",
        "쀍이",
        "홀쭈기",
        "누렁하이",
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "suffix.nominal.i")),
            "{word}"
        );
    }
    for (word, expected) in [
        ("끈끈이", 2),
        ("누렁이", 1),
        ("뚱뚱이", 2),
        ("멍청이", 2),
        ("미치광이", 1),
        ("합죽이", 3),
        ("홀쭉이", 2),
    ] {
        let a = engine.analyze_word(word).unwrap();
        let paths: Vec<_> = a
            .analyses
            .iter()
            .filter(|p| p.rules.iter().any(|r| r == "suffix.nominal.i"))
            .collect();
        assert_eq!(paths.len(), expected, "{word}");
        assert!(
            paths
                .iter()
                .any(|a| a.lemmas[0].kind == klem::LemmaKind::Root)
        );
        for a in paths {
            assert_eq!(
                a.lemmas[0].kind == klem::LemmaKind::Predicate,
                a.rules
                    .iter()
                    .any(|r| r == "derivation.nominal.related_root")
            );
        }
    }
    for word in ["미치광이풀", "미치광이풀로", "미치광이풀을"] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|a| !a.rules.iter().any(|r| r == "suffix.nominal.i"))
        );
    }
    for word in ["누렁이", "미치광이"] {
        let a = engine.analyze_word(word).unwrap();
        assert!(
            a.analyses
                .iter()
                .filter(|a| a.rules.iter().any(|r| r == "suffix.nominal.i"))
                .all(|a| a
                    .lemmas
                    .iter()
                    .all(|l| !["누렁하다", "누렇다", "미치다", "광"].contains(&l.text.as_str())))
        );
    }
}

#[test]
fn root_base_suffix_boundary_rejects_external_prefinals_and_recursive_suffixes() {
    for word in [
        "끈끈이",
        "누렁이",
        "뚱뚱이",
        "멍청이",
        "미치광이",
        "합죽이",
        "홀쭉이",
    ] {
        let a = Lemmatizer::new()
            .analyze_word(word)
            .unwrap()
            .analyses
            .into_iter()
            .find(|a| a.rules.iter().any(|r| r == "suffix.nominal.i"))
            .unwrap();
        for morphemes in [
            vec![],
            vec![klem::Morpheme {
                form: "이".into(),
                kind: klem::MorphemeKind::Particle,
            }],
            vec![
                klem::Morpheme {
                    form: "었".into(),
                    kind: klem::MorphemeKind::Prefinal,
                },
                klem::Morpheme {
                    form: "이".into(),
                    kind: klem::MorphemeKind::Suffix,
                },
            ],
            vec![
                klem::Morpheme {
                    form: "이".into(),
                    kind: klem::MorphemeKind::Suffix,
                },
                klem::Morpheme {
                    form: "이".into(),
                    kind: klem::MorphemeKind::Suffix,
                },
            ],
        ] {
            let mut invalid = a.clone();
            invalid.morphemes = morphemes;
            assert!(invalid.breakdown().is_none());
        }
        let legal = Lemmatizer::new()
            .analyze_word(&format!("{word}들쯤에는"))
            .unwrap();
        let p = legal
            .analyses
            .iter()
            .find(|a| a.rules.iter().any(|r| r == "suffix.nominal.i"))
            .unwrap();
        assert_eq!(
            p.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .collect::<Vec<_>>(),
            ["이", "들", "쯤", "에", "는"]
        );
        assert_eq!(
            p.breakdown().unwrap(),
            vec![
                klem::breakdown::Component::Lemma(0),
                klem::breakdown::Component::Morpheme(0),
                klem::breakdown::Component::Morpheme(1),
                klem::breakdown::Component::Morpheme(2),
                klem::breakdown::Component::Morpheme(3),
                klem::breakdown::Component::Morpheme(4)
            ]
        );
    }
}
#[test]
fn root_base_gold_dictionary_filters_and_cli_exports_preserve_lexical_alternatives() {
    let path = std::env::temp_dir().join(format!("klem-noun-root-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-root.json")],
        &path,
        "noun-root",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    assert_eq!(db.entry("krdict:88924").unwrap().unwrap().senses.len(), 3);
    assert!(
        db.lookup("홀쭉하다")
            .unwrap()
            .iter()
            .any(|e| e.pos == "형용사")
    );
    assert!(
        db.lookup("합죽하다")
            .unwrap()
            .iter()
            .any(|e| e.pos == "형용사")
    );
    assert!(db.lookup("합죽거리다").unwrap().is_empty());
    assert!(db.lookup("누렁").unwrap().is_empty());
    assert!(db.lookup("누렁하다").unwrap().is_empty());
    assert_eq!(db.lookup("미치다").unwrap().len(), 2);
    assert_eq!(db.lookup("광").unwrap().len(), 2);
    let manifest: Value =
        serde_json::from_str(include_str!("fixtures/noun-root-sources.json")).unwrap();
    let gold = include_str!("fixtures/kaist-noun-root.conllu");
    assert_eq!(gold.split("\n\n").filter(|b| !b.is_empty()).count(), 5);
    for item in arr(&manifest["corpus"]) {
        let block = gold
            .split("\n\n")
            .find(|b| {
                b.lines()
                    .any(|l| l == format!("# sent_id = {}", item["sent_id"].as_str().unwrap()))
            })
            .unwrap();
        let row = block
            .lines()
            .find(|l| l.split('\t').next() == item["token_id"].as_str())
            .unwrap();
        let fields: Vec<_> = row.split('\t').collect();
        assert_eq!(fields[1], item["surface"]);
        assert_eq!(fields[2], item["lemma"]);
        assert_eq!(fields[3], item["upos"]);
        assert_eq!(fields[4], item["xpos"]);
    }
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
                let found = a.analyses.iter().any(|a| matches(a, j));
                assert_eq!(
                    found,
                    matches!(j.verdict, validity::Verdict::Required)
                        && (filter.is_none()
                            || j.lemmas.iter().all(|l| !db.lookup(l).unwrap().is_empty())),
                    "{} {flag:?}",
                    c.id
                );
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"]).arg(&path);
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
        cmd.args(["text", "-", "--dictionary"]).arg(&path);
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
fn root_base_spacing_keeps_case_roles_without_treating_nouns_as_predicates() {
    let path =
        std::env::temp_dir().join(format!("klem-noun-root-spacing-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-root.json")],
        &path,
        "noun-root-spacing",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut session = klem::Session::new(Lemmatizer::new().into(), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    for noun in ["끈끈이", "뚱뚱이", "멍청이", "합죽이", "홀쭉이"] {
        let surface = format!("{noun}를미치광이");
        let result = klem::spacing::suggest(
            &mut session,
            &mut dictionary,
            &surface,
            0,
            Default::default(),
        )
        .unwrap();
        assert!(
            result
                .alternatives
                .iter()
                .all(|a| a.spaced != format!("{noun}를 미치광이"))
        );
        let surface = format!("{noun}를먹는다");
        let result = klem::spacing::suggest(
            &mut session,
            &mut dictionary,
            &surface,
            0,
            Default::default(),
        )
        .unwrap();
        let phrase = result
            .alternatives
            .iter()
            .find(|a| a.spaced == format!("{noun}를 먹는다"))
            .unwrap();
        assert!(
            phrase.records[0]
                .record
                .analysis
                .as_ref()
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "suffix.nominal.i"))
        );
        assert!(
            phrase.records[1]
                .record
                .analysis
                .as_ref()
                .unwrap()
                .analyses
                .iter()
                .all(|a| !a.rules.iter().any(|r| r == "suffix.nominal.i"))
        );
        assert!(
            phrase
                .records
                .iter()
                .all(|r| r.breakdowns.iter().all(Option::is_some))
        );
    }
    assert!(dictionary.cache_bytes() <= 4096);
}

#[test]
fn related_root_provenance_rejects_unregistered_or_misowned_external_shapes() {
    let a = Lemmatizer::new().analyze_word("합죽이").unwrap();
    for legal in a.analyses.iter().filter(|a| {
        a.rules
            .iter()
            .any(|r| r == "derivation.nominal.related_root")
    }) {
        assert_eq!(legal.lemmas[0].kind, klem::LemmaKind::Predicate);
        assert!(legal.breakdown().is_some());
        let mut invalid = legal.clone();
        invalid.lemmas[0].text = "누렁하다".into();
        assert!(invalid.breakdown().is_none());
        let mut invalid = legal.clone();
        invalid.lemmas[0].kind = klem::LemmaKind::Root;
        assert!(invalid.breakdown().is_none());
        let mut invalid = legal.clone();
        invalid.rules.retain(|r| r != "suffix.nominal.i");
        assert!(invalid.breakdown().is_none());
        let mut invalid = legal.clone();
        invalid.rules.push("derivation.nominal.compound".into());
        assert!(invalid.breakdown().is_none());
    }
}
