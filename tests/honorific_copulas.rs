//! COV-020f: omitted copular 이 before honorific 시 and bundled -세요.
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
fn omitted_honorific_copulas_preserve_full_form_parity_and_prefinal_order() {
    let engine = Lemmatizer::new();
    for (word, full, base, forms) in [
        ("선수셨다", "선수이셨다", "선수", vec!["시", "었", "다"]),
        ("의사시니까", "의사이시니까", "의사", vec!["시", "으니까"]),
        ("의사시었다", "의사이시었다", "의사", vec!["시", "었", "다"]),
        ("의사셔요", "의사이셔요", "의사", vec!["시", "어요"]),
        (
            "의사셨어요",
            "의사이셨어요",
            "의사",
            vec!["시", "었", "어요"],
        ),
        (
            "배우셨었겠더라",
            "배우이셨었겠더라",
            "배우",
            vec!["시", "었", "었", "겠", "더", "라"],
        ),
        (
            "선수시겠더라",
            "선수이시겠더라",
            "선수",
            vec!["시", "겠", "더", "라"],
        ),
        ("의사시죠", "의사이시죠", "의사", vec!["시", "죠"]),
        ("의사십니다", "의사이십니다", "의사", vec!["시", "습니다"]),
        ("의사십니까", "의사이십니까", "의사", vec!["시", "습니까"]),
        ("의사시기", "의사이시기", "의사", vec!["시", "기"]),
        ("의사신데", "의사이신데", "의사", vec!["시", "은데"]),
        (
            "의사셨는가",
            "의사이셨는가",
            "의사",
            vec!["시", "었", "는가"],
        ),
        (
            "의사시리라",
            "의사이시리라",
            "의사",
            vec!["시", "으리", "라"],
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &[base, "이다"], &forms))
            .expect(word);
        assert_eq!(a.lemmas[0].kind, LemmaKind::Nominal);
        assert_eq!(a.lemmas[1].kind, LemmaKind::Copula);
        assert!(
            a.rules.iter().any(|r| r == "copula.omitted_honorific"),
            "{word}"
        );
        assert!(
            engine
                .analyze_word(full)
                .unwrap()
                .analyses
                .iter()
                .any(|f| f.lemmas == a.lemmas && f.morphemes == a.morphemes),
            "{word}"
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
    for (word, lemmas, forms) in [
        ("의사세요", vec!["의사", "이다"], vec!["으세요"]),
        ("의사이세요", vec!["의사", "이다"], vec!["으세요"]),
        (
            "의사셨어요",
            vec!["의사", "이다"],
            vec!["시", "었", "어", "요"],
        ),
        (
            "의사시니까요",
            vec!["의사", "이다"],
            vec!["시", "으니까", "요"],
        ),
        (
            "의사시고싶다",
            vec!["의사", "이다", "싶다"],
            vec!["시", "고", "다"],
        ),
        (
            "의사시고도싶다",
            vec!["의사", "이다", "싶다"],
            vec!["시", "고", "도", "다"],
        ),
        (
            "의사시지않다",
            vec!["의사", "이다", "않다"],
            vec!["시", "지", "다"],
        ),
        (
            "의사시긴데",
            vec!["의사", "이다", "이다"],
            vec!["시", "기", "은데"],
        ),
        (
            "먹기셨다",
            vec!["먹다", "이다"],
            vec!["기", "시", "었", "다"],
        ),
        (
            "먹어보기셨다",
            vec!["먹다", "보다", "이다"],
            vec!["어", "기", "시", "었", "다"],
        ),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
    // Nominalization composition is structural, not an honorific referent judgment.
    for (word, forms, conditional) in [
        ("ABC셨다", vec!["시", "었", "다"], true),
        ("ABC이셨다", vec!["시", "었", "다"], false),
        ("ABC세요", vec!["으세요"], true),
        ("ABC이세요", vec!["으세요"], false),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &["ABC", "이다"], &forms))
            .expect(word);
        assert_eq!(
            a.rules.iter().any(|r| r == "pronunciation.assumed_vowel"),
            conditional,
            "{word}"
        );
    }
}

#[test]
fn honorific_omission_rejects_wrong_nominal_boundaries_and_known_ending_violations() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("학생셨다", vec!["학생", "이다"], vec!["시", "었", "다"]),
        ("길셨다", vec!["길", "이다"], vec!["시", "었", "다"]),
        ("도우셨다", vec!["돕", "이다"], vec!["시", "었", "다"]),
        ("사셨다", vec!["살", "이다"], vec!["시", "었", "다"]),
        ("학생세요", vec!["학생", "이다"], vec!["으세요"]),
        ("길세요", vec!["길", "이다"], vec!["으세요"]),
        ("의사시시다", vec!["의사", "이다"], vec!["시", "시", "다"]),
        ("의사겠시다", vec!["의사", "이다"], vec!["겠", "시", "다"]),
        ("의사신다", vec!["의사", "이다"], vec!["시", "는다"]),
        ("의사신다든가", vec!["의사", "이다"], vec!["시", "는다든가"]),
        ("의사시자면", vec!["의사", "이다"], vec!["시", "자면"]),
        ("의사시요", vec!["의사", "이다"], vec!["시", "요"]),
        (
            "의사셨세요",
            vec!["의사", "이다"],
            vec!["시", "었", "으세요"],
        ),
        (
            "의사셔해요",
            vec!["의사", "이다", "하다"],
            vec!["시", "어", "어요"],
        ),
        ("의사셨다", vec!["의사이다"], vec!["시", "었", "다"]),
        (
            "의사셨기다",
            vec!["의사이다", "이다"],
            vec!["시", "었", "기", "다"],
        ),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
    for (word, lemmas, forms) in [
        ("도우셨다", vec!["돕다"], vec!["시", "었", "다"]),
        ("사셨다", vec!["살다"], vec!["시", "었", "다"]),
        ("마셨다", vec!["마시다"], vec!["었", "다"]),
        ("주셨습니다", vec!["주다"], vec!["시", "었", "습니다"]),
        ("학생이셨다", vec!["학생", "이다"], vec!["시", "었", "다"]),
        ("길이세요", vec!["길", "이다"], vec!["으세요"]),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
}
