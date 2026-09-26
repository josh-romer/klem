//! COV-017u: lexical 놓아 -> 놔 contraction, not general ㅎ deletion.
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
fn noh_contraction_preserves_full_forms_tense_compounds_and_auxiliaries() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &str, &[&str], &[&str])] = &[
        ("놔", "놓아", &["놓다"], &["어"]),
        ("놔요", "놓아요", &["놓다"], &["어요"]),
        ("놔서", "놓아서", &["놓다"], &["어서"]),
        ("놔라", "놓아라", &["놓다"], &["어라"]),
        ("놔도", "놓아도", &["놓다"], &["어도"]),
        ("놔야", "놓아야", &["놓다"], &["어야"]),
        ("놔야겠다", "놓아야겠다", &["놓다"], &["어야겠", "다"]),
        ("놨다", "놓았다", &["놓다"], &["었", "다"]),
        ("놨었지요", "놓았었지요", &["놓다"], &["었", "었", "지요"]),
        ("내놔", "내놓아", &["내놓다"], &["어"]),
        ("내놔요", "내놓아요", &["내놓다"], &["어요"]),
        ("내놔서", "내놓아서", &["내놓다"], &["어서"]),
        ("내놔라", "내놓아라", &["내놓다"], &["어라"]),
        ("내놔도", "내놓아도", &["내놓다"], &["어도"]),
        ("내놔야", "내놓아야", &["내놓다"], &["어야"]),
        ("내놔야겠다", "내놓아야겠다", &["내놓다"], &["어야겠", "다"]),
        ("내놨다", "내놓았다", &["내놓다"], &["었", "다"]),
        (
            "내놨었지요",
            "내놓았었지요",
            &["내놓다"],
            &["었", "었", "지요"],
        ),
        ("내려놔", "내려놓아", &["내려놓다"], &["어"]),
        ("내려놔요", "내려놓아요", &["내려놓다"], &["어요"]),
        ("내려놔서", "내려놓아서", &["내려놓다"], &["어서"]),
        ("내려놔라", "내려놓아라", &["내려놓다"], &["어라"]),
        ("내려놔도", "내려놓아도", &["내려놓다"], &["어도"]),
        ("내려놔야", "내려놓아야", &["내려놓다"], &["어야"]),
        (
            "내려놔야겠다",
            "내려놓아야겠다",
            &["내려놓다"],
            &["어야겠", "다"],
        ),
        ("내려놨다", "내려놓았다", &["내려놓다"], &["었", "다"]),
        (
            "내려놨었지요",
            "내려놓았었지요",
            &["내려놓다"],
            &["었", "었", "지요"],
        ),
        ("풀어놔", "풀어놓아", &["풀어놓다"], &["어"]),
        ("풀어놔요", "풀어놓아요", &["풀어놓다"], &["어요"]),
        ("풀어놔서", "풀어놓아서", &["풀어놓다"], &["어서"]),
        ("풀어놔라", "풀어놓아라", &["풀어놓다"], &["어라"]),
        ("풀어놔도", "풀어놓아도", &["풀어놓다"], &["어도"]),
        ("풀어놔야", "풀어놓아야", &["풀어놓다"], &["어야"]),
        (
            "풀어놔야겠다",
            "풀어놓아야겠다",
            &["풀어놓다"],
            &["어야겠", "다"],
        ),
        ("풀어놨다", "풀어놓았다", &["풀어놓다"], &["었", "다"]),
        (
            "풀어놨었지요",
            "풀어놓았었지요",
            &["풀어놓다"],
            &["었", "었", "지요"],
        ),
        (
            "먹어놨다",
            "먹어놓았다",
            &["먹다", "놓다"],
            &["어", "었", "다"],
        ),
        (
            "적어놔두었다",
            "적어놓아두었다",
            &["적다", "놓다", "두다"],
            &["어", "어", "었", "다"],
        ),
        (
            "놔두었다",
            "놓아두었다",
            &["놓다", "두다"],
            &["어", "었", "다"],
        ),
        ("좋아놔서", "좋아놓아서", &["좋다", "놓다"], &["어", "어서"]),
        (
            "학생이어놔서",
            "학생이어놓아서",
            &["학생", "이다", "놓다"],
            &["어", "어서"],
        ),
        ("놨겠지요", "놓았겠지요", &["놓다"], &["었", "겠", "지요"]),
        ("놨어도", "놓았어도", &["놓다"], &["었", "어도"]),
        ("놔서는", "놓아서는", &["놓다"], &["어서는"]),
        ("놔서도", "놓아서도", &["놓다"], &["어서도"]),
        (
            "놔보았다",
            "놓아보았다",
            &["놓다", "보다"],
            &["어", "었", "다"],
        ),
        (
            "놔버렸다",
            "놓아버렸다",
            &["놓다", "버리다"],
            &["어", "었", "다"],
        ),
        ("놔야만", "놓아야만", &["놓다"], &["어야", "만"]),
    ];
    for &(word, full_word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        let full = engine.analyze_word(full_word).unwrap();
        let candidate = result
            .analyses
            .iter()
            .find(|a| path(a, lemmas, forms))
            .expect(word);
        assert!(candidate.rules.iter().any(|r| r == "contraction.noh"));
        assert!(
            full.analyses
                .iter()
                .any(|a| a.lemmas == candidate.lemmas && a.morphemes == candidate.morphemes),
            "{word}: {candidate:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert!(
            result
                .analyses
                .iter()
                .flat_map(|a| &a.rules)
                .all(|r| klem::rule_explanation(r).is_some())
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
fn noh_contraction_requires_aeo_and_does_not_generalize_hieut_deletion() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("좌", &["좋다"], &["어"]),
        ("좌요", &["좋다"], &["어요"]),
        ("좠다", &["좋다"], &["었", "다"]),
        ("노아", &["놓다"], &["어"]),
        ("노았다", &["놓다"], &["었", "다"]),
        ("놔다", &["놓다"], &["다"]),
        ("놔고", &["놓다"], &["고"]),
        ("놔는", &["놓다"], &["는"]),
        ("놔으니", &["놓다"], &["으니"]),
        ("놔었다", &["놓다"], &["었", "다"]),
        ("놰", &["놓다"], &["어"]),
        ("놓어", &["놓다"], &["어"]),
        ("놔시다", &["놓다"], &["시", "다"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, lemmas, forms)),
            "{word}"
        );
    }
}
#[test]
fn noh_contraction_keeps_vowel_recovery_and_lexical_nwaduda() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("놔", vec!["노다"], vec!["어"]),
        ("놔두었다", vec!["놔두다"], vec!["었", "다"]),
        ("놓아두었다", vec!["놓아두다"], vec!["었", "다"]),
        ("좋아", vec!["좋다"], vec!["어"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
    // An internal lexical contraction is not whole-headword normalization.
    let result = engine.analyze_word("놔두었다").unwrap();
    assert!(
        !result
            .analyses
            .iter()
            .any(|a| path(a, &["놓아두다"], &["었", "다"]))
    );
}
