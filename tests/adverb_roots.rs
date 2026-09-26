//! COV-022b: source-listed adverb and repeated nominal bases, not free stripping.
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind};
use unicode_normalization::UnicodeNormalization;

fn path(a: &Analysis, base: &str, kind: LemmaKind, forms: &[&str]) -> bool {
    a.lemmas.len() == 1
        && a.lemmas[0].text == base
        && a.lemmas[0].kind == kind
        && a.morphemes
            .iter()
            .map(|m| m.form.as_str())
            .eq(forms.iter().copied())
        && a.morphemes
            .first()
            .is_some_and(|m| m.kind == MorphemeKind::Suffix)
}

#[test]
fn recorded_source_inventory_has_role_correct_suffix_paths() {
    let inventory: serde_json::Value =
        serde_json::from_str(include_str!("../docs/adverb-root-inventory.json")).unwrap();
    let forms = inventory["forms"].as_array().unwrap();
    assert_eq!(forms.len(), 33);
    let engine = Lemmatizer::new();
    for row in forms {
        let word = row["surface"].as_str().unwrap();
        let kind = serde_json::from_value(row["kind"].clone()).unwrap();
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| {
                path(
                    a,
                    row["base"].as_str().unwrap(),
                    kind,
                    &[row["suffix"].as_str().unwrap()],
                )
            })
            .expect(word);
        assert!(
            a.rules.iter().any(|r| r == row["rule"].as_str().unwrap()),
            "{word}"
        );
        assert_eq!(
            a.breakdown().unwrap(),
            [
                klem::breakdown::Component::Lemma(0),
                klem::breakdown::Component::Morpheme(0)
            ]
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
        assert!(
            result
                .analyses
                .iter()
                .flat_map(|a| &a.rules)
                .all(|r| klem::rule_explanation(r).is_some()),
            "{word}"
        );
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
}

#[test]
fn root_classes_and_shortened_adverbs_compose_with_adverb_particles() {
    for (word, base, kind, forms) in [
        ("더욱이도", "더욱", LemmaKind::Adverbial, vec!["이", "도"]),
        (
            "곰곰이만은",
            "곰곰",
            LemmaKind::Adverbial,
            vec!["이", "만", "은"],
        ),
        ("가만히들", "가만", LemmaKind::Adverbial, vec!["히", "들"]),
        ("낱낱이도", "낱낱", LemmaKind::Nominal, vec!["이", "도"]),
        ("틈틈이요", "틈틈", LemmaKind::Nominal, vec!["이", "요"]),
        ("집집이는", "집집", LemmaKind::Nominal, vec!["이", "는"]),
        ("익히도", "익숙하다", LemmaKind::Predicate, vec!["히", "도"]),
        ("특히는", "특별하다", LemmaKind::Predicate, vec!["히", "는"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, base, kind, &forms))
            .expect(word);
        assert!(
            a.morphemes[1..]
                .iter()
                .all(|m| m.kind == MorphemeKind::Particle)
        );
        assert!(a.breakdown().is_some());
    }
}

#[test]
fn derivations_do_not_invent_verbs_noun_case_paths_or_recursive_reduplication() {
    for word in [
        "곰곰히",
        "더욱히",
        "가만이",
        "낱낱히",
        "집집히",
        "학교학교이",
        "집집집이",
        "틈틈이이",
        "특별시히",
        "익히를",
        "더욱이가",
        "낱낱이를",
        "집집이에서",
        "곰곰이요요",
    ] {
        let r = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !r.analyses.iter().any(|a| a.rules.iter().any(|r| matches!(
                r.as_str(),
                "derivation.adverbial.adverb"
                    | "derivation.adverbial.nominal"
                    | "derivation.adverbial.shortened"
            ))),
            "{word}"
        );
        assert!(r.analyses.iter().any(|a| a.unchanged));
    }
    for (word, nonexistent) in [
        ("특히", "특하다"),
        ("익히", "익하다"),
        ("더욱이", "더욱다"),
        ("낱낱이", "낱낱다"),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text == nonexistent
                    && a.morphemes.iter().any(|m| m.kind == MorphemeKind::Suffix)),
            "{word}"
        );
    }
    // The surface 이 may instead be a subject particle; role-specific alternatives survive.
    let r = Lemmatizer::new().analyze_word("낱낱이").unwrap();
    assert!(r.analyses.iter().any(|a| a.lemmas[0].text == "낱낱"
        && a.morphemes.len() == 1
        && a.morphemes[0].kind == MorphemeKind::Particle));
}
