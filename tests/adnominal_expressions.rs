//! COV-017b: bundled (으)려는/자는 expressions, without invented 하다 lemmas.
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
fn shortened_adnominals_preserve_boundaries_prefinals_and_auxiliary_order() {
    for (word, lemmas, forms) in [
        ("가려는", vec!["가다"], vec!["으려는"]),
        ("살려는", vec!["살다"], vec!["으려는"]),
        ("먹으려는", vec!["먹다"], vec!["으려는"]),
        ("들으려는", vec!["듣다"], vec!["으려는"]),
        ("도우려는", vec!["돕다"], vec!["으려는"]),
        ("지으려는", vec!["짓다"], vec!["으려는"]),
        ("모르려는", vec!["모르다"], vec!["으려는"]),
        ("가시려는", vec!["가다"], vec!["시", "으려는"]),
        ("먹으시려는", vec!["먹다"], vec!["시", "으려는"]),
        ("가자는", vec!["가다"], vec!["자는"]),
        ("놀자는", vec!["놀다"], vec!["자는"]),
        ("먹자는", vec!["먹다"], vec!["자는"]),
        ("듣자는", vec!["듣다"], vec!["자는"]),
        ("돕자는", vec!["돕다"], vec!["자는"]),
        ("바꿔보자는", vec!["바꾸다", "보다"], vec!["어", "자는"]),
        ("먹어보려는", vec!["먹다", "보다"], vec!["어", "으려는"]),
        ("먹지않으려는", vec!["먹다", "않다"], vec!["지", "으려는"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending.adnominal_expression"));
        for m in &a.morphemes {
            assert_eq!(
                m.kind,
                if m.form == "시" {
                    MorphemeKind::Prefinal
                } else {
                    MorphemeKind::Ending
                }
            );
        }
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for candidate in &result.analyses {
            assert_eq!(
                candidate.breakdown().expect(word).len(),
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
    // 자는 is also 자다 + 는: retain the whole-word lexical stem alternative.
    let result = Lemmatizer::new().analyze_word("자는").unwrap();
    assert!(result.analyses.iter().any(|a| path(a, &["자다"], &["는"])));
}

#[test]
fn shortened_adnominals_reject_wrong_boundaries_and_terminal_attachments() {
    for (word, lemmas, forms) in [
        ("먹려는", vec!["먹다"], vec!["으려는"]),
        ("가으려는", vec!["가다"], vec!["으려는"]),
        ("살으려는", vec!["살다"], vec!["으려는"]),
        ("들려는", vec!["듣다"], vec!["으려는"]),
        ("몰라려는", vec!["모르다"], vec!["으려는"]),
        ("먹으자는", vec!["먹다"], vec!["자는"]),
        ("들자는", vec!["듣다"], vec!["자는"]),
        ("도우자는", vec!["돕다"], vec!["자는"]),
        ("먹었으려는", vec!["먹다"], vec!["었", "으려는"]),
        ("먹겠으려는", vec!["먹다"], vec!["겠", "으려는"]),
        ("먹었자는", vec!["먹다"], vec!["었", "자는"]),
        ("먹으려는", vec!["먹다", "하다"], vec!["으려고", "는"]),
        ("먹자는요", vec!["먹다"], vec!["자는", "요"]),
        ("먹으려는요", vec!["먹다"], vec!["으려는", "요"]),
        ("먹자는보다", vec!["먹다", "보다"], vec!["자는", "다"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
}
