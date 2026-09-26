//! COV-017t: preserve retrospective adnominals while constraining present/prospective followers.
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
fn retrospective_rejects_present_and_prospective_followers() {
    let engine = Lemmatizer::new();
    for (stem, lemmas) in [
        ("먹", vec!["먹다"]),
        ("좋", vec!["좋다"]),
        ("학생이", vec!["학생", "이다"]),
        ("의사", vec!["의사", "이다"]),
    ] {
        for (form, tail) in [
            ("는", "더는"),
            ("는데", "더는데"),
            ("는데요", "더는데요"),
            ("는데도", "더는데도"),
            ("는데다가", "더는데다가"),
            ("는가", "더는가"),
            ("는가요", "더는가요"),
            ("는지", "더는지"),
            ("을", "덜"),
            ("을까", "덜까"),
            ("을까요", "덜까요"),
            ("을게", "덜게"),
            ("을게요", "덜게요"),
            ("을래", "덜래"),
            ("을래요", "덜래요"),
            ("을지", "덜지"),
            ("을수록", "덜수록"),
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
}
#[test]
fn retrospective_bundles_preserve_split_adnominals_and_licensed_composition() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹던", vec!["먹다"], vec!["더", "은"]),
        ("먹던", vec!["먹다"], vec!["던"]),
        ("먹던데", vec!["먹다"], vec!["더", "은데"]),
        ("먹던데", vec!["먹다"], vec!["던데"]),
        ("먹던가", vec!["먹다"], vec!["더", "은가"]),
        ("먹던가", vec!["먹다"], vec!["던가"]),
        ("먹던지", vec!["먹다"], vec!["더", "은지"]),
        ("먹던지", vec!["먹다"], vec!["던지"]),
        ("좋던", vec!["좋다"], vec!["더", "은"]),
        ("좋던", vec!["좋다"], vec!["던"]),
        ("좋던데", vec!["좋다"], vec!["더", "은데"]),
        ("좋던데", vec!["좋다"], vec!["던데"]),
        ("좋던가", vec!["좋다"], vec!["더", "은가"]),
        ("좋던가", vec!["좋다"], vec!["던가"]),
        ("좋던지", vec!["좋다"], vec!["더", "은지"]),
        ("좋던지", vec!["좋다"], vec!["던지"]),
        ("학생이던", vec!["학생", "이다"], vec!["더", "은"]),
        ("학생이던", vec!["학생", "이다"], vec!["던"]),
        ("학생이던데", vec!["학생", "이다"], vec!["더", "은데"]),
        ("학생이던데", vec!["학생", "이다"], vec!["던데"]),
        ("학생이던가", vec!["학생", "이다"], vec!["더", "은가"]),
        ("학생이던가", vec!["학생", "이다"], vec!["던가"]),
        ("학생이던지", vec!["학생", "이다"], vec!["더", "은지"]),
        ("학생이던지", vec!["학생", "이다"], vec!["던지"]),
        ("의사던데", vec!["의사", "이다"], vec!["더", "은데"]),
        ("의사던데", vec!["의사", "이다"], vec!["던데"]),
        ("의사던가", vec!["의사", "이다"], vec!["더", "은가"]),
        ("의사던가", vec!["의사", "이다"], vec!["던가"]),
        ("의사던지", vec!["의사", "이다"], vec!["더", "은지"]),
        ("의사던지", vec!["의사", "이다"], vec!["던지"]),
        ("먹던가요", vec!["먹다"], vec!["던가", "요"]),
        ("먹던지요", vec!["먹다"], vec!["던지", "요"]),
        ("먹던가요", vec!["먹다"], vec!["더", "은가", "요"]),
        ("먹던가요", vec!["먹다"], vec!["더", "은가요"]),
        ("먹던지요", vec!["먹다"], vec!["더", "은지", "요"]),
        ("먹던데도", vec!["먹다"], vec!["더", "은데", "도"]),
        ("먹던데도", vec!["먹다"], vec!["더", "은데도"]),
        ("먹던데다가", vec!["먹다"], vec!["더", "은데다가"]),
        ("먹던가를", vec!["먹다"], vec!["던가", "를"]),
        ("먹던가를", vec!["먹다"], vec!["더", "은가", "를"]),
        ("먹으셨겠던가", vec!["먹다"], vec!["시", "었", "겠", "던가"]),
        (
            "먹으셨겠던가",
            vec!["먹다"],
            vec!["시", "었", "겠", "더", "은가"],
        ),
        ("먹었었던지", vec!["먹다"], vec!["었", "었", "던지"]),
        ("먹어야겠던가", vec!["먹다"], vec!["어야겠", "던가"]),
        ("먹어보던지", vec!["먹다", "보다"], vec!["어", "던지"]),
        ("먹고싶던가", vec!["먹다", "싶다"], vec!["고", "던가"]),
        ("먹던가보다", vec!["먹다", "보다"], vec!["던가", "다"]),
        ("먹던가보다", vec!["먹다", "보다"], vec!["더", "은가", "다"]),
        ("먹던가싶다", vec!["먹다", "싶다"], vec!["던가", "다"]),
        ("먹던가싶다", vec!["먹다", "싶다"], vec!["더", "은가", "다"]),
        ("학생답던가", vec!["학생"], vec!["답다", "던가"]),
        ("학생답던지", vec!["학생"], vec!["답다", "던지"]),
        ("의사였던가", vec!["의사", "이다"], vec!["었", "던가"]),
        ("학생이던지", vec!["학생", "이다"], vec!["던지"]),
        ("먹는", vec!["먹다"], vec!["는"]),
        ("먹는데", vec!["먹다"], vec!["는데"]),
        ("먹는데요", vec!["먹다"], vec!["는데요"]),
        ("먹는데도", vec!["먹다"], vec!["는데도"]),
        ("먹는데다가", vec!["먹다"], vec!["는데다가"]),
        ("먹는가", vec!["먹다"], vec!["는가"]),
        ("먹는가요", vec!["먹다"], vec!["는가요"]),
        ("먹는지", vec!["먹다"], vec!["는지"]),
        ("먹을", vec!["먹다"], vec!["을"]),
        ("먹을까", vec!["먹다"], vec!["을까"]),
        ("먹을까요", vec!["먹다"], vec!["을까요"]),
        ("먹을게", vec!["먹다"], vec!["을게"]),
        ("먹을게요", vec!["먹다"], vec!["을게요"]),
        ("먹을래", vec!["먹다"], vec!["을래"]),
        ("먹을래요", vec!["먹다"], vec!["을래요"]),
        ("먹을지", vec!["먹다"], vec!["을지"]),
        ("먹을수록", vec!["먹다"], vec!["을수록"]),
        ("먹겠는", vec!["먹다"], vec!["겠", "는"]),
        ("먹었는데", vec!["먹다"], vec!["었", "는데"]),
        ("먹었는지", vec!["먹다"], vec!["었", "는지"]),
        ("먹었을까", vec!["먹다"], vec!["었", "을까"]),
        ("먹더는", vec!["먹더다"], vec!["는"]),
        ("먹든지", vec!["먹다"], vec!["든지"]),
        ("먹든가", vec!["먹다"], vec!["든가"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?} {forms:?}"
        );
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
    }
}
#[test]
fn retrospective_boundaries_constrain_composition_and_keep_bundle_roles() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹더는데도", vec!["먹다"], vec!["더", "는데", "도"]),
        ("먹덜까요", vec!["먹다"], vec!["더", "을까", "요"]),
        ("먹덜게요", vec!["먹다"], vec!["더", "을게", "요"]),
        ("먹덜래요", vec!["먹다"], vec!["더", "을래", "요"]),
        ("먹더는가를", vec!["먹다"], vec!["더", "는가", "를"]),
        ("먹더는지요", vec!["먹다"], vec!["더", "는지", "요"]),
        (
            "먹더는척했다",
            vec!["먹다", "척하다"],
            vec!["더", "는", "었", "다"],
        ),
        ("먹덜듯하다", vec!["먹다", "듯하다"], vec!["더", "을", "다"]),
        (
            "먹덜뻔했다",
            vec!["먹다", "뻔하다"],
            vec!["더", "을", "었", "다"],
        ),
        (
            "먹더는가보다",
            vec!["먹다", "보다"],
            vec!["더", "는가", "다"],
        ),
        ("먹덜까싶다", vec!["먹다", "싶다"], vec!["더", "을까", "다"]),
        ("먹었더는", vec!["먹다"], vec!["었", "더", "는"]),
        (
            "먹으셨겠더는",
            vec!["먹다"],
            vec!["시", "었", "겠", "더", "는"],
        ),
        ("먹어보더는", vec!["먹다", "보다"], vec!["어", "더", "는"]),
        ("먹고싶더는", vec!["먹다", "싶다"], vec!["고", "더", "는"]),
        ("학생답더는", vec!["학생"], vec!["답다", "더", "는"]),
        ("먹던가본다", vec!["먹다", "보다"], vec!["던가", "는다"]),
        ("먹던가싶는다", vec!["먹다", "싶다"], vec!["던가", "는다"]),
        ("먹던가있다", vec!["먹다", "있다"], vec!["던가", "다"]),
        ("먹던지보다", vec!["먹다", "보다"], vec!["던지", "다"]),
        ("먹던가다", vec!["먹다", "이다"], vec!["던가", "다"]),
        ("먹던지다", vec!["먹다", "이다"], vec!["던지", "다"]),
        ("먹던가", vec!["먹다"], vec!["든가"]),
        ("먹던지", vec!["먹다"], vec!["든지"]),
        ("먹든가", vec!["먹다"], vec!["던가"]),
        ("먹든지", vec!["먹다"], vec!["던지"]),
        ("먹더던가", vec!["먹다"], vec!["더", "던가"]),
        ("먹더던지", vec!["먹다"], vec!["더", "던지"]),
        ("좋더던가", vec!["좋다"], vec!["더", "던가"]),
        ("좋더던지", vec!["좋다"], vec!["더", "던지"]),
        ("학생이더던가", vec!["학생", "이다"], vec!["더", "던가"]),
        ("학생이더던지", vec!["학생", "이다"], vec!["더", "던지"]),
        ("의사더던가", vec!["의사", "이다"], vec!["더", "던가"]),
        ("의사더던지", vec!["의사", "이다"], vec!["더", "던지"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?} {forms:?}"
        );
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
    }
}
