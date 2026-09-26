//! COV-018g: enumerative 다/이다, separate from emphasis and copular endings.
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
fn enumerative_da_preserves_nominal_composition_and_homonymous_readings() {
    for (word, lemmas, forms) in [
        ("구두다", vec!["구두"], vec!["다"]),
        ("노래다", vec!["노래"], vec!["다"]),
        ("옷이다", vec!["옷"], vec!["이다"]),
        ("춤이다", vec!["춤"], vec!["이다"]),
        ("배드민턴이다", vec!["배드민턴"], vec!["이다"]),
        ("수영이다", vec!["수영"], vec!["이다"]),
        ("수박이다", vec!["수박"], vec!["이다"]),
        ("귤이다", vec!["귤"], vec!["이다"]),
        ("학교다", vec!["학교"], vec!["다"]),
        ("학생이다", vec!["학생"], vec!["이다"]),
        ("학생들이다", vec!["학생"], vec!["들", "이다"]),
        ("선생님이다", vec!["선생"], vec!["님", "이다"]),
        ("먹기다", vec!["먹다"], vec!["기", "다"]),
        ("먹음이다", vec!["먹다"], vec!["음", "이다"]),
        ("먹어보기다", vec!["먹다", "보다"], vec!["어", "기", "다"]),
        ("학생다움이다", vec!["학생"], vec!["답다", "음", "이다"]),
        ("학교다요", vec!["학교"], vec!["다", "요"]),
        ("학생이다요", vec!["학생"], vec!["이다", "요"]),
    ] {
        let engine = Lemmatizer::new();
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Particle);
        assert!(
            a.rules.iter().any(|r| r == "particle.enumerative_da"),
            "{word}"
        );
        assert!(
            !a.rules.iter().any(|r| r == "particle.emphatic_adverbial"),
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
    for word in ["구두다", "옷이다", "학교다", "학생이다", "저기다"] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.kind == LemmaKind::Copula)
                    && a.morphemes
                        .last()
                        .is_some_and(|m| m.form == "다" && m.kind == MorphemeKind::Ending)),
            "{word}"
        );
    }
    let result = Lemmatizer::new().analyze_word("저기다").unwrap();
    let merged: Vec<_> = result
        .analyses
        .iter()
        .filter(|a| path(a, &["저기"], &["다"]))
        .collect();
    assert_eq!(merged.len(), 1);
    for rule in ["particle.enumerative_da", "particle.emphatic_adverbial"] {
        assert!(merged[0].rules.iter().any(|r| r == rule));
    }
    for (word, form, rule) in [
        ("ABC다", "다", "pronunciation.assumed_vowel"),
        ("ABC이다", "이다", "pronunciation.assumed_consonant"),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &["ABC"], &[form]) && a.rules.iter().any(|r| r == rule)),
            "{word}"
        );
    }
}

#[test]
fn enumerative_da_rejects_wrong_boundaries_case_phrases_and_predicate_endings() {
    for (word, lemmas, forms) in [
        ("학생다", vec!["학생"], vec!["다"]),
        ("학교이다", vec!["학교"], vec!["이다"]),
        ("귤다", vec!["귤"], vec!["다"]),
        ("먹음다", vec!["먹다"], vec!["음", "다"]),
        ("먹기이다", vec!["먹다"], vec!["기", "이다"]),
        ("학교에서다", vec!["학교"], vec!["에서", "다"]),
        ("손으로다", vec!["손"], vec!["으로", "다"]),
        ("학생만이다", vec!["학생"], vec!["만", "이다"]),
        ("학생이다다", vec!["학생"], vec!["이다", "다"]),
        ("학교다다", vec!["학교"], vec!["다", "다"]),
        ("먹고다", vec!["먹다"], vec!["고", "다"]),
        ("먹는다다", vec!["먹다"], vec!["는다", "다"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)
                    && a.rules.iter().any(|r| r == "particle.enumerative_da")),
            "{word}"
        );
    }
    for (word, lemmas, forms) in [
        ("손으로다", vec!["손"], vec!["으로", "다"]),
        ("저기다가", vec!["저기"], vec!["다가"]),
        ("이리다", vec!["이리"], vec!["다"]),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)
                    && a.rules.iter().any(|r| r == "particle.emphatic_adverbial")),
            "{word}"
        );
    }
}
