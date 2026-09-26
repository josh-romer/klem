//! COV-020d: enumerative -요 is distinct from polite particle 요.
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
        && a.morphemes
            .last()
            .is_some_and(|m| m.kind == MorphemeKind::Ending && m.form == "요")
}
#[test]
fn enumerative_copulas_preserve_roles_composition_and_polite_homonyms() {
    for (word, lemmas, forms) in [
        ("연장이요", vec!["연장", "이다"], vec!["요"]),
        ("자화상이요", vec!["자화상", "이다"], vec!["요"]),
        ("선배요", vec!["선배", "이다"], vec!["요"]),
        ("아비요", vec!["아비", "이다"], vec!["요"]),
        ("아비이요", vec!["아비", "이다"], vec!["요"]),
        ("아니요", vec!["아니다"], vec!["요"]),
        ("이요", vec!["이다"], vec!["요"]),
        ("친구들이요", vec!["친구", "이다"], vec!["들", "요"]),
        ("선생님이요", vec!["선생", "이다"], vec!["님", "요"]),
        ("학생만이요", vec!["학생", "이다"], vec!["만", "요"]),
        ("먹기요", vec!["먹다", "이다"], vec!["기", "요"]),
        (
            "먹고싶음이요",
            vec!["먹다", "싶다", "이다"],
            vec!["고", "음", "요"],
        ),
    ] {
        let engine = Lemmatizer::new();
        let r = engine.analyze_word(word).unwrap();
        let a = r
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "ending.enumerative_yo"));
        if word != "아니요" {
            assert_eq!(a.lemmas.last().unwrap().kind, LemmaKind::Copula);
        }
        assert!(r.analyses.iter().any(|a| a.unchanged));
        assert!(r.analyses.iter().all(|a| a.breakdown().is_some()), "{word}");
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        assert_eq!(
            r,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    let r = Lemmatizer::new().analyze_word("아비요").unwrap();
    assert!(r.analyses.iter().any(|a| a.lemmas[0].text == "아비"
        && a.morphemes.len() == 1
        && a.morphemes[0].kind == MorphemeKind::Particle));
    let r = Lemmatizer::new().analyze_word("아니요").unwrap();
    assert!(r.analyses.iter().any(|a| a.unchanged));
}
#[test]
fn enumeration_does_not_license_arbitrary_predicates_prefinals_or_outer_particles() {
    for (word, lemmas, forms) in [
        ("먹요", vec!["먹다"], vec!["요"]),
        ("보이요", vec!["보이다"], vec!["요"]),
        ("학생요", vec!["학생", "이다"], vec!["요"]),
        ("학생이시요", vec!["학생", "이다"], vec!["시", "요"]),
        ("학생이었요", vec!["학생", "이다"], vec!["었", "요"]),
        ("아니겠요", vec!["아니다"], vec!["겠", "요"]),
        ("아니더요", vec!["아니다"], vec!["더", "요"]),
        ("아니하요", vec!["아니하다"], vec!["요"]),
    ] {
        let r = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !r.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(r.analyses.iter().any(|a| a.unchanged));
    }
    for word in ["학생이요요", "학생이요를", "학생이요보다"] {
        let r = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !r.analyses.iter().any(|a| a.lemmas[0].text == "학생"
                && a.rules.iter().any(|r| r == "ending.enumerative_yo")),
            "{word}"
        );
    }
    // The spelling rule does not rewrite terminal 오 as 요.
    let r = Lemmatizer::new().analyze_word("학생이오").unwrap();
    assert!(
        !r.analyses
            .iter()
            .any(|a| path(a, &["학생", "이다"], &["요"]))
    );
}
