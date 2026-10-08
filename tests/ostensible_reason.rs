use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::path::PathBuf;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn finite_source_judgments_have_stable_individual_case_and_judgment_ids() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/ostensible-reason-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.cases, 26);
    assert_eq!(report.required_total, 21);
    assert_eq!(report.forbidden_total, 5);
}

#[test]
fn individual_dictionary_mode_judgments_preserve_homonyms_unknowns_and_raw_hypotheses() {
    let matrix: Value =
        serde_json::from_str(include_str!("fixtures/ostensible-reason-mode-scope.json")).unwrap();
    let cases = matrix["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 12);
    let mut ids = std::collections::HashSet::new();
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("individual-mode-ledger");
    let mut session = DictionarySession::new(&db, 1024);
    for case in cases {
        let id = case["id"].as_str().unwrap();
        assert!(ids.insert(id));
        assert_eq!(case["contextual_verdict"], "unjudged");
        for word in [
            case["surface"].as_str().unwrap().to_owned(),
            case["surface"].as_str().unwrap().nfd().collect(),
        ] {
            let raw = engine.analyze_word(&word).unwrap();
            let annotation = session.annotate(&raw).unwrap();
            let targets: Vec<_> = raw
                .analyses
                .iter()
                .filter(|a| matches(a, &case["expected"]))
                .collect();
            assert_eq!(
                targets.len(),
                usize::from(case["expected_presence"]["raw"].as_bool().unwrap()),
                "{id}"
            );
            for candidate in targets {
                let assessment = serde_json::to_value(annotation.assess(candidate)).unwrap();
                for entry in case["expected_entry_statuses"].as_array().unwrap() {
                    let lemma = entry["lemma"].as_u64().unwrap() as usize;
                    let actual = assessment["lemmas"][lemma]["entries"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .find(|e| e["id"] == entry["id"])
                        .unwrap();
                    assert_eq!(actual["status"], entry["status"], "{id}: {}", entry["id"]);
                }
            }
            for (mode, key) in [
                (DictionaryFilter::Headword, "headword"),
                (DictionaryFilter::Compatible, "compatible"),
            ] {
                let mut filtered = raw.clone();
                let mut annotation = annotation.clone();
                annotation.filter(&mut filtered, mode);
                assert_eq!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| matches(a, &case["expected"])),
                    case["expected_presence"][key].as_bool().unwrap(),
                    "{id}: {key}"
                );
            }
        }
    }
}

fn matches(analysis: &Analysis, expected: &Value) -> bool {
    let value = serde_json::to_value(analysis).unwrap();
    value["lemmas"]
        .as_array()
        .unwrap()
        .iter()
        .map(|l| l["text"].as_str().unwrap())
        .eq(expected["lemmas"]
            .as_array()
            .unwrap()
            .iter()
            .map(|l| l.as_str().unwrap()))
        && value["lemmas"]
            .as_array()
            .unwrap()
            .iter()
            .map(|l| l["kind"].as_str().unwrap())
            .eq(expected["lemma_kinds"]
                .as_array()
                .unwrap()
                .iter()
                .map(|l| l.as_str().unwrap()))
        && value["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| m["form"].as_str().unwrap())
            .eq(expected["morphemes"]
                .as_array()
                .unwrap()
                .iter()
                .map(|m| m.as_str().unwrap()))
        && value["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| m["kind"].as_str().unwrap())
            .eq(expected["morpheme_kinds"]
                .as_array()
                .unwrap()
                .iter()
                .map(|m| m.as_str().unwrap()))
        && expected["required_rules"]
            .as_array()
            .unwrap()
            .iter()
            .all(|rule| analysis.rules.iter().any(|r| r == rule.as_str().unwrap()))
}

fn path<'a>(word: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> Option<&'a Analysis> {
    word.analyses.iter().find(|analysis| {
        analysis
            .lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(heads.iter().copied())
            && analysis
                .morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(forms.iter().copied())
            && analysis
                .rules
                .iter()
                .any(|r| r == "ending.ostensible_reason")
    })
}

struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(name: &str) -> (SqliteDictionary, Cleanup) {
    let path = std::env::temp_dir().join(format!(
        "klem-ostensible-prototype-{name}-{}.db",
        std::process::id()
    ));
    assert!(!path.exists());
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/ostensible-reason-boundary-english.json",
        )],
        &path,
        "ostensible-source",
    )
    .unwrap();
    (SqliteDictionary::open(path).unwrap(), cleanup)
}

