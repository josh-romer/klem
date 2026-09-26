//! COV-020i: nominal approximation suffix -쯤, separate from particles.
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
fn approximation_suffix_preserves_nominal_composition() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("번쯤", &["번"], &["쯤"]),
        ("내일쯤", &["내일"], &["쯤"]),
        ("중간쯤", &["중간"], &["쯤"]),
        ("사정쯤", &["사정"], &["쯤"]),
        ("사흘쯤", &["사흘"], &["쯤"]),
        ("나흘쯤", &["나흘"], &["쯤"]),
        ("얼마쯤", &["얼마"], &["쯤"]),
        ("이쯤", &["이"], &["쯤"]),
        ("그쯤", &["그"], &["쯤"]),
        ("저쯤", &["저"], &["쯤"]),
        ("여기쯤", &["여기"], &["쯤"]),
        ("저녁쯤", &["저녁"], &["쯤"]),
        ("걸음쯤", &["걸음"], &["쯤"]),
        ("내일쯤에", &["내일"], &["쯤", "에"]),
        ("번쯤은", &["번"], &["쯤", "은"]),
        ("번쯤도", &["번"], &["쯤", "도"]),
        ("번쯤만", &["번"], &["쯤", "만"]),
        ("중간쯤에서", &["중간"], &["쯤", "에서"]),
        ("중간쯤으로", &["중간"], &["쯤", "으로"]),
        ("여기쯤이", &["여기"], &["쯤", "이"]),
        ("그쯤을", &["그"], &["쯤", "을"]),
        ("사흘쯤이나", &["사흘"], &["쯤", "이나"]),
        ("번쯤은요", &["번"], &["쯤", "은", "요"]),
        ("사흘쯤이다", &["사흘", "이다"], &["쯤", "다"]),
        ("사흘쯤이에요", &["사흘", "이다"], &["쯤", "에요"]),
        ("중간쯤이었다", &["중간", "이다"], &["쯤", "었", "다"]),
        ("아이들쯤은", &["아이"], &["들", "쯤", "은"]),
        ("교수님쯤은", &["교수"], &["님", "쯤", "은"]),
        ("교수님들쯤은", &["교수"], &["님", "들", "쯤", "은"]),
        ("감기쯤이야", &["감기"], &["쯤", "이야"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, lemmas, forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "suffix.approximation"));
        assert_eq!(
            a.morphemes.iter().find(|m| m.form == "쯤").unwrap().kind,
            MorphemeKind::Suffix
        );
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
#[test]
fn approximation_suffix_rejects_wrong_outer_allomorphs() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("번쯤는", &["번"], &["쯤", "는"]),
        ("번쯤가", &["번"], &["쯤", "가"]),
        ("번쯤를", &["번"], &["쯤", "를"]),
        ("번쯤로", &["번"], &["쯤", "로"]),
        ("번쯤랑", &["번"], &["쯤", "랑"]),
        ("번쯤나", &["번"], &["쯤", "나"]),
        ("번쯤야", &["번"], &["쯤", "야"]),
        ("번쯤예요", &["번", "이다"], &["쯤", "에요"]),
        ("번쯤로는", &["번"], &["쯤", "로", "는"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, lemmas, forms)),
            "{word}: {forms:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
#[test]
fn approximation_keeps_lexical_words_and_known_suffix_boundary() {
    let engine = Lemmatizer::new();
    for word in ["그쯤", "이쯤", "저쯤", "쯤"] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.unchanged && a.lemmas[0].text == word)
        );
        assert!(
            result
                .analyses
                .iter()
                .all(|a| a.lemmas.iter().all(|l| !l.text.is_empty()))
        );
    }
    for (word, lemmas, forms) in [
        ("25일쯤에", vec!["25일"], vec!["쯤", "에"]),
        ("3쯤은", vec!["3"], vec!["쯤", "은"]),
        ("ABC쯤으로", vec!["ABC"], vec!["쯤", "으로"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(!a.rules.iter().any(|r| r.starts_with("pronunciation.")));
    }
}
