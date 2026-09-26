//! COV-017w: literal 되 and lexically/prefinally licensed 으되.
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
fn doe_endings_preserve_stems_prefinals_and_composition() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("그리되", &["그리다"], &["으되"]),
        ("먹되", &["먹다"], &["으되"]),
        ("살되", &["살다"], &["으되"]),
        ("듣되", &["듣다"], &["으되"]),
        ("돕되", &["돕다"], &["으되"]),
        ("파랗되", &["파랗다"], &["으되"]),
        ("이르되", &["이르다"], &["으되"]),
        ("좋되", &["좋다"], &["으되"]),
        ("있으되", &["있다"], &["으되"]),
        ("없으되", &["없다"], &["으되"]),
        ("맛있으되", &["맛있다"], &["으되"]),
        ("재미없으되", &["재미없다"], &["으되"]),
        ("치렀으되", &["치르다"], &["었", "으되"]),
        ("먹었었으되", &["먹다"], &["었", "었", "으되"]),
        ("먹겠으되", &["먹다"], &["겠", "으되"]),
        ("먹으셨겠으되", &["먹다"], &["시", "었", "겠", "으되"]),
        ("먹으시되", &["먹다"], &["시", "으되"]),
        ("있으시되", &["있다"], &["시", "으되"]),
        ("학생이되", &["학생", "이다"], &["으되"]),
        ("아니되", &["아니다"], &["으되"]),
        ("학생이었으되", &["학생", "이다"], &["었", "으되"]),
        ("의사였으되", &["의사", "이다"], &["었", "으되"]),
        ("먹어보되", &["먹다", "보다"], &["어", "으되"]),
        ("먹어보았으되", &["먹다", "보다"], &["어", "었", "으되"]),
        ("먹고있으되", &["먹다", "있다"], &["고", "으되"]),
        ("먹고싶되", &["먹다", "싶다"], &["고", "으되"]),
        ("먹지않되", &["먹다", "않다"], &["지", "으되"]),
        ("학생답되", &["학생"], &["답다", "으되"]),
        ("학생다웠으되", &["학생"], &["답다", "었", "으되"]),
        ("먹되요", &["먹다"], &["으되", "요"]),
        ("있으되요", &["있다"], &["으되", "요"]),
        ("먹어야겠으되", &["먹다"], &["어야겠", "으되"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        let candidate = result
            .analyses
            .iter()
            .find(|a| path(a, lemmas, forms))
            .expect(word);
        assert!(candidate.rules.iter().any(|r| r == "ending.contrast_doe"));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert!(
            candidate
                .rules
                .iter()
                .all(|r| klem::rule_explanation(r).is_some())
        );
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
#[test]
fn doe_endings_reject_generic_eu_recovery_and_wrong_prefinal_allomorphs() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("먹으되", &["먹다"], &["으되"]),
        ("살으되", &["살다"], &["으되"]),
        ("가으되", &["가다"], &["으되"]),
        ("사되", &["살다"], &["으되"]),
        ("들되", &["듣다"], &["으되"]),
        ("들으되", &["듣다"], &["으되"]),
        ("도우되", &["돕다"], &["으되"]),
        ("도우으되", &["돕다"], &["으되"]),
        ("파라되", &["파랗다"], &["으되"]),
        ("파라으되", &["파랗다"], &["으되"]),
        ("먹었되", &["먹다"], &["었", "으되"]),
        ("먹겠되", &["먹다"], &["겠", "으되"]),
        ("먹더되", &["먹다"], &["더", "으되"]),
        ("먹더으되", &["먹다"], &["더", "으되"]),
        ("먹으시으되", &["먹다"], &["시", "으되"]),
        ("학생이으되", &["학생", "이다"], &["으되"]),
        ("먹고싶으되", &["먹다", "싶다"], &["고", "으되"]),
        ("학생다우되", &["학생"], &["답다", "으되"]),
        ("학생답으되", &["학생"], &["답다", "으되"]),
        ("먹되보다", &["먹다", "보다"], &["으되", "다"]),
        ("먹되다", &["먹다", "이다"], &["으되", "다"]),
        ("먹되를", &["먹다"], &["으되", "를"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, lemmas, forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