#[test]
fn all_original_targets_preserve_previous_paths_and_survive_every_mode_and_encoding() {
    let cases: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/ostensible-reason-original-cases.json"
    ))
    .unwrap();
    assert_eq!(cases.len(), 12);
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("originals");
    let mut session = DictionarySession::new(&db, 1024);
    for case in cases {
        let old: WordAnalysis = serde_json::from_value(case["before"].clone()).unwrap();
        let word = case["surface"].as_str().unwrap();
        for surface in [word.to_owned(), word.nfd().collect()] {
            let raw = engine.analyze_word(&surface).unwrap();
            assert_eq!(
                raw.analyses
                    .iter()
                    .filter(|a| old.analyses.contains(a))
                    .cloned()
                    .collect::<Vec<_>>(),
                old.analyses,
                "{word}"
            );
            let original = raw
                .analyses
                .iter()
                .find(|a| matches(a, &case["expected"]))
                .unwrap_or_else(|| panic!("missing {word}"));
            assert!(original.breakdown().is_some());
            assert!(
                original
                    .rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
            for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = raw.clone();
                let mut annotation = session.annotate(&raw).unwrap();
                annotation.filter(&mut filtered, mode);
                assert!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| matches(a, &case["expected"])),
                    "{word} {mode:?}"
                );
            }
        }
    }
}

#[test]
fn all_finite_native_fields_and_same_head_homonyms_survive_the_real_importer() {
    let native: Value = serde_json::from_str(include_str!(
        "fixtures/ostensible-reason-boundary-native.json"
    ))
    .unwrap();
    let (db, _cleanup) = dictionary("native");
    for (id, expected) in native.as_object().unwrap() {
        let actual = serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap();
        let mut projected = expected.clone();
        for sense in projected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(actual, projected, "{id}");
        let ids: Vec<_> = db
            .lookup(expected["headword"].as_str().unwrap())
            .unwrap()
            .into_iter()
            .map(|e| e.id)
            .collect();
        for (other, value) in native.as_object().unwrap() {
            if value["headword"] == expected["headword"] {
                assert!(ids.contains(other), "{id} lost {other}");
            }
        }
    }
}

#[test]
fn phonological_and_prefinal_boundaries_target_paths_without_banning_lemmas() {
    let engine = Lemmatizer::new();
    for (surface, head, forms) in [
        ("간답시고", "가다", vec!["는답시고"]),
        ("산답시고", "살다", vec!["는답시고"]),
        ("먹는답시고", "먹다", vec!["는답시고"]),
        ("가신답시고", "가다", vec!["시", "는답시고"]),
        ("먹었답시고", "먹다", vec!["었", "답시고"]),
        ("가겠답시고", "가다", vec!["겠", "답시고"]),
        ("좋답시고", "좋다", vec!["답시고"]),
        ("높으시답시고", "높다", vec!["시", "답시고"]),
        ("돕는답시고", "돕다", vec!["는답시고"]),
    ] {
        for word in [surface.to_owned(), surface.nfd().collect()] {
            let result = engine.analyze_word(&word).unwrap();
            assert!(
                result.analyses.iter().any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
                    && a.rules.iter().any(|r| r == "ending.ostensible_reason")),
                "{surface} {head}"
            );
        }
    }
    for (surface, head, forms) in [
        ("가는답시고", "가다", vec!["는답시고"]),
        ("살는답시고", "살다", vec!["는답시고"]),
        ("가겠는답시고", "가다", vec!["겠", "는답시고"]),
        ("먹었는답시고", "먹다", vec!["었", "는답시고"]),
        ("도운답시고", "돕다", vec!["는답시고"]),
    ] {
        for word in [surface.to_owned(), surface.nfd().collect()] {
            let result = engine.analyze_word(&word).unwrap();
            assert!(
                !result.analyses.iter().any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == head
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
                    && a.rules.iter().any(|r| r == "ending.ostensible_reason")),
                "{surface} {head}"
            );
            assert!(
                !result.analyses.is_empty(),
                "{surface}: preserve alternatives"
            );
        }
    }
}

