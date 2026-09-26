//! COV-017o: source-listed reported alternatives, without implicit 하다 lemmas.
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
fn reported_alternatives_preserve_allomorphs_prefinals_and_composition() {
    for (word, lemmas, forms) in [
        ("된다거나", vec!["되다"], vec!["는다거나"]),
        ("해방시킨다거나", vec!["해방시키다"], vec!["는다거나"]),
        ("경시한다든가", vec!["경시하다"], vec!["는다든가"]),
        ("세련되었다든가", vec!["세련되다"], vec!["었", "다든가"]),
        ("먹는다거나", vec!["먹다"], vec!["는다거나"]),
        ("먹는다든가", vec!["먹다"], vec!["는다든가"]),
        ("산다거나", vec!["살다"], vec!["는다거나"]),
        ("산다든가", vec!["살다"], vec!["는다든가"]),
        ("먹으신다거나", vec!["먹다"], vec!["시", "는다거나"]),
        ("먹으신다든가", vec!["먹다"], vec!["시", "는다든가"]),
        ("먹었다거나", vec!["먹다"], vec!["었", "다거나"]),
        ("먹겠다거나", vec!["먹다"], vec!["겠", "다거나"]),
        ("먹겠다든가", vec!["먹다"], vec!["겠", "다든가"]),
        ("먹어야겠다거나", vec!["먹다"], vec!["어야겠", "다거나"]),
        ("좋다거나", vec!["좋다"], vec!["다거나"]),
        ("좋으시다든가", vec!["좋다"], vec!["시", "다든가"]),
        (
            "먹고싶으시다거나",
            vec!["먹다", "싶다"],
            vec!["고", "시", "다거나"],
        ),
        ("학생이시라든가", vec!["학생", "이다"], vec!["시", "라든가"]),
        (
            "학생다우시다든가",
            vec!["학생"],
            vec!["답다", "시", "다든가"],
        ),
        ("학생이라거나", vec!["학생", "이다"], vec!["라거나"]),
        ("교사라거나", vec!["교사", "이다"], vec!["라거나"]),
        ("아니라거나", vec!["아니다"], vec!["라거나"]),
        ("학생이라든가", vec!["학생", "이다"], vec!["라든가"]),
        ("교사라든가", vec!["교사", "이다"], vec!["라든가"]),
        ("아니라든가", vec!["아니다"], vec!["라든가"]),
        (
            "학생이셨다든가",
            vec!["학생", "이다"],
            vec!["시", "었", "다든가"],
        ),
        ("먹으시라든가", vec!["먹다"], vec!["시", "라든가"]),
        ("먹었더라든가", vec!["먹다"], vec!["었", "더", "라든가"]),
        ("먹으리라든가", vec!["먹다"], vec!["으리", "라든가"]),
        ("가라거나", vec!["가다"], vec!["으라거나"]),
        ("살라거나", vec!["살다"], vec!["으라거나"]),
        ("먹으라거나", vec!["먹다"], vec!["으라거나"]),
        ("들으라거나", vec!["듣다"], vec!["으라거나"]),
        ("도우라거나", vec!["돕다"], vec!["으라거나"]),
        ("먹으시라거나", vec!["먹다"], vec!["시", "으라거나"]),
        ("먹자거나", vec!["먹다"], vec!["자거나"]),
        ("살자거나", vec!["살다"], vec!["자거나"]),
        ("먹어본다거나", vec!["먹다", "보다"], vec!["어", "는다거나"]),
        ("먹고싶다든가", vec!["먹다", "싶다"], vec!["고", "다든가"]),
        ("먹어보자거나", vec!["먹다", "보다"], vec!["어", "자거나"]),
        ("먹어보라거나", vec!["먹다", "보다"], vec!["어", "으라거나"]),
        ("학생답다거나", vec!["학생"], vec!["답다", "다거나"]),
        ("학생답다든가", vec!["학생"], vec!["답다", "다든가"]),
    ] {
        let engine = Lemmatizer::new();
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(
            a.rules.iter().any(|r| r == "ending.quoted_alternative"),
            "{word}"
        );
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
}

#[test]
fn reported_alternatives_reject_wrong_boundaries_classes_and_prefinals() {
    for (word, lemmas, forms) in [
        ("가는다거나", vec!["가다"], vec!["는다거나"]),
        ("살는다든가", vec!["살다"], vec!["는다든가"]),
        ("도운다거나", vec!["돕다"], vec!["는다거나"]),
        ("먹었는다거나", vec!["먹다"], vec!["었", "는다거나"]),
        ("먹겠는다든가", vec!["먹다"], vec!["겠", "는다든가"]),
        ("먹더다거나", vec!["먹다"], vec!["더", "다거나"]),
        ("먹더다든가", vec!["먹다"], vec!["더", "다든가"]),
        ("먹었으라거나", vec!["먹다"], vec!["었", "으라거나"]),
        ("먹겠자거나", vec!["먹다"], vec!["겠", "자거나"]),
        ("먹었라든가", vec!["먹다"], vec!["었", "라든가"]),
        ("먹겠라든가", vec!["먹다"], vec!["겠", "라든가"]),
        ("먹라거나", vec!["먹다"], vec!["으라거나"]),
        ("가으라거나", vec!["가다"], vec!["으라거나"]),
        (
            "먹고싶는다거나",
            vec!["먹다", "싶다"],
            vec!["고", "는다거나"],
        ),
        ("먹고싶자거나", vec!["먹다", "싶다"], vec!["고", "자거나"]),
        (
            "먹고싶으라거나",
            vec!["먹다", "싶다"],
            vec!["고", "으라거나"],
        ),
        ("먹어보다거나", vec!["먹다", "보다"], vec!["어", "다거나"]),
        ("학생이자거나", vec!["학생", "이다"], vec!["자거나"]),
        (
            "먹고싶으신다거나",
            vec!["먹다", "싶다"],
            vec!["고", "시", "는다거나"],
        ),
        (
            "학생이신다든가",
            vec!["학생", "이다"],
            vec!["시", "는다든가"],
        ),
        (
            "학생다우신다거나",
            vec!["학생"],
            vec!["답다", "시", "는다거나"],
        ),
        ("학생이라거나", vec!["학생", "이다"], vec!["으라거나"]),
        ("학생이다거나", vec!["학생", "이다"], vec!["다거나"]),
        ("학생답는다든가", vec!["학생"], vec!["답다", "는다든가"]),
        ("학생다우라거나", vec!["학생"], vec!["답다", "으라거나"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    for word in ["먹는다거나보다", "먹자거나를", "학생이라든가보다"] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "ending.quoted_alternative")),
            "{word}"
        );
    }
}
