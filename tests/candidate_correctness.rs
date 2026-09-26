//! Independent spelling constraints, not engine-generated expected outputs.
//! Linguistic sources and the scope of these negative cases: docs/rules.md.
use klem::Lemmatizer;

fn has_group(engine: &Lemmatizer, word: &str, lemmas: &[&str]) -> bool {
    engine.analyze_word(word).unwrap().analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(lemmas.iter().copied())
    })
}

fn has_path(engine: &Lemmatizer, word: &str, lemmas: &[&str], forms: &[&str]) -> bool {
    engine.analyze_word(word).unwrap().analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(lemmas.iter().copied())
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(forms.iter().copied())
    })
}

#[test]
fn nominal_plural_precedes_particles_and_copulas_without_replacing_lexical_readings() {
    use klem::MorphemeKind;
    let engine = Lemmatizer::new();
    // KRDict -들 (74906): nominal plural suffix; 을 (86355): consonant allomorph.
    for (word, lemmas, forms) in [
        ("지식인들", vec!["지식인"], vec!["들"]),
        ("지식인들을", vec!["지식인"], vec!["들", "을"]),
        ("친구들은", vec!["친구"], vec!["들", "은"]),
        (
            "지식인들에게서는",
            vec!["지식인"],
            vec!["들", "에게서", "는"],
        ),
        ("지식인들이다", vec!["지식인", "이다"], vec!["들", "다"]),
        ("지식인들이에요", vec!["지식인", "이다"], vec!["들", "에요"]),
        (
            "지식인들만이다",
            vec!["지식인", "이다"],
            vec!["들", "만", "다"],
        ),
        ("아들들을", vec!["아들"], vec!["들", "을"]),
    ] {
        assert!(
            has_path(&engine, word, &lemmas, &forms),
            "missing plural reading for {word}"
        );
        let result = engine.analyze_word(word).unwrap();
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for a in &result.analyses {
            assert!(a.breakdown().is_some(), "{word}: {a:?}");
            if a.rules.iter().any(|r| r == "suffix.plural") {
                assert_eq!(a.morphemes[0].kind, MorphemeKind::Suffix);
                assert_eq!(a.morphemes[0].form, "들");
            }
        }
    }
    assert!(has_path(&engine, "아들을", &["아들"], &["을"]));
    assert!(has_path(&engine, "들을", &["들"], &["을"]));
    for word in ["들", "들을", "들이다"] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|a| !a.rules.iter().any(|r| r == "suffix.plural"))
        );
    }
    for word in ["지식인들를", "지식인들가", "지식인들는"] {
        assert!(
            !has_group(&engine, word, &["지식인"]),
            "invalid particle boundary: {word}"
        );
    }
    assert!(!has_path(
        &engine,
        "지식인들들을",
        &["지식인"],
        &["들", "들", "을"]
    ));
}

#[test]
fn bieup_vowel_choice_depends_on_the_ending() {
    let engine = Lemmatizer::new();
    for (valid, invalid, lemma) in [
        ("도와", "도워", "돕다"),
        ("고와", "고워", "곱다"),
        ("추워", "추와", "춥다"),
        ("아름다워", "아름다와", "아름답다"),
        ("괴로워", "괴로와", "괴롭다"),
    ] {
        for ending in ["", "요", "서", "도", "야"] {
            let valid = format!("{valid}{ending}");
            let invalid = format!("{invalid}{ending}");
            assert!(
                has_group(&engine, &valid, &[lemma]),
                "{valid} missing {lemma}"
            );
            assert!(
                !has_group(&engine, &invalid, &[lemma]),
                "{invalid} must not recover {lemma}"
            );
        }
    }
    for (word, lemma) in [
        ("도왔다", "돕다"),
        ("고왔다", "곱다"),
        ("도우면", "돕다"),
        ("고우니", "곱다"),
        ("도운", "돕다"),
        ("고울", "곱다"),
        ("추우면", "춥다"),
        ("도우시다", "돕다"),
        ("고움", "곱다"),
        ("더우어", "덥다"),
        ("도워", "도우다"),
        ("고워", "고우다"),
    ] {
        assert!(has_group(&engine, word, &[lemma]), "{word} missing {lemma}");
    }
    for (word, lemma) in [
        ("도웠다", "돕다"),
        ("고웠다", "곱다"),
        ("도우어", "돕다"),
        ("고우어", "곱다"),
    ] {
        assert!(
            !has_group(&engine, word, &[lemma]),
            "{word} must not recover {lemma}"
        );
    }
}

