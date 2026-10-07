#[path = "deoniman_support/parent.rs"]
mod deoniman_parent;
#[path = "support/literary_ri_prefinal_history.rs"]
mod ri_history;
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind, WordAnalysis};
use serde_json::Value;
use std::{path::PathBuf, sync::OnceLock};
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/hada_nominal_preservation.rs"]
mod historical;
#[path = "../tools/validity.rs"]
mod validity;

fn source() -> &'static Value {
    static SOURCE: OnceLock<Value> = OnceLock::new();
    SOURCE.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/friendly-command-sources.json")).unwrap()
    })
}
fn command(a: &Analysis) -> bool {
    a.rules.iter().any(|r| r == "ending.friendly_command.n")
}
#[test]
fn original_command_examples_preserve_adnominals_and_unicode() {
    let engine = Lemmatizer::new();
    for (word, head) in [
        ("온", "오다"),
        ("날아온", "날아오다"),
        ("내려온", "내려오다"),
        ("돌아온", "돌아오다"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| command(a)
            && a.lemmas.len() == 1
            && a.lemmas[0].text == head
            && a.morphemes.len() == 1
            && a.morphemes[0].form == "ㄴ"
            && a.morphemes[0].kind == MorphemeKind::Ending));
        assert!(result.analyses.iter().any(|a| a.lemmas.len() == 1
            && a.lemmas[0].text == head
            && a.morphemes.len() == 1
            && a.morphemes[0].form == "은"));
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for a in result.analyses.iter().filter(|a| command(a)) {
            assert!(a.breakdown().is_some(), "{word}: {a:?}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}
#[test]
fn source_stem_boundary_and_unreviewed_prefinal_controls() {
    let engine = Lemmatizer::new();
    for word in ["간", "먹은", "좋은", "학생인"] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(command),
            "{word}"
        );
    }
    // These controls describe the implemented bare-stem scope. They do not
    // pronounce unlisted prefinals linguistically impossible.
    for word in ["오신", "오셨던", "왔던", "오는", "올", "와요"] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(command),
            "{word}"
        );
    }
}
#[test]
fn frozen_source_orders_are_retained_and_new_paths_have_exact_parents() {
    let engine = Lemmatizer::new();
    let before = source()["before_analyses"].as_object().unwrap();
    assert_eq!(before.len(), 4794);
    for (word, old) in before {
        let old: WordAnalysis = serde_json::from_value(old.clone()).unwrap();
        let new = engine.analyze_word(word).unwrap();
        let retained: Vec<_> = new
            .analyses
            .iter()
            .filter(|a| old.analyses.contains(a))
            .cloned()
            .collect();
        assert_eq!(retained, old.analyses, "{word}");
        for a in new.analyses.iter().filter(|a| !old.analyses.contains(a)) {
            if a.rules.iter().any(|r| r == "prefinal.conjectural_ni") {
                ri_history::assert_addition(
                    "tests/fixtures/friendly-command-sources.json",
                    word,
                    a,
                );
                continue;
            }
            if a.rules
                .iter()
                .any(|r| matches!(r.as_str(), "ending.deoniman" | "ending.reported_deoni"))
            {
                deoniman_parent::assert_report_parent(word, a);
                continue;
            }
            assert!(command(a), "unattributed {word}: {a:?}");
            assert!(a.breakdown().is_some(), "unordered {word}: {a:?}");
            let mut parent = a.clone();
            parent.rules.retain(|r| r != "ending.friendly_command.n");
            let ending = parent
                .morphemes
                .iter_mut()
                .rev()
                .find(|m| m.kind == MorphemeKind::Ending)
                .unwrap();
            assert_eq!(ending.form, "ㄴ");
            ending.form = "은".into();
            assert!(
                old.analyses.contains(&parent),
                "missing exact parent {word}: {a:?}"
            );
        }
    }
}
#[test]
fn complete_native_import_and_conditional_auxiliary_assessment() {
    use klem::dictionary::{
        Compatibility, Dictionary, DictionarySession, SqliteDictionary, import_krdict,
    };
    let path =
        std::env::temp_dir().join(format!("klem-friendly-command-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = std::fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-friendly-command-english.json",
        )],
        &path,
        "friendly-command-source",
    )
    .unwrap();
    let dictionary = SqliteDictionary::open(path).unwrap();
    let native = source()["complete_native_entries"].as_object().unwrap();
    assert_eq!(native.len(), 60);
    for (id, original) in native {
        let mut expected = original.clone();
        for sense in expected["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(dictionary.entry(id).unwrap().unwrap()).unwrap(),
            expected,
            "{id}"
        );
    }
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 1048576);
    for word in ["온", "날아온", "내려온", "돌아온"] {
        let result = engine.analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        for (i, a) in result
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, a)| command(a))
        {
            let owner = a.lemmas.len() - 1;
            let assessment = annotation.readings[i]
                .lemmas
                .iter()
                .find(|l| l.lemma_index == owner)
                .unwrap();
            if a.lemmas[owner].kind == LemmaKind::Auxiliary {
                assert_eq!(assessment.status, Compatibility::Unknown, "{word}: {a:?}");
            } else {
                assert_eq!(
                    assessment.status,
                    Compatibility::Compatible,
                    "{word}: {a:?}"
                );
            }
        }
    }
}
#[test]
fn command_breakdown_checks_immediate_owner_and_provenance() {
    let original = Lemmatizer::new()
        .analyze_word("온")
        .unwrap()
        .analyses
        .into_iter()
        .find(command)
        .unwrap();
    for kind in [LemmaKind::Nominal, LemmaKind::Copula, LemmaKind::Adverbial] {
        let mut a = original.clone();
        a.lemmas[0].kind = kind;
        assert!(a.breakdown().is_none());
    }
    let mut a = original.clone();
    a.lemmas[0].text = "가다".into();
    assert!(a.breakdown().is_none());
    let mut a = original.clone();
    a.morphemes[0].kind = MorphemeKind::Particle;
    assert!(a.breakdown().is_none());
    let mut a = original.clone();
    a.morphemes[0].form = "은".into();
    assert!(a.breakdown().is_none());
    let mut a = original.clone();
    a.morphemes.insert(
        0,
        klem::Morpheme {
            form: "시".into(),
            kind: MorphemeKind::Prefinal,
        },
    );
    assert!(a.breakdown().is_none());
    let mut a = original.clone();
    a.morphemes.push(a.morphemes[0].clone());
    assert!(a.breakdown().is_none());
    let mut a = original.clone();
    a.lemmas.push(klem::Lemma {
        text: "하다".into(),
        kind: LemmaKind::Auxiliary,
    });
    a.morphemes.push(klem::Morpheme {
        form: "다".into(),
        kind: MorphemeKind::Ending,
    });
    assert!(a.breakdown().is_none());
    // Existing adnominal ㄴ in finite noun formation has no command marker.
    for word in ["못난이", "흰둥이"] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .filter(|a| a.rules.iter().any(|r| r == "derivation.nominal.adnominal"))
                .all(|a| !command(a) && a.breakdown().is_some())
        );
    }
}
#[test]
fn individual_source_judgments() {
    let fixture = source();
    let suite: validity::Suite = serde_json::from_value(serde_json::json!({"schema_version":1,"review_status":"Source-backed agent judgments; independent review pending.","sources":fixture["sources"],"cases":fixture["cases"]})).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (4, 3));
}

#[test]
fn historical_preservation_proves_command_parents_and_rejects_corruption() {
    let frozen: WordAnalysis =
        serde_json::from_value(source()["before_analyses"]["살아온"].clone()).unwrap();
    let actual = Lemmatizer::new().analyze_word("살아온").unwrap();
    historical::assert_preserved(&actual, &frozen);
    let mut lost = actual.clone();
    lost.analyses.retain(|a| a != &frozen.analyses[0]);
    assert!(std::panic::catch_unwind(|| historical::assert_preserved(&lost, &frozen)).is_err());
    let mut unowned = actual.clone();
    unowned
        .analyses
        .iter_mut()
        .find(|a| command(a))
        .unwrap()
        .rules
        .push("unreviewed.command".into());
    assert!(std::panic::catch_unwind(|| historical::assert_preserved(&unowned, &frozen)).is_err());
}
