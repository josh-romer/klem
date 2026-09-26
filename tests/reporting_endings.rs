//! COV-017m: informative/reported -답니다 and the homonymous -랍니다 family.
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
fn reporting_endings_preserve_stems_prefinals_and_homonymous_groups() {
    for (word, lemmas, forms) in [
        ("좋답니다", vec!["좋다"], vec!["답니다"]),
        ("있답니다", vec!["있다"], vec!["답니다"]),
        ("넘었답니다", vec!["넘다"], vec!["었", "답니다"]),
        ("묻었답니다", vec!["묻다"], vec!["었", "답니다"]),
        ("좋았답니다", vec!["좋다"], vec!["었", "답니다"]),
        (
            "먹으셨겠답니다",
            vec!["먹다"],
            vec!["시", "었", "겠", "답니다"],
        ),
        ("간답니다", vec!["가다"], vec!["는답니다"]),
        ("산답니다", vec!["살다"], vec!["는답니다"]),
        ("먹는답니다", vec!["먹다"], vec!["는답니다"]),
        ("도우신답니다", vec!["돕다"], vec!["시", "는답니다"]),
        ("물어본답니다", vec!["물어보다"], vec!["는답니다"]),
        ("물어본답니다", vec!["묻다", "보다"], vec!["어", "는답니다"]),
        ("먹고싶답니다", vec!["먹다", "싶다"], vec!["고", "답니다"]),
        ("학생이랍니다", vec!["학생", "이다"], vec!["랍니다"]),
        ("의사랍니다", vec!["의사", "이다"], vec!["랍니다"]),
        ("아니랍니다", vec!["아니다"], vec!["랍니다"]),
        (
            "학생이셨답니다",
            vec!["학생", "이다"],
            vec!["시", "었", "답니다"],
        ),
        ("먹으시랍니다", vec!["먹다"], vec!["시", "랍니다"]),
        ("먹었더랍니다", vec!["먹다"], vec!["었", "더", "랍니다"]),
        ("먹으리랍니다", vec!["먹다"], vec!["으리", "랍니다"]),
        ("가랍니다", vec!["가다"], vec!["으랍니다"]),
        ("살랍니다", vec!["살다"], vec!["으랍니다"]),
        ("먹으랍니다", vec!["먹다"], vec!["으랍니다"]),
        ("들으랍니다", vec!["듣다"], vec!["으랍니다"]),
        ("도우랍니다", vec!["돕다"], vec!["으랍니다"]),
        ("먹으시랍니다", vec!["먹다"], vec!["시", "으랍니다"]),
        ("도와주랍니다", vec!["돕다", "주다"], vec!["어", "으랍니다"]),
        ("학생답답니다", vec!["학생"], vec!["답다", "답니다"]),
    ] {
        let engine = Lemmatizer::new();
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(
            a.rules.iter().any(|r| r == "ending.reporting_polite"),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged), "{word}");
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
        assert!(
            a.rules.iter().all(|r| klem::rule_explanation(r).is_some()),
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

#[test]
fn reporting_endings_reject_wrong_boundaries_and_prefinal_slots() {
    for (word, lemmas, forms) in [
        ("가는답니다", vec!["가다"], vec!["는답니다"]),
        ("살는답니다", vec!["살다"], vec!["는답니다"]),
        ("먹답니다", vec!["먹다"], vec!["는답니다"]),
        ("도운답니다", vec!["돕다"], vec!["는답니다"]),
        ("먹었는답니다", vec!["먹다"], vec!["었", "는답니다"]),
        ("먹겠는답니다", vec!["먹다"], vec!["겠", "는답니다"]),
        ("먹더답니다", vec!["먹다"], vec!["더", "답니다"]),
        ("먹었랍니다", vec!["먹다"], vec!["었", "랍니다"]),
        ("먹겠랍니다", vec!["먹다"], vec!["겠", "랍니다"]),
        ("먹었으랍니다", vec!["먹다"], vec!["었", "으랍니다"]),
        ("먹겠으랍니다", vec!["먹다"], vec!["겠", "으랍니다"]),
        ("먹더랍니다", vec!["먹다"], vec!["더", "으랍니다"]),
        ("먹랍니다", vec!["먹다"], vec!["으랍니다"]),
        ("가으랍니다", vec!["가다"], vec!["으랍니다"]),
        (
            "먹고싶는답니다",
            vec!["먹다", "싶다"],
            vec!["고", "는답니다"],
        ),
        ("학생답는답니다", vec!["학생"], vec!["답다", "는답니다"]),
        ("학생랍니다", vec!["학생", "이다"], vec!["랍니다"]),
        ("학생이답니다", vec!["학생", "이다"], vec!["답니다"]),
        ("학생인답니다", vec!["학생", "이다"], vec!["는답니다"]),
        ("학생이랍니다", vec!["학생", "이다"], vec!["으랍니다"]),
        (
            "먹고싶으랍니다",
            vec!["먹다", "싶다"],
            vec!["고", "으랍니다"],
        ),
        (
            "학생다우시랍니다",
            vec!["학생"],
            vec!["답다", "시", "으랍니다"],
        ),
        ("먹는답니다요", vec!["먹다"], vec!["는답니다", "요"]),
    ] {
        let r = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !r.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(r.analyses.iter().any(|a| a.unchanged));
    }
    // The reporting ending is not an auxiliary connector or a nominalizer.
    for word in ["먹는답니다보다", "먹는답니다를"] {
        let r = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !r.analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "ending.reporting_polite")),
            "{word}"
        );
    }
    let r = Lemmatizer::new().analyze_word("답니다").unwrap();
    assert!(r.analyses.iter().any(|a| path(a, &["달다"], &["습니다"])));
    assert!(
        r.analyses
            .iter()
            .any(|a| a.lemmas[0].kind == LemmaKind::Unclassified)
    );
}
