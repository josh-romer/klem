//! COV-017n: causal -기에/-길래 versus nominalization -기 + 에.
use klem::{Analysis, Lemmatizer, MorphemeKind};
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
fn causal_endings_preserve_prefinals_copulas_auxiliaries_and_nominalization() {
    for (word, lemmas, forms) in [
        ("추천하길래", vec!["추천하다"], vec!["길래"]),
        ("뽑길래", vec!["뽑다"], vec!["길래"]),
        ("먹기에", vec!["먹다"], vec!["기에"]),
        ("살길래", vec!["살다"], vec!["길래"]),
        ("살기에", vec!["살다"], vec!["기에"]),
        ("듣길래", vec!["듣다"], vec!["길래"]),
        ("돕기에", vec!["돕다"], vec!["기에"]),
        ("좋길래", vec!["좋다"], vec!["길래"]),
        ("먹었기에", vec!["먹다"], vec!["었", "기에"]),
        ("먹겠기에", vec!["먹다"], vec!["겠", "기에"]),
        ("먹어야겠기에", vec!["먹다"], vec!["어야겠", "기에"]),
        ("들으셨길래", vec!["듣다"], vec!["시", "었", "길래"]),
        ("먹으셨었기에", vec!["먹다"], vec!["시", "었", "었", "기에"]),
        ("학생이기에", vec!["학생", "이다"], vec!["기에"]),
        ("의사이길래", vec!["의사", "이다"], vec!["길래"]),
        (
            "학생이셨길래",
            vec!["학생", "이다"],
            vec!["시", "었", "길래"],
        ),
        ("아니길래", vec!["아니다"], vec!["길래"]),
        ("먹어봤길래", vec!["먹다", "보다"], vec!["어", "었", "길래"]),
        ("먹고싶기에", vec!["먹다", "싶다"], vec!["고", "기에"]),
        ("먹지않길래", vec!["먹다", "않다"], vec!["지", "길래"]),
        ("학생답기에", vec!["학생"], vec!["답다", "기에"]),
        ("학생답길래", vec!["학생"], vec!["답다", "길래"]),
    ] {
        let engine = Lemmatizer::new();
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending.causal"), "{word}");
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    for word in ["먹기에", "학생이기에", "먹었기에"] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| a.morphemes.ends_with(&[
                klem::Morpheme {
                    form: "기".into(),
                    kind: MorphemeKind::Ending
                },
                klem::Morpheme {
                    form: "에".into(),
                    kind: MorphemeKind::Particle
                },
            ])),
            "{word}"
        );
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.morphemes.last().is_some_and(|m| m.form == "기에"))
        );
    }
}

#[test]
fn causal_endings_reject_unlicensed_prefinals_and_vowel_recoveries() {
    for (word, lemmas, forms) in [
        ("먹겠길래", vec!["먹다"], vec!["겠", "길래"]),
        ("먹어야겠길래", vec!["먹다"], vec!["어야겠", "길래"]),
        ("먹더길래", vec!["먹다"], vec!["더", "길래"]),
        ("먹더기에", vec!["먹다"], vec!["더", "기에"]),
        ("들길래", vec!["듣다"], vec!["길래"]),
        ("도우기에", vec!["돕다"], vec!["기에"]),
        ("가까우길래", vec!["가깝다"], vec!["길래"]),
        ("사길래", vec!["살다"], vec!["길래"]),
        ("학생다우기에", vec!["학생"], vec!["답다", "기에"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    // These endings do not themselves license auxiliaries or nominal case particles.
    for word in ["먹기에보다", "먹길래보다", "먹길래를"] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "ending.causal")),
            "{word}"
        );
    }
}
