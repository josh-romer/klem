//! COV-006..009: independently specified paths from KRDict ㄴ/ㄹ/요/들
//! attachment notes and pronoun entries. See docs/rules.md for source IDs.
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind};

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
fn contractions_preserve_case_chains_and_pronoun_alternatives() {
    for (word, noun, forms) in [
        ("학교에선", "학교", vec!["에서", "는"]),
        ("선생님께선", "선생님", vec!["께서", "는"]),
        ("집엔", "집", vec!["에", "는"]),
        ("길론", "길", vec!["로", "는"]),
        ("병원엘", "병원", vec!["에", "를"]),
        ("커필", "커피", vec!["를"]),
        ("난", "나", vec!["는"]),
        ("날", "나", vec!["를"]),
        ("넌", "너", vec!["는"]),
        ("널", "너", vec!["를"]),
        ("우린", "우리", vec!["는"]),
        ("우릴", "우리", vec!["를"]),
        ("이게", "이거", vec!["가"]),
        ("이게", "이것", vec!["이"]),
        ("그건", "그거", vec!["는"]),
        ("그건", "그것", vec!["은"]),
        ("저걸", "저거", vec!["를"]),
        ("저걸", "저것", vec!["을"]),
        ("뭘", "뭐", vec!["를"]),
        ("뭘", "무엇", vec!["을"]),
        ("그걸도", "그것", vec!["을", "도"]),
        ("이건요", "이것", vec!["은", "요"]),
        ("제가요", "저", vec!["가", "요"]),
        ("학교에선요", "학교", vec!["에서", "는", "요"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &[noun], &forms)),
            "{word}: {noun} {forms:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged), "{word}");
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
    }
    for prefix in ["이", "그", "저"] {
        for (ending, short_case, full_case) in
            [("게", "가", "이"), ("건", "는", "은"), ("걸", "를", "을")]
        {
            let result = Lemmatizer::new()
                .analyze_word(&format!("{prefix}{ending}"))
                .unwrap();
            assert!(result.analyses.iter().any(|a| path(
                a,
                &[&format!("{prefix}거")],
                &[short_case]
            )));
            assert!(result.analyses.iter().any(|a| path(
                a,
                &[&format!("{prefix}것")],
                &[full_case]
            )));
        }
    }
    let nfd = Lemmatizer::new().analyze_word("이건요").unwrap();
    assert_eq!(nfd, Lemmatizer::new().analyze_word("이건요").unwrap());
}

#[test]
fn particles_attach_to_licensed_endings_and_keep_auxiliary_order() {
    for (word, lemmas, forms) in [
        ("저도요", vec!["저"], vec!["도", "요"]),
        ("친구는요", vec!["친구"], vec!["는", "요"]),
        ("먹어들", vec!["먹다"], vec!["어", "들"]),
        ("먹어들요", vec!["먹다"], vec!["어", "들", "요"]),
        (
            "먹어봤어요",
            vec!["먹다", "보다"],
            vec!["어", "었", "어", "요"],
        ),
        ("먹어봤어요", vec!["먹다", "보다"], vec!["어", "었", "어요"]),
        ("좋군요", vec!["좋다"], vec!["군", "요"]),
        ("먹으면요", vec!["먹다"], vec!["으면", "요"]),
        ("먹어선", vec!["먹다"], vec!["어서", "는"]),
        ("보곤", vec!["보다"], vec!["고", "는"]),
        ("걷질", vec!["걷다"], vec!["지", "를"]),
        ("먹고들", vec!["먹다"], vec!["고", "들"]),
        ("먹는다고들", vec!["먹다"], vec!["는다고", "들"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?} {forms:?}"
        );
        for a in &result.analyses {
            let parts = a.breakdown().expect(word);
            assert_eq!(parts.len(), a.lemmas.len() + a.morphemes.len());
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn adverbs_and_plural_nouns_have_distinct_role_hypotheses() {
    for (word, form) in [("빨리들", "들"), ("빨리요", "요")] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(result.analyses.iter().any(|a| path(a, &["빨리"], &[form])
            && a.lemmas[0].kind == LemmaKind::Adverbial
            && a.morphemes[0].kind == MorphemeKind::Particle));
    }
    let result = Lemmatizer::new().analyze_word("지식인들").unwrap();
    for kind in [MorphemeKind::Particle, MorphemeKind::Suffix] {
        assert!(
            result
                .analyses
                .iter()
                .any(|a| path(a, &["지식인"], &["들"]) && a.morphemes[0].kind == kind)
        );
    }
}

#[test]
fn particle_slots_and_ending_boundaries_do_not_overstrip() {
    for (word, lemmas, forms) in [
        ("친구는요요", vec!["친구"], vec!["는", "요", "요"]),
        ("먹어들들", vec!["먹다"], vec!["어", "들", "들"]),
        ("먹은요", vec!["먹다"], vec!["은", "요"]),
        ("먹을들", vec!["먹다"], vec!["을", "들"]),
        ("먹습니다요", vec!["먹다"], vec!["습니다", "요"]),
        ("학생은", vec!["학생"], vec!["는"]),
        ("이건", vec!["이것"], vec!["을"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "unlicensed path for {word}"
        );
    }
    for word in ["요", "들", "ㄴ", "ㄹ"] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|a| a.lemmas.iter().all(|l| !l.text.is_empty()))
        );
    }
}
