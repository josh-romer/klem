//! COV-019e: contrastive 고 + 는 before 싶다, including contracted 곤.
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
fn desire_topic_keeps_contracted_full_and_composed_paths() {
    let engine = Lemmatizer::new();
    for (word, full, lemmas, forms) in [
        (
            "놀곤싶지만",
            "놀고는싶지만",
            vec!["놀다", "싶다"],
            vec!["고", "는", "지만"],
        ),
        (
            "먹곤싶다",
            "먹고는싶다",
            vec!["먹다", "싶다"],
            vec!["고", "는", "다"],
        ),
        (
            "살곤싶어요",
            "살고는싶어요",
            vec!["살다", "싶다"],
            vec!["고", "는", "어요"],
        ),
        (
            "돕곤싶었다",
            "돕고는싶었다",
            vec!["돕다", "싶다"],
            vec!["고", "는", "었", "다"],
        ),
        (
            "먹곤싶겠지만",
            "먹고는싶겠지만",
            vec!["먹다", "싶다"],
            vec!["고", "는", "겠", "지만"],
        ),
        (
            "먹곤싶으셨다",
            "먹고는싶으셨다",
            vec!["먹다", "싶다"],
            vec!["고", "는", "시", "었", "다"],
        ),
        (
            "먹어보곤싶었다",
            "먹어보고는싶었다",
            vec!["먹다", "보다", "싶다"],
            vec!["어", "고", "는", "었", "다"],
        ),
        (
            "먹곤싶어한다",
            "먹고는싶어한다",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "는", "어", "는다"],
        ),
        (
            "먹곤싶지않다",
            "먹고는싶지않다",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "는", "지", "다"],
        ),
        (
            "학생이곤싶다",
            "학생이고는싶다",
            vec!["학생", "이다", "싶다"],
            vec!["고", "는", "다"],
        ),
        (
            "의사곤싶다",
            "의사고는싶다",
            vec!["의사", "이다", "싶다"],
            vec!["고", "는", "다"],
        ),
        (
            "먹기곤싶다",
            "먹기고는싶다",
            vec!["먹다", "이다", "싶다"],
            vec!["기", "고", "는", "다"],
        ),
    ] {
        let short = engine.analyze_word(word).unwrap();
        let full_result = engine.analyze_word(full).unwrap();
        let a = short
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(
            full_result
                .analyses
                .iter()
                .any(|f| f.lemmas == a.lemmas && f.morphemes == a.morphemes),
            "{full}"
        );
        assert!(a.rules.iter().any(|r| r == "particle.contraction.n"));
        assert!(a.rules.iter().any(|r| r == "auxiliary.internal_particle"));
        let particle = a.morphemes.iter().position(|m| m.form == "는").unwrap();
        assert_eq!(a.morphemes[particle].kind, MorphemeKind::Particle);
        assert_eq!(a.morphemes[particle - 1].form, "고");
        assert_eq!(a.morphemes[particle - 1].kind, MorphemeKind::Ending);
        assert_eq!(
            a.lemmas.iter().find(|l| l.text == "싶다").unwrap().kind,
            LemmaKind::Auxiliary
        );
        for result in [&short, &full_result] {
            assert!(result.analyses.iter().any(|a| a.unchanged));
            assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
            assert!(
                result
                    .analyses
                    .iter()
                    .flat_map(|a| &a.rules)
                    .all(|r| klem::rule_explanation(r).is_some())
            );
        }
        assert_eq!(
            short,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            full_result,
            engine
                .analyze_word(&full.nfd().collect::<String>())
                .unwrap()
        );
    }
    // Nominalization composition above is structural evidence, not a judgment
    // about the naturalness of every referent in a desire construction.
}

#[test]
fn desire_topic_preserves_connector_boundaries_and_adjective_inflection() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹고은싶다", vec!["먹다", "싶다"], vec!["고", "은", "다"]),
        (
            "먹고는싶는다",
            vec!["먹다", "싶다"],
            vec!["고", "는", "는다"],
        ),
        ("먹곤싶는", vec!["먹다", "싶다"], vec!["고", "는", "는"]),
        (
            "학생곤싶다",
            vec!["학생", "이다", "싶다"],
            vec!["고", "는", "다"],
        ),
        ("도우곤싶다", vec!["돕다", "싶다"], vec!["고", "는", "다"]),
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
        (
            "먹고는싶었는가",
            vec!["먹다", "싶다"],
            vec!["고", "는", "었", "는가"],
        ),
        (
            "먹고는싶어요",
            vec!["먹다", "싶다"],
            vec!["고", "는", "어", "요"],
        ),
        (
            "먹고는싶지만요",
            vec!["먹다", "싶다"],
            vec!["고", "는", "지만", "요"],
        ),
        (
            "먹곤했다",
            vec!["먹다", "하다"],
            vec!["고", "는", "었", "다"],
        ),
        ("먹진않다", vec!["먹다", "않다"], vec!["지", "는", "다"]),
        ("먹고도싶다", vec!["먹다", "싶다"], vec!["고", "도", "다"]),
        ("먹고만싶다", vec!["먹다", "싶다"], vec!["고", "만", "다"]),
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
    // Other internal-particle licenses are unreviewed, not forbidden judgments.
}