#[test]
fn bare_verbal_hypothesis_is_filtered_by_native_pos_without_a_global_raw_lemma_ban() {
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("bare-verb");
    let mut session = DictionarySession::new(&db, 1024);
    for word in ["먹답시고".to_owned(), "먹답시고".nfd().collect()] {
        let raw = engine.analyze_word(&word).unwrap();
        let target = |a: &Analysis| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "먹다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "답시고"
                && a.rules.iter().any(|r| r == "ending.ostensible_reason")
        };
        assert!(raw.analyses.iter().any(target));
        for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
            let mut filtered = raw.clone();
            let mut annotation = session.annotate(&raw).unwrap();
            annotation.filter(&mut filtered, mode);
            assert_eq!(
                filtered.analyses.iter().any(target),
                mode == DictionaryFilter::Headword
            );
        }
    }
}

#[test]
fn native_homonyms_receive_independent_plain_and_present_assessments() {
    use klem::dictionary::Compatibility::{Compatible, Incompatible};
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("homonyms");
    let mut session = DictionarySession::new(&db, 1024);
    for (surface, form, present) in [
        ("멀답시고", "답시고", false),
        ("먼답시고", "는답시고", true),
    ] {
        for word in [surface.to_owned(), surface.nfd().collect()] {
            let raw = engine.analyze_word(&word).unwrap();
            let candidate = path(&raw, &["멀다"], &[form]).unwrap();
            let annotation = session.annotate(&raw).unwrap();
            let assessed = annotation.assess(candidate);
            assert_eq!(assessed.status, Compatible);
            for (id, status) in [
                (
                    "krdict:54855",
                    if present { Compatible } else { Incompatible },
                ),
                (
                    "krdict:26833",
                    if present { Incompatible } else { Compatible },
                ),
            ] {
                assert_eq!(
                    assessed.lemmas[0]
                        .entries
                        .iter()
                        .find(|e| e.id == id)
                        .unwrap()
                        .status,
                    status,
                    "{surface} {id}"
                );
            }
        }
    }
}

#[test]
fn auxiliary_connector_and_own_class_determine_attachment_independently_of_left_owner() {
    use klem::dictionary::Compatibility::{Compatible, Incompatible};
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("auxiliary");
    let mut session = DictionarySession::new(&db, 1024);
    for (surface, heads, forms, present) in [
        (
            "좋게한답시고",
            vec!["좋다", "하다"],
            vec!["게", "는답시고"],
            true,
        ),
        (
            "먹기는하답시고",
            vec!["먹다", "하다"],
            vec!["기", "는", "답시고"],
            false,
        ),
        (
            "좋기는하답시고",
            vec!["좋다", "하다"],
            vec!["기는", "답시고"],
            false,
        ),
    ] {
        for word in [surface.to_owned(), surface.nfd().collect()] {
            let raw = engine.analyze_word(&word).unwrap();
            let candidate = path(&raw, &heads, &forms).unwrap_or_else(|| panic!("{surface}"));
            assert_eq!(candidate.lemmas[1].kind, klem::LemmaKind::Auxiliary);
            let annotation = session.annotate(&raw).unwrap();
            let assessed = annotation.assess(candidate);
            assert_eq!(assessed.status, Compatible, "{surface} {assessed:?}");
            for (id, status) in [
                (
                    "krdict:62888",
                    if present { Compatible } else { Incompatible },
                ),
                (
                    "krdict:62899",
                    if present { Incompatible } else { Compatible },
                ),
                ("krdict:73277", Incompatible),
            ] {
                assert_eq!(
                    assessed.lemmas[1]
                        .entries
                        .iter()
                        .find(|e| e.id == id)
                        .unwrap()
                        .status,
                    status,
                    "{surface} {id}"
                );
            }
        }
    }
    let raw = engine.analyze_word("좋게하답시고").unwrap();
    assert!(
        path(&raw, &["좋다", "하다"], &["게", "답시고"]).is_none(),
        "Do not lend the left adjective class to its verbal auxiliary"
    );
}

