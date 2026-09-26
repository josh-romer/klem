//! COV-012: scoped derivation, not arbitrary -이 removal or contextual tagging.
use klem::breakdown::Component;
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind};
use unicode_normalization::UnicodeNormalization;

fn derived(a: &Analysis, base: &str, forms: &[&str]) -> bool {
    a.lemmas.len() == 1
        && a.lemmas[0].text == base
        && a.lemmas[0].kind == LemmaKind::Predicate
        && a.morphemes
            .iter()
            .map(|m| m.form.as_str())
            .eq(forms.iter().copied())
        && a.morphemes[0].kind == MorphemeKind::Suffix
}

#[test]
fn scoped_adverbs_preserve_whole_words_and_use_suffixes_without_endings() {
    for (word, base) in [
        ("같이", "같다"),
        ("없이", "없다"),
        ("똑같이", "똑같다"),
        ("틀림없이", "틀림없다"),
        ("끝없이", "끝없다"),
        ("굳이", "굳다"),
        ("길이", "길다"),
        ("깊이", "깊다"),
        ("높이", "높다"),
        ("많이", "많다"),
        ("달리", "다르다"),
        ("빨리", "빠르다"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| derived(a, base, &["이"]))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "suffix.adverbial.i"));
        assert_eq!(
            a.breakdown().unwrap(),
            [Component::Lemma(0), Component::Morpheme(0)]
        );
        if matches!(word, "달리" | "빨리") {
            assert!(a.rules.iter().any(|r| r == "derivation.adverbial.lexical"));
            assert!(!a.rules.iter().any(|r| r == "irregular.reu"));
        }
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.unchanged && a.lemmas[0].text == word)
        );
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert!(
            result
                .analyses
                .iter()
                .all(|a| a.rules.iter().all(|r| klem::rule_explanation(r).is_some()))
        );
        let nfd: String = word.nfd().collect();
        assert_eq!(result, Lemmatizer::new().analyze_word(&nfd).unwrap());
    }
}

#[test]
fn adverb_derivation_precedes_reviewed_particle_chains() {
    for (word, base, forms) in [
        ("같이도", "같다", vec!["이", "도"]),
        ("같이는", "같다", vec!["이", "는"]),
        ("같이요", "같다", vec!["이", "요"]),
        ("없이도", "없다", vec!["이", "도"]),
        ("달리만은", "다르다", vec!["이", "만", "은"]),
        ("빨리들", "빠르다", vec!["이", "들"]),
        ("같이들요", "같다", vec!["이", "들", "요"]),
        ("끝없이도요", "끝없다", vec!["이", "도", "요"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| derived(a, base, &forms))
            .expect(word);
        assert!(
            a.morphemes[1..]
                .iter()
                .all(|m| m.kind == MorphemeKind::Particle)
        );
        let mut order = vec![Component::Lemma(0)];
        order.extend((0..forms.len()).map(Component::Morpheme));
        assert_eq!(a.breakdown().unwrap(), order);
    }
}

#[test]
fn derivation_does_not_invent_inflection_causatives_or_noun_case_paths() {
    for (word, base) in [
        ("같히", "같다"),
        ("없히", "없다"),
        ("다르이", "다르다"),
        ("먹이", "먹다"),
        ("어린이", "어리다"),
        ("가르이", "가르다"),
        ("같았이", "같다"),
        ("같시이", "같다"),
        ("같이이", "같다"),
        ("같이를", "같다"),
        ("없이가", "없다"),
        ("높이에서", "높다"),
        ("같이요요", "같다"),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text == base
                    && a.rules.iter().any(|r| r == "suffix.adverbial.i")),
            "{word}"
        );
    }
    // 달리다 remains a verb, and bare nominal readings stay available for 높이.
    assert!(
        Lemmatizer::new()
            .analyze_word("달려")
            .unwrap()
            .lemma_strings()
            .contains(&"달리다")
    );
    assert!(
        Lemmatizer::new()
            .analyze_word("높이를")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.lemmas[0].text == "높이" && a.lemmas[0].kind == LemmaKind::Nominal)
    );
    let mut a = Lemmatizer::new()
        .analyze_word("같이")
        .unwrap()
        .analyses
        .into_iter()
        .find(|a| derived(a, "같다", &["이"]))
        .unwrap();
    a.morphemes[0].kind = MorphemeKind::Prefinal;
    assert!(a.breakdown().is_none());
}
