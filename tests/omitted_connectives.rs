//! COV-020e: omitted copula before reviewed consonant-initial endings.
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
fn omitted_connectives_preserve_explicit_copula_parity_and_composition() {
    let engine = Lemmatizer::new();
    for (suffix, canonical) in [
        ("니", "니"),
        ("니", "으니"),
        ("니까", "으니까"),
        ("고", "고"),
        ("지만", "지만"),
        ("지만요", "지만요"),
        ("거든", "거든"),
        ("거든요", "거든요"),
        ("네", "네"),
        ("네요", "네요"),
    ] {
        for (base, nominal) in [
            ("의사", "의사"),
            ("거", "거"),
            ("거", "것"),
            ("어디", "어디"),
        ] {
            let word = format!("{base}{suffix}");
            let full = engine.analyze_word(&format!("{base}이{suffix}")).unwrap();
            let result = engine.analyze_word(&word).unwrap();
            let a = result
                .analyses
                .iter()
                .find(|a| path(a, &[nominal, "이다"], &[canonical]))
                .expect(&word);
            assert_eq!(a.lemmas[0].kind, LemmaKind::Nominal);
            assert_eq!(a.lemmas[1].kind, LemmaKind::Copula);
            assert!(
                a.rules.iter().any(|r| r == "copula.omitted_ending"),
                "{word}"
            );
            assert!(
                full.analyses
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
    }
    for (word, lemmas, forms) in [
        ("노동자니까", vec!["노동자", "이다"], vec!["으니까"]),
        ("거니까요", vec!["것", "이다"], vec!["으니까", "요"]),
        ("의사고도", vec!["의사", "이다"], vec!["고", "도"]),
        ("의사지만은", vec!["의사", "이다"], vec!["지만", "은"]),
        ("먹기니까", vec!["먹다", "이다"], vec!["기", "으니까"]),
        (
            "먹어보기니까",
            vec!["먹다", "보다", "이다"],
            vec!["어", "기", "으니까"],
        ),
        (
            "학생다움이니까",
            vec!["학생", "이다"],
            vec!["답다", "음", "으니까"],
        ),
        ("의사고싶다", vec!["의사", "이다", "싶다"], vec!["고", "다"]),
        (
            "의사고도싶다",
            vec!["의사", "이다", "싶다"],
            vec!["고", "도", "다"],
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
    for (word, form) in [("ABC니까", "으니까"), ("ABC고", "고"), ("ABC네요", "네요")] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &["ABC", "이다"], &[form])
                    && a.rules.iter().any(|r| r == "pronunciation.assumed_vowel")),
            "{word}"
        );
    }
}

#[test]
fn omitted_connectives_do_not_conjugate_nominals_or_replace_lexical_predicates() {
    let engine = Lemmatizer::new();
    for (suffix, form) in [
        ("니", "니"),
        ("니", "으니"),
        ("니까", "으니까"),
        ("고", "고"),
        ("지만", "지만"),
        ("지만요", "지만요"),
        ("거든", "거든"),
        ("거든요", "거든요"),
        ("네", "네"),
        ("네요", "네요"),
    ] {
        for base in ["학생", "길", "먹음"] {
            let word = format!("{base}{suffix}");
            assert!(
                !engine
                    .analyze_word(&word)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| path(a, &[base, "이다"], &[form])),
                "{word}"
            );
        }
    }
    for (word, lemmas, forms) in [
        ("도우니까", vec!["돕", "이다"], vec!["으니까"]),
        ("사니", vec!["살", "이다"], vec!["으니"]),
        ("먹었네", vec!["먹", "이다"], vec!["었", "네"]),
        ("의사었고", vec!["의사", "이다"], vec!["었", "고"]),
        ("의사네요", vec!["의사이다"], vec!["네요"]),
        ("먹음니까", vec!["먹다", "이다"], vec!["음", "으니까"]),
        (
            "학생다움니까",
            vec!["학생", "이다"],
            vec!["답다", "음", "으니까"],
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
        ("먹고", vec!["먹다"], vec!["고"]),
        ("도우니까", vec!["돕다"], vec!["으니까"]),
        ("사니", vec!["살다"], vec!["으니"]),
        ("먹었네", vec!["먹다"], vec!["었", "네"]),
        ("아니니까", vec!["아니다"], vec!["으니까"]),
        ("의사이시니까", vec!["의사", "이다"], vec!["시", "으니까"]),
        ("의사였고", vec!["의사", "이다"], vec!["었", "고"]),
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

#[test]
fn closed_connectives_accept_eun_without_losing_neun_boundary_checks() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹지만은", vec!["먹다"], vec!["지만", "은"]),
        ("먹거든은", vec!["먹다"], vec!["거든", "은"]),
        ("먹으면은", vec!["먹다"], vec!["으면", "은"]),
        ("학생이지만은", vec!["학생", "이다"], vec!["지만", "은"]),
        ("의사지만은", vec!["의사", "이다"], vec!["지만", "은"]),
        ("먹으니까는", vec!["먹다"], vec!["으니까", "는"]),
        ("먹고는", vec!["먹다"], vec!["고", "는"]),
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
    for (word, forms) in [
        ("먹지만는", vec!["지만", "는"]),
        ("먹거든는", vec!["거든", "는"]),
        ("먹고은", vec!["고", "은"]),
        ("먹으니까은", vec!["으니까", "은"]),
        ("먹습니다은", vec!["습니다", "은"]),
        ("먹은은", vec!["은", "은"]),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &["먹다"], &forms)),
            "{word}"
        );
    }
}
