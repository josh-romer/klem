//! COV-017s: retrospective nominalization and connective boundaries.
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
fn retrospective_rejects_nominalizers_and_connectives_across_classes() {
    let engine = Lemmatizer::new();
    for (stem, lemmas) in [
        ("먹", vec!["먹다"]),
        ("좋", vec!["좋다"]),
        ("학생이", vec!["학생", "이다"]),
        ("의사", vec!["의사", "이다"]),
    ] {
        for (form, tail) in [
            ("나", "더나"),
            ("으나", "더나"),
            ("기", "더기"),
            ("기로", "더기로"),
            ("기가", "더기가"),
            ("기는", "더기는"),
            ("기도", "더기도"),
            ("기만", "더기만"),
            ("기를", "더기를"),
            ("기보다", "더기보다"),
            ("음", "덤"),
            ("게", "더게"),
            ("게요", "더게요"),
            ("도록", "더도록"),
            ("듯", "더듯"),
            ("듯이", "더듯이"),
            ("으면", "더면"),
            ("으며", "더며"),
            ("으면서", "더면서"),
            ("으므로", "더므로"),
            ("어서", "더서"),
            ("어서야", "더서야"),
            ("어도", "더도"),
            ("어야", "더야"),
            ("어야지", "더야지"),
            ("어야죠", "더야죠"),
            ("어다가", "더다가"),
            ("어서는", "더서는"),
            ("어서도", "더서도"),
            ("고자", "더고자"),
            ("건대", "더건대"),
            ("소", "더소"),
            ("오", "더오"),
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
fn nominalizers_and_connectives_preserve_licensed_stacks_and_alternatives() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹나", vec!["먹다"], vec!["나"]),
        ("먹으나", vec!["먹다"], vec!["으나"]),
        ("먹나요", vec!["먹다"], vec!["나", "요"]),
        ("가나", vec!["가다"], vec!["으나"]),
        ("먹기", vec!["먹다"], vec!["기"]),
        ("먹기로", vec!["먹다"], vec!["기로"]),
        ("먹기로", vec!["먹다"], vec!["기", "로"]),
        ("먹기가", vec!["먹다"], vec!["기가"]),
        ("먹기가", vec!["먹다"], vec!["기", "가"]),
        ("먹기는", vec!["먹다"], vec!["기는"]),
        ("먹기는", vec!["먹다"], vec!["기", "는"]),
        ("먹기도", vec!["먹다"], vec!["기도"]),
        ("먹기도", vec!["먹다"], vec!["기", "도"]),
        ("먹기만", vec!["먹다"], vec!["기만"]),
        ("먹기만", vec!["먹다"], vec!["기", "만"]),
        ("먹기를", vec!["먹다"], vec!["기를"]),
        ("먹기보다", vec!["먹다"], vec!["기보다"]),
        ("먹음", vec!["먹다"], vec!["음"]),
        ("삶", vec!["살다"], vec!["음"]),
        ("먹으심", vec!["먹다"], vec!["시", "음"]),
        ("먹었음", vec!["먹다"], vec!["었", "음"]),
        ("먹겠음", vec!["먹다"], vec!["겠", "음"]),
        ("먹었기", vec!["먹다"], vec!["었", "기"]),
        ("학생이기", vec!["학생", "이다"], vec!["기"]),
        ("학생이었음을", vec!["학생", "이다"], vec!["었", "음", "을"]),
        ("먹게", vec!["먹다"], vec!["게"]),
        ("먹게요", vec!["먹다"], vec!["게요"]),
        ("먹도록", vec!["먹다"], vec!["도록"]),
        ("먹듯", vec!["먹다"], vec!["듯"]),
        ("먹듯이", vec!["먹다"], vec!["듯이"]),
        ("먹으면", vec!["먹다"], vec!["으면"]),
        ("먹으며", vec!["먹다"], vec!["으며"]),
        ("가며", vec!["가다"], vec!["으며"]),
        ("먹으면서", vec!["먹다"], vec!["으면서"]),
        ("가면서", vec!["가다"], vec!["으면서"]),
        ("들으면서", vec!["듣다"], vec!["으면서"]),
        ("먹으므로", vec!["먹다"], vec!["으므로"]),
        ("가므로", vec!["가다"], vec!["으므로"]),
        ("학생이며", vec!["학생", "이다"], vec!["으며"]),
        ("먹어서", vec!["먹다"], vec!["어서"]),
        ("먹어서야", vec!["먹다"], vec!["어서야"]),
        ("먹어도", vec!["먹다"], vec!["어도"]),
        ("먹어야", vec!["먹다"], vec!["어야"]),
        ("먹어야지", vec!["먹다"], vec!["어야지"]),
        ("먹어야죠", vec!["먹다"], vec!["어야죠"]),
        ("먹어다가", vec!["먹다"], vec!["어다가"]),
        ("먹어서는", vec!["먹다"], vec!["어서는"]),
        ("먹어서도", vec!["먹다"], vec!["어서도"]),
        ("먹고자", vec!["먹다"], vec!["고자"]),
        ("바라건대", vec!["바라다"], vec!["건대"]),
        ("먹소", vec!["먹다"], vec!["소"]),
        ("가오", vec!["가다"], vec!["오"]),
        (
            "먹기로들었다",
            vec!["먹다", "들다"],
            vec!["기로", "었", "다"],
        ),
        (
            "먹기나했다",
            vec!["먹다", "하다"],
            vec!["기", "나", "었", "다"],
        ),
        ("먹기다", vec!["먹다", "이다"], vec!["기", "다"]),
        ("먹기는했다", vec!["먹다", "하다"], vec!["기는", "었", "다"]),
        ("먹으면서부터", vec!["먹다"], vec!["으면서", "부터"]),
        ("먹게했다", vec!["먹다", "하다"], vec!["게", "었", "다"]),
        ("먹고싶으면", vec!["먹다", "싶다"], vec!["고", "으면"]),
        ("학생답기", vec!["학생"], vec!["답다", "기"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {forms:?}"
        );
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
    }
    // Unknown lexical stems are not removed just because they end in 더.
    assert!(
        engine
            .analyze_word("먹더기")
            .unwrap()
            .analyses
            .iter()
            .any(|a| path(a, &["먹더다"], &["기"]))
    );
}

#[test]
fn nominalized_clause_and_lexical_hada_remain_separate_words() {
    // KRDict 73277 sense 16 treats -기로 하다 as lexical 하다, unlike
    // the auxiliary 들다 in -기로 들다. Do not invent an auxiliary link
    // just to combine a properly spaced clause into one token.
    let engine = Lemmatizer::new();
    let words: Vec<_> = engine
        .analyze_text("먹기로 했다")
        .filter_map(|token| token.analysis)
        .collect();
    assert_eq!(words.len(), 2);
    assert!(
        words[0]
            .analyses
            .iter()
            .any(|a| path(a, &["먹다"], &["기", "로"]))
    );
    assert!(
        words[1]
            .analyses
            .iter()
            .any(|a| path(a, &["하다"], &["었", "다"]))
    );
}
#[test]
fn retrospective_cannot_pass_through_nominalization_or_auxiliary_links() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹더나요", vec!["먹다"], vec!["더", "나", "요"]),
        ("의사더나요", vec!["의사", "이다"], vec!["더", "나", "요"]),
        ("먹더기다", vec!["먹다", "이다"], vec!["더", "기", "다"]),
        ("먹더기예요", vec!["먹다", "이다"], vec!["더", "기", "에요"]),
        (
            "먹더기로들었다",
            vec!["먹다", "들다"],
            vec!["더", "기로", "었", "다"],
        ),
        (
            "먹더기는했다",
            vec!["먹다", "하다"],
            vec!["더", "기는", "었", "다"],
        ),
        (
            "먹더기나했다",
            vec!["먹다", "하다"],
            vec!["더", "기", "나", "었", "다"],
        ),
        (
            "먹더게했다",
            vec!["먹다", "하다"],
            vec!["더", "게", "었", "다"],
        ),
        (
            "먹더야한다",
            vec!["먹다", "하다"],
            vec!["더", "어야", "는다"],
        ),
        ("먹더서부터", vec!["먹다"], vec!["더", "어서", "부터"]),
        ("먹더면서부터", vec!["먹다"], vec!["더", "으면서", "부터"]),
        ("먹더기에는", vec!["먹다"], vec!["더", "기", "에", "는"]),
        ("먹더기에", vec!["먹다"], vec!["더", "기", "에"]),
        ("먹더기는", vec!["먹다"], vec!["더", "기", "는"]),
        ("먹더기도", vec!["먹다"], vec!["더", "기", "도"]),
        ("먹더기에요", vec!["먹다"], vec!["더", "기", "에", "요"]),
        ("먹덤이다", vec!["먹다", "이다"], vec!["더", "음", "다"]),
        ("먹었더기", vec!["먹다"], vec!["었", "더", "기"]),
        (
            "먹으셨겠더기",
            vec!["먹다"],
            vec!["시", "었", "겠", "더", "기"],
        ),
        ("먹어야겠더기", vec!["먹다"], vec!["어야겠", "더", "기"]),
        ("먹어보더기", vec!["먹다", "보다"], vec!["어", "더", "기"]),
        ("먹고싶더기", vec!["먹다", "싶다"], vec!["고", "더", "기"]),
        ("학생답더기", vec!["학생"], vec!["답다", "더", "기"]),
        ("학생이더기", vec!["학생", "이다"], vec!["더", "기"]),
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
