//! COV-019d: known left classes before expressive -어 하다.
use klem::{Analysis, Lemmatizer};
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
fn expressive_hada_keeps_adjectives_negatives_and_unclassified_heads() {
    for (word, lemmas, forms) in [
        (
            "먹고싶어한다",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "어", "는다"],
        ),
        (
            "먹고싶어해요",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "어", "어요"],
        ),
        (
            "먹고싶어도한다",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "어", "도", "는다"],
        ),
        (
            "먹고싶지않아해요",
            vec!["먹다", "싶다", "않다", "하다"],
            vec!["고", "지", "어", "어요"],
        ),
        (
            "먹고싶지는않아해요",
            vec!["먹다", "싶다", "않다", "하다"],
            vec!["고", "지", "는", "어", "어요"],
        ),
        (
            "먹고싶잖아해요",
            vec!["먹다", "싶다", "않다", "하다"],
            vec!["고", "지", "어", "어요"],
        ),
        (
            "먹고싶지못해해요",
            vec!["먹다", "싶다", "못하다", "하다"],
            vec!["고", "지", "어", "어요"],
        ),
        (
            "먹고싶어해본다",
            vec!["먹다", "싶다", "하다", "보다"],
            vec!["고", "어", "어", "는다"],
        ),
        (
            "먹나봐해요",
            vec!["먹다", "보다", "하다"],
            vec!["나", "어", "어요"],
        ),
        (
            "학생다워해요",
            vec!["학생", "하다"],
            vec!["답다", "어", "어요"],
        ),
        (
            "학생이고싶다",
            vec!["학생", "이다", "싶다"],
            vec!["고", "다"],
        ),
        ("먹어하다", vec!["먹다", "하다"], vec!["어", "다"]),
        ("좋아한다", vec!["좋다", "하다"], vec!["어", "는다"]),
    ] {
        let engine = Lemmatizer::new();
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
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
fn expressive_hada_rejects_known_verbs_copulas_and_inherited_classes() {
    for (word, lemmas, forms) in [
        (
            "먹어봐해요",
            vec!["먹다", "보다", "하다"],
            vec!["어", "어", "어요"],
        ),
        (
            "먹어봐도한다",
            vec!["먹다", "보다", "하다"],
            vec!["어", "어", "도", "는다"],
        ),
        (
            "먹고있어해요",
            vec!["먹다", "있다", "하다"],
            vec!["고", "어", "어요"],
        ),
        (
            "먹고계셔해요",
            vec!["먹다", "계시다", "하다"],
            vec!["고", "어", "어요"],
        ),
        (
            "학생이어해요",
            vec!["학생", "이다", "하다"],
            vec!["어", "어요"],
        ),
        (
            "학생이었어해요",
            vec!["학생", "이다", "하다"],
            vec!["었", "어", "어요"],
        ),
        (
            "먹기이어해요",
            vec!["먹다", "이다", "하다"],
            vec!["기", "어", "어요"],
        ),
        (
            "학생답게해해요",
            vec!["학생", "하다", "하다"],
            vec!["답다", "게", "어", "어요"],
        ),
        (
            "먹어보지않아해요",
            vec!["먹다", "보다", "않다", "하다"],
            vec!["어", "지", "어", "어요"],
        ),
        (
            "먹어보지는않아해요",
            vec!["먹다", "보다", "않다", "하다"],
            vec!["어", "지", "는", "어", "어요"],
        ),
        (
            "먹어보잖아해요",
            vec!["먹다", "보다", "않다", "하다"],
            vec!["어", "지", "어", "어요"],
        ),
        (
            "먹어보지아니해해요",
            vec!["먹다", "보다", "아니하다", "하다"],
            vec!["어", "지", "어", "어요"],
        ),
        (
            "먹어보지못해해요",
            vec!["먹다", "보다", "못하다", "하다"],
            vec!["어", "지", "어", "어요"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
