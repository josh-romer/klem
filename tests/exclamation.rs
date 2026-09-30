//! COV-017bg: distinct ending bundles, immediate owners and preserved source spelling.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    AttachmentRule, Compatibility, DictionaryFilter, DictionarySession, SqliteDictionary,
    import_krdict,
};
use klem::{Analysis, Lemmatizer};
use std::{collections::BTreeSet, fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;
fn suite(file: &str) -> validity::Suite {
    let mut s: validity::Suite = serde_json::from_str(file).unwrap();
    s.cases.retain(|c| c.id.starts_with("exclamation-"));
    s
}
fn raw() -> validity::Suite {
    suite(include_str!("fixtures/validity.json"))
}
fn policy() -> validity::Suite {
    suite(include_str!("fixtures/dictionary-attachments.json"))
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let p =
            std::env::temp_dir().join(format!("klem-exclamation-{}-{name}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-exclamation.json")],
            &p,
            "exclamation-fixture",
        )
        .unwrap();
        Self(p)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(j.lemmas.iter())
        && j.lemma_kinds
            .as_ref()
            .is_none_or(|k| a.lemmas.iter().map(|l| l.kind).eq(k.iter().copied()))
        && j.morphemes
            .as_ref()
            .is_none_or(|f| a.morphemes.iter().map(|m| &m.form).eq(f.iter()))
        && j.morpheme_kinds
            .as_ref()
            .is_none_or(|k| a.morphemes.iter().map(|m| m.kind).eq(k.iter().copied()))
}
#[test]
fn exclamation_endings_preserve_allomorphs_prefinal_owners_and_lexical_alternatives() {
    let s = raw();
    let r = validity::evaluate(&s).unwrap();
    assert!(r.passed(), "{:?}", r.violations);
    assert_eq!((r.required_total, r.forbidden_total), (213, 63));
    let engine = Lemmatizer::new();
    for c in s.cases {
        let a = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            a,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(a.analyses.iter().any(|p| p.unchanged));
        for p in &a.analyses {
            assert!(p.breakdown().is_some(), "{}: {p:?}", c.id);
            assert!(p.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    for (surface, form) in [
        ("좋구만", "구먼"),
        ("먹는구만", "는구먼"),
        ("먹더구만", "더구먼"),
        ("의사로구만", "로구먼"),
    ] {
        let a = engine.analyze_word(surface).unwrap();
        let paths: Vec<_> = a
            .analyses
            .iter()
            .filter(|p| p.morphemes.iter().any(|m| m.form == form))
            .collect();
        assert!(!paths.is_empty());
        assert!(
            paths
                .iter()
                .all(|p| p.rules.iter().any(|r| r == "ending.exclamation_variant"))
        );
        assert_eq!(a.normalized, surface);
    }
    let a = engine.analyze_word("사는군").unwrap();
    for head in ["사다", "살다"] {
        assert!(a.analyses.iter().any(|p| p.lemmas.len() == 1
            && p.lemmas[0].text == head
            && p.morphemes.len() == 1
            && p.morphemes[0].form == "는군"));
    }
}
#[test]
fn exclamation_native_sources_preserve_every_group_and_unresolved_spelling() {
    let m: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/exclamation-sources.json")).unwrap();
    let n: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-exclamation.json")).unwrap();
    let es = n["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(es.len(), m["entry_ids"].as_array().unwrap().len());
    let groups = m["primary_groups"].as_array().unwrap();
    assert_eq!(groups.len(), 127);
    let mut seen = BTreeSet::new();
    for g in groups {
        let id = g["entry_id"].as_u64().unwrap().to_string();
        let sid = g["sense_id"].as_str().unwrap();
        let idx = g["example_group"].as_u64().unwrap() as usize;
        assert!(seen.insert((id.clone(), sid.to_owned(), idx)));
        let e = es.iter().find(|e| e["val"].as_str() == Some(&id)).unwrap();
        let s = e["Sense"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["val"].as_str() == Some(sid))
            .unwrap();
        assert_eq!(s["SenseExample"][idx - 1], g["native_group"]);
    }
    assert_eq!(m["primary_examples"].as_array().unwrap().len(), 127);
    let raw = raw();
    for p in m["primary_examples"].as_array().unwrap() {
        let c = raw
            .cases
            .iter()
            .find(|c| c.id == p["case_id"].as_str().unwrap())
            .unwrap();
        assert_eq!(c.surface, p["surface"].as_str().unwrap());
    }
    // Arrow entries have no example groups. Preserve each native identity,
    // including the exceptional headword without a leading hyphen.
    for redirect in m["redirects"].as_array().unwrap() {
        let id = redirect["entry_id"].as_u64().unwrap().to_string();
        let e = es.iter().find(|e| e["val"].as_str() == Some(&id)).unwrap();
        let feat = &e["Lemma"]["feat"];
        let head = if let Some(fs) = feat.as_array() {
            fs.iter().find(|f| f["att"] == "writtenForm").unwrap()
        } else {
            feat
        };
        assert_eq!(head["val"], redirect["native_headword"]);
        assert!(!groups.iter().any(|g| g["entry_id"] == redirect["entry_id"]));
    }
    let mut expected = BTreeSet::new();
    for e in es.iter().filter(|e| {
        m["primary_entry_ids"]
            .as_array()
            .unwrap()
            .iter()
            .chain(m["polite_entry_ids"].as_array().unwrap())
            .any(|id| id.as_u64().unwrap().to_string() == e["val"].as_str().unwrap())
    }) {
        for sense in e["Sense"].as_array().unwrap() {
            for (i, _) in sense["SenseExample"]
                .as_array()
                .into_iter()
                .flatten()
                .enumerate()
            {
                expected.insert((
                    e["val"].as_str().unwrap().to_owned(),
                    sense["val"].as_str().unwrap().to_owned(),
                    i + 1,
                ));
            }
        }
    }
    assert_eq!(seen, expected);
    for p in m["primary_examples"].as_array().unwrap() {
        let feats = p["native_group"]["feat"].as_array().unwrap();
        let text = feats
            .iter()
            .filter(|f| f["att"] == "example")
            .nth(p["turn"].as_u64().unwrap() as usize)
            .unwrap()["val"]
            .as_str()
            .unwrap();
        let tokens: Vec<_> = text
            .split(|c: char| !(('가'..='힣').contains(&c)))
            .filter(|s| !s.is_empty())
            .collect();
        assert_eq!(
            tokens[p["token"].as_u64().unwrap() as usize],
            p["surface"].as_str().unwrap()
        );
    }
    assert_eq!(m["redirects"][3]["native_headword"], "로구만");
    assert_eq!(m["source_disagreements"][0]["entry_id"], 76568);
    assert_eq!(m["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn exclamation_dictionary_checks_bare_classes_and_preserves_homonyms_and_prefinals() {
    let fixture = Fixture::new("policy");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    let s = policy();
    let r = validity::evaluate_with(&s, |w| {
        let mut a = engine.analyze_word(w).unwrap();
        let mut an = d.annotate(&a).unwrap();
        an.filter(&mut a, DictionaryFilter::Compatible);
        Ok(a)
    })
    .unwrap();
    assert!(r.passed(), "{:?}", r.violations);
    assert_eq!((r.required_total, r.forbidden_total), (10, 9));
    let r = validity::evaluate_with(&s, |w| {
        let mut a = engine.analyze_word(w).unwrap();
        let mut an = d.annotate(&a).unwrap();
        an.filter(&mut a, DictionaryFilter::Headword);
        Ok(a)
    })
    .unwrap();
    assert_eq!((r.required_present, r.forbidden_present), (10, 9));
    for c in raw().cases {
        let mut a = engine.analyze_word(&c.surface).unwrap();
        let mut an = d.annotate(&a).unwrap();
        an.filter(&mut a, DictionaryFilter::Compatible);
        for j in c
            .judgments
            .iter()
            .filter(|j| j.verdict == validity::Verdict::Required)
        {
            if policy().cases.iter().any(|p| {
                p.surface == c.surface
                    && p.judgments.iter().any(|x| {
                        x.verdict == validity::Verdict::Forbidden
                            && x.lemmas == j.lemmas
                            && x.morphemes == j.morphemes
                    })
            }) {
                continue;
            }
            // Required raw hypotheses can have a separately reviewed lexical conflict.
            assert!(
                a.analyses.iter().any(|p| matches(p, j)),
                "{}: {:?}",
                c.id,
                a.analyses
            );
        }
    }
    for w in ["좋는구나", "고르는군"] {
        let a = engine.analyze_word(w).unwrap();
        let an = d.annotate(&a).unwrap();
        assert!(
            an.readings
                .iter()
                .flat_map(|r| &r.lemmas)
                .flat_map(|l| &l.entries)
                .flat_map(|e| &e.conflicts)
                .any(|c| c.rule == AttachmentRule::BareExclamationVerb)
        );
    }
    for (word, forms, entries) in [
        (
            "고르는군",
            vec!["는군"],
            vec![
                ("krdict:19935", Compatibility::Compatible),
                ("krdict:19938", Compatibility::Compatible),
                ("krdict:25632", Compatibility::Incompatible),
            ],
        ),
        (
            "고르군",
            vec!["군"],
            vec![
                ("krdict:19935", Compatibility::Incompatible),
                ("krdict:19938", Compatibility::Incompatible),
                ("krdict:25632", Compatibility::Compatible),
            ],
        ),
        (
            "있는구나",
            vec!["는구나"],
            vec![
                ("krdict:68796", Compatibility::Compatible),
                ("krdict:68797", Compatibility::Incompatible),
                ("krdict:62595", Compatibility::Incompatible),
            ],
        ),
        (
            "있구나",
            vec!["구나"],
            vec![
                ("krdict:68796", Compatibility::Unknown),
                ("krdict:68797", Compatibility::Compatible),
                ("krdict:62595", Compatibility::Unknown),
            ],
        ),
        (
            "잘되더구나",
            vec!["더구나"],
            vec![("krdict:62302", Compatibility::Unknown)],
        ),
        (
            "먹으옵시는구나",
            vec!["으옵시", "는구나"],
            vec![("krdict:58272", Compatibility::Unknown)],
        ),
    ] {
        let a = engine.analyze_word(word).unwrap();
        let path = a
            .analyses
            .iter()
            .find(|p| {
                p.lemmas.len() == 1
                    && p.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        let an = d.annotate(&a).unwrap();
        let assessment = an.assess(path);
        for (id, status) in entries {
            let entry = assessment.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == id)
                .unwrap();
            assert_eq!(entry.status, status, "{word}: {id}");
            if status == Compatibility::Unknown {
                assert!(entry.conflicts.is_empty());
            }
        }
    }
    assert!(d.cache_bytes() <= 4096);
}
#[test]
fn exclamation_cli_and_ordered_exports_match_dictionary_library_results() {
    let fixture = Fixture::new("cli");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    for c in raw().cases.into_iter().chain(policy().cases) {
        let original = engine.analyze_word(&c.surface).unwrap();
        for filter in [
            None,
            Some(DictionaryFilter::Headword),
            Some(DictionaryFilter::Compatible),
        ] {
            let mut a = original.clone();
            let mut an = d.annotate(&a).unwrap();
            if let Some(f) = filter {
                an.filter(&mut a, f);
            }
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &c.surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(f) = filter {
                cmd.arg(if f == DictionaryFilter::Headword {
                    "--dict-only"
                } else {
                    "--dict-compatible"
                });
            }
            let result = cmd.output().unwrap();
            assert!(result.status.success());
            let mut actual: serde_json::Value = serde_json::from_slice(&result.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(&an).unwrap()
            );
            assert_eq!(actual, serde_json::to_value(&a).unwrap());
            for p in a.analyses {
                let parts = p.breakdown().unwrap();
                let heads: Vec<_> = parts
                    .iter()
                    .filter_map(|c| match c {
                        klem::breakdown::Component::Lemma(i) => Some(p.lemmas[*i].text.as_str()),
                        klem::breakdown::Component::Morpheme(_) => None,
                    })
                    .collect();
                assert_eq!(
                    heads,
                    p.lemmas.iter().map(|l| l.text.as_str()).collect::<Vec<_>>()
                );
            }
        }
    }
}
