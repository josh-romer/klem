//! COV-018c/017i: emphatic/concessive particles and the separate -(으)나마 ending.
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
fn emphatic_particles_compose_with_nominalizations_cases_and_derived_adverbs() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("학교야말로", vec!["학교"], vec!["야말로"]),
        ("학생이야말로", vec!["학생"], vec!["이야말로"]),
        ("길이야말로", vec!["길"], vec!["이야말로"]),
        ("학교에서야말로", vec!["학교"], vec!["에서", "야말로"]),
        ("학교로나마", vec!["학교"], vec!["로", "나마"]),
        ("학교에서나마", vec!["학교"], vec!["에서", "나마"]),
        ("학생만이나마", vec!["학생"], vec!["만", "이나마"]),
        ("학생들은커녕", vec!["학생"], vec!["들", "은커녕"]),
        ("사과는커녕", vec!["사과"], vec!["는커녕"]),
        ("학생은커녕", vec!["학생"], vec!["은커녕"]),
        ("밥커녕", vec!["밥"], vec!["커녕"]),
        ("버스커녕", vec!["버스"], vec!["커녕"]),
        ("학굔커녕", vec!["학교"], vec!["는커녕"]),
        ("화핸커녕", vec!["화해"], vec!["는커녕"]),
        ("먹기는커녕", vec!["먹다"], vec!["기", "는커녕"]),
        ("먹긴커녕", vec!["먹다"], vec!["기", "는커녕"]),
        ("먹었기는커녕", vec!["먹다"], vec!["었", "기", "는커녕"]),
        ("먹음은커녕", vec!["먹다"], vec!["음", "은커녕"]),
        (
            "먹어보기는커녕",
            vec!["먹다", "보다"],
            vec!["어", "기", "는커녕"],
        ),
        (
            "먹어보긴커녕",
            vec!["먹다", "보다"],
            vec!["어", "기", "는커녕"],
        ),
        (
            "먹고싶기는커녕",
            vec!["먹다", "싶다"],
            vec!["고", "기", "는커녕"],
        ),
        ("학생이기는커녕", vec!["학생", "이다"], vec!["기", "는커녕"]),
        ("학생답기는커녕", vec!["학생"], vec!["답다", "기", "는커녕"]),
        ("먹기야말로", vec!["먹다"], vec!["기", "야말로"]),
        ("먹음이나마", vec!["먹다"], vec!["음", "이나마"]),
        ("막연하게나마", vec!["막연하다"], vec!["게", "나마"]),
        ("조용히나마", vec!["조용하다"], vec!["히", "나마"]),
        ("빨리는커녕", vec!["빠르다"], vec!["이", "는커녕"]),
        ("학생이야말로요", vec!["학생"], vec!["이야말로", "요"]),
        ("서울서", vec!["서울"], vec!["서"]),
        ("부산서도", vec!["부산"], vec!["서", "도"]),
        ("시장서는", vec!["시장"], vec!["서", "는"]),
        ("학교서", vec!["학교"], vec!["서"]),
        ("학교서는커녕", vec!["학교"], vec!["서", "는커녕"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert!(a.morphemes.iter().any(|m| m.kind == MorphemeKind::Particle));
        assert!(a.rules.iter().any(|r| r == "particle"));
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert!(
            result
                .analyses
                .iter()
                .flat_map(|a| &a.rules)
                .all(|r| klem::rule_explanation(r).is_some())
        );
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        if word == "먹긴커녕" {
            assert!(
                a.rules
                    .iter()
                    .any(|r| r == "particle.contraction.nkeonyeong")
            );
            assert_eq!(a.morphemes[0].kind, MorphemeKind::Ending);
            assert_eq!(a.morphemes[1].kind, MorphemeKind::Particle);
        }
    }
    for (word, base, form) in [
        ("잠시나마", "잠시", "나마"),
        ("조금이나마", "조금", "이나마"),
        ("빨리야말로", "빨리", "야말로"),
        ("빨리는커녕", "빨리", "는커녕"),
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &[base], &[form]) && a.lemmas[0].kind == LemmaKind::Adverbial),
            "{word}"
        );
    }
    // Bare 커녕 has a nominal source license; do not manufacture an adverbial path.
    assert!(
        !engine
            .analyze_word("빨리커녕")
            .unwrap()
            .analyses
            .iter()
            .any(|a| path(a, &["빨리"], &["커녕"]) && a.lemmas[0].kind == LemmaKind::Adverbial)
    );
}

