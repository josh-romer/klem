//! COV-018aa: separately represented polite followers of native quote reports.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer};
use std::{collections::BTreeSet, fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;
fn suite(file: &str) -> validity::Suite {
    let mut s: validity::Suite = serde_json::from_str(file).unwrap();
    s.cases.retain(|c| c.id.starts_with("qfollow-"));
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
        let p = std::env::temp_dir().join(format!("klem-qfollow-{}-{name}.db", std::process::id()));
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-quoted-exclamation.json"),
                PathBuf::from("tests/fixtures/krdict-quote-followers.json"),
            ],
            &p,
            "qfollow-fixture",
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
fn qfollow_paths_preserve_owners_boundaries_normalization_and_alternatives() {
    let s = raw();
    let r = validity::evaluate(&s).unwrap();
    assert!(r.passed(), "{:?}", r.violations);
    assert_eq!((r.required_total, r.forbidden_total), (55, 12));
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
        for j in c
            .judgments
            .iter()
            .filter(|j| j.verdict == validity::Verdict::Required)
        {
            assert!(
                a.analyses
                    .iter()
                    .filter(|p| matches(p, j))
                    .all(|p| p.rules.iter().any(|r| r == "ending.quoted_exclamation")),
                "{}",
                c.id
            );
        }
    }
    let a = engine.analyze_word("산다는군요").unwrap();
    for head in ["사다", "살다"] {
        assert!(a.analyses.iter().any(|p| {
            p.lemmas.len() == 1
                && p.lemmas[0].text == head
                && p.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["는다는군", "요"])
        }));
    }
}
fn feature<'a>(v: &'a serde_json::Value, att: &str) -> Option<&'a str> {
    if let Some(fs) = v["feat"].as_array() {
        fs.iter()
            .find(|f| f["att"] == att)
            .and_then(|f| f["val"].as_str())
    } else if v["feat"]["att"] == att {
        v["feat"]["val"].as_str()
    } else {
        None
    }
}
#[test]
fn qfollow_native_groups_keep_source_identity_and_unjudged_followers() {
    let m: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/quote-followers-sources.json")).unwrap();
    let groups = m["source_groups"].as_array().unwrap();
    assert_eq!(groups.len(), 17);
    let mut seen = BTreeSet::new();
    let raw = raw();
    let policy = policy();
    for g in groups {
        assert!(seen.insert((
            g["entry_id"].as_str().unwrap(),
            g["sense_id"].as_str().unwrap(),
            g["example_group"].as_u64().unwrap(),
            g["turn"].as_u64().unwrap(),
            g["token"].as_u64().unwrap()
        )));
        let n: serde_json::Value =
            serde_json::from_slice(&fs::read(g["fixture"].as_str().unwrap()).unwrap()).unwrap();
        let e = n["LexicalResource"]["Lexicon"]["LexicalEntry"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| {
                e["val"] == g["native_entry_id"]
                    && feature(&e["Lemma"], "writtenForm") == g["headword"].as_str()
                    && feature(e, "lexicalUnit") == g["lexical_unit"].as_str()
            })
            .unwrap();
        let sense = e["Sense"]
            .as_array()
            .unwrap()
            .iter()
            .find(|s| s["val"] == g["sense_id"])
            .unwrap();
        let index = g["example_group"].as_u64().unwrap() as usize - 1;
        let examples = &sense["SenseExample"];
        let native = if let Some(groups) = examples.as_array() {
            &groups[index]
        } else {
            assert_eq!(index, 0);
            examples
        };
        assert_eq!(native, &g["native_group"]);
        let text = native["feat"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|f| f["att"] == "example")
            .nth(g["turn"].as_u64().unwrap() as usize)
            .unwrap()["val"]
            .as_str()
            .unwrap();
        let token = text
            .split_whitespace()
            .nth(g["token"].as_u64().unwrap() as usize)
            .unwrap()
            .trim_end_matches(['.', '?', '!', ',']);
        assert_eq!(token, g["surface"].as_str().unwrap());
        assert!(
            raw.cases
                .iter()
                .any(|c| Some(c.id.as_str()) == g["case_id"].as_str() && c.surface == token)
        );
        assert!(
            policy
                .cases
                .iter()
                .any(|c| Some(c.id.as_str()) == g["policy_case_id"].as_str() && c.surface == token)
        );
    }
    for o in m["unjudged_follower_observations"].as_array().unwrap() {
        assert_eq!(o["status"], "unjudged");
        assert!(
            !raw.cases
                .iter()
                .chain(&policy.cases)
                .any(|c| Some(c.surface.as_str()) == o["surface"].as_str())
        );
    }
    assert_eq!(m["license"], "CC BY-SA 2.0 KR");
}
#[test]
fn qfollow_policy_keeps_native_classes_and_inferred_experience_unknown() {
    let fixture = Fixture::new("policy");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    let mut d = DictionarySession::new(&db, 4096);
    let s = policy();
    for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
        let r = validity::evaluate_with(&s, |w| {
            let mut a = engine.analyze_word(w).unwrap();
            let mut an = d.annotate(&a).unwrap();
            an.filter(&mut a, filter);
            Ok(a)
        })
        .unwrap();
        assert_eq!((r.required_total, r.forbidden_total), (30, 3));
        assert_eq!(r.required_present, 30, "{:?}", r.violations);
        assert_eq!(
            r.forbidden_present,
            if filter == DictionaryFilter::Compatible {
                0
            } else {
                3
            }
        );
    }
    for (word, head, forms, entries) in [
        (
            "고른다는군요",
            "고르다",
            vec!["는다는군", "요"],
            vec![
                ("krdict:19935", Compatibility::Compatible),
                ("krdict:19938", Compatibility::Compatible),
                ("krdict:25632", Compatibility::Incompatible),
            ],
        ),
        (
            "고르다는군요",
            "고르다",
            vec!["다는군", "요"],
            vec![
                ("krdict:19935", Compatibility::Incompatible),
                ("krdict:19938", Compatibility::Incompatible),
                ("krdict:25632", Compatibility::Compatible),
            ],
        ),
        (
            "먹더라는군요",
            "먹다",
            vec!["더라는군", "요"],
            vec![("krdict:58272", Compatibility::Unknown)],
        ),
        (
            "먹으시다는군요",
            "먹다",
            vec!["시", "다는군", "요"],
            vec![("krdict:58272", Compatibility::Unknown)],
        ),
    ] {
        let a = engine.analyze_word(word).unwrap();
        let p = a
            .analyses
            .iter()
            .find(|p| {
                p.lemmas.len() == 1
                    && p.lemmas[0].text == head
                    && p.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        let an = d.annotate(&a).unwrap();
        let assessment = an.assess(p);
        for (id, status) in entries {
            let e = assessment.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == id)
                .unwrap();
            assert_eq!(e.status, status, "{word}: {id}");
            if status == Compatibility::Unknown {
                assert!(e.conflicts.is_empty());
            }
        }
    }
    assert!(d.cache_bytes() <= 4096);
}
#[test]
fn qfollow_cli_and_ordered_exports_match_dictionary_library_results() {
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
