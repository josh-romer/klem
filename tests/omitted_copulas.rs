//! COV-020c: reviewed omitted-copula endings and colloquial 거 alternatives.
use klem::{Analysis, LemmaKind, Lemmatizer};
use unicode_normalization::UnicodeNormalization;

fn path(a: &Analysis, lemmas: &[&str], forms: &[&str]) -> bool {
    a.lemmas
        .iter()
        .map(|l| l.text.as_str())
        .eq(lemmas.iter().copied())
        && a.morphemes
            .iter()
            .map(|m| m.form.as_str())
            .eq(forms.iter().copied())
}

#[test]
fn omitted_copulas_keep_short_and_expanded_nominals_with_ordered_endings() {
    let engine = Lemmatizer::new();
    for (word, bases, forms) in [
        ("겁니다", vec!["거", "것"], vec!["습니다"]),
        ("겁니까", vec!["거", "것"], vec!["습니까"]),
        ("건데", vec!["거", "것"], vec!["은데"]),
        ("건데요", vec!["거", "것"], vec!["은데", "요"]),
        ("거지", vec!["거", "것"], vec!["지"]),
        ("거지요", vec!["거", "것"], vec!["지요"]),
        ("거죠", vec!["거", "것"], vec!["죠"]),
        ("거면", vec!["거", "것"], vec!["으면"]),
        ("이겁니다", vec!["이거", "이것"], vec!["습니다"]),
        ("그건데", vec!["그거", "그것"], vec!["은데"]),
        ("저거죠", vec!["저거", "저것"], vec!["죠"]),
        ("의삽니다", vec!["의사"], vec!["습니다"]),
        ("학교죠", vec!["학교"], vec!["죠"]),
        ("의산데", vec!["의사"], vec!["은데"]),
        ("의사면", vec!["의사"], vec!["으면"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        for base in bases {
            let a = result
                .analyses
                .iter()
                .find(|a| path(a, &[base, "이다"], &forms))
                .expect(word);
            assert_eq!(a.lemmas[0].kind, LemmaKind::Nominal);
            assert_eq!(a.lemmas[1].kind, LemmaKind::Copula);
            assert!(a.rules.iter().any(|r| r == "copula.omitted_ending"));
            if base.ends_with('것') {
                assert!(a.rules.iter().any(|r| r == "nominal.colloquial_geot"));
            }
        }
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert!(
            result
                .analyses
                .iter()
                .flat_map(|a| &a.rules)
                .all(|r| klem::rule_explanation(r).is_some())
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
}

#[test]
fn omitted_copulas_compose_with_nominalizations_auxiliaries_and_outer_particles() {
    for (word, lemmas, forms) in [
        ("먹긴데", vec!["먹다", "이다"], vec!["기", "은데"]),
        (
            "먹어보긴데",
            vec!["먹다", "보다", "이다"],
            vec!["어", "기", "은데"],
        ),
        ("거지않다", vec!["것", "이다", "않다"], vec!["지", "다"]),
        ("겁니다만", vec!["것", "이다"], vec!["습니다", "만"]),
        ("거면요", vec!["것", "이다"], vec!["으면", "요"]),
        ("거입니다", vec!["것", "이다"], vec!["습니다"]),
        ("거예요", vec!["것", "이다"], vec!["에요"]),
        ("거였다", vec!["것", "이다"], vec!["었", "다"]),
        ("그거라면", vec!["그것", "이다"], vec!["라면"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
    }
}

#[test]
fn omission_does_not_conjugate_nominals_or_expand_arbitrary_geo_words() {
    for (word, lemmas, forms) in [
        ("학생죠", vec!["학생", "이다"], vec!["죠"]),
        ("학생면", vec!["학생", "이다"], vec!["으면"]),
        ("학생데", vec!["학생", "이다"], vec!["은데"]),
        ("거니다", vec!["거", "이다"], vec!["습니다"]),
        ("의사는다", vec!["의사", "이다"], vec!["는다"]),
        ("먹었죠", vec!["먹", "이다"], vec!["었", "죠"]),
        ("도운데", vec!["돕", "이다"], vec!["은데"]),
        ("살면", vec!["살", "이다"], vec!["으면"]),
        ("학교죠", vec!["학교이다"], vec!["죠"]),
        ("자전거죠", vec!["자전것", "이다"], vec!["죠"]),
        ("거들입니다", vec!["것", "이다"], vec!["들", "습니다"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    let result = Lemmatizer::new().analyze_word("ABC죠").unwrap();
    let a = result
        .analyses
        .iter()
        .find(|a| path(a, &["ABC", "이다"], &["죠"]))
        .unwrap();
    assert!(a.rules.iter().any(|r| r == "pronunciation.assumed_vowel"));
    let result = Lemmatizer::new().analyze_word("거지").unwrap();
    assert!(
        result
            .analyses
            .iter()
            .any(|a| a.unchanged && a.lemmas[0].text == "거지")
    );
}
