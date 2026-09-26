//! COV-017c: literal -다가 remains distinct from vowel-boundary -어다가.
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
fn daga_preserves_stems_past_honorifics_copulas_and_auxiliary_order() {
    for (word, lemmas, forms) in [
        ("먹다가", vec!["먹다"], vec!["다가"]),
        ("가다가", vec!["가다"], vec!["다가"]),
        ("살다가", vec!["살다"], vec!["다가"]),
        ("듣다가", vec!["듣다"], vec!["다가"]),
        ("돕다가", vec!["돕다"], vec!["다가"]),
        ("덥다가", vec!["덥다"], vec!["다가"]),
        ("쓰다가", vec!["쓰다"], vec!["다가"]),
        ("갔다가", vec!["가다"], vec!["었", "다가"]),
        ("불렀다가", vec!["부르다"], vec!["었", "다가"]),
        ("먹으시다가", vec!["먹다"], vec!["시", "다가"]),
        ("먹으셨다가", vec!["먹다"], vec!["시", "었", "다가"]),
        ("갔었다가", vec!["가다"], vec!["었", "었", "다가"]),
        ("학생이다가", vec!["학생", "이다"], vec!["다가"]),
        ("학생이었다가", vec!["학생", "이다"], vec!["었", "다가"]),
        ("먹어보다가", vec!["먹다", "보다"], vec!["어", "다가"]),
        ("먹고있다가", vec!["먹다", "있다"], vec!["고", "다가"]),
        ("학생답다가", vec!["학생"], vec!["답다", "다가"]),
        ("학생다웠다가", vec!["학생"], vec!["답다", "었", "다가"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending"));
        for m in &a.morphemes {
            assert_eq!(
                m.kind,
                match m.form.as_str() {
                    "답다" => MorphemeKind::Suffix,
                    "시" | "었" => MorphemeKind::Prefinal,
                    _ => MorphemeKind::Ending,
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
}

#[test]
fn daga_and_eodaga_preserve_distinct_readings_and_boundaries() {
    let result = Lemmatizer::new().analyze_word("가다가").unwrap();
    for form in ["다가", "어다가"] {
        assert!(result.analyses.iter().any(|a| path(a, &["가다"], &[form])));
    }
    for (word, lemma) in [
        ("먹어다가", "먹다"),
        ("빌려다가", "빌리다"),
        ("도와다가", "돕다"),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &[lemma], &["어다가"]))
        );
    }
    for (word, lemmas, forms) in [
        ("먹으다가", vec!["먹다"], vec!["다가"]),
        ("들다가", vec!["듣다"], vec!["다가"]),
        ("도우다가", vec!["돕다"], vec!["다가"]),
        ("몰라다가", vec!["모르다"], vec!["다가"]),
        ("살다가", vec!["사다"], vec!["다가"]),
        ("먹겠다가", vec!["먹다"], vec!["겠", "다가"]),
        ("살겠다가", vec!["살다"], vec!["겠", "다가"]),
        ("먹더다가", vec!["먹다"], vec!["더", "다가"]),
        ("먹다가보다", vec!["먹다", "보다"], vec!["다가", "다"]),
        ("학생답았다가", vec!["학생"], vec!["답다", "었", "다가"]),
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
