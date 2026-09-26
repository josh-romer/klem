//! COV-010: bounded suffix hypotheses, not semantic attachment validation.
use klem::breakdown::Component;
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind};

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
fn nominal_suffixes_keep_whole_words_and_compose_with_case_and_copulas() {
    for (word, lemmas, forms) in [
        ("선생님", vec!["선생"], vec!["님"]),
        ("선생님께", vec!["선생"], vec!["님", "께"]),
        ("선생님께선요", vec!["선생"], vec!["님", "께서", "는", "요"]),
        ("선생님들을", vec!["선생"], vec!["님", "들", "을"]),
        ("선생님들이다", vec!["선생", "이다"], vec!["님", "들", "다"]),
        ("선생님이에요", vec!["선생", "이다"], vec!["님", "에요"]),
        ("과학적", vec!["과학"], vec!["적"]),
        ("과학적으로", vec!["과학"], vec!["적", "으로"]),
        ("과학적이다", vec!["과학", "이다"], vec!["적", "다"]),
        (
            "과학적이었어요",
            vec!["과학", "이다"],
            vec!["적", "었", "어요"],
        ),
        ("과학적인", vec!["과학", "이다"], vec!["적", "은"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.lemmas[0].kind, LemmaKind::Nominal);
        assert_eq!(a.morphemes[0].kind, MorphemeKind::Suffix);
        assert!(a.rules.iter().any(|r| r.starts_with("suffix.")));
        assert!(result.analyses.iter().any(|a| a.unchanged), "{word}");
        for a in &result.analyses {
            assert!(a.breakdown().is_some(), "{word}: {a:?}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
    for (word, whole) in [("선생님께", "선생님"), ("과학적이다", "과학적")] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text == whole),
            "{word}"
        );
    }
}

#[test]
fn adjectival_suffix_inflects_before_auxiliaries_and_nominalization() {
    for (word, lemmas, forms) in [
        ("학생답다", vec!["학생"], vec!["답다", "다"]),
        ("학생다워요", vec!["학생"], vec!["답다", "어요"]),
        ("학생다웠어요", vec!["학생"], vec!["답다", "었", "어요"]),
        ("학생다우면", vec!["학생"], vec!["답다", "으면"]),
        ("학생다운", vec!["학생"], vec!["답다", "은"]),
        ("학생답습니다", vec!["학생"], vec!["답다", "습니다"]),
        ("학생답겠어요", vec!["학생"], vec!["답다", "겠", "어요"]),
        (
            "선생님다우셨다",
            vec!["선생"],
            vec!["님", "답다", "시", "었", "다"],
        ),
        ("선생님들답다", vec!["선생"], vec!["님", "들", "답다", "다"]),
        (
            "학생답게됐다",
            vec!["학생", "되다"],
            vec!["답다", "게", "었", "다"],
        ),
        (
            "학생답지않았다",
            vec!["학생", "않다"],
            vec!["답다", "지", "었", "다"],
        ),
        ("학생다움을", vec!["학생"], vec!["답다", "음", "을"]),
        (
            "학생다움만이다",
            vec!["학생", "이다"],
            vec!["답다", "음", "만", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "suffix.adjectival.dap"));
        assert_eq!(a.lemmas[0].kind, LemmaKind::Nominal);
        assert_eq!(
            a.morphemes.iter().find(|m| m.form == "답다").unwrap().kind,
            MorphemeKind::Suffix
        );
        let order = a.breakdown().unwrap();
        let components: Vec<_> = order
            .iter()
            .map(|part| match part {
                Component::Lemma(i) => a.lemmas[*i].text.as_str(),
                Component::Morpheme(i) => a.morphemes[*i].form.as_str(),
            })
            .collect();
        if word == "학생답게됐다" {
            assert_eq!(components, ["학생", "답다", "게", "되다", "었", "다"]);
        }
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
        // Derivation augments the original whole predicate hypothesis.
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text.ends_with("답다")
                    && a.lemmas[0].kind == LemmaKind::Predicate),
            "{word}"
        );
    }
}

#[test]
fn suffix_slots_and_known_irregular_class_reject_specific_invalid_paths() {
    for (word, base, forms) in [
        ("선생님님께", "선생", vec!["님", "님", "께"]),
        ("과학적적이다", "과학", vec!["적", "적", "다"]),
        ("선생들님께", "선생", vec!["들", "님", "께"]),
        ("선생님를", "선생", vec!["님", "를"]),
        ("과학적로", "과학", vec!["적", "로"]),
        ("학생답아요", "학생", vec!["답다", "어요"]),
        ("학생답으면", "학생", vec!["답다", "으면"]),
        ("학생답은", "학생", vec!["답다", "은"]),
        ("학생답는", "학생", vec!["답다", "는"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| a.lemmas[0].text == base
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())),
            "{word}"
        );
    }
    for word in ["님", "적", "답다", "다워요"] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|a| a.lemmas.iter().all(|l| !l.text.is_empty()))
        );
    }
    // Malformed externally supplied derived predicates need their own ending.
    let mut a = Lemmatizer::new()
        .analyze_word("학생답다")
        .unwrap()
        .analyses
        .into_iter()
        .find(|a| path(a, &["학생"], &["답다", "다"]))
        .unwrap();
    a.morphemes.pop();
    assert!(a.breakdown().is_none());
}
