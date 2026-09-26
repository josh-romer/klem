//! COV-020a: nominalizing endings followed directly by a copula.
use klem::breakdown::Component;
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
fn direct_nominalizations_preserve_stems_suffixes_and_copula_order() {
    for (word, lemmas, forms) in [
        (
            "학생다움이다",
            vec!["학생", "이다"],
            vec!["답다", "음", "다"],
        ),
        (
            "학생다움이에요",
            vec!["학생", "이다"],
            vec!["답다", "음", "에요"],
        ),
        (
            "학생다움이야",
            vec!["학생", "이다"],
            vec!["답다", "음", "야"],
        ),
        (
            "학생다움이라고",
            vec!["학생", "이다"],
            vec!["답다", "음", "라고"],
        ),
        (
            "학생다움이다만",
            vec!["학생", "이다"],
            vec!["답다", "음", "다", "만"],
        ),
        (
            "선생님다움이다",
            vec!["선생", "이다"],
            vec!["님", "답다", "음", "다"],
        ),
        ("먹음이다", vec!["먹다", "이다"], vec!["음", "다"]),
        ("먹기이다", vec!["먹다", "이다"], vec!["기", "다"]),
        ("먹기다", vec!["먹다", "이다"], vec!["기", "다"]),
        ("먹기예요", vec!["먹다", "이다"], vec!["기", "에요"]),
        ("먹기야", vec!["먹다", "이다"], vec!["기", "야"]),
        (
            "먹었음이었다",
            vec!["먹다", "이다"],
            vec!["었", "음", "었", "다"],
        ),
        (
            "먹어보기였다",
            vec!["먹다", "보다", "이다"],
            vec!["어", "기", "었", "다"],
        ),
        (
            "먹을만함이다",
            vec!["먹다", "만하다", "이다"],
            vec!["을", "음", "다"],
        ),
        (
            "학생다움인듯하다",
            vec!["학생", "이다", "듯하다"],
            vec!["답다", "음", "은", "다"],
        ),
        ("학생임이다", vec!["학생", "이다", "이다"], vec!["음", "다"]),
        (
            "먹음임이다",
            vec!["먹다", "이다", "이다"],
            vec!["음", "음", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "nominalization"), "{word}");
        assert!(
            a.lemmas.iter().any(|l| l.kind == LemmaKind::Copula),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert_eq!(
            result,
            Lemmatizer::new()
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        for a in &result.analyses {
            assert!(a.breakdown().is_some(), "{word}: {a:?}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
        if word == "학생다움인듯하다" {
            let order: Vec<_> = a
                .breakdown()
                .unwrap()
                .iter()
                .map(|p| match p {
                    Component::Lemma(i) => a.lemmas[*i].text.as_str(),
                    Component::Morpheme(i) => a.morphemes[*i].form.as_str(),
                })
                .collect();
            assert_eq!(order, ["학생", "답다", "음", "이다", "은", "듯하다", "다"]);
        }
    }
    // Nominalization is optional decomposition, never a replacement for a word.
    for (word, base) in [("학생다움이다", "학생다움"), ("먹기다", "먹기")] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &[base, "이다"], &["다"]))
        );
    }
}

#[test]
fn direct_composition_does_not_relax_nominalizer_or_copula_boundaries() {
    for (word, lemmas, forms) in [
        (
            "학생답음이다",
            vec!["학생", "이다"],
            vec!["답다", "음", "다"],
        ),
        ("먹음다", vec!["먹다", "이다"], vec!["음", "다"]),
        ("먹음예요", vec!["먹다", "이다"], vec!["음", "에요"]),
        ("먹고이다", vec!["먹다", "이다"], vec!["고", "다"]),
        ("먹는이다", vec!["먹다", "이다"], vec!["는", "다"]),
        ("먹어이다", vec!["먹다", "이다"], vec!["어", "다"]),
        (
            "학생다움이느냐는",
            vec!["학생", "이다"],
            vec!["답다", "음", "느냐는"],
        ),
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

#[test]
fn nested_nominalizations_have_no_fixed_depth_cutoff() {
    let count = 64;
    let word = format!("먹음{}이다", "임".repeat(count));
    let result = Lemmatizer::new().analyze_word(&word).unwrap();
    let mut lemmas = vec!["먹다"];
    lemmas.extend(std::iter::repeat_n("이다", count + 1));
    let mut forms = vec!["음"; count + 1];
    forms.push("다");
    let a = result
        .analyses
        .iter()
        .find(|a| path(a, &lemmas, &forms))
        .unwrap();
    assert_eq!(a.breakdown().unwrap().len(), lemmas.len() + forms.len());
}
