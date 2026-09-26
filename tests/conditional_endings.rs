//! COV-017a: KRDict -ㄴ다면/-는다면 present conditional allomorphs.
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
fn present_conditionals_recover_stems_honorifics_and_auxiliary_groups() {
    for (word, lemmas, forms) in [
        ("한다면", vec!["하다"], vec!["는다면"]),
        ("간다면", vec!["가다"], vec!["는다면"]),
        ("산다면", vec!["살다"], vec!["는다면"]),
        ("먹는다면", vec!["먹다"], vec!["는다면"]),
        ("듣는다면", vec!["듣다"], vec!["는다면"]),
        ("돕는다면", vec!["돕다"], vec!["는다면"]),
        ("하신다면", vec!["하다"], vec!["시", "는다면"]),
        ("먹으신다면", vec!["먹다"], vec!["시", "는다면"]),
        ("사신다면", vec!["살다"], vec!["시", "는다면"]),
        ("들으신다면", vec!["듣다"], vec!["시", "는다면"]),
        ("도우신다면", vec!["돕다"], vec!["시", "는다면"]),
        ("먹어본다면", vec!["먹다", "보다"], vec!["어", "는다면"]),
        ("먹지않는다면", vec!["먹다", "않다"], vec!["지", "는다면"]),
        // Past on the left predicate is independent of the final auxiliary's ending.
        (
            "먹었어야한다면",
            vec!["먹다", "하다"],
            vec!["었", "어야", "는다면"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending"));
        if lemmas.len() > 1 {
            assert_eq!(a.lemmas[1].kind, LemmaKind::Auxiliary);
        }
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for candidate in &result.analyses {
            let parts = candidate.breakdown().expect(word);
            assert_eq!(
                parts.len(),
                candidate.lemmas.len() + candidate.morphemes.len()
            );
            assert!(
                candidate
                    .rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
        }
        assert_eq!(
            result,
            Lemmatizer::new()
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    // Attached ㄴ keeps both open and ㄹ stem hypotheses.
    let result = Lemmatizer::new().analyze_word("산다면").unwrap();
    assert!(
        result
            .analyses
            .iter()
            .any(|a| path(a, &["사다"], &["는다면"]))
    );
}

#[test]
fn present_conditionals_reject_wrong_allomorphs_and_vowel_only_recoveries() {
    for (word, lemma, forms) in [
        ("가는다면", "가다", vec!["는다면"]),
        ("살는다면", "살다", vec!["는다면"]),
        ("먹은다면", "먹다", vec!["는다면"]),
        ("먹으는다면", "먹다", vec!["는다면"]),
        ("들은다면", "듣다", vec!["는다면"]),
        ("도운다면", "돕다", vec!["는다면"]),
        ("빨간다면", "빨갛다", vec!["는다면"]),
        ("몰란다면", "모르다", vec!["는다면"]),
        ("먹었는다면", "먹다", vec!["었", "는다면"]),
        ("먹겠는다면", "먹다", vec!["겠", "는다면"]),
        ("먹더는다면", "먹다", vec!["더", "는다면"]),
        ("먹으셨는다면", "먹다", vec!["시", "었", "는다면"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &[lemma], &forms)),
            "{word}: {lemma}"
        );
    }
    // Rejecting the new present path must not affect existing plain 다면.
    for (word, lemma, forms) in [
        ("먹었다면", "먹다", vec!["었", "다면"]),
        ("먹겠다면", "먹다", vec!["겠", "다면"]),
        ("먹으셨다면", "먹다", vec!["시", "었", "다면"]),
        ("좋다면", "좋다", vec!["다면"]),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &[lemma], &forms)),
            "{word}"
        );
    }
}
