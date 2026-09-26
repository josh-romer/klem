//! COV-020g: omitted copulas before modal/retrospective markers and reviewed bundles.
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
fn omitted_prefinal_copulas_preserve_roles_composition_and_alternatives() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        (
            "의사겠지",
            &["의사", "이다"] as &[&str],
            &["겠", "지"] as &[&str],
        ),
        (
            "의사겠어요",
            &["의사", "이다"] as &[&str],
            &["겠", "어요"] as &[&str],
        ),
        (
            "누구겠니",
            &["누구", "이다"] as &[&str],
            &["겠", "니"] as &[&str],
        ),
        (
            "최고겠습니다",
            &["최고", "이다"] as &[&str],
            &["겠", "습니다"] as &[&str],
        ),
        (
            "먹기겠다",
            &["먹다", "이다"] as &[&str],
            &["기", "겠", "다"] as &[&str],
        ),
        (
            "먹어보기겠지",
            &["먹다", "보다", "이다"] as &[&str],
            &["어", "기", "겠", "지"] as &[&str],
        ),
        (
            "의사겠더라",
            &["의사", "이다"] as &[&str],
            &["겠", "더", "라"] as &[&str],
        ),
        (
            "의사겠더라",
            &["의사", "이다"] as &[&str],
            &["겠", "더라"] as &[&str],
        ),
        (
            "의사시겠더라",
            &["의사", "이다"] as &[&str],
            &["시", "겠", "더", "라"] as &[&str],
        ),
        (
            "학생이겠지",
            &["학생", "이다"] as &[&str],
            &["겠", "지"] as &[&str],
        ),
        (
            "의사더라",
            &["의사", "이다"] as &[&str],
            &["더", "라"] as &[&str],
        ),
        (
            "의사더라",
            &["의사", "이다"] as &[&str],
            &["더라"] as &[&str],
        ),
        (
            "의사더라고",
            &["의사", "이다"] as &[&str],
            &["더라고"] as &[&str],
        ),
        (
            "최고더군",
            &["최고", "이다"] as &[&str],
            &["더군"] as &[&str],
        ),
        (
            "최고더군요",
            &["최고", "이다"] as &[&str],
            &["더군요"] as &[&str],
        ),
        (
            "최고더군요",
            &["최고", "이다"] as &[&str],
            &["더", "군", "요"] as &[&str],
        ),
        (
            "의사더니",
            &["의사", "이다"] as &[&str],
            &["더니"] as &[&str],
        ),
        (
            "의사더니",
            &["의사", "이다"] as &[&str],
            &["더니"] as &[&str],
        ),
        (
            "의사더라도",
            &["의사", "이다"] as &[&str],
            &["더라도"] as &[&str],
        ),
        (
            "의사던데",
            &["의사", "이다"] as &[&str],
            &["던데"] as &[&str],
        ),
        (
            "의사던데요",
            &["의사", "이다"] as &[&str],
            &["던데요"] as &[&str],
        ),
        ("거더라", &["거", "이다"] as &[&str], &["더라"] as &[&str]),
        ("거더라", &["것", "이다"] as &[&str], &["더라"] as &[&str]),
        (
            "먹기더라",
            &["먹다", "이다"] as &[&str],
            &["기", "더라"] as &[&str],
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, lemmas, forms))
            .expect(word);
        assert_eq!(a.lemmas.last().unwrap().kind, LemmaKind::Copula, "{word}");
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
    for (word, full, head) in [
        ("의사겠지", "의사이겠지", "의사"),
        ("의사겠더라", "의사이겠더라", "의사"),
        ("최고더군요", "최고이더군요", "최고"),
        ("의사던데요", "의사이던데요", "의사"),
        ("먹기겠다", "먹기이겠다", "먹다"),
        ("먹어보기겠지", "먹어보기이겠지", "먹다"),
    ] {
        let short = engine.analyze_word(word).unwrap();
        let full = engine.analyze_word(full).unwrap();
        let restored: Vec<_> = short
            .analyses
            .iter()
            .filter(|a| {
                a.lemmas[0].text == head && a.rules.iter().any(|r| r == "copula.omitted_ending")
            })
            .collect();
        assert!(!restored.is_empty(), "{word}");
        for a in restored {
            assert!(
                full.analyses
                    .iter()
                    .any(|f| f.lemmas == a.lemmas && f.morphemes == a.morphemes),
                "{word}: {a:?}"
            );
        }
    }
    for (word, forms, assumed) in [
        ("ABC겠지", vec!["겠", "지"], true),
        ("ABC이겠지", vec!["겠", "지"], false),
        ("ABC더군요", vec!["더군요"], true),
        ("ABC이더군요", vec!["더군요"], false),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &["ABC", "이다"], &forms))
            .expect(word);
        assert_eq!(
            a.rules.iter().any(|r| r == "pronunciation.assumed_vowel"),
            assumed
        );
    }
    for word in ["의사겠지", "의사더구나"] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "copula.omitted_prefinal")),
            "{word}"
        );
    }
}
#[test]
fn omitted_prefinal_copulas_reject_wrong_boundaries_order_and_fabricated_verbs() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        (
            "학생겠지",
            &["학생", "이다"] as &[&str],
            &["겠", "지"] as &[&str],
        ),
        (
            "길겠지",
            &["길", "이다"] as &[&str],
            &["겠", "지"] as &[&str],
        ),
        (
            "학생더군요",
            &["학생", "이다"] as &[&str],
            &["더군요"] as &[&str],
        ),
        ("길더라", &["길", "이다"] as &[&str], &["더라"] as &[&str]),
        (
            "도우겠지",
            &["돕", "이다"] as &[&str],
            &["겠", "지"] as &[&str],
        ),
        (
            "사겠지",
            &["살", "이다"] as &[&str],
            &["겠", "지"] as &[&str],
        ),
        (
            "의사더겠지",
            &["의사", "이다"] as &[&str],
            &["더", "겠", "지"] as &[&str],
        ),
        (
            "의사겠었다",
            &["의사", "이다"] as &[&str],
            &["겠", "었", "다"] as &[&str],
        ),
        (
            "의사겠시다",
            &["의사", "이다"] as &[&str],
            &["겠", "시", "다"] as &[&str],
        ),
        (
            "의사겠지",
            &["의사이다"] as &[&str],
            &["겠", "지"] as &[&str],
        ),
        (
            "최고더군요",
            &["최고이다"] as &[&str],
            &["더군요"] as &[&str],
        ),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, lemmas, forms)),
            "{word}"
        );
    }
    // The new omitted-copula path does not replace a lexical vowel-final verb.
    for (word, lemma) in [
        ("가겠지", "가다"),
        ("사더라", "사다"),
        ("배우겠어요", "배우다"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.lemmas[0].kind == LemmaKind::Predicate),
            "{word}"
        );
    }
}
