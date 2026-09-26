//! Definition particles versus copular, retrospective and command quotations.
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
fn definitions_and_quoted_facts_keep_distinct_groups_and_roles() {
    let engine = Lemmatizer::new();
    let fragment = engine.analyze_word("이란").unwrap();
    let a = fragment
        .analyses
        .iter()
        .find(|a| path(a, &["이다"], &["란"]) && a.lemmas[0].kind == LemmaKind::Copula)
        .unwrap();
    assert!(a.rules.iter().any(|r| r == "copula.fragment"));
    assert!(a.breakdown().is_some());
    for (word, lemmas, forms) in [
        ("학교란", vec!["학교"], vec!["란"]),
        ("학생이란", vec!["학생"], vec!["이란"]),
        ("길이란", vec!["길"], vec!["이란"]),
        ("학교란요", vec!["학교"], vec!["란", "요"]),
        ("학생들이란", vec!["학생"], vec!["들", "이란"]),
        ("먹기란", vec!["먹다"], vec!["기", "란"]),
        ("먹음이란", vec!["먹다"], vec!["음", "이란"]),
        ("먹어보기란", vec!["먹다", "보다"], vec!["어", "기", "란"]),
        ("학생답기란", vec!["학생"], vec!["답다", "기", "란"]),
        ("학교란", vec!["학교", "이다"], vec!["란"]),
        ("학생이란", vec!["학생", "이다"], vec!["란"]),
        ("학생이시란", vec!["학생", "이다"], vec!["시", "란"]),
        ("아니란", vec!["아니다"], vec!["란"]),
        ("아니시란", vec!["아니다"], vec!["시", "란"]),
        ("먹었더란", vec!["먹다"], vec!["었", "더", "란"]),
        ("먹으셨더란", vec!["먹다"], vec!["시", "었", "더", "란"]),
        ("학생이었더란", vec!["학생", "이다"], vec!["었", "더", "란"]),
        (
            "먹어봤더란",
            vec!["먹다", "보다"],
            vec!["어", "었", "더", "란"],
        ),
        ("작으리란", vec!["작다"], vec!["으리", "란"]),
        ("먹었으리란", vec!["먹다"], vec!["었", "으리", "란"]),
        (
            "먹으셨겠으리란",
            vec!["먹다"],
            vec!["시", "었", "겠", "으리", "란"],
        ),
        ("살리란", vec!["살다"], vec!["으리", "란"]),
        ("들으리란", vec!["듣다"], vec!["으리", "란"]),
        ("도우리란", vec!["돕다"], vec!["으리", "란"]),
        ("학생이리란", vec!["학생", "이다"], vec!["으리", "란"]),
        ("학생다우리란", vec!["학생"], vec!["답다", "으리", "란"]),
        (
            "먹고싶으리란",
            vec!["먹다", "싶다"],
            vec!["고", "으리", "란"],
        ),
        ("먹어보리란", vec!["먹다", "보다"], vec!["어", "으리", "란"]),
        ("먹으란", vec!["먹다"], vec!["으란"]),
        ("가란", vec!["가다"], vec!["으란"]),
        ("살란", vec!["살다"], vec!["으란"]),
        ("들으란", vec!["듣다"], vec!["으란"]),
        ("도우란", vec!["돕다"], vec!["으란"]),
        ("먹으시란", vec!["먹다"], vec!["시", "으란"]),
        ("행복하란", vec!["행복하다"], vec!["으란"]),
        ("먹어보란", vec!["먹다", "보다"], vec!["어", "으란"]),
        ("먹지말란", vec!["먹다", "말다"], vec!["지", "으란"]),
        // Existing full quotation is preserved, including its extra copula.
        ("사회주의라는", vec!["사회주의", "이다"], vec!["라는"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.breakdown().is_some());
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
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
        if let Some(m) = a.morphemes.iter().find(|m| m.form == "으리") {
            assert_eq!(m.kind, MorphemeKind::Prefinal);
            assert!(
                a.rules
                    .iter()
                    .any(|r| r == "prefinal.conjectural_quotation")
            );
        }
    }
    for (word, base, particle) in [("학교란", "학교", "란"), ("학생이란", "학생", "이란")]
    {
        let result = engine.analyze_word(word).unwrap();
        let nominal = result
            .analyses
            .iter()
            .find(|a| path(a, &[base], &[particle]))
            .unwrap();
        assert_eq!(nominal.lemmas[0].kind, LemmaKind::Nominal);
        assert_eq!(nominal.morphemes[0].kind, MorphemeKind::Particle);
        let copular = result
            .analyses
            .iter()
            .find(|a| path(a, &[base, "이다"], &["란"]))
            .unwrap();
        assert_eq!(copular.lemmas[1].kind, LemmaKind::Copula);
        assert_eq!(copular.morphemes[0].kind, MorphemeKind::Ending);
        assert!(
            copular
                .rules
                .iter()
                .any(|r| r == "ending.adnominal_expression")
        );
    }
}

#[test]
fn quotations_do_not_relax_allomorphs_case_chains_or_prefinal_licenses() {
    for (word, lemmas, forms) in [
        ("학교이란", vec!["학교"], vec!["이란"]),
        ("학생란", vec!["학생"], vec!["란"]),
        ("길란", vec!["길"], vec!["란"]),
        ("학생이란", vec!["학생"], vec!["이", "란"]),
        ("학교에서란", vec!["학교"], vec!["에서", "란"]),
        ("학교란란", vec!["학교"], vec!["란", "란"]),
        ("학생란", vec!["학생", "이다"], vec!["란"]),
        ("학생이란", vec!["학생", "이다"], vec!["으란"]),
        ("먹란", vec!["먹다"], vec!["으란"]),
        ("살으란", vec!["살다"], vec!["으란"]),
        ("먹었으란", vec!["먹다"], vec!["었", "으란"]),
        ("먹겠으란", vec!["먹다"], vec!["겠", "으란"]),
        ("먹었란", vec!["먹다"], vec!["었", "란"]),
        ("학생이었란", vec!["학생", "이다"], vec!["었", "란"]),
        ("살으리란", vec!["살다"], vec!["으리", "란"]),
        ("먹더리란", vec!["먹다"], vec!["더", "으리", "란"]),
        ("먹으리었란", vec!["먹다"], vec!["으리", "었", "란"]),
        ("먹으란보다", vec!["먹다", "보다"], vec!["으란", "다"]),
        (
            "먹었더란보다",
            vec!["먹다", "보다"],
            vec!["었", "더", "란", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    for (word, base, form, condition) in [
        ("ABC란", "ABC", "란", "vowel"),
        ("3이란", "3", "이란", "consonant"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &[base], &[form]))
            .unwrap();
        assert!(
            a.rules
                .contains(&format!("pronunciation.assumed_{condition}"))
        );
    }
}
