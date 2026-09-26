//! COV-017l: keep factual 라-family readings separate from commands.
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
fn factual_and_bundled_readings_preserve_their_prefinals() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹었더라", vec!["먹다"], vec!["었", "더라"]),
        ("먹었더라", vec!["먹다"], vec!["었", "더", "라"]),
        ("해야겠더라", vec!["하다"], vec!["어야겠", "더라"]),
        ("해야겠더라", vec!["하다"], vec!["어야겠", "더", "라"]),
        ("먹었더라고", vec!["먹다"], vec!["었", "더라고"]),
        ("먹었더라고", vec!["먹다"], vec!["었", "더", "라고"]),
        ("먹었더라면", vec!["먹다"], vec!["었", "더", "라면"]),
        ("먹었더라서", vec!["먹다"], vec!["었", "더", "라서"]),
        ("못하더라는", vec!["못하다"], vec!["더라는"]),
        ("먹더라는", vec!["먹다"], vec!["더라는"]),
        (
            "먹으셨겠더라는",
            vec!["먹다"],
            vec!["시", "었", "겠", "더라는"],
        ),
        ("학생이더라는", vec!["학생", "이다"], vec!["더라는"]),
        ("학생답더라는", vec!["학생"], vec!["답다", "더라는"]),
        (
            "먹어봤더라는",
            vec!["먹다", "보다"],
            vec!["어", "었", "더라는"],
        ),
        (
            "먹었었겠더라",
            vec!["먹다"],
            vec!["었", "었", "겠", "더", "라"],
        ),
        ("먹으셨더라", vec!["먹다"], vec!["시", "었", "더", "라"]),
        ("학생이었더라", vec!["학생", "이다"], vec!["었", "더", "라"]),
        ("학생이시라서", vec!["학생", "이다"], vec!["시", "라서"]),
        ("학생이시라는", vec!["학생", "이다"], vec!["시", "라는"]),
        ("먹으시라", vec!["먹다"], vec!["시", "라"]),
        ("먹으시라", vec!["먹다"], vec!["시", "으라"]),
        ("먹으시라고", vec!["먹다"], vec!["시", "라고"]),
        ("먹으시라고", vec!["먹다"], vec!["시", "으라고"]),
        ("먹으리라", vec!["먹다"], vec!["으리라"]),
        ("먹으리라", vec!["먹다"], vec!["으리", "라"]),
        ("먹으리라고", vec!["먹다"], vec!["으리라고"]),
        ("먹으리라고", vec!["먹다"], vec!["으리", "라고"]),
        ("먹으리라면", vec!["먹다"], vec!["으리", "라면"]),
        ("먹으리라서", vec!["먹다"], vec!["으리", "라서"]),
        ("도우리라", vec!["돕다"], vec!["으리", "라"]),
        ("들으리라", vec!["듣다"], vec!["으리", "라"]),
        ("살리라", vec!["살다"], vec!["으리", "라"]),
        ("학생이리라", vec!["학생", "이다"], vec!["으리", "라"]),
        ("학생다우리라", vec!["학생"], vec!["답다", "으리", "라"]),
        (
            "먹어봤더라",
            vec!["먹다", "보다"],
            vec!["어", "었", "더", "라"],
        ),
        ("먹어보리라", vec!["먹다", "보다"], vec!["어", "으리", "라"]),
        (
            "먹기였더라",
            vec!["먹다", "이다"],
            vec!["기", "었", "더", "라"],
        ),
        // Preserve ordinary commands, proposals and exclamations.
        ("먹어라", vec!["먹다"], vec!["어라"]),
        ("먹으라", vec!["먹다"], vec!["으라"]),
        ("먹으셔라", vec!["먹다"], vec!["시", "어라"]),
        ("먹으라는", vec!["먹다"], vec!["으라는"]),
        ("먹으세요", vec!["먹다"], vec!["으세요"]),
        ("학생이세요", vec!["학생", "이다"], vec!["으세요"]),
        ("먹으십시오", vec!["먹다"], vec!["으십시오"]),
        ("먹읍시다", vec!["먹다"], vec!["읍시다"]),
        ("가십시다", vec!["가다"], vec!["시", "읍시다"]),
        ("행복해라", vec!["행복하다"], vec!["어라"]),
        ("먹어보았자", vec!["먹다", "보다"], vec!["어", "었", "자"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {forms:?}"
        );
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
        assert!(
            result
                .analyses
                .iter()
                .flat_map(|a| &a.rules)
                .all(|r| klem::rule_explanation(r).is_some())
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
}

#[test]
fn commands_do_not_inherit_tense_modal_or_retrospective_prefinals() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("먹었더라", vec!["먹다"], vec!["었", "더", "어라"]),
        ("먹었더라", vec!["먹다"], vec!["었", "더", "으라"]),
        ("해야겠더라", vec!["하다"], vec!["어야겠", "더", "어라"]),
        ("먹었으라", vec!["먹다"], vec!["었", "으라"]),
        ("먹겠으라", vec!["먹다"], vec!["겠", "으라"]),
        ("먹었으라고", vec!["먹다"], vec!["었", "으라고"]),
        ("먹었으라는", vec!["먹다"], vec!["었", "으라는"]),
        ("먹겠으라면", vec!["먹다"], vec!["겠", "으라면"]),
        ("먹었으세요", vec!["먹다"], vec!["었", "으세요"]),
        ("먹겠으십시오", vec!["먹다"], vec!["겠", "으십시오"]),
        ("먹었읍시다", vec!["먹다"], vec!["었", "읍시다"]),
        ("먹어야겠으라", vec!["먹다"], vec!["어야겠", "으라"]),
        ("학생이라", vec!["학생", "이다"], vec!["으라"]),
        ("학생이라고", vec!["학생", "이다"], vec!["으라고"]),
        ("학생이라는", vec!["학생", "이다"], vec!["으라는"]),
        ("학생이라면", vec!["학생", "이다"], vec!["으라면"]),
        ("학생이십시오", vec!["학생", "이다"], vec!["으십시오"]),
        ("학생입시다", vec!["학생", "이다"], vec!["읍시다"]),
        ("먹라", vec!["먹다"], vec!["라"]),
        ("가라", vec!["가다"], vec!["라"]),
        ("먹었라", vec!["먹다"], vec!["었", "라"]),
        ("먹겠라", vec!["먹다"], vec!["겠", "라"]),
        ("먹더라는", vec!["먹다"], vec!["더", "라는"]),
        ("먹더더라는", vec!["먹다"], vec!["더", "더라는"]),
        ("살으리라", vec!["살다"], vec!["으리", "라"]),
        ("먹더리라", vec!["먹다"], vec!["더", "으리", "라"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {forms:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}

#[test]
fn factual_components_and_quoted_bundle_have_distinct_roles_and_provenance() {
    let engine = Lemmatizer::new();
    for (word, forms, rule) in [
        ("먹었더라", vec!["었", "더", "라"], "ending.factual_ra"),
        ("먹으리라", vec!["으리", "라"], "prefinal.conjectural_ra"),
        ("먹더라는", vec!["더라는"], "ending.adnominal_expression"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &["먹다"], &forms))
            .unwrap();
        assert!(a.rules.iter().any(|r| r == rule), "{word}");
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(
            a.morphemes[..a.morphemes.len() - 1]
                .iter()
                .all(|m| m.kind == MorphemeKind::Prefinal)
        );
    }
}