#[test]
fn rira_cannot_bypass_eu_allomorph_selection() {
    let engine = Lemmatizer::new();
    for (valid, invalid, lemma) in [
        ("먹으리라", "먹리라", "먹다"),
        ("잡으리라", "잡리라", "잡다"),
        ("있으리라", "있리라", "있다"),
        ("갔으리라", "갔리라", "가다"),
        ("가겠으리라", "가겠리라", "가다"),
    ] {
        assert!(
            has_group(&engine, valid, &[lemma]),
            "{valid} missing {lemma}"
        );
        assert!(
            !has_group(&engine, invalid, &[lemma]),
            "{invalid} must not recover {lemma}"
        );
    }
    for (word, lemma) in [
        ("가리라", "가다"),
        ("살리라", "살다"),
        ("들으리라", "듣다"),
        ("추우리라", "춥다"),
    ] {
        assert!(has_group(&engine, word, &[lemma]), "{word} missing {lemma}");
    }
}

#[test]
fn interrogative_ni_and_connective_euni_are_distinct_paths() {
    let engine = Lemmatizer::new();
    for (word, lemma) in [
        ("먹니", "먹다"),
        ("듣니", "듣다"),
        ("그렇니", "그렇다"),
        ("하얗니", "하얗다"),
        ("춥니", "춥다"),
        ("사니", "살다"),
    ] {
        assert!(
            has_path(&engine, word, &[lemma], &["니"]),
            "{word} missing interrogative {lemma}"
        );
    }
    for (word, lemma) in [
        ("먹으니", "먹다"),
        ("들으니", "듣다"),
        ("그러니", "그렇다"),
        ("하야니", "하얗다"),
        ("추우니", "춥다"),
        ("사니", "살다"),
    ] {
        assert!(
            has_path(&engine, word, &[lemma], &["으니"]),
            "{word} missing connective {lemma}"
        );
    }
    assert!(!has_path(&engine, "그러니", &["그렇다"], &["니"]));
    assert!(!has_group(&engine, "살니", &["살다"]));
}

#[test]
fn obligation_connective_is_not_part_of_the_auxiliary_lemma() {
    let engine = Lemmatizer::new();
    // Joined input is recognized; standard spelling spaces 어야 and 하다.
    for (word, lemma, forms) in [
        ("먹어야한다", "먹다", vec!["어야", "는다"]),
        ("가야했다", "가다", vec!["어야", "었", "다"]),
        ("도와야해요", "돕다", vec!["어야", "어요"]),
        ("공부해야합니다", "공부하다", vec!["어야", "습니다"]),
    ] {
        assert!(
            has_path(&engine, word, &[lemma, "하다"], &forms),
            "{word} missing obligation analysis"
        );
        assert!(
            !engine.analyze_word(word).unwrap().analyses.iter().any(|a| a
                .lemmas
                .iter()
                .any(|l| l.kind == klem::LemmaKind::Auxiliary && l.text == "야하다")),
            "{word} has spurious auxiliary 야하다"
        );
    }
    assert!(has_group(
        &engine,
        "먹어봐야했다",
        &["먹다", "보다", "하다"]
    ));
    assert!(has_group(&engine, "야하다", &["야하다"])); // standalone lexical hypothesis remains
}

#[test]
fn auxiliary_groups_require_their_connectives() {
    let engine = Lemmatizer::new();
    for (valid, invalid, lemmas) in [
        ("먹어보다", "먹고보다", ["먹다", "보다"]),
        ("먹고싶다", "먹어싶다", ["먹다", "싶다"]),
        ("먹지않다", "먹게않다", ["먹다", "않다"]),
        ("먹게하다", "먹고하다", ["먹다", "하다"]),
        ("먹어야하다", "먹고야하다", ["먹다", "하다"]),
    ] {
        assert!(
            has_group(&engine, valid, &lemmas),
            "{valid} missing {lemmas:?}"
        );
        assert!(
            !has_group(&engine, invalid, &lemmas),
            "{invalid} wrongly groups {lemmas:?}"
        );
    }
}

#[test]
fn irregular_changes_stay_at_their_licensed_boundaries() {
    let engine = Lemmatizer::new();
    for (valid, invalid, lemma) in [
        ("들으면", "들면", "듣다"),
        ("걸어", "걸아", "걷다"),
        ("물어", "물아", "묻다"),
        ("실으면", "실면", "싣다"),
        ("듣고", "들고", "듣다"),
        ("지으면", "지면", "짓다"),
        ("지어", "지아", "짓다"),
        ("짓고", "지고", "짓다"),
        ("빨갛고", "빨가고", "빨갛다"),
        ("빨갛습니다", "빨가습니다", "빨갛다"),
        ("그렇고", "그래고", "그렇다"),
        ("몰라", "몰러", "모르다"),
        ("불러", "불라", "부르다"),
        ("모르고", "몰고", "모르다"),
        ("따라", "따러", "따르다"),
        ("아파", "아퍼", "아프다"),
    ] {
        assert!(
            has_group(&engine, valid, &[lemma]),
            "{valid} missing {lemma}"
        );
        assert!(
            !has_group(&engine, invalid, &[lemma]),
            "{invalid} must not recover {lemma}"
        );
    }
    for (word, lemma) in [
        ("빨개", "빨갛다"),
        ("빨간", "빨갛다"),
        ("빨감", "빨갛다"),
        ("빨가면", "빨갛다"),
        ("그래", "그렇다"),
        ("푸르러", "푸르다"),
        ("써", "쓰다"),
        ("걷어", "걷다"),
        ("물어", "물다"),
        ("벗어", "벗다"),
        ("좋아", "좋다"),
        ("잡아", "잡다"),
    ] {
        assert!(has_group(&engine, word, &[lemma]), "{word} missing {lemma}");
    }
}

