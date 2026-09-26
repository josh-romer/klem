//! COV-017q/018i: 고서, 어서야, and reviewed post-connective particles.
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind};
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
fn seo_connectives_keep_literal_vowel_and_particle_alternatives() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹고서", vec!["먹다"], vec!["고서"]),
        ("살고서", vec!["살다"], vec!["고서"]),
        ("듣고서", vec!["듣다"], vec!["고서"]),
        ("돕고서", vec!["돕다"], vec!["고서"]),
        ("쓰고서", vec!["쓰다"], vec!["고서"]),
        ("먹으시고서", vec!["먹다"], vec!["시", "고서"]),
        ("아니고서", vec!["아니다"], vec!["고서"]),
        ("먹어보고서", vec!["먹다", "보다"], vec!["어", "고서"]),
        ("먹지않고서", vec!["먹다", "않다"], vec!["지", "고서"]),
        (
            "먹어보지않고서",
            vec!["먹다", "보다", "않다"],
            vec!["어", "지", "고서"],
        ),
        ("가지고서", vec!["가지다"], vec!["고서"]),
        ("돌리고서는", vec!["돌리다"], vec!["고서", "는"]),
        ("먹고서도", vec!["먹다"], vec!["고서", "도"]),
        ("먹고서만", vec!["먹다"], vec!["고서", "만"]),
        ("먹고서야", vec!["먹다"], vec!["고서", "야"]),
        ("먹고서요", vec!["먹다"], vec!["고서", "요"]),
        ("먹어서야", vec!["먹다"], vec!["어서야"]),
        ("되어서야", vec!["되다"], vec!["어서야"]),
        ("돼서야", vec!["되다"], vec!["어서야"]),
        ("가서야", vec!["가다"], vec!["어서야"]),
        ("살아서야", vec!["살다"], vec!["어서야"]),
        ("들어서야", vec!["듣다"], vec!["어서야"]),
        ("도와서야", vec!["돕다"], vec!["어서야"]),
        ("써서야", vec!["쓰다"], vec!["어서야"]),
        ("추워서야", vec!["춥다"], vec!["어서야"]),
        ("공부해서야", vec!["공부하다"], vec!["어서야"]),
        ("공부하여서야", vec!["공부하다"], vec!["어서야"]),
        ("먹으셔서야", vec!["먹다"], vec!["시", "어서야"]),
        ("학생이어서야", vec!["학생", "이다"], vec!["어서야"]),
        ("학생다워서야", vec!["학생"], vec!["답다", "어서야"]),
        ("먹고싶어서야", vec!["먹다", "싶다"], vec!["고", "어서야"]),
        ("젊어서부터", vec!["젊다"], vec!["어서", "부터"]),
        ("먹고부터", vec!["먹다"], vec!["고", "부터"]),
        ("나오면서부터", vec!["나오다"], vec!["으면서", "부터"]),
        (
            "기록하면서부터는",
            vec!["기록하다"],
            vec!["으면서", "부터", "는"],
        ),
        ("먹으면서부터도", vec!["먹다"], vec!["으면서", "부터", "도"]),
        ("먹고부터요", vec!["먹다"], vec!["고", "부터", "요"]),
        ("통해서보다는", vec!["통하다"], vec!["어서", "보다", "는"]),
        ("통하여서보다", vec!["통하다"], vec!["어서", "보다"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.breakdown().is_some());
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    for (word, base) in [
        ("먹어서야", "먹다"),
        ("돼서야", "되다"),
        ("공부해서야", "공부하다"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| path(a, &[base], &["어서야"]))
        );
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &[base], &["어서", "야"]))
            .expect(word);
        assert_eq!(a.morphemes[1].kind, MorphemeKind::Particle);
    }
}
#[test]
fn seo_connectives_reject_wrong_boundaries_prefinals_and_known_classes() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹었고서", vec!["먹다"], vec!["었", "고서"]),
        ("먹겠고서", vec!["먹다"], vec!["겠", "고서"]),
        ("먹더고서", vec!["먹다"], vec!["더", "고서"]),
        ("먹으셨고서", vec!["먹다"], vec!["시", "었", "고서"]),
        ("도우고서", vec!["돕다"], vec!["고서"]),
        ("들고서", vec!["듣다"], vec!["고서"]),
        ("사고서", vec!["살다"], vec!["고서"]),
        ("학생이고서", vec!["학생", "이다"], vec!["고서"]),
        ("학생이시고서", vec!["학생", "이다"], vec!["시", "고서"]),
        ("학생답고서", vec!["학생"], vec!["답다", "고서"]),
        ("먹고싶고서", vec!["먹다", "싶다"], vec!["고", "고서"]),
        (
            "먹고싶지않고서",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "고서"],
        ),
        ("먹는가보고서", vec!["먹다", "보다"], vec!["는가", "고서"]),
        ("먹고서는다", vec!["먹다", "서다"], vec!["고서", "는다"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    // Unknown lexical adjective/verb classes remain hypotheses, not validation.
    let result = engine.analyze_word("좋고서").unwrap();
    assert!(
        result
            .analyses
            .iter()
            .any(|a| path(a, &["좋다"], &["고서"]) && a.lemmas[0].kind == LemmaKind::Predicate)
    );
}