#[test]
fn unreviewed_copular_negative_and_stative_extensions_remain_unknown_and_eligible() {
    use klem::dictionary::Compatibility::Unknown;
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("unknown");
    let mut session = DictionarySession::new(&db, 1024);
    for (surface, heads, forms, id) in [
        (
            "먹고있답시고",
            vec!["먹다", "있다"],
            vec!["고", "답시고"],
            "krdict:62595",
        ),
        (
            "좋지는않답시고",
            vec!["좋다", "않다"],
            vec!["지", "는", "답시고"],
            "krdict:71583",
        ),
        (
            "먹지는않답시고",
            vec!["먹다", "않다"],
            vec!["지", "는", "답시고"],
            "krdict:71581",
        ),
        (
            "학생이답시고",
            vec!["학생", "이다"],
            vec!["답시고"],
            "krdict:86232",
        ),
        (
            "학생이었답시고",
            vec!["학생", "이다"],
            vec!["었", "답시고"],
            "krdict:86232",
        ),
    ] {
        for word in [surface.to_owned(), surface.nfd().collect()] {
            let raw = engine.analyze_word(&word).unwrap();
            let candidate = path(&raw, &heads, &forms).unwrap_or_else(|| panic!("{surface}"));
            let annotation = session.annotate(&raw).unwrap();
            let assessed = annotation.assess(candidate);
            assert_eq!(assessed.lemmas[1].status, Unknown, "{surface} {assessed:?}");
            assert_eq!(
                assessed.lemmas[1]
                    .entries
                    .iter()
                    .find(|e| e.id == id)
                    .unwrap()
                    .status,
                Unknown
            );
            let mut filtered = raw.clone();
            let mut annotated = annotation.clone();
            annotated.filter(&mut filtered, DictionaryFilter::Compatible);
            assert!(path(&filtered, &heads, &forms).is_some(), "{surface}");
        }
    }
}

#[test]
fn ordered_breakdowns_keep_prefinals_particles_and_auxiliaries_with_their_owners() {
    use klem::breakdown::Component::{Lemma, Morpheme};
    let engine = Lemmatizer::new();
    for (surface, heads, forms, order) in [
        (
            "간답시고",
            vec!["가다"],
            vec!["는답시고"],
            vec![Lemma(0), Morpheme(0)],
        ),
        (
            "가신답시고",
            vec!["가다"],
            vec!["시", "는답시고"],
            vec![Lemma(0), Morpheme(0), Morpheme(1)],
        ),
        (
            "먹었답시고",
            vec!["먹다"],
            vec!["었", "답시고"],
            vec![Lemma(0), Morpheme(0), Morpheme(1)],
        ),
        (
            "좋게한답시고",
            vec!["좋다", "하다"],
            vec!["게", "는답시고"],
            vec![Lemma(0), Morpheme(0), Lemma(1), Morpheme(1)],
        ),
        (
            "먹기는하답시고",
            vec!["먹다", "하다"],
            vec!["기", "는", "답시고"],
            vec![Lemma(0), Morpheme(0), Morpheme(1), Lemma(1), Morpheme(2)],
        ),
        (
            "학생이었답시고",
            vec!["학생", "이다"],
            vec!["었", "답시고"],
            vec![Lemma(0), Lemma(1), Morpheme(0), Morpheme(1)],
        ),
    ] {
        for word in [surface.to_owned(), surface.nfd().collect()] {
            let raw = engine.analyze_word(&word).unwrap();
            let candidate = path(&raw, &heads, &forms).unwrap_or_else(|| panic!("{surface}"));
            assert_eq!(candidate.breakdown(), Some(order.clone()), "{surface}");
            let exported = serde_json::to_value(candidate).unwrap();
            let restored: Analysis = serde_json::from_value(exported).unwrap();
            assert_eq!(&restored, candidate);
            assert_eq!(restored.breakdown(), Some(order.clone()));
        }
    }
}
