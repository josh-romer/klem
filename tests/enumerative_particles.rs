//! COV-018e: enumerative particles and their separate ending/copula readings.
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
fn enumeration_preserves_nominals_composition_and_distinct_readings() {
    for (word, lemmas, forms) in [
        ("학생이라든가", vec!["학생"], vec!["이라든가"]),
        ("학교라든가", vec!["학교"], vec!["라든가"]),
        ("길이라든가", vec!["길"], vec!["이라든가"]),
        ("밥이라든지", vec!["밥"], vec!["이라든지"]),
        ("학교라든지", vec!["학교"], vec!["라든지"]),
        ("학생이든가", vec!["학생"], vec!["이든가"]),
        ("학교든가", vec!["학교"], vec!["든가"]),
        ("학교에서든가", vec!["학교"], vec!["에서", "든가"]),
        ("학교에서라든지", vec!["학교"], vec!["에서", "라든지"]),
        ("학교에서라든가", vec!["학교"], vec!["에서", "라든가"]),
        ("학생만이든가", vec!["학생"], vec!["만", "이든가"]),
        ("학생들이라든가", vec!["학생"], vec!["들", "이라든가"]),
        (
            "선생님들이라든지",
            vec!["선생"],
            vec!["님", "들", "이라든지"],
        ),
        ("학생이라든가요", vec!["학생"], vec!["이라든가", "요"]),
        ("학교라든지요", vec!["학교"], vec!["라든지", "요"]),
        ("먹기라든가", vec!["먹다"], vec!["기", "라든가"]),
        ("먹음이라든지", vec!["먹다"], vec!["음", "이라든지"]),
        ("먹었음이든가", vec!["먹다"], vec!["었", "음", "이든가"]),
        (
            "학생다움이라든가",
            vec!["학생"],
            vec!["답다", "음", "이라든가"],
        ),
        (
            "먹어보기라든지",
            vec!["먹다", "보다"],
            vec!["어", "기", "라든지"],
        ),
        ("먹는다든가", vec!["먹다"], vec!["는다", "든가"]),
        ("산다든가", vec!["살다"], vec!["는다", "든가"]),
        ("먹으신다든가", vec!["먹다"], vec!["시", "는다", "든가"]),
        (
            "먹어보신다든가",
            vec!["먹다", "보다"],
            vec!["어", "시", "는다", "든가"],
        ),
        ("먹었다든가", vec!["먹다"], vec!["었", "다", "든가"]),
        ("좋다든가", vec!["좋다"], vec!["다", "든가"]),
        ("먹으라든가", vec!["먹다"], vec!["으라", "든가"]),
        ("먹어라든가", vec!["먹다"], vec!["어라", "든가"]),
        ("학생이라든가", vec!["학생", "이다"], vec!["라", "든가"]),
        ("학교라든가", vec!["학교", "이다"], vec!["라", "든가"]),
        ("학생이라든지", vec!["학생", "이다"], vec!["라", "든지"]),
    ] {
        let engine = Lemmatizer::new();
        let result = engine.analyze_word(word).unwrap();
        let analysis = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(
            analysis.morphemes.last().unwrap().kind,
            MorphemeKind::Particle
        );
        if forms.iter().any(|f| {
            matches!(
                *f,
                "든가" | "이든가" | "라든가" | "이라든가" | "라든지" | "이라든지"
            )
        }) {
            assert!(
                analysis.rules.iter().any(|r| r == "particle.enumerative"),
                "{word}"
            );
        }
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
        ("학생이라든가", vec!["학생", "이다"], vec!["라든가"]),
        ("먹는다든가", vec!["먹다"], vec!["는다든가"]),
        ("학교이든가", vec!["학교", "이다"], vec!["든가"]),
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
    for word in ["빨리라든가", "빨리라든지", "빨리든가"] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text == "빨리" && a.lemmas[0].kind == LemmaKind::Adverbial)
        );
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text == "빠르다" && a.morphemes[0].form == "이")
        );
    }
    for (word, rule) in [
        ("ABC이라든가", "pronunciation.assumed_consonant"),
        ("ABC라든가", "pronunciation.assumed_vowel"),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text == "ABC" && a.rules.iter().any(|r| r == rule))
        );
    }
}

