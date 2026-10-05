//! All remaining original -하다 senses keep sourced base roles and whole parents.
#[path = "../tools/hada_nominal_preservation.rs"]
mod preservation;
#[path = "../tools/validity.rs"]
mod validity;
use klem::{LemmaKind, Lemmatizer, MorphemeKind};
use serde_json::{Value, json};
use std::sync::OnceLock;
use unicode_normalization::UnicodeNormalization;
fn fixture() -> &'static Value {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    SOURCE.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/hada-remaining-sources.json")).unwrap()
    })
}
#[test]
fn all_seventeen_source_groups_and_nineteen_classes_have_stable_paths() {
    let suite: validity::Suite = serde_json::from_value(json!({
        "schema_version":1,"review_status":"Source-derived structure; contextual and independent review pending",
        "sources":{"hada-remaining-krdict":"https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=88475"},
        "cases":fixture()["cases"],
    })).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (158, 51));
    assert_eq!(fixture()["owners"].as_array().unwrap().len(), 17);
    let engine = Lemmatizer::new();
    for case in fixture()["cases"].as_array().unwrap() {
        let text = case["surface"].as_str().unwrap();
        let actual = engine.analyze_word(text).unwrap();
        assert_eq!(
            actual,
            engine
                .analyze_word(&text.nfd().collect::<String>())
                .unwrap()
        );
        for path in &actual.analyses {
            assert!(path.breakdown().is_some(), "{text}: {path:?}");
            assert!(
                path.rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some()),
                "{text}"
            );
        }
    }
}
#[test]
fn every_original_word_and_whole_parent_remains_in_order() {
    let engine = Lemmatizer::new();
    let before = fixture()["before_analyses"].as_object().unwrap();
    assert_eq!(before.len(), 649);
    for (word, value) in before {
        let frozen: klem::WordAnalysis = serde_json::from_value(value.clone()).unwrap();
        let after = engine.analyze_word(word).unwrap();
        preservation::assert_preserved(&after, &frozen);
        let retained: Vec<_> = after
            .analyses
            .iter()
            .filter(|a| frozen.analyses.contains(a))
            .cloned()
            .collect();
        assert_eq!(retained, frozen.analyses, "{word}");
    }
    for parent in fixture()["required_parents"].as_array().unwrap() {
        let old: klem::Analysis = serde_json::from_value(parent["before_parent"].clone()).unwrap();
        let actual = engine
            .analyze_word(parent["surface"].as_str().unwrap())
            .unwrap();
        assert!(actual.analyses.contains(&old));
    }
}
#[test]
fn source_classes_reject_opposite_class_and_verbal_adjective_boundaries() {
    let engine = Lemmatizer::new();
    for word in [
        "돌연하는",
        "돌연하고있다",
        "따뜻하는",
        "착하고있다",
        "듯하는",
        "법하는",
        "뻔하는",
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result
                .analyses
                .iter()
                .any(|a| a.lemmas.first().is_some_and(|l| matches!(
                    l.kind,
                    LemmaKind::Adverbial | LemmaKind::Root | LemmaKind::Nominal
                ) && fixture()["owners"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .any(|o| o["base"].as_str() == Some(&l.text)))
                    && a.morphemes
                        .first()
                        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "하다")),
            "{word}"
        );
    }
    for (word, kind, wrong) in [
        (
            "소곤소곤하다",
            LemmaKind::Adverbial,
            "suffix.adjective.hada",
        ),
        ("착하다", LemmaKind::Root, "suffix.verb.hada"),
        (
            "척하다",
            LemmaKind::Nominal,
            "suffix.auxiliary.adjective.hada",
        ),
    ] {
        let actual = engine.analyze_word(word).unwrap();
        let mut forged = actual
            .analyses
            .iter()
            .find(|a| {
                a.lemmas[0].kind == kind
                    && a.morphemes
                        .first()
                        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "하다")
            })
            .unwrap()
            .clone();
        forged
            .rules
            .retain(|r| !r.starts_with("suffix.") || !r.ends_with(".hada"));
        forged.rules.push(wrong.into());
        forged.rules.sort();
        assert!(forged.breakdown().is_none(), "{word}");
    }
}
#[test]
fn bound_noun_suffixes_retain_the_original_auxiliary_connectors() {
    let engine = Lemmatizer::new();
    for (word, base, connector) in [
        ("먹을듯하다", "듯", "을"),
        ("먹을법하다", "법", "을"),
        ("먹을뻔하다", "뻔", "을"),
        ("먹은척하다", "척", "은"),
        ("먹은체하다", "체", "은"),
        ("학생인양하다", "양", "은"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| a
                .lemmas
                .last()
                .is_some_and(|l| l.text == base && l.kind == LemmaKind::Nominal)
                && a.morphemes
                    .iter()
                    .any(|m| m.form == "하다" && m.kind == MorphemeKind::Suffix)
                && a.morphemes[0].form == connector),
            "{word}"
        );
    }
    for (word, base) in [
        ("먹는법하다", "법"),
        ("먹은뻔하다", "뻔"),
        ("먹을척하다", "척"),
        ("먹을체하다", "체"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result
                .analyses
                .iter()
                .any(|a| a.lemmas.first().is_some_and(|l| l.text == "먹다")
                    && a.lemmas.last().is_some_and(|l| l.text == base)
                    && a.morphemes
                        .iter()
                        .any(|m| m.form == "하다" && m.kind == MorphemeKind::Suffix)),
            "{word}"
        );
    }
}

