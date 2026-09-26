//! COV-017r: retrospective prefinal licenses, preserving lexical/bundled alternatives.
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
fn retrospective_rejects_reviewed_endings_across_predicate_and_copula_classes() {
    let engine = Lemmatizer::new();
    for (stem, lemmas) in [
        ("먹", vec!["먹다"]),
        ("좋", vec!["좋다"]),
        ("학생이", vec!["학생", "이다"]),
        ("의사", vec!["의사", "이다"]),
    ] {
        for (form, tail) in [
            ("다", "더다"),
            ("다고", "더다고"),
            ("다는", "더다는"),
            ("다니", "더다니"),
            ("다면", "더다면"),
            ("어", "더"),
            ("어요", "더요"),
            ("지", "더지"),
            ("지요", "더지요"),
            ("죠", "더죠"),
            ("습니다", "덥니다"),
            ("습니까", "덥니까"),
            ("네", "더네"),
            ("네요", "더네요"),
            ("나요", "더나요"),
            ("고", "더고"),
            ("고요", "더고요"),
            ("지만", "더지만"),
            ("지만요", "더지만요"),
            ("거든", "더거든"),
            ("거든요", "더거든요"),
            ("거나", "더거나"),
            ("건", "더건"),
            ("더라", "더더라"),
            ("더라고", "더더라고"),
            ("더라는", "더더라는"),
            ("더니", "더더니"),
            ("더라도", "더더라도"),
            ("더군", "더더군"),
            ("더군요", "더더군요"),
            ("던", "더던"),
            ("던데", "더던데"),
            ("던데요", "더던데요"),
        ] {
            let word = format!("{stem}{tail}");
            let result = engine.analyze_word(&word).unwrap();
            assert!(
                !result
                    .analyses
                    .iter()
                    .any(|a| path(a, &lemmas, &["더", form])),
                "{word}: {form}"
            );
            assert!(result.analyses.iter().any(|a| a.unchanged), "{word}");
            assert!(
                result.analyses.iter().all(|a| a.breakdown().is_some()),
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
}
#[test]
fn retrospective_preserves_licensed_followers_bundles_and_lexical_stems() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹더라", vec!["먹다"], vec!["더", "라"]),
        ("먹더라", vec!["먹다"], vec!["더라"]),
        ("먹더라고", vec!["먹다"], vec!["더", "라고"]),
        ("먹더라고", vec!["먹다"], vec!["더라고"]),
        ("먹더라면", vec!["먹다"], vec!["더", "라면"]),
        ("먹더라서", vec!["먹다"], vec!["더", "라서"]),
        ("먹더란", vec!["먹다"], vec!["더", "란"]),
        ("먹더랍니다", vec!["먹다"], vec!["더", "랍니다"]),
        ("먹더라든가", vec!["먹다"], vec!["더", "라든가"]),
        ("먹더니", vec!["먹다"], vec!["더", "니"]),
        ("먹더니", vec!["먹다"], vec!["더", "으니"]),
        ("먹더니", vec!["먹다"], vec!["더니"]),
        ("먹더니까", vec!["먹다"], vec!["더", "으니까"]),
        ("먹더냐", vec!["먹다"], vec!["더", "냐"]),
        ("먹더냐고", vec!["먹다"], vec!["더", "냐고"]),
        ("먹더냐는", vec!["먹다"], vec!["더", "냐는"]),
        ("먹더구나", vec!["먹다"], vec!["더", "구나"]),
        ("먹더군요", vec!["먹다"], vec!["더", "군요"]),
        ("먹더군요", vec!["먹다"], vec!["더군요"]),
        ("먹던데요", vec!["먹다"], vec!["던데요"]),
        ("먹었더라", vec!["먹다"], vec!["었", "더", "라"]),
        (
            "먹었었겠더라",
            vec!["먹다"],
            vec!["었", "었", "겠", "더", "라"],
        ),
        (
            "먹으셨겠더라",
            vec!["먹다"],
            vec!["시", "었", "겠", "더", "라"],
        ),
        ("먹어야겠더라", vec!["먹다"], vec!["어야겠", "더", "라"]),
        ("의사더라", vec!["의사", "이다"], vec!["더", "라"]),
        ("학생이더군요", vec!["학생", "이다"], vec!["더군요"]),
        ("먹고싶더라", vec!["먹다", "싶다"], vec!["고", "더", "라"]),
        ("먹어보더니", vec!["먹다", "보다"], vec!["어", "더니"]),
        ("먹지않더라", vec!["먹다", "않다"], vec!["지", "더", "라"]),
        ("학생답더라", vec!["학생"], vec!["답다", "더", "라"]),
        ("더뎌요", vec!["더디다"], vec!["어요"]),
        ("더해요", vec!["더하다"], vec!["어요"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {forms:?}"
        );
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
    }
    // A recovered marker is rejected; an unknown lexical stem stays a hypothesis.
    let result = engine.analyze_word("먹더다").unwrap();
    assert!(
        result
            .analyses
            .iter()
            .any(|a| path(a, &["먹더다"], &["다"]))
    );
}
#[test]
fn retrospective_constraints_compose_with_prefinals_auxiliaries_and_particles() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹으셨더다", vec!["먹다"], vec!["시", "었", "더", "다"]),
        (
            "먹었었겠더다",
            vec!["먹다"],
            vec!["었", "었", "겠", "더", "다"],
        ),
        ("먹어야겠더다", vec!["먹다"], vec!["어야겠", "더", "다"]),
        ("먹어보더다", vec!["먹다", "보다"], vec!["어", "더", "다"]),
        ("먹고싶더다", vec!["먹다", "싶다"], vec!["고", "더", "다"]),
        ("먹지않더다", vec!["먹다", "않다"], vec!["지", "더", "다"]),
        ("학생답더다", vec!["학생"], vec!["답다", "더", "다"]),
        ("먹더고싶다", vec!["먹다", "싶다"], vec!["더", "고", "다"]),
        (
            "먹더고는싶다",
            vec!["먹다", "싶다"],
            vec!["더", "고", "는", "다"],
        ),
        ("먹더지않다", vec!["먹다", "않다"], vec!["더", "지", "다"]),
        (
            "먹더봤다",
            vec!["먹다", "보다"],
            vec!["더", "어", "었", "다"],
        ),
        (
            "의사더고싶다",
            vec!["의사", "이다", "싶다"],
            vec!["더", "고", "다"],
        ),
        ("먹더다마는", vec!["먹다"], vec!["더", "다", "마는"]),
        ("먹더고는", vec!["먹다"], vec!["더", "고", "는"]),
        ("먹더지요", vec!["먹다"], vec!["더", "지", "요"]),
        ("먹더더라", vec!["먹다"], vec!["더", "더", "라"]),
        ("먹더어", vec!["먹다"], vec!["더", "어"]),
        ("먹더어요", vec!["먹다"], vec!["더", "어요"]),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}: {forms:?}"
        );
    }
}
