//! COV-017d: bundled -냐는/-느냐는, without inferred 하다 components.
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
fn quoted_questions_keep_boundaries_prefinals_copulas_and_auxiliaries() {
    for ending in ["냐는", "느냐는"] {
        for (stem, lemmas, prefix) in [
            ("하", vec!["하다"], vec![]),
            ("먹", vec!["먹다"], vec![]),
            ("사", vec!["살다"], vec![]),
            ("듣", vec!["듣다"], vec![]),
            ("돕", vec!["돕다"], vec![]),
            ("있", vec!["있다"], vec![]),
            ("없", vec!["없다"], vec![]),
            ("먹으시", vec!["먹다"], vec!["시"]),
            ("했", vec!["하다"], vec!["었"]),
            ("먹겠", vec!["먹다"], vec!["겠"]),
            ("먹으셨겠", vec!["먹다"], vec!["시", "었", "겠"]),
            ("먹어봤", vec!["먹다", "보다"], vec!["어", "었"]),
            ("먹고있", vec!["먹다", "있다"], vec!["고"]),
        ] {
            let word = format!("{stem}{ending}");
            let mut forms = prefix;
            forms.push(ending);
            let result = Lemmatizer::new().analyze_word(&word).unwrap();
            let a = result
                .analyses
                .iter()
                .find(|a| path(a, &lemmas, &forms))
                .expect(&word);
            assert!(a.rules.iter().any(|r| r == "ending.adnominal_expression"));
            for m in &a.morphemes {
                assert_eq!(
                    m.kind,
                    if matches!(m.form.as_str(), "시" | "었" | "겠") {
                        MorphemeKind::Prefinal
                    } else {
                        MorphemeKind::Ending
                    }
                );
            }
            assert!(result.analyses.iter().any(|a| a.unchanged));
            for candidate in &result.analyses {
                assert_eq!(
                    candidate.breakdown().expect(&word).len(),
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
    for (word, lemmas, forms) in [
        ("아니냐는", vec!["아니다"], vec!["냐는"]),
        ("좋냐는", vec!["좋다"], vec!["냐는"]),
        ("춥냐는", vec!["춥다"], vec!["냐는"]),
        ("학생이냐는", vec!["학생", "이다"], vec!["냐는"]),
        ("학생이었냐는", vec!["학생", "이다"], vec!["었", "냐는"]),
        ("학생이었느냐는", vec!["학생", "이다"], vec!["었", "느냐는"]),
        ("학생답냐는", vec!["학생"], vec!["답다", "냐는"]),
        ("학생답겠느냐는", vec!["학생"], vec!["답다", "겠", "느냐는"]),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
}

#[test]
fn quoted_questions_reject_unlicensed_recoveries_and_preserve_other_readings() {
    for (word, lemmas, forms) in [
        ("살냐는", vec!["살다"], vec!["냐는"]),
        ("살느냐는", vec!["살다"], vec!["느냐는"]),
        ("들냐는", vec!["듣다"], vec!["냐는"]),
        ("도우느냐는", vec!["돕다"], vec!["느냐는"]),
        ("몰라냐는", vec!["모르다"], vec!["냐는"]),
        ("먹냐는요", vec!["먹다"], vec!["냐는", "요"]),
        ("먹느냐는보다", vec!["먹다", "보다"], vec!["느냐는", "다"]),
        ("먹냐는", vec!["먹다", "하다"], vec!["냐고", "는"]),
        ("학생답느냐는", vec!["학생"], vec!["답다", "느냐는"]),
        ("학생이느냐는", vec!["학생", "이다"], vec!["느냐는"]),
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
    // ㄹ recovery is a hypothesis alongside the open stem, not a replacement.
    let result = Lemmatizer::new().analyze_word("사냐는").unwrap();
    for lemma in ["사다", "살다"] {
        assert!(result.analyses.iter().any(|a| path(a, &[lemma], &["냐는"])));
    }
}

#[test]
fn adjective_question_allomorphs_and_retrospective_questions() {
    for (word, lemmas, forms, recovery) in [
        ("좋으냐는", vec!["좋다"], vec!["으냐는"], "boundary.eu"),
        ("기냐는", vec!["길다"], vec!["냐는"], "deletion.rieul"),
        ("추우냐는", vec!["춥다"], vec!["으냐는"], "irregular.bieup"),
        (
            "파라냐는",
            vec!["파랗다"],
            vec!["으냐는"],
            "irregular.hieut",
        ),
        (
            "그러냐는",
            vec!["그렇다"],
            vec!["으냐는"],
            "irregular.hieut",
        ),
        (
            "학생다우냐는",
            vec!["학생"],
            vec!["답다", "으냐는"],
            "irregular.bieup",
        ),
        (
            "먹더냐는",
            vec!["먹다"],
            vec!["더", "냐는"],
            "prefinal.retrospective",
        ),
        (
            "살더냐는",
            vec!["살다"],
            vec!["더", "냐는"],
            "prefinal.retrospective",
        ),
        (
            "먹으셨겠더냐는",
            vec!["먹다"],
            vec!["시", "었", "겠", "더", "냐는"],
            "prefinal.retrospective",
        ),
        (
            "학생이더냐는",
            vec!["학생", "이다"],
            vec!["더", "냐는"],
            "copula",
        ),
        (
            "먹어봤더냐는",
            vec!["먹다", "보다"],
            vec!["어", "었", "더", "냐는"],
            "auxiliary",
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(
            a.rules.iter().any(|r| r == recovery),
            "{word}: {:?}",
            a.rules
        );
        assert!(a.rules.iter().any(|r| r == "ending.adnominal_expression"));
        for candidate in &result.analyses {
            assert_eq!(
                candidate.breakdown().expect(word).len(),
                candidate.lemmas.len() + candidate.morphemes.len()
            );
        }
        assert_eq!(
            result,
            Lemmatizer::new()
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    for (word, lemmas, forms) in [
        ("길으냐는", vec!["길다"], vec!["으냐는"]),
        ("학생답으냐는", vec!["학생"], vec!["답다", "으냐는"]),
        ("학생이으냐는", vec!["학생", "이다"], vec!["으냐는"]),
        ("파래냐는", vec!["파랗다"], vec!["으냐는"]),
        ("추워냐는", vec!["춥다"], vec!["으냐는"]),
        ("추우냐는", vec!["춥다"], vec!["냐는"]),
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