#[test]
fn complete_native_entries_and_bound_noun_origin_roles_remain_independent() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, OriginRelation, SqliteDictionary,
        import_krdict,
    };
    let path = std::env::temp_dir().join(format!("klem-hada-remaining-{}.db", std::process::id()));
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/krdict-hada-six-sense.json",
        )],
        &path,
        "hada-remaining-test",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let native = fixture()["complete_native_entries"].as_object().unwrap();
    assert_eq!(native.len(), 138);
    for (id, expected) in native {
        let mut projected = expected.clone();
        for sense in projected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            projected,
            "{id}"
        );
    }
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&db, 1048576);
    for word in ["법하다", "양하다", "척하다", "체하다", "돌연하다"] {
        let result = engine.analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        for (i, a) in result.analyses.iter().enumerate().filter(|(_, a)| {
            a.morphemes
                .first()
                .is_some_and(|m| m.form == "하다" && m.kind == MorphemeKind::Suffix)
        }) {
            let owner = fixture()["owners"]
                .as_array()
                .unwrap()
                .iter()
                .find(|o| o["base"].as_str() == Some(&a.lemmas[0].text))
                .unwrap();
            for entry in &annotation.readings[i].lemmas[0].entries {
                let original = &native[&entry.id];
                if owner["base_role"] == "bound_noun" && original["pos"] != "의존 명사" {
                    assert_eq!(entry.status, Compatibility::Incompatible);
                }
                if let Some(identity) = &entry.derivational_identity {
                    assert_eq!(
                        identity.whole_entries,
                        owner["whole_entries"]
                            .as_array()
                            .unwrap()
                            .iter()
                            .map(|v| v.as_str().unwrap().to_owned())
                            .collect::<Vec<_>>()
                    );
                    if owner["whole_expected_base_origins"]
                        .as_array()
                        .unwrap()
                        .is_empty()
                    {
                        assert_eq!(identity.relation, OriginRelation::Unknown);
                    }
                    if word == "돌연하다" || (word == "법하다" && original["pos"] == "의존 명사")
                    {
                        assert_eq!(identity.relation, OriginRelation::RecordedMatch);
                    }
                }
            }
        }
    }
    drop(session);
    drop(db);
    std::fs::remove_file(path).unwrap();
}
#[test]
fn auxiliary_class_and_connector_licenses_are_scoped_to_the_source_owner() {
    let engine = Lemmatizer::new();
    let result = engine.analyze_word("학생인양하다").unwrap();
    let copular = |a: &klem::Analysis| {
        a.lemmas.iter().any(|l| l.kind == LemmaKind::Copula)
            && a.lemmas
                .last()
                .is_some_and(|l| l.text == "양" && l.kind == LemmaKind::Nominal)
    };
    assert!(result.analyses.iter().any(|a| {
        copular(a)
            && a.rules
                .iter()
                .any(|r| r == "suffix.auxiliary.adjective.hada")
    }));
    assert!(
        !result
            .analyses
            .iter()
            .any(|a| copular(a) && a.rules.iter().any(|r| r == "suffix.auxiliary.verb.hada"))
    );
    for (word, base) in [
        ("학생인척하다", "척"),
        ("학생인체하다", "체"),
        ("학생일법하다", "법"),
    ] {
        assert!(
            !engine.analyze_word(word).unwrap().analyses.iter().any(|a| a
                .lemmas
                .iter()
                .any(|l| l.kind == LemmaKind::Copula)
                && a.lemmas
                    .last()
                    .is_some_and(|l| l.text == base && l.kind == LemmaKind::Nominal)
                && a.morphemes
                    .iter()
                    .any(|m| m.form == "하다" && m.kind == MorphemeKind::Suffix)),
            "{word}"
        );
    }
}

#[test]
fn repeated_dual_class_owners_cannot_borrow_another_owners_verbal_flag() {
    let word = Lemmatizer::new().analyze_word("먹는양하는양하는").unwrap();
    let paths: Vec<_> = word
        .analyses
        .iter()
        .filter(|a| {
            a.lemmas
                .iter()
                .filter(|l| l.text == "양" && l.kind == LemmaKind::Nominal)
                .count()
                == 2
        })
        .collect();
    assert!(!paths.is_empty());
    for path in paths {
        assert!(path.rules.iter().any(|r| r == "suffix.auxiliary.verb.hada"));
        assert!(
            !path
                .rules
                .iter()
                .any(|r| r == "suffix.auxiliary.adjective.hada"),
            "{path:?}"
        );
        assert!(path.breakdown().is_some());
    }
}