#[test]
fn enumeration_rejects_wrong_allomorphs_unlicensed_clauses_and_repetition() {
    for (word, lemmas, forms) in [
        ("학생이신다", vec!["학생", "이다"], vec!["시", "는다"]),
        (
            "학생이신다든가",
            vec!["학생", "이다"],
            vec!["시", "는다", "든가"],
        ),
        (
            "먹고싶으신다",
            vec!["먹다", "싶다"],
            vec!["고", "시", "는다"],
        ),
        (
            "먹고싶으신다든가",
            vec!["먹다", "싶다"],
            vec!["고", "시", "는다", "든가"],
        ),
        ("학생다우신다", vec!["학생"], vec!["답다", "시", "는다"]),
        (
            "학생다우신다든가",
            vec!["학생"],
            vec!["답다", "시", "는다", "든가"],
        ),
        ("학생라든가", vec!["학생"], vec!["라든가"]),
        ("학교이라든가", vec!["학교"], vec!["이라든가"]),
        ("길라든지", vec!["길"], vec!["라든지"]),
        ("학교이라든지", vec!["학교"], vec!["이라든지"]),
        ("학생든가", vec!["학생"], vec!["든가"]),
        ("학생이든가", vec!["학생"], vec!["이", "든가"]),
        ("학교가든가", vec!["학교"], vec!["가", "든가"]),
        ("학교이든가", vec!["학교"], vec!["이든가"]),
        ("학교이라든가", vec!["학교"], vec!["이", "라든가"]),
        ("학교가라든지", vec!["학교"], vec!["가", "라든지"]),
        ("학생만이라든가", vec!["학생"], vec!["만", "이라든가"]),
        ("학교라든가라든지", vec!["학교"], vec!["라든가", "라든지"]),
        ("학교든가든지", vec!["학교"], vec!["든가", "든지"]),
        ("학교든지든가", vec!["학교"], vec!["든지", "든가"]),
        ("먹고라든지", vec!["먹다"], vec!["고", "라든지"]),
        ("먹는든가", vec!["먹다"], vec!["는", "든가"]),
        ("먹고든가", vec!["먹다"], vec!["고", "든가"]),
        ("먹음라든가", vec!["먹다"], vec!["음", "라든가"]),
        ("먹기이라든지", vec!["먹다"], vec!["기", "이라든지"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}

#[test]
fn choice_ending_has_its_own_literal_boundary_and_prefinal_license() {
    for (word, lemmas, forms) in [
        ("먹든가", vec!["먹다"], vec!["든가"]),
        ("가든가", vec!["가다"], vec!["든가"]),
        ("살든가", vec!["살다"], vec!["든가"]),
        ("돕든가", vec!["돕다"], vec!["든가"]),
        ("먹으셨든가", vec!["먹다"], vec!["시", "었", "든가"]),
        ("먹었든가", vec!["먹다"], vec!["었", "든가"]),
        ("좋든가", vec!["좋다"], vec!["든가"]),
        ("학교이든가", vec!["학교", "이다"], vec!["든가"]),
        ("학생이든가", vec!["학생", "이다"], vec!["든가"]),
        ("먹고싶든가", vec!["먹다", "싶다"], vec!["고", "든가"]),
        ("학생답든가", vec!["학생"], vec!["답다", "든가"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending.choice"));
        assert!(a.breakdown().is_some());
    }
    for (word, lemma, forms) in [
        ("사든가", "살다", vec!["든가"]),
        ("도우든가", "돕다", vec!["든가"]),
        ("들든가", "듣다", vec!["든가"]),
        ("먹겠든가", "먹다", vec!["겠", "든가"]),
        ("먹더든가", "먹다", vec!["더", "든가"]),
        ("먹어야겠든가", "먹다", vec!["어야겠", "든가"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &[lemma], &forms)),
            "{word}"
        );
    }
}