#[test]
fn concessive_ending_keeps_its_own_boundaries_prefinals_and_copular_alternative() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("작으나마", vec!["작다"], vec!["으나마"]),
        ("약소하나마", vec!["약소하다"], vec!["으나마"]),
        ("사나마", vec!["살다"], vec!["으나마"]),
        ("들으나마", vec!["듣다"], vec!["으나마"]),
        ("지으나마", vec!["짓다"], vec!["으나마"]),
        ("도우나마", vec!["돕다"], vec!["으나마"]),
        ("빨가나마", vec!["빨갛다"], vec!["으나마"]),
        (
            "먹으셨겠으나마",
            vec!["먹다"],
            vec!["시", "었", "겠", "으나마"],
        ),
        ("먹었었으나마", vec!["먹다"], vec!["었", "었", "으나마"]),
        ("먹지못하나마", vec!["먹다", "못하다"], vec!["지", "으나마"]),
        ("조금이나마", vec!["조금", "이다"], vec!["으나마"]),
        ("학생다우나마", vec!["학생"], vec!["답다", "으나마"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Ending);
        assert!(a.breakdown().is_some());
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    let result = engine.analyze_word("조금이나마").unwrap();
    assert!(
        result
            .analyses
            .iter()
            .any(|a| path(a, &["조금"], &["이나마"]))
    );
}

#[test]
fn emphatic_families_reject_wrong_allomorphs_and_unlicensed_chains() {
    for (word, lemmas, forms) in [
        ("조금이나마", vec!["조금"], vec!["이", "나마"]),
        ("학교가야말로", vec!["학교"], vec!["가", "야말로"]),
        ("학교를나마", vec!["학교"], vec!["를", "나마"]),
        ("학교서커녕", vec!["학교"], vec!["서", "커녕"]),
        ("학교이야말로", vec!["학교"], vec!["이야말로"]),
        ("학생야말로", vec!["학생"], vec!["야말로"]),
        ("길야말로", vec!["길"], vec!["야말로"]),
        ("학교이나마", vec!["학교"], vec!["이나마"]),
        ("학생나마", vec!["학생"], vec!["나마"]),
        ("학교은커녕", vec!["학교"], vec!["은커녕"]),
        ("학생는커녕", vec!["학생"], vec!["는커녕"]),
        ("학굘커녕", vec!["학교"], vec!["는커녕"]),
        ("학교야말로나마", vec!["학교"], vec!["야말로", "나마"]),
        ("학교나마나마", vec!["학교"], vec!["나마", "나마"]),
        ("학교는커녕은커녕", vec!["학교"], vec!["는커녕", "은커녕"]),
        ("학교요나마", vec!["학교"], vec!["요", "나마"]),
        ("먹는커녕", vec!["먹다"], vec!["는", "커녕"]),
        ("먹기는커녕", vec!["먹다"], vec!["기", "는", "커녕"]),
        ("먹고나마", vec!["먹다"], vec!["고", "나마"]),
        (
            "먹기는커녕하다",
            vec!["먹다", "하다"],
            vec!["기", "는커녕", "다"],
        ),
        ("살으나마", vec!["살다"], vec!["으나마"]),
        ("먹나마", vec!["먹다"], vec!["으나마"]),
        ("먹더나마", vec!["먹다"], vec!["더", "으나마"]),
        ("학생답으나마", vec!["학생"], vec!["답다", "으나마"]),
        ("먹으나마보다", vec!["먹다", "보다"], vec!["으나마", "다"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
    // No pronunciation is guessed for foreign nominal particle allomorphs.
    for (word, form, condition) in [
        ("ABC야말로", "야말로", "vowel"),
        ("3이나마", "이나마", "consonant"),
        ("ABC는커녕", "는커녕", "vowel"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let base = word.strip_suffix(form).unwrap();
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
    let result = Lemmatizer::new().analyze_word("ABC서").unwrap();
    let a = result
        .analyses
        .iter()
        .find(|a| path(a, &["ABC"], &["서"]))
        .unwrap();
    assert!(
        !a.rules
            .iter()
            .any(|r| r.starts_with("pronunciation.assumed_"))
    );
}
