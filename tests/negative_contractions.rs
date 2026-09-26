//! COV-021a: Article 39 negative expansion and the separate confirmation expression.
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
fn article_39_keeps_expanded_groups_and_original_lexical_readings() {
    for (short, full, lemmas, forms) in [
        (
            "거북잖다",
            "거북하지않다",
            vec!["거북하다", "않다"],
            vec!["지", "다"],
        ),
        ("적잖은", "적지않은", vec!["적다", "않다"], vec!["지", "은"]),
        (
            "그렇잖으면",
            "그렇지않으면",
            vec!["그렇다", "않다"],
            vec!["지", "으면"],
        ),
        (
            "만만찮았다",
            "만만하지않았다",
            vec!["만만하다", "않다"],
            vec!["지", "었", "다"],
        ),
        (
            "변변찮다",
            "변변하지않다",
            vec!["변변하다", "않다"],
            vec!["지", "다"],
        ),
        (
            "넉넉잖다",
            "넉넉하지않다",
            vec!["넉넉하다", "않다"],
            vec!["지", "다"],
        ),
        (
            "먹잖아요",
            "먹지않아요",
            vec!["먹다", "않다"],
            vec!["지", "어요"],
        ),
        (
            "먹고싶잖다",
            "먹고싶지않다",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "다"],
        ),
        (
            "먹고싶잖아도",
            "먹고싶지않아도",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "어도"],
        ),
        (
            "먹잖고있다",
            "먹지않고있다",
            vec!["먹다", "않다", "있다"],
            vec!["지", "고", "다"],
        ),
        (
            "학생답잖다",
            "학생답지않다",
            vec!["학생", "않다"],
            vec!["답다", "지", "다"],
        ),
        (
            "적잖음이다",
            "적지않음이다",
            vec!["적다", "않다", "이다"],
            vec!["지", "음", "다"],
        ),
    ] {
        for word in [short, full] {
            let result = Lemmatizer::new().analyze_word(word).unwrap();
            let a = result
                .analyses
                .iter()
                .find(|a| path(a, &lemmas, &forms))
                .expect(word);
            assert!(
                a.lemmas
                    .iter()
                    .any(|l| l.text == "않다" && l.kind == LemmaKind::Auxiliary)
            );
            if word == short {
                assert!(a.rules.iter().any(|r| r == "contraction.negative"));
            }
            assert!(result.analyses.iter().any(|a| a.unchanged));
            assert_eq!(
                result,
                Lemmatizer::new()
                    .analyze_word(&word.nfd().collect::<String>())
                    .unwrap()
            );
            for a in &result.analyses {
                assert!(a.breakdown().is_some(), "{word}: {a:?}");
                assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            }
        }
    }
    for (word, root, ending) in [
        ("적잖은", "적잖다", "은"),
        ("만만찮았다", "만만찮다", "다"),
        ("괜찮아요", "괜찮다", "어요"),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == root
                    && a.morphemes.last().unwrap().form == ending),
            "{word}"
        );
    }
}

#[test]
fn confirmation_expressions_are_separate_from_negative_contractions() {
    for (word, lemmas, forms) in [
        ("먹잖아", vec!["먹다"], vec!["잖아"]),
        ("먹잖아요", vec!["먹다"], vec!["잖아요"]),
        ("먹었잖아요", vec!["먹다"], vec!["었", "잖아요"]),
        ("먹으시겠잖아요", vec!["먹다"], vec!["시", "겠", "잖아요"]),
        ("학생이잖아요", vec!["학생", "이다"], vec!["잖아요"]),
        (
            "먹어봤잖아요",
            vec!["먹다", "보다"],
            vec!["어", "었", "잖아요"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "ending.confirmation"));
        assert!(!a.rules.iter().any(|r| r == "contraction.negative"));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
    }
    for (word, lemmas, forms) in [
        ("거북찮다", vec!["거북하다", "않다"], vec!["지", "다"]),
        ("넉넉찮다", vec!["넉넉하다", "않다"], vec!["지", "다"]),
        ("적쟎은", vec!["적다", "않다"], vec!["지", "은"]),
        ("만만챦다", vec!["만만하다", "않다"], vec!["지", "다"]),
        ("만만잖다", vec!["만만하다", "않다"], vec!["지", "다"]),
        ("먹더잖아요", vec!["먹다"], vec!["더", "잖아요"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
}