#[test]
fn rieul_deletion_is_required_at_triggering_endings() {
    let engine = Lemmatizer::new();
    for (stem, shortened, lemma) in [
        ("살", "사", "살다"),
        ("알", "아", "알다"),
        ("만들", "만드", "만들다"),
        ("놀", "노", "놀다"),
    ] {
        for ending in [
            "는",
            "는데",
            "느냐",
            "느라고",
            "네",
            "나",
            "냐",
            "니",
            "니까",
            "세요",
            "십시오",
            "오",
        ] {
            let valid = format!("{shortened}{ending}");
            let invalid = format!("{stem}{ending}");
            assert!(
                engine
                    .analyze_word(&valid)
                    .unwrap()
                    .lemma_strings()
                    .contains(&lemma),
                "{valid} must recover {lemma}"
            );
            assert!(
                !engine
                    .analyze_word(&invalid)
                    .unwrap()
                    .lemma_strings()
                    .contains(&lemma),
                "{invalid} must not recover {lemma}"
            );
        }
        for ending in ["고", "면", "며", "려고", "지", "기"] {
            let valid = format!("{stem}{ending}");
            assert!(
                engine
                    .analyze_word(&valid)
                    .unwrap()
                    .lemma_strings()
                    .contains(&lemma),
                "{valid} must retain ㄹ in {lemma}"
            );
        }
    }
    // Honorific prefinals and ㄷ irregular recovery use different boundaries.
    for (word, lemma) in [
        ("사셨다", "살다"),
        ("들으니", "듣다"),
        ("들으니까", "듣다"),
        ("살면", "살다"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .lemma_strings()
                .contains(&lemma),
            "{word} missing {lemma}"
        );
    }
    assert!(
        !engine
            .analyze_word("살셨다")
            .unwrap()
            .lemma_strings()
            .contains(&"살다")
    );
}

#[test]
fn copular_i_is_not_stripped_from_arbitrary_predicates() {
    let engine = Lemmatizer::new();
    for (word, forbidden) in [
        ("학생이라", "학생다"),
        ("학생이라서", "학생다"),
        ("학생이라고", "학생다"),
        ("학생이라는", "학생다"),
        ("학생이라면", "학생다"),
        ("먹이라", "먹다"),
        ("먹이라고", "먹다"),
        ("먹라는", "먹다"),
        ("먹라고", "먹다"),
        ("먹라면", "먹다"),
        ("먹라서", "먹다"),
        ("가라서", "가다"),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .lemma_strings()
                .contains(&forbidden),
            "{word} must not recover {forbidden}"
        );
    }
    for (word, expected) in [
        ("먹이라", "먹이다"),
        ("먹이라고", "먹이다"),
        ("먹으라고", "먹다"),
        ("먹으라는", "먹다"),
        ("먹으라면", "먹다"),
        ("가라고", "가다"),
        ("가라는", "가다"),
        ("가라면", "가다"),
        ("아니라", "아니다"),
        ("아니라서", "아니다"),
        ("아니라고", "아니다"),
        ("아니라는", "아니다"),
        ("아니라면", "아니다"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .lemma_strings()
                .contains(&expected),
            "{word} missing {expected}"
        );
    }
}

#[test]
fn explicit_and_omitted_copulas_keep_component_groups() {
    let engine = Lemmatizer::new();
    for (base, forms) in [
        (
            "학생",
            [
                "학생이라",
                "학생이라서",
                "학생이라고",
                "학생이라는",
                "학생이라면",
            ],
        ),
        (
            "의사",
            ["의사라", "의사라서", "의사라고", "의사라는", "의사라면"],
        ),
    ] {
        for word in forms {
            let result = engine.analyze_word(word).unwrap();
            assert!(
                result.analyses.iter().any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq([base, "이다"])),
                "{word} missing grouped copula"
            );
        }
    }
}

#[test]
fn unverified_lexical_classes_remain_alternatives() {
    let engine = Lemmatizer::new();
    for (word, alternatives) in [("들어", ["들다", "듣다"]), ("사는", ["사다", "살다"])]
    {
        let result = engine.analyze_word(word).unwrap();
        for expected in alternatives {
            assert!(
                result.lemma_strings().contains(&expected),
                "{word} missing {expected}"
            );
        }
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
