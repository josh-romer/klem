//! COV-022h: sound/manner bases retain lookup uncertainty and noun ownership.
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
    s.cases.retain(|c| c.id.starts_with("noun-sound-"));
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
fn sound_base_source_retains_every_native_sense_group_and_target() {
    let m: Value = serde_json::from_str(include_str!("fixtures/noun-sound-sources.json")).unwrap();
    let f: Value = serde_json::from_str(include_str!("fixtures/krdict-noun-sound.json")).unwrap();
    let entries = arr(&f["LexicalResource"]["Lexicon"]["LexicalEntry"]);
    assert_eq!(entries.len(), 32);
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
    assert_eq!(seen.len(), 9);
    assert_eq!(m["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn sound_base_paths_keep_homonym_identity_boundaries_and_order() {
    let report = validity::evaluate(&suite()).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (153, 27));
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
        "깜빡이님",
        "꿀꿀이적",
        "짝짝이답다",
        "뺑뺑이이",
        "쀍이",
        "오뚜기",
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
    for (word, kind) in [
        ("깜빡이", klem::LemmaKind::Adverbial),
        ("꿀꿀이들쯤에는", klem::LemmaKind::Adverbial),
        ("뺑뺑이들이었다", klem::LemmaKind::Root),
        ("짝짝이예요", klem::LemmaKind::Adverbial),
    ] {
        let a = engine.analyze_word(word).unwrap();
        let p = a
            .analyses
            .iter()
            .find(|p| p.rules.iter().any(|r| r == "suffix.nominal.i"))
            .unwrap();
        assert_eq!(p.lemmas[0].kind, kind);
        assert!(p.rules.iter().all(|r| r != "derivation.nominal.compound"));
    }
    let ambiguous = engine.analyze_word("오뚝이").unwrap();
    assert!(
        ambiguous
            .analyses
            .iter()
            .any(|a| a.rules.iter().any(|r| r == "suffix.nominal.i"))
    );
    assert!(
        ambiguous
            .analyses
            .iter()
            .any(|a| a.rules.iter().any(|r| r == "suffix.adverbial.i"))
    );
}

#[test]
fn sound_base_suffix_boundary_rejects_external_prefinals_and_recursive_suffixes() {
    for word in [
        "깜빡이",
        "깡깡이",
        "깽깽이",
        "꿀꿀이",
        "덜렁이",
        "딸랑이",
        "뺑뺑이",
        "오뚝이",
        "짝짝이",
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
fn sound_base_gold_dictionary_filters_and_cli_exports_preserve_lexical_alternatives() {
    let path = std::env::temp_dir().join(format!("klem-noun-sound-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-sound.json")],
        &path,
        "noun-sound",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    assert_eq!(db.entry("krdict:88924").unwrap().unwrap().senses.len(), 3);
    assert!(db.lookup("깜빡이").unwrap().iter().any(|e| e.pos == "명사"));
    assert!(db.lookup("짝짝").unwrap().iter().all(|e| e.pos == "부사"));
    assert_eq!(db.lookup("짝짝").unwrap().len(), 4);
    assert_eq!(db.lookup("덜렁").unwrap().len(), 2);
    assert_eq!(db.lookup("딸랑").unwrap().len(), 2);
    assert!(db.lookup("뺑뺑").unwrap().is_empty());
    assert!(db.lookup("깡깡이").unwrap().is_empty());
    assert!(db.lookup("깽깽이").unwrap().is_empty());
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
                        && !(filter.is_some()
                            && j.lemma_kinds.as_ref().unwrap()[0] == klem::LemmaKind::Root),
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
fn sound_base_spacing_keeps_case_roles_without_treating_nouns_as_predicates() {
    let path =
        std::env::temp_dir().join(format!("klem-noun-sound-spacing-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-noun-sound.json")],
        &path,
        "noun-sound-spacing",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut session = klem::Session::new(Lemmatizer::new().into(), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    for noun in [
        "깜빡이",
        "깡깡이",
        "깽깽이",
        "꿀꿀이",
        "덜렁이",
        "딸랑이",
        "오뚝이",
        "짝짝이",
    ] {
        let surface = format!("{noun}를꿀꿀이");
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
                .all(|a| a.spaced != format!("{noun}를 꿀꿀이"))
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
