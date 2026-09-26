//! COV-017k: bundled -아/어/여야겠- with vowel recovery and ordered prefinals.
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
fn necessity_bundles_keep_spelling_prefinals_and_component_order() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("말해야겠다", vec!["말하다"], vec!["어야겠", "다"]),
        ("이야기해야겠다", vec!["이야기하다"], vec!["어야겠", "다"]),
        ("먹어야겠네요", vec!["먹다"], vec!["어야겠", "네요"]),
        ("가야겠다", vec!["가다"], vec!["어야겠", "다"]),
        ("와야겠다", vec!["오다"], vec!["어야겠", "다"]),
        ("살아야겠다", vec!["살다"], vec!["어야겠", "다"]),
        ("해야겠더라", vec!["하다"], vec!["어야겠", "더라"]),
        ("하여야겠다", vec!["하다"], vec!["어야겠", "다"]),
        ("넓어야겠군요", vec!["넓다"], vec!["어야겠", "군요"]),
        ("끊어야겠다", vec!["끊다"], vec!["어야겠", "다"]),
        ("들어야겠다", vec!["듣다"], vec!["어야겠", "다"]),
        ("들어야겠다", vec!["들다"], vec!["어야겠", "다"]),
        ("도와야겠다", vec!["돕다"], vec!["어야겠", "다"]),
        ("부어야겠다", vec!["붓다"], vec!["어야겠", "다"]),
        ("몰라야겠다", vec!["모르다"], vec!["어야겠", "다"]),
        ("써야겠다", vec!["쓰다"], vec!["어야겠", "다"]),
        ("퍼야겠다", vec!["푸다"], vec!["어야겠", "다"]),
        ("그래야겠다", vec!["그렇다"], vec!["어야겠", "다"]),
        ("먹으셔야겠다", vec!["먹다"], vec!["시", "어야겠", "다"]),
        ("먹었어야겠다", vec!["먹다"], vec!["었", "어야겠", "다"]),
        (
            "먹으셨어야겠다",
            vec!["먹다"],
            vec!["시", "었", "어야겠", "다"],
        ),
        ("먹어야겠더니", vec!["먹다"], vec!["어야겠", "더", "으니"]),
        ("먹어야겠습니다", vec!["먹다"], vec!["어야겠", "습니다"]),
        ("먹어야겠다고", vec!["먹다"], vec!["어야겠", "다고"]),
        ("먹어야겠지요", vec!["먹다"], vec!["어야겠", "지요"]),
        ("먹어야겠지만요", vec!["먹다"], vec!["어야겠", "지만", "요"]),
        ("학생이어야겠다", vec!["학생", "이다"], vec!["어야겠", "다"]),
        ("학교여야겠다", vec!["학교", "이다"], vec!["어야겠", "다"]),
        ("학생다워야겠다", vec!["학생"], vec!["답다", "어야겠", "다"]),
        (
            "먹어봐야겠다",
            vec!["먹다", "보다"],
            vec!["어", "어야겠", "다"],
        ),
        (
            "먹지않아야겠다",
            vec!["먹다", "않다"],
            vec!["지", "어야겠", "다"],
        ),
        (
            "먹고있어야겠다",
            vec!["먹다", "있다"],
            vec!["고", "어야겠", "다"],
        ),
        (
            "먹고싶어야겠다",
            vec!["먹다", "싶다"],
            vec!["고", "어야겠", "다"],
        ),
        (
            "먹어야겠음이다",
            vec!["먹다", "이다"],
            vec!["어야겠", "음", "다"],
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(
            a.morphemes
                .iter()
                .find(|m| m.form == "어야겠")
                .unwrap()
                .kind,
            MorphemeKind::Prefinal
        );
        assert!(a.rules.iter().any(|r| r == "prefinal.obligation"));
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
        assert!(
            result
                .analyses
                .iter()
                .flat_map(|a| &a.rules)
                .all(|r| klem::rule_explanation(r).is_some())
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
}

#[test]
fn bundle_recovery_does_not_relax_boundaries_or_prefinal_order() {
    for (word, lemmas, forms) in [
        ("먹야겠다", vec!["먹다"], vec!["어야겠", "다"]),
        ("먹아야겠다", vec!["먹다"], vec!["어야겠", "다"]),
        ("하어야겠다", vec!["하다"], vec!["어야겠", "다"]),
        ("학생답아야겠다", vec!["학생"], vec!["답다", "어야겠", "다"]),
        ("먹겠어야겠다", vec!["먹다"], vec!["겠", "어야겠", "다"]),
        ("먹더어야겠다", vec!["먹다"], vec!["더", "어야겠", "다"]),
        ("먹어야겠었다", vec!["먹다"], vec!["어야겠", "었", "다"]),
        ("먹어야겠겠다", vec!["먹다"], vec!["어야겠", "겠", "다"]),
        ("먹어야겠시다", vec!["먹다"], vec!["어야겠", "시", "다"]),
        ("먹어야겠으란", vec!["먹다"], vec!["어야겠", "으란"]),
        (
            "먹어야겠다보다",
            vec!["먹다", "보다"],
            vec!["어야겠", "다", "다"],
        ),
        (
            "먹어야겠고있다",
            vec!["먹다", "있다"],
            vec!["어야겠", "고", "다"],
        ),
        (
            "먹어야겠고계시다",
            vec!["먹다", "계시다"],
            vec!["어야겠", "고", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    // The uncontracted auxiliary remains distinct. The bundled path must not
    // manufacture 하다 solely because a corpus expands an implicit predicate.
    let e = Lemmatizer::new();
    assert!(
        !e.analyze_word("와야겠다")
            .unwrap()
            .analyses
            .iter()
            .any(|a| path(a, &["오다", "하다"], &["어야", "겠", "다"]))
    );
    assert!(
        e.analyze_word("와야하겠다")
            .unwrap()
            .analyses
            .iter()
            .any(|a| path(a, &["오다", "하다"], &["어야", "겠", "다"]))
    );
}
