//! NIKL's finite adverb-plus-predicate compound preserves whole lexical alternatives.
#[path = "../tools/validity.rs"]
mod validity;
use klem::breakdown::Component;
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, Session};
use std::{fs, path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut s: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    s.cases.retain(|c| c.id.starts_with("well-doeda-"));
    s
}
fn compound(a: &Analysis) -> bool {
    a.rules.iter().any(|r| r == "compound.predicate.well_doeda")
}
fn dictionary() -> (PathBuf, SqliteDictionary) {
    let dir = std::env::temp_dir().join(format!(
        "klem-well-doeda-{}-{}",
        std::process::id(),
        std::thread::current().name().unwrap()
    ));
    fs::create_dir_all(&dir).unwrap();
    fs::write(
        dir.join("native.json"),
        include_bytes!("fixtures/krdict-well-doeda.json"),
    )
    .unwrap();
    let db = dir.join("native.db");
    import_krdict(&[dir.join("native.json")], &db, "well-doeda-test").unwrap();
    let dictionary = SqliteDictionary::open(&db).unwrap();
    (dir, dictionary)
}

#[test]
fn stable_compound_cases_preserve_whole_heads_and_owned_inflections() {
    let s = suite();
    let report = validity::evaluate(&s).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (30, 14));
    let engine = Lemmatizer::new();
    for c in s.cases {
        let result = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            result,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        for a in result.analyses.iter().filter(|a| compound(a)) {
            assert_eq!(a.lemmas[0].text, "잘");
            assert_eq!(a.lemmas[0].kind, LemmaKind::Adverbial);
            assert_eq!(a.lemmas[1].text, "되다");
            assert_eq!(a.lemmas[1].kind, LemmaKind::Predicate);
            assert!(
                !a.rules
                    .iter()
                    .any(|r| r.starts_with("suffix.") && r.ends_with("doeda"))
            );
            let mut parent = a.clone();
            parent.lemmas.remove(0);
            parent.lemmas[0].text = "잘되다".into();
            parent
                .rules
                .retain(|r| r != "compound.predicate.well_doeda");
            assert!(result.analyses.contains(&parent), "{}: {a:?}", c.surface);
            let order = a.breakdown().unwrap();
            assert_eq!(&order[..2], &[Component::Lemma(0), Component::Lemma(1)]);
            let expected: Vec<_> = std::iter::once(Component::Lemma(0))
                .chain(parent.breakdown().unwrap().into_iter().map(|c| match c {
                    Component::Lemma(i) => Component::Lemma(i + 1),
                    Component::Morpheme(i) => Component::Morpheme(i),
                }))
                .collect();
            assert_eq!(order, expected);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn native_verb_owner_conflicts_with_adjective_without_selecting_a_sense() {
    let (dir, db) = dictionary();
    assert_eq!(
        db.entry("krdict:58939").unwrap().unwrap().summary.pos,
        "부사"
    );
    assert_eq!(
        db.entry("krdict:62302").unwrap().unwrap().summary.pos,
        "동사"
    );
    let mut expected = None;
    for budget in [0, 1, 1024, 4 * 1024 * 1024] {
        let mut dictionary = DictionarySession::new(&db, budget);
        let mut session = Session::new(Arc::new(Lemmatizer::new()), budget);
        for surface in [
            "잘됐어요",
            "잘되는",
            "잘됨은",
            "잘되기였다",
            "잘되고있다",
            "잘되지않았다",
        ] {
            let raw = session.analyze_word(surface).unwrap();
            let annotation = dictionary.annotate(&raw).unwrap();
            if surface == "잘됐어요" {
                if let Some(old) = &expected {
                    assert_eq!(&annotation, old);
                } else {
                    expected = Some(annotation.clone());
                }
            }
            for (i, _) in raw.analyses.iter().enumerate().filter(|(_, a)| compound(a)) {
                let reading = &annotation.readings[i];
                let owner = &reading.lemmas[1];
                assert_eq!(
                    owner
                        .entries
                        .iter()
                        .find(|e| e.id == "krdict:89858")
                        .unwrap()
                        .status,
                    Compatibility::Compatible
                );
                assert_eq!(
                    owner
                        .entries
                        .iter()
                        .find(|e| e.id == "krdict:48214")
                        .unwrap()
                        .status,
                    Compatibility::Incompatible
                );
                assert_eq!(reading.status, Compatibility::Compatible);
                assert!(
                    owner
                        .entries
                        .iter()
                        .all(|e| e.derivational_identity.is_none())
                );
            }
            for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = (*raw).clone();
                let mut filtered_annotation = annotation.clone();
                filtered_annotation.filter(&mut filtered, filter);
                assert!(filtered.analyses.iter().any(compound), "{surface}");
                assert!(
                    filtered
                        .analyses
                        .iter()
                        .any(|a| a.lemmas[0].text == "잘되다")
                );
            }
            assert_eq!(
                raw,
                session
                    .analyze_word(&surface.nfd().collect::<String>())
                    .unwrap()
            );
        }
    }
    drop(db);
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn external_rule_marker_does_not_borrow_a_compound_owner() {
    let engine = Lemmatizer::new();
    let mut invalid = engine
        .analyze_word("된다")
        .unwrap()
        .analyses
        .into_iter()
        .find(|a| a.lemmas[0].kind == LemmaKind::Predicate)
        .unwrap();
    invalid.rules.push("compound.predicate.well_doeda".into());
    assert!(invalid.breakdown().is_none());
    let valid = engine
        .analyze_word("잘됨은")
        .unwrap()
        .analyses
        .into_iter()
        .find(compound)
        .unwrap();
    let mut invalid = valid.clone();
    invalid.lemmas[0].text = "더".into();
    assert!(invalid.breakdown().is_none());
    let mut invalid = valid;
    invalid.lemmas[1].kind = LemmaKind::Auxiliary;
    assert!(invalid.breakdown().is_none());
}

#[test]
fn original_candidates_and_corpus_whole_annotations_remain() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/well-doeda-sources.json")).unwrap();
    let engine = Lemmatizer::new();
    let original = source["before_analyses"].as_object().unwrap();
    assert_eq!(original.len(), 46);
    for (word, before) in original {
        let before: klem::WordAnalysis = serde_json::from_value(before.clone()).unwrap();
        let after = engine.analyze_word(word).unwrap();
        let retained: Vec<_> = after
            .analyses
            .iter()
            .filter(|a| !compound(a))
            .cloned()
            .collect();
        assert_eq!(
            retained, before.analyses,
            "{word}: original candidate/order drift"
        );
    }
    let mut rows = 0;
    for corpus in source["corpora"].as_array().unwrap() {
        for row in corpus["rows"].as_array().unwrap() {
            rows += 1;
            let surface = row["original_row"][1].as_str().unwrap();
            let after = engine.analyze_word(surface).unwrap();
            assert!(
                after.analyses.iter().any(|a| a.lemmas[0].text == "잘되다"),
                "{surface}"
            );
            assert!(after.analyses.iter().any(compound), "{surface}");
            assert!(
                row["original_lemma"].as_str().unwrap().starts_with("잘되+")
                    || row["original_lemma"]
                        .as_str()
                        .unwrap()
                        .starts_with("잘+되+")
            );
        }
    }
    assert_eq!(rows, 8);
}

#[test]
fn compound_verb_class_does_not_restrict_a_later_independent_owner() {
    let (dir, db) = dictionary();
    let mut path = Lemmatizer::new()
        .analyze_word("잘되고")
        .unwrap()
        .analyses
        .into_iter()
        .find(compound)
        .unwrap();
    path.lemmas.push(klem::Lemma {
        text: "되다".into(),
        kind: LemmaKind::Predicate,
    });
    path.morphemes.push(klem::Morpheme {
        form: "다".into(),
        kind: klem::MorphemeKind::Ending,
    });
    assert!(path.breakdown().is_some());
    let mut word = Lemmatizer::new().analyze_word("잘되고").unwrap();
    word.analyses = vec![path];
    let assessed = DictionarySession::new(&db, 0).annotate(&word).unwrap();
    let slots = &assessed.readings[0].lemmas;
    let adjective = |index: usize| {
        slots[index]
            .entries
            .iter()
            .find(|e| e.id == "krdict:48214")
            .unwrap()
            .status
    };
    assert_eq!(adjective(1), Compatibility::Incompatible);
    assert_eq!(adjective(2), Compatibility::Compatible);
    drop(db);
    fs::remove_dir_all(dir).unwrap();
}
