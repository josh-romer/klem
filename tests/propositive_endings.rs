//! The label-source audit exposed 습시다 substituted for standard 읍시다.
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
fn propositive_boundaries_preserve_plain_stems_and_auxiliary_groups() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹읍시다", vec!["먹다"], vec!["읍시다"]),
        ("갑시다", vec!["가다"], vec!["읍시다"]),
        ("합시다", vec!["하다"], vec!["읍시다"]),
        ("삽시다", vec!["살다"], vec!["읍시다"]),
        ("들읍시다", vec!["듣다"], vec!["읍시다"]),
        ("부읍시다", vec!["붓다"], vec!["읍시다"]),
        ("도웁시다", vec!["돕다"], vec!["읍시다"]),
        ("먹어봅시다", vec!["먹다", "보다"], vec!["어", "읍시다"]),
        ("먹지맙시다", vec!["먹다", "말다"], vec!["지", "읍시다"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.rules.iter().any(|r| r == "ending"));
        assert!(a.breakdown().is_some());
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    let ambiguous = engine.analyze_word("삽시다").unwrap();
    assert!(
        ambiguous
            .analyses
            .iter()
            .any(|a| path(a, &["사다"], &["읍시다"]))
    );
    for (word, lemma) in [
        ("먹습시다", "먹다"),
        ("가읍시다", "가다"),
        ("살읍시다", "살다"),
        ("듭시다", "듣다"),
        ("돕시다", "돕다"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && a.morphemes
                    .iter()
                    .any(|m| m.form == "읍시다" || m.form == "습시다")),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
