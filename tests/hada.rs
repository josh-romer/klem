//! COV-011: Article 40 deletion/aspiration paths; lexical hypotheses coexist.
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind};
use unicode_normalization::UnicodeNormalization;

#[test]
fn shortened_ki_preserves_bundled_and_separated_nominalizations() {
    let engine = Lemmatizer::new();
    for (root, short, rule) in [
        ("강구", "키", "contraction.ha_aspiration"),
        ("조성", "키", "contraction.ha_aspiration"),
        ("돌변", "키", "contraction.ha_aspiration"),
        ("분발", "키", "contraction.ha_aspiration"),
        ("결심", "키", "contraction.ha_aspiration"),
        ("생각", "기", "deletion.ha"),
        ("깨끗", "기", "deletion.ha"),
        ("섭섭", "기", "deletion.ha"),
    ] {
        for tail in ["", "로", "가", "는", "도", "만", "를", "보다"] {
            let word = format!("{root}{short}{tail}");
            let full = engine.analyze_word(&format!("{root}하기{tail}")).unwrap();
            let result = engine.analyze_word(&word).unwrap();
            let lemma = format!("{root}하다");
            let expected: Vec<_> = full
                .analyses
                .iter()
                .filter(|a| a.lemmas.len() == 1 && a.lemmas[0].text == lemma)
                .collect();
            assert!(!expected.is_empty(), "{word}");
            for a in expected {
                assert!(
                    result.analyses.iter().any(|b| b.lemmas == a.lemmas
                        && b.morphemes == a.morphemes
                        && b.rules.iter().any(|r| r == rule)),
                    "{word}: {a:?}"
                );
            }
            assert!(
                result.analyses.iter().all(|a| a.breakdown().is_some()),
                "{word}"
            );
            assert_eq!(
                result,
                engine
                    .analyze_word(&word.nfd().collect::<String>())
                    .unwrap()
            );
        }
    }
    for (word, lemma) in [
        ("생각키에", "생각하다"),
        ("깨끗키는", "깨끗하다"),
        ("섭섭키도", "섭섭하다"),
        ("강구기를", "강구하다"),
        ("조성기로", "조성하다"),
        ("돌변기도", "돌변하다"),
        ("ABC키로", "ABC하다"),
        ("키로", "하다"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result
                .analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.text == lemma)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}

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
fn article_40_examples_recover_the_same_lemma_and_ending_as_full_forms() {
    for (short, full, lemma, ending, rule) in [
        (
            "강구키",
            "강구하기",
            "강구하다",
            "기",
            "contraction.ha_aspiration",
        ),
        (
            "조성키로",
            "조성하기로",
            "조성하다",
            "기로",
            "contraction.ha_aspiration",
        ),
        (
            "돌변키도",
            "돌변하기도",
            "돌변하다",
            "기도",
            "contraction.ha_aspiration",
        ),
        ("생각기", "생각하기", "생각하다", "기", "deletion.ha"),
        ("생각지", "생각하지", "생각하다", "지", "deletion.ha"),
        ("생각건대", "생각하건대", "생각하다", "건대", "deletion.ha"),
        ("생각다", "생각하다", "생각하다", "다", "deletion.ha"),
        ("넉넉지", "넉넉하지", "넉넉하다", "지", "deletion.ha"),
        ("깨끗지", "깨끗하지", "깨끗하다", "지", "deletion.ha"),
        ("섭섭지", "섭섭하지", "섭섭하다", "지", "deletion.ha"),
        ("익숙지", "익숙하지", "익숙하다", "지", "deletion.ha"),
        (
            "간편케",
            "간편하게",
            "간편하다",
            "게",
            "contraction.ha_aspiration",
        ),
        (
            "연구토록",
            "연구하도록",
            "연구하다",
            "도록",
            "contraction.ha_aspiration",
        ),
        (
            "다정타",
            "다정하다",
            "다정하다",
            "다",
            "contraction.ha_aspiration",
        ),
        (
            "분발토록",
            "분발하도록",
            "분발하다",
            "도록",
            "contraction.ha_aspiration",
        ),
        (
            "무심치",
            "무심하지",
            "무심하다",
            "지",
            "contraction.ha_aspiration",
        ),
        (
            "결근코자",
            "결근하고자",
            "결근하다",
            "고자",
            "contraction.ha_aspiration",
        ),
        (
            "회상컨대",
            "회상하건대",
            "회상하다",
            "건대",
            "contraction.ha_aspiration",
        ),
        (
            "비유컨대",
            "비유하건대",
            "비유하다",
            "건대",
            "contraction.ha_aspiration",
        ),
        (
            "피케",
            "피하게",
            "피하다",
            "게",
            "contraction.ha_aspiration",
        ),
    ] {
        for word in [short, full] {
            let result = Lemmatizer::new().analyze_word(word).unwrap();
            let a = result
                .analyses
                .iter()
                .find(|a| path(a, &[lemma], &[ending]))
                .expect(word);
            assert_eq!(a.lemmas[0].kind, LemmaKind::Predicate);
            assert_eq!(a.morphemes[0].kind, MorphemeKind::Ending);
            if word == short {
                assert!(a.rules.iter().any(|r| r == rule), "{word}");
            }
            assert!(result.analyses.iter().any(|a| a.unchanged));
            assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
            assert!(
                result
                    .analyses
                    .iter()
                    .all(|a| a.rules.iter().all(|r| klem::rule_explanation(r).is_some()))
            );
        }
        let nfd: String = short.nfd().collect();
        assert_eq!(
            Lemmatizer::new().analyze_word(&nfd),
            Lemmatizer::new().analyze_word(short)
        );
    }
}

#[test]
fn contractions_compose_with_auxiliaries_particles_and_explicit_ending_variants() {
    for (word, lemmas, forms) in [
        ("강구키를", vec!["강구하다"], vec!["기", "를"]),
        ("조성키로", vec!["조성하다"], vec!["기", "로"]),
        ("생각기에", vec!["생각하다"], vec!["기", "에"]),
        (
            "돌변키도했다",
            vec!["돌변하다", "하다"],
            vec!["기도", "었", "다"],
        ),
        (
            "강구키만했다",
            vec!["강구하다", "하다"],
            vec!["기", "만", "었", "다"],
        ),
        (
            "생각기는했다",
            vec!["생각하다", "하다"],
            vec!["기는", "었", "다"],
        ),
        ("연구키이다", vec!["연구하다", "이다"], vec!["기", "다"]),
        (
            "생각지않았다",
            vec!["생각하다", "않다"],
            vec!["지", "었", "다"],
        ),
        (
            "간편케됐다",
            vec!["간편하다", "되다"],
            vec!["게", "었", "다"],
        ),
        (
            "생각지않았음을",
            vec!["생각하다", "않다"],
            vec!["지", "었", "음", "을"],
        ),
        ("생각지요", vec!["생각하다"], vec!["지", "요"]),
        ("간편케요", vec!["간편하다"], vec!["게요"]),
        ("간편케요", vec!["간편하다"], vec!["게", "요"]),
        ("만만치만", vec!["만만하다"], vec!["지만"]),
        ("다정타고", vec!["다정하다"], vec!["다고"]),
        ("다정타는", vec!["다정하다"], vec!["다는"]),
        ("다정타니", vec!["다정하다"], vec!["다니"]),
        ("다정타면", vec!["다정하다"], vec!["다면"]),
        ("걷지", vec!["걷다"], vec!["지"]),
        ("걷지", vec!["걷하다"], vec!["지"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
    }
}

#[test]
fn aspiration_and_deletion_cannot_swap_coda_classes_or_rewrite_arbitrary_tails() {
    assert!(
        !Lemmatizer::new()
            .analyze_word("생각다")
            .unwrap()
            .analyses
            .iter()
            .any(|a| path(a, &["생각하", "이다"], &["다"]))
    );
    for (word, lemma, ending) in [
        ("생각키", "생각하다", "기"),
        ("강구기", "강구하다", "기"),
        ("조성기로", "조성하다", "기로"),
        ("ABC키", "ABC하다", "기"),
        ("키", "하다", "기"),
        ("생각컨대", "생각하다", "건대"),
        ("익숙치", "익숙하다", "지"),
        ("깨끗치", "깨끗하다", "지"),
        ("섭섭치", "섭섭하다", "지"),
        ("간편게", "간편하다", "게"),
        ("비유건대", "비유하다", "건대"),
        ("연구도록", "연구하다", "도록"),
        ("무심지", "무심하다", "지"),
        ("분발도록", "분발하다", "도록"),
        ("피게", "피하다", "게"),
        ("생각케", "생각하다", "게"),
        ("피켜", "피하다", "게"),
        ("생각네요", "생각하다", "네요"),
        ("ABC케", "ABC하다", "게"),
        ("3케", "3하다", "게"),
        ("케", "하다", "게"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &[lemma], &[ending])),
            "{word}"
        );
    }
}
