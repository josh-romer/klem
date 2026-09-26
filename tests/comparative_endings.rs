//! COV-016: KRDict -듯/-듯이, distinct from the spaced bound noun 듯.
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
fn comparative_endings_keep_stems_prefinals_and_auxiliary_order() {
    for ending in ["듯", "듯이"] {
        for (stem, lemmas, prefix) in [
            ("보", vec!["보다"], vec![]),
            ("먹", vec!["먹다"], vec![]),
            ("살", vec!["살다"], vec![]),
            ("듣", vec!["듣다"], vec![]),
            ("흐르", vec!["흐르다"], vec![]),
            ("좋", vec!["좋다"], vec![]),
            ("예쁘", vec!["예쁘다"], vec![]),
            ("보시", vec!["보다"], vec!["시"]),
            ("봤", vec!["보다"], vec!["었"]),
            ("보겠", vec!["보다"], vec!["겠"]),
            ("보셨겠", vec!["보다"], vec!["시", "었", "겠"]),
            ("학생이", vec!["학생", "이다"], vec![]),
            ("아니", vec!["아니다"], vec![]),
            ("먹어보", vec!["먹다", "보다"], vec!["어"]),
            ("먹고있었", vec!["먹다", "있다"], vec!["고", "었"]),
        ] {
            let word = format!("{stem}{ending}");
            let result = Lemmatizer::new().analyze_word(&word).unwrap();
            let mut forms = prefix;
            forms.push(ending);
            let a = result
                .analyses
                .iter()
                .find(|a| path(a, &lemmas, &forms))
                .expect(&word);
            assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
            assert!(a.rules.iter().any(|r| r == "ending"));
            if lemmas.len() == 2 && lemmas[1] != "이다" {
                assert_eq!(a.lemmas[1].kind, LemmaKind::Auxiliary);
            }
            assert!(result.analyses.iter().any(|a| a.unchanged));
            for candidate in &result.analyses {
                let parts = candidate.breakdown().expect(&word);
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
    }
}

#[test]
fn comparative_endings_do_not_invent_vowel_recovery_or_auxiliary_connections() {
    for (word, lemmas, forms) in [
        ("보으듯이", vec!["보다"], vec!["듯이"]),
        ("먹으듯이", vec!["먹다"], vec!["듯이"]),
        ("살듯이", vec!["사다"], vec!["듯이"]),
        ("들듯이", vec!["듣다"], vec!["듯이"]),
        ("도우듯이", vec!["돕다"], vec!["듯이"]),
        ("몰라듯이", vec!["모르다"], vec!["듯이"]),
        ("보듯이", vec!["보다"], vec!["듯", "이"]),
        ("먹듯이보다", vec!["먹다", "보다"], vec!["듯이", "다"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
    // 들다 is still a possible literal stem: forbid only the spurious 듣다 recovery.
    assert!(
        Lemmatizer::new()
            .analyze_word("들듯이")
            .unwrap()
            .analyses
            .iter()
            .any(|a| path(a, &["들다"], &["듯이"]))
    );
}
