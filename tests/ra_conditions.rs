//! COV-017aj/018r/020k: conditional/concessive 라 homonyms.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite.cases.retain(|c| c.id.starts_with("ra-conditions-"));
    suite
}

#[test]
fn ra_conditions_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (47, 26));
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let result = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            result,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for a in result.analyses {
            assert!(a.breakdown().is_some(), "{}: {a:?}", case.surface);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn ra_conditions_dictionary_filters_preserve_roles_and_cli_parity() {
    let path = std::env::temp_dir().join(format!("klem-ra_conditions-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-ra-conditions.json")],
        &path,
        "ra_conditions",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let report = validity::evaluate_with(&suite(), |word| {
            let mut analysis = engine.analyze_word(word).unwrap();
            let mut annotation = dictionary.annotate(&analysis).unwrap();
            annotation.filter(&mut analysis, policy);
            let cli = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", word, "--dictionary"])
                .arg(&path)
                .arg(flag)
                .output()
                .unwrap();
            assert!(
                cli.status.success(),
                "{}",
                String::from_utf8_lossy(&cli.stderr)
            );
            let value: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                analysis
            );
            assert_eq!(
                value["dictionary"],
                serde_json::to_value(&annotation).unwrap()
            );
            assert!(dictionary.cache_bytes() <= 4096);
            Ok(analysis)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
    }
}

#[test]
fn annotated_ra_conditions_keep_particle_and_copula_groups() {
    let source = include_str!("fixtures/kaist-ra-conditions.conllu");
    assert_eq!(source.matches("# sent_id =").count(), 3);
    let engine = Lemmatizer::new();
    for (surface, gold, lemmas, kinds, forms, morph_kinds) in [
        (
            "교양만이라도",
            "교양+만+이+라+도",
            vec!["교양", "이다"],
            vec!["nominal", "copula"],
            vec!["만", "라", "도"],
            vec!["particle", "ending", "particle"],
        ),
        (
            "꽃다발이라야",
            "꽃다발+이라야",
            vec!["꽃다발"],
            vec!["nominal"],
            vec!["이라야"],
            vec!["particle"],
        ),
        (
            "것이라야만",
            "것+이+라야+만",
            vec!["것", "이다"],
            vec!["nominal", "copula"],
            vec!["라야", "만"],
            vec!["ending", "particle"],
        ),
    ] {
        assert!(
            source
                .lines()
                .any(|l| l.contains(&format!("\t{surface}\t{gold}\t")))
        );
        let word = engine.analyze_word(surface).unwrap();
        assert!(
            word.analyses.iter().any(|a| {
                let v = serde_json::to_value(a).unwrap();
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && v["lemmas"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|l| l["kind"].as_str().unwrap())
                        .eq(kinds.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
                    && v["morphemes"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|m| m["kind"].as_str().unwrap())
                        .eq(morph_kinds.iter().copied())
            }),
            "{surface}"
        );
    }
}

#[test]
fn ra_conditions_do_not_merge_roles_or_reorder_compounds() {
    let engine = Lemmatizer::new();
    for surface in ["휴가라야만", "것이라야만"] {
        let word = engine.analyze_word(surface).unwrap();
        let mut checked = 0;
        for a in &word.analyses {
            let Some(slot) = a.morphemes.iter().position(|m| {
                m.kind == klem::MorphemeKind::Particle
                    && matches!(m.form.as_str(), "이라야만" | "라야만")
            }) else {
                continue;
            };
            let mut split = a.clone();
            let form = split.morphemes[slot]
                .form
                .strip_suffix('만')
                .unwrap()
                .to_owned();
            split.morphemes.splice(
                slot..=slot,
                [
                    klem::Morpheme {
                        form,
                        kind: klem::MorphemeKind::Particle,
                    },
                    klem::Morpheme {
                        form: "만".into(),
                        kind: klem::MorphemeKind::Particle,
                    },
                ],
            );
            assert!(
                word.analyses
                    .iter()
                    .any(|b| b.lemmas == split.lemmas && b.morphemes == split.morphemes)
            );
            checked += 1;
        }
        assert!(checked > 0);
        assert!(
            word.analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.kind == klem::LemmaKind::Copula))
        );
    }
    let word = engine.analyze_word("먹으라도").unwrap();
    assert!(!word.analyses.iter().any(|a| {
        a.lemmas.len() == 1
            && a.lemmas[0].text == "먹다"
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["으라", "도"])
    }));
    for surface in ["Alex라야", "Alex이라야", "쀍이라야", "쀍이라야만"] {
        assert!(
            engine
                .analyze_word(surface)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.unchanged)
        );
    }
}

#[test]
fn gsd_ra_condition_observation_preserves_both_analyses() {
    let source = include_str!("fixtures/gsd-ra-conditions.conllu");
    assert_eq!(source.matches("# sent_id =").count(), 1);
    assert!(source.contains("\t자전거도로라도\t자전거+도로+이+라도\tNOUN\tNNG+NNG+VCP+EC\t"));
    // The corpus adapter joins adjacent nominal pieces. Matching its copula
    // annotation does not establish that copular syntax is intended here.
    let word = Lemmatizer::new().analyze_word("자전거도로라도").unwrap();
    assert!(word.analyses.iter().any(|a| a.lemmas.len() == 2
        && a.lemmas[0].text == "자전거도로"
        && a.lemmas[1].kind == klem::LemmaKind::Copula
        && a.morphemes.iter().map(|m| m.form.as_str()).eq(["라도"])));
    assert!(word.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "자전거도로"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "라도"
        && a.morphemes[0].kind == klem::MorphemeKind::Particle));
}
