//! COV-017h: intention/expectation and concessive ending boundaries.
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
fn intention_and_concession_preserve_boundaries_groups_and_normalization() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("되리라고", vec!["되다"], vec!["으리라고"]),
        ("먹으리라고", vec!["먹다"], vec!["으리라고"]),
        ("살리라고", vec!["살다"], vec!["으리라고"]),
        ("들으리라고", vec!["듣다"], vec!["으리라고"]),
        ("지으리라고", vec!["짓다"], vec!["으리라고"]),
        ("도우리라고", vec!["돕다"], vec!["으리라고"]),
        ("빨가리라고", vec!["빨갛다"], vec!["으리라고"]),
        (
            "먹으셨겠으리라고",
            vec!["먹다"],
            vec!["시", "었", "겠", "으리라고"],
        ),
        ("먹었었으리라고", vec!["먹다"], vec!["었", "었", "으리라고"]),
        ("학생이리라고", vec!["학생", "이다"], vec!["으리라고"]),
        ("학생다우리라고", vec!["학생"], vec!["답다", "으리라고"]),
        ("먹어보리라고", vec!["먹다", "보다"], vec!["어", "으리라고"]),
        (
            "먹고싶으리라고",
            vec!["먹다", "싶다"],
            vec!["고", "으리라고"],
        ),
        ("할지라도", vec!["하다"], vec!["을지라도"]),
        ("먹을지라도", vec!["먹다"], vec!["을지라도"]),
        ("살지라도", vec!["살다"], vec!["을지라도"]),
        ("들을지라도", vec!["듣다"], vec!["을지라도"]),
        ("지을지라도", vec!["짓다"], vec!["을지라도"]),
        ("도울지라도", vec!["돕다"], vec!["을지라도"]),
        ("빨갈지라도", vec!["빨갛다"], vec!["을지라도"]),
        ("먹으셨을지라도", vec!["먹다"], vec!["시", "었", "을지라도"]),
        ("먹었었을지라도", vec!["먹다"], vec!["었", "었", "을지라도"]),
        ("학생일지라도", vec!["학생", "이다"], vec!["을지라도"]),
        ("학생다울지라도", vec!["학생"], vec!["답다", "을지라도"]),
        ("먹어볼지라도", vec!["먹다", "보다"], vec!["어", "을지라도"]),
        (
            "먹고싶을지라도",
            vec!["먹다", "싶다"],
            vec!["고", "을지라도"],
        ),
        ("들자면", vec!["들다"], vec!["자면"]),
        ("먹자면", vec!["먹다"], vec!["자면"]),
        ("가자면", vec!["가다"], vec!["자면"]),
        ("살자면", vec!["살다"], vec!["자면"]),
        ("듣자면", vec!["듣다"], vec!["자면"]),
        ("돕자면", vec!["돕다"], vec!["자면"]),
        ("먹으시자면", vec!["먹다"], vec!["시", "자면"]),
        ("먹어보자면", vec!["먹다", "보다"], vec!["어", "자면"]),
        ("먹지말자면", vec!["먹다", "말다"], vec!["지", "자면"]),
        (
            "먹고싶어하자면",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "어", "자면"],
        ),
        // The terminal restriction does not reach into the left predicate.
        (
            "먹었어야하자면",
            vec!["먹다", "하다"],
            vec!["었", "어야", "자면"],
        ),
        (
            "학생이고싶어하자면",
            vec!["학생", "이다", "싶다", "하다"],
            vec!["고", "어", "자면"],
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending"));
        if lemmas.last() == Some(&"보다") {
            assert_eq!(a.lemmas.last().unwrap().kind, LemmaKind::Auxiliary);
        }
        for candidate in &result.analyses {
            assert!(candidate.breakdown().is_some(), "{word}");
            assert!(
                candidate
                    .rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
        }
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    // These endings preserve lexical ambiguity at genuinely ambiguous boundaries.
    for (word, lemmas, forms) in [
        ("살지라도", vec!["사다"], vec!["을지라도"]),
        ("들자면", vec!["들자다"], vec!["으면"]),
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
fn ending_licenses_do_not_relax_allomorphs_classes_or_auxiliary_connectors() {
    for (word, lemmas, forms) in [
        ("먹리라고", vec!["먹다"], vec!["으리라고"]),
        ("가으리라고", vec!["가다"], vec!["으리라고"]),
        ("살으리라고", vec!["살다"], vec!["으리라고"]),
        ("먹더리라고", vec!["먹다"], vec!["더", "으리라고"]),
        ("가지라도", vec!["가다"], vec!["을지라도"]),
        ("가을지라도", vec!["가다"], vec!["을지라도"]),
        ("살을지라도", vec!["살다"], vec!["을지라도"]),
        ("먹겠을지라도", vec!["먹다"], vec!["겠", "을지라도"]),
        ("먹덜지라도", vec!["먹다"], vec!["더", "을지라도"]),
        ("들자면", vec!["듣다"], vec!["자면"]),
        ("도우자면", vec!["돕다"], vec!["자면"]),
        ("먹었자면", vec!["먹다"], vec!["었", "자면"]),
        ("먹겠자면", vec!["먹다"], vec!["겠", "자면"]),
        ("먹더자면", vec!["먹다"], vec!["더", "자면"]),
        ("학생이자면", vec!["학생", "이다"], vec!["자면"]),
        ("학생이시자면", vec!["학생", "이다"], vec!["시", "자면"]),
        ("학생답으리라고", vec!["학생"], vec!["답다", "으리라고"]),
        ("학생답을지라도", vec!["학생"], vec!["답다", "을지라도"]),
        ("학생답자면", vec!["학생"], vec!["답다", "자면"]),
        ("학생다우시자면", vec!["학생"], vec!["답다", "시", "자면"]),
        ("먹고싶자면", vec!["먹다", "싶다"], vec!["고", "자면"]),
        (
            "먹고싶으시자면",
            vec!["먹다", "싶다"],
            vec!["고", "시", "자면"],
        ),
        (
            "먹고싶지않자면",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "자면"],
        ),
        ("먹자면보다", vec!["먹다", "보다"], vec!["자면", "다"]),
        (
            "먹으리라고보다",
            vec!["먹다", "보다"],
            vec!["으리라고", "다"],
        ),
        (
            "먹을지라도보다",
            vec!["먹다", "보다"],
            vec!["을지라도", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
