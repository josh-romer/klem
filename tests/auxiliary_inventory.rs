//! COV-019: connector-specific paths from KRDict's auxiliary attachment notes.
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
fn documented_auxiliary_families_preserve_order_and_lexical_alternatives() {
    for (word, lemmas, forms) in [
        (
            "번져나갔다",
            vec!["번지다", "나가다"],
            vec!["어", "었", "다"],
        ),
        ("늘어났다", vec!["늘다", "나다"], vec!["어", "었", "다"]),
        ("먹고났다", vec!["먹다", "나다"], vec!["고", "었", "다"]),
        ("먹고계셨다", vec!["먹다", "계시다"], vec!["고", "었", "다"]),
        ("앉아계신다", vec!["앉다", "계시다"], vec!["어", "는다"]),
        ("먹어가지고", vec!["먹다", "가지다"], vec!["어", "고"]),
        ("먹어갖고", vec!["먹다", "갖다"], vec!["어", "고"]),
        ("먹어달라", vec!["먹다", "달다"], vec!["어", "으라"]),
        ("먹어다오", vec!["먹다", "달다"], vec!["어", "오"]),
        (
            "칭찬해마지않는다",
            vec!["칭찬하다", "마지않다"],
            vec!["어", "는다"],
        ),
        (
            "칭찬해마지아니한다",
            vec!["칭찬하다", "마지아니하다"],
            vec!["어", "는다"],
        ),
        ("벌어먹는다", vec!["벌다", "먹다"], vec!["어", "는다"]),
        (
            "먹어버릇했다",
            vec!["먹다", "버릇하다"],
            vec!["어", "었", "다"],
        ),
        ("낡아빠졌다", vec!["낡다", "빠지다"], vec!["어", "었", "다"]),
        ("울어쌓는다", vec!["울다", "쌓다"], vec!["어", "는다"]),
        ("웃어재낀다", vec!["웃다", "재끼다"], vec!["어", "는다"]),
        ("웃어젖힌다", vec!["웃다", "젖히다"], vec!["어", "는다"]),
        ("좋아죽겠다", vec!["좋다", "죽다"], vec!["어", "겠", "다"]),
        ("먹어치웠다", vec!["먹다", "치우다"], vec!["어", "었", "다"]),
        (
            "느려터졌다",
            vec!["느리다", "터지다"],
            vec!["어", "었", "다"],
        ),
        ("예뻐한다", vec!["예쁘다", "하다"], vec!["어", "는다"]),
        ("먹고보자", vec!["먹다", "보다"], vec!["고", "자"]),
        ("먹고한다", vec!["먹다", "하다"], vec!["고", "는다"]),
        (
            "먹고자빠졌다",
            vec!["먹다", "자빠지다"],
            vec!["고", "었", "다"],
        ),
        (
            "먹지아니했다",
            vec!["먹다", "아니하다"],
            vec!["지", "었", "다"],
        ),
        ("먹게생겼다", vec!["먹다", "생기다"], vec!["게", "었", "다"]),
        ("먹으려고든다", vec!["먹다", "들다"], vec!["으려고", "는다"]),
        (
            "먹기로들었다",
            vec!["먹다", "들다"],
            vec!["기로", "었", "다"],
        ),
        ("먹자고든다", vec!["먹다", "들다"], vec!["자고", "는다"]),
        ("먹고든다", vec!["먹다", "들다"], vec!["고", "는다"]),
        ("먹는듯하다", vec!["먹다", "듯하다"], vec!["는", "다"]),
        ("먹은듯싶다", vec!["먹다", "듯싶다"], vec!["은", "다"]),
        ("먹을만하다", vec!["먹다", "만하다"], vec!["을", "다"]),
        ("먹을법하다", vec!["먹다", "법하다"], vec!["을", "다"]),
        ("먹을뻔했다", vec!["먹다", "뻔하다"], vec!["을", "었", "다"]),
        ("먹을성싶다", vec!["먹다", "성싶다"], vec!["을", "다"]),
        ("먹는양한다", vec!["먹다", "양하다"], vec!["는", "는다"]),
        ("먹음직하다", vec!["먹다", "직하다"], vec!["음", "다"]),
        ("먹은척했다", vec!["먹다", "척하다"], vec!["은", "었", "다"]),
        ("먹는체했다", vec!["먹다", "체하다"], vec!["는", "었", "다"]),
        ("먹나보다", vec!["먹다", "보다"], vec!["나", "다"]),
        ("먹는가싶다", vec!["먹다", "싶다"], vec!["는가", "다"]),
        ("먹을까보다", vec!["먹다", "보다"], vec!["을까", "다"]),
        (
            "먹었으면한다",
            vec!["먹다", "하다"],
            vec!["었", "으면", "는다"],
        ),
        (
            "먹었으면싶다",
            vec!["먹다", "싶다"],
            vec!["었", "으면", "다"],
        ),
        ("살다보니", vec!["살다", "보다"], vec!["다", "으니"]),
        ("살다가보면", vec!["살다", "보다"], vec!["다가", "으면"]),
        ("참다못해", vec!["참다", "못하다"], vec!["다", "어"]),
        ("먹으려한다", vec!["먹다", "하다"], vec!["으려", "는다"]),
        ("먹고자한다", vec!["먹다", "하다"], vec!["고자", "는다"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "auxiliary"), "{word}");
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(
            result.analyses.iter().all(|a| a.breakdown().is_some()),
            "{word}"
        );
        assert_eq!(
            result,
            Lemmatizer::new()
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
}

#[test]
fn internal_particles_keep_their_positions_and_boundary_licenses() {
    for (word, lemmas, forms) in [
        ("먹어들봐요", vec!["먹다", "보다"], vec!["어", "들", "어요"]),
        (
            "먹어만봤다",
            vec!["먹다", "보다"],
            vec!["어", "만", "었", "다"],
        ),
        (
            "먹어도봤다",
            vec!["먹다", "보다"],
            vec!["어", "도", "었", "다"],
        ),
        (
            "먹고야말았다",
            vec!["먹다", "말다"],
            vec!["고", "야", "었", "다"],
        ),
        (
            "먹고는했다",
            vec!["먹다", "하다"],
            vec!["고", "는", "었", "다"],
        ),
        (
            "먹곤했다",
            vec!["먹다", "하다"],
            vec!["고", "는", "었", "다"],
        ),
        (
            "먹기도했다",
            vec!["먹다", "하다"],
            vec!["기", "도", "었", "다"],
        ),
        (
            "먹기는했다",
            vec!["먹다", "하다"],
            vec!["기", "는", "었", "다"],
        ),
        (
            "먹기나했다",
            vec!["먹다", "하다"],
            vec!["기", "나", "었", "다"],
        ),
        (
            "먹기야했다",
            vec!["먹다", "하다"],
            vec!["기", "야", "었", "다"],
        ),
        (
            "먹기만했다",
            vec!["먹다", "하다"],
            vec!["기", "만", "었", "다"],
        ),
        (
            "먹어들보고있다",
            vec!["먹다", "보다", "있다"],
            vec!["어", "들", "고", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "auxiliary.internal_particle"));
        assert_eq!(a.morphemes[1].kind, MorphemeKind::Particle);
        assert_eq!(
            a.breakdown().unwrap().len(),
            a.lemmas.len() + a.morphemes.len()
        );
    }
    for (word, lemmas) in [
        ("먹어만하다", vec!["먹다", "만하다"]),
        ("먹는법하다", vec!["먹다", "법하다"]),
        ("먹고나가다", vec!["먹다", "나가다"]),
        ("먹게보다", vec!["먹다", "보다"]),
        ("먹어가졌다", vec!["먹다", "가지다"]),
        ("먹어달았다", vec!["먹다", "달다"]),
        ("먹기들하다", vec!["먹다", "하다"]),
        ("먹고야하다", vec!["먹다", "하다"]),
        ("먹어들들보다", vec!["먹다", "보다"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())),
            "{word}"
        );
    }
}

#[test]
fn negative_auxiliary_particles_and_short_imperatives() {
    for (word, lemmas, forms) in [
        ("마", vec!["말다"], vec!["어"]),
        ("마라", vec!["말다"], vec!["어라"]),
        ("마요", vec!["말다"], vec!["어요"]),
        ("먹지마", vec!["먹다", "말다"], vec!["지", "어"]),
        ("먹지마라", vec!["먹다", "말다"], vec!["지", "어라"]),
        ("먹지마요", vec!["먹다", "말다"], vec!["지", "어요"]),
        ("먹지말아", vec!["먹다", "말다"], vec!["지", "어"]),
        ("먹지말아라", vec!["먹다", "말다"], vec!["지", "어라"]),
        ("먹지말아요", vec!["먹다", "말다"], vec!["지", "어요"]),
        ("먹지마세요", vec!["먹다", "말다"], vec!["지", "으세요"]),
        (
            "먹지는않았다",
            vec!["먹다", "않다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹진않았다",
            vec!["먹다", "않다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹지는못했다",
            vec!["먹다", "못하다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹진못했다",
            vec!["먹다", "못하다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹지는아니했다",
            vec!["먹다", "아니하다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹진아니했다",
            vec!["먹다", "아니하다"],
            vec!["지", "는", "었", "다"],
        ),
        ("먹지는말자", vec!["먹다", "말다"], vec!["지", "는", "자"]),
        ("먹진마라", vec!["먹다", "말다"], vec!["지", "는", "어라"]),
        ("먹지만마", vec!["먹다", "말다"], vec!["지", "만", "어"]),
        ("먹지도마요", vec!["먹다", "말다"], vec!["지", "도", "어요"]),
        (
            "먹어보지는않았다",
            vec!["먹다", "보다", "않다"],
            vec!["어", "지", "는", "었", "다"],
        ),
        (
            "먹어보진마요",
            vec!["먹다", "보다", "말다"],
            vec!["어", "지", "는", "어요"],
        ),
        // NIKL accepts questions and indirect wishes; do not impose a final-mood whitelist.
        ("먹지말까요", vec!["먹다", "말다"], vec!["지", "을까요"]),
        (
            "먹지말았으면",
            vec!["먹다", "말다"],
            vec!["지", "었", "으면"],
        ),
        ("먹지말라고", vec!["먹다", "말다"], vec!["지", "으라고"]),
        (
            "먹지말아야한다",
            vec!["먹다", "말다", "하다"],
            vec!["지", "어야", "는다"],
        ),
        ("먹고말았다", vec!["먹다", "말다"], vec!["고", "었", "다"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.breakdown().is_some(), "{word}");
        if forms.contains(&"는") {
            assert!(
                a.rules.iter().any(|r| r == "auxiliary.internal_particle"),
                "{word}"
            );
            assert_eq!(
                a.morphemes.iter().find(|m| m.form == "는").unwrap().kind,
                MorphemeKind::Particle
            );
        }
        if word.contains('진') {
            assert!(
                a.rules.iter().any(|r| r == "particle.contraction.n"),
                "{word}"
            );
        }
        if ["마", "마라", "마요"].contains(&word) {
            assert!(a.rules.iter().any(|r| r == "irregular.mal"));
        }
        assert!(result.analyses.iter().any(|a| a.unchanged), "{word}");
        assert_eq!(
            result,
            Lemmatizer::new()
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        for rule in &a.rules {
            assert!(klem::rule_explanation(rule).is_some(), "{rule}");
        }
    }
}

#[test]
fn negative_shortening_does_not_invent_other_stems_or_connectors() {
    for (word, lemmas, forms) in [
        ("사", vec!["살다"], vec!["어"]),
        ("마서", vec!["말다"], vec!["어서"]),
        ("마야", vec!["말다"], vec!["어야"]),
        ("맜다", vec!["말다"], vec!["었", "다"]),
        ("먹고마", vec!["먹다", "말다"], vec!["고", "어"]),
        ("먹고마라", vec!["먹다", "말다"], vec!["고", "어라"]),
        ("먹지마라요", vec!["먹다", "말다"], vec!["지", "어라", "요"]),
        (
            "먹지마봐",
            vec!["먹다", "말다", "보다"],
            vec!["지", "어", "어"],
        ),
        ("먹지는보다", vec!["먹다", "보다"], vec!["지", "는", "다"]),
        ("먹진하다", vec!["먹다", "하다"], vec!["지", "는", "다"]),
        (
            "먹지는는않다",
            vec!["먹다", "않다"],
            vec!["지", "는", "는", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}

#[test]
fn known_auxiliary_classes_reject_incompatible_bare_endings() {
    // Each is an auxiliary adjective in KRDict; both consonant and vowel
    // allomorphs of the present/adnominal verb endings must be excluded.
    for (prefix, head, stem, adjective) in [
        ("먹고", "먹다", "싶", "싶다"),
        ("먹는", "먹다", "듯하", "듯하다"),
        ("먹는", "먹다", "듯싶", "듯싶다"),
        ("먹을", "먹다", "만하", "만하다"),
        ("먹을", "먹다", "법하", "법하다"),
        ("먹을", "먹다", "뻔하", "뻔하다"),
        ("먹을", "먹다", "성싶", "성싶다"),
        ("먹음", "먹다", "직하", "직하다"),
    ] {
        for ending in [
            "는",
            "는데",
            "는데요",
            "는데도",
            "는데다가",
            "는지",
            "는가",
            "는가요",
            "느냐",
            "느냐는",
        ] {
            let word = format!("{prefix}{stem}{ending}");
            let a = Lemmatizer::new().analyze_word(&word).unwrap();
            assert!(
                !a.analyses.iter().any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq([head, adjective])),
                "{word}"
            );
            assert!(a.analyses.iter().any(|a| a.unchanged));
        }
        for ending in ["다", "다고", "다는", "다면"] {
            let present_stem = if stem.ends_with('하') {
                format!("{}한", stem.strip_suffix('하').unwrap())
            } else {
                format!("{stem}는")
            };
            let word = format!("{prefix}{present_stem}{ending}");
            let a = Lemmatizer::new().analyze_word(&word).unwrap();
            assert!(
                !a.analyses.iter().any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq([head, adjective])),
                "{word}"
            );
        }
        let word = format!("{prefix}{stem}다");
        assert!(
            Lemmatizer::new()
                .analyze_word(&word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq([head, adjective])),
            "{word}"
        );
    }
}

#[test]
fn auxiliary_class_follows_connectors_negation_and_derivation() {
    for (word, lemmas, forms) in [
        ("먹고계신가", vec!["먹다", "계시다"], vec!["고", "은가"]),
        (
            "먹고있지않은가",
            vec!["먹다", "있다", "않다"],
            vec!["고", "지", "은가"],
        ),
        ("먹고싶은", vec!["먹다", "싶다"], vec!["고", "은"]),
        ("먹을만한", vec!["먹다", "만하다"], vec!["을", "은"]),
        (
            "먹고싶었는데",
            vec!["먹다", "싶다"],
            vec!["고", "었", "는데"],
        ),
        (
            "먹고싶겠는가",
            vec!["먹다", "싶다"],
            vec!["고", "겠", "는가"],
        ),
        (
            "먹고싶었느냐는",
            vec!["먹다", "싶다"],
            vec!["고", "었", "느냐는"],
        ),
        ("먹고싶어라", vec!["먹다", "싶다"], vec!["고", "어라"]),
        (
            "먹고싶지않은",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "은"],
        ),
        (
            "먹고싶지는않은",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "는", "은"],
        ),
        (
            "먹고싶잖은",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "은"],
        ),
        (
            "먹고싶지아니한",
            vec!["먹다", "싶다", "아니하다"],
            vec!["고", "지", "은"],
        ),
        (
            "먹고싶지못한",
            vec!["먹다", "싶다", "못하다"],
            vec!["고", "지", "은"],
        ),
        (
            "먹고싶지않지않은",
            vec!["먹다", "싶다", "않다", "않다"],
            vec!["고", "지", "지", "은"],
        ),
        (
            "먹어보지않는",
            vec!["먹다", "보다", "않다"],
            vec!["어", "지", "는"],
        ),
        (
            "먹고싶어하는",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "어", "는"],
        ),
        ("먹어본다", vec!["먹다", "보다"], vec!["어", "는다"]),
        ("먹나보다", vec!["먹다", "보다"], vec!["나", "다"]),
        ("먹나본가", vec!["먹다", "보다"], vec!["나", "은가"]),
        ("먹고본다", vec!["먹다", "보다"], vec!["고", "는다"]),
        ("먹고본가", vec!["먹다", "보다"], vec!["고", "은가"]),
        (
            "학생답지않은",
            vec!["학생", "않다"],
            vec!["답다", "지", "은"],
        ),
        (
            "학생인듯한",
            vec!["학생", "이다", "듯하다"],
            vec!["은", "은"],
        ),
        ("먹지않는", vec!["먹다", "않다"], vec!["지", "는"]),
        ("좋지않은", vec!["좋다", "않다"], vec!["지", "은"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.breakdown().is_some(), "{word}");
        assert_eq!(
            result,
            Lemmatizer::new()
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    for (word, lemmas, forms) in [
        ("먹나본다", vec!["먹다", "보다"], vec!["나", "는다"]),
        (
            "먹고싶지않는",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "는"],
        ),
        (
            "먹고싶지는않는",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "는", "는"],
        ),
        (
            "먹고싶잖는",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "는"],
        ),
        (
            "먹고싶지아니하는",
            vec!["먹다", "싶다", "아니하다"],
            vec!["고", "지", "는"],
        ),
        (
            "먹고싶지못하는",
            vec!["먹다", "싶다", "못하다"],
            vec!["고", "지", "는"],
        ),
        (
            "먹고싶지않지않는",
            vec!["먹다", "싶다", "않다", "않다"],
            vec!["고", "지", "지", "는"],
        ),
        (
            "학생답지않는",
            vec!["학생", "않다"],
            vec!["답다", "지", "는"],
        ),
        (
            "학생인듯하는",
            vec!["학생", "이다", "듯하다"],
            vec!["은", "는"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}

#[test]
fn lexical_eopda_is_not_an_eo_auxiliary() {
    for word in [
        "먹어없다",
        "먹어없었다",
        "먹어없어요",
        "먹어도없다",
        "학생다워없다",
        "먹어없어보다",
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .any(|l| l.text == "없다" && l.kind == klem::LemmaKind::Auxiliary)),
            "{word}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    for word in ["없다", "없어요", "없으면", "없는", "없이"] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .lemma_strings()
                .contains(&"없다"),
            "{word}"
        );
    }
}
