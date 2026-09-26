//! COV-020h: omitted copula before reviewed attached question endings.
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
fn omitted_questions_preserve_full_copula_parity_and_ordered_roles() {
    let engine = Lemmatizer::new();
    for (word, full_word, head, form) in [
        ("뭔지", "뭐인지", "뭐", "은지"),
        ("뭔가", "뭐인가", "뭐", "은가"),
        ("뭔가요", "뭐인가요", "뭐", "은가요"),
        ("뭘까", "뭐일까", "뭐", "을까"),
        ("뭘까요", "뭐일까요", "뭐", "을까요"),
        ("뭘지", "뭐일지", "뭐", "을지"),
        ("누군지", "누구인지", "누구", "은지"),
        ("누군가", "누구인가", "누구", "은가"),
        ("누군가요", "누구인가요", "누구", "은가요"),
        ("누굴까", "누구일까", "누구", "을까"),
        ("누굴까요", "누구일까요", "누구", "을까요"),
        ("누굴지", "누구일지", "누구", "을지"),
        ("어딘지", "어디인지", "어디", "은지"),
        ("어딘가", "어디인가", "어디", "은가"),
        ("어딘가요", "어디인가요", "어디", "은가요"),
        ("어딜까", "어디일까", "어디", "을까"),
        ("어딜까요", "어디일까요", "어디", "을까요"),
        ("어딜지", "어디일지", "어디", "을지"),
        ("언젠지", "언제인지", "언제", "은지"),
        ("언젠가", "언제인가", "언제", "은가"),
        ("언젠가요", "언제인가요", "언제", "은가요"),
        ("언젤까", "언제일까", "언제", "을까"),
        ("언젤까요", "언제일까요", "언제", "을까요"),
        ("언젤지", "언제일지", "언제", "을지"),
        ("얼만지", "얼마인지", "얼마", "은지"),
        ("얼만가", "얼마인가", "얼마", "은가"),
        ("얼만가요", "얼마인가요", "얼마", "은가요"),
        ("얼말까", "얼마일까", "얼마", "을까"),
        ("얼말까요", "얼마일까요", "얼마", "을까요"),
        ("얼말지", "얼마일지", "얼마", "을지"),
        ("무언지", "무어인지", "무어", "은지"),
        ("무언가", "무어인가", "무어", "은가"),
        ("무언가요", "무어인가요", "무어", "은가요"),
        ("무얼까", "무어일까", "무어", "을까"),
        ("무얼까요", "무어일까요", "무어", "을까요"),
        ("무얼지", "무어일지", "무어", "을지"),
        ("의산지", "의사인지", "의사", "은지"),
        ("의산가", "의사인가", "의사", "은가"),
        ("의산가요", "의사인가요", "의사", "은가요"),
        ("의살까", "의사일까", "의사", "을까"),
        ("의살까요", "의사일까요", "의사", "을까요"),
        ("의살지", "의사일지", "의사", "을지"),
        ("학굔지", "학교인지", "학교", "은지"),
        ("학굔가", "학교인가", "학교", "은가"),
        ("학굔가요", "학교인가요", "학교", "은가요"),
        ("학굘까", "학교일까", "학교", "을까"),
        ("학굘까요", "학교일까요", "학교", "을까요"),
        ("학굘지", "학교일지", "학교", "을지"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let full = engine.analyze_word(full_word).unwrap();
        let candidate = result
            .analyses
            .iter()
            .find(|a| path(a, &[head, "이다"], &[form]))
            .expect(word);
        assert_eq!(candidate.lemmas[0].kind, LemmaKind::Nominal);
        assert_eq!(candidate.lemmas[1].kind, LemmaKind::Copula);
        assert!(candidate.rules.iter().any(|r| r == "copula.omitted_ending"));
        assert!(
            full.analyses
                .iter()
                .any(|a| a.lemmas == candidate.lemmas && a.morphemes == candidate.morphemes),
            "{word}"
        );
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
    }
}
#[test]
fn omitted_questions_compose_with_particles_nominalizations_and_auxiliaries() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("뭔지요", vec!["뭐", "이다"], vec!["은지", "요"]),
        ("뭔가요", vec!["뭐", "이다"], vec!["은가", "요"]),
        ("뭘까요", vec!["뭐", "이다"], vec!["을까", "요"]),
        ("뭔지를", vec!["뭐", "이다"], vec!["은지", "를"]),
        ("누군가의", vec!["누구", "이다"], vec!["은가", "의"]),
        ("언젠가는", vec!["언제", "이다"], vec!["은가", "는"]),
        ("뭔가보다", vec!["뭐", "이다", "보다"], vec!["은가", "다"]),
        (
            "누군가싶다",
            vec!["누구", "이다", "싶다"],
            vec!["은가", "다"],
        ),
        ("뭘까싶다", vec!["뭐", "이다", "싶다"], vec!["을까", "다"]),
        ("먹긴지", vec!["먹다", "이다"], vec!["기", "은지"]),
        (
            "먹어보긴가",
            vec!["먹다", "보다", "이다"],
            vec!["어", "기", "은가"],
        ),
        ("먹길까", vec!["먹다", "이다"], vec!["기", "을까"]),
        ("건지", vec!["거", "이다"], vec!["은지"]),
        ("건지", vec!["것", "이다"], vec!["은지"]),
        ("건가", vec!["것", "이다"], vec!["은가"]),
        ("걸까", vec!["것", "이다"], vec!["을까"]),
        ("이건지", vec!["이것", "이다"], vec!["은지"]),
        ("그건가요", vec!["그것", "이다"], vec!["은가요"]),
        ("저걸까요", vec!["저것", "이다"], vec!["을까요"]),
        ("학생인지", vec!["학생", "이다"], vec!["은지"]),
        ("길인가", vec!["길", "이다"], vec!["은가"]),
        ("학생일까", vec!["학생", "이다"], vec!["을까"]),
        ("누구였는지", vec!["누구", "이다"], vec!["었", "는지"]),
        ("누구겠는가", vec!["누구", "이다"], vec!["겠", "는가"]),
        ("무엇인지", vec!["무엇", "이다"], vec!["은지"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?} {forms:?}"
        );
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
    }
}
#[test]
fn omitted_questions_require_nominal_boundaries_and_copula_roles() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("학생지", vec!["학생", "이다"], vec!["은지"]),
        ("학생가", vec!["학생", "이다"], vec!["은가"]),
        ("학생까", vec!["학생", "이다"], vec!["을까"]),
        ("학생가지", vec!["학생", "이다"], vec!["은지"]),
        ("길가", vec!["길", "이다"], vec!["은가"]),
        ("길까", vec!["길", "이다"], vec!["을까"]),
        ("산지", vec!["살", "이다"], vec!["은지"]),
        ("도운가", vec!["돕", "이다"], vec!["은가"]),
        ("파란가", vec!["파랗", "이다"], vec!["은가"]),
        ("뭐지", vec!["뭐", "이다"], vec!["은지"]),
        ("뭐가", vec!["뭐", "이다"], vec!["은가"]),
        ("뭐까", vec!["뭐", "이다"], vec!["을까"]),
        ("ABC가", vec!["ABC", "이다"], vec!["은가"]),
        ("7까", vec!["7", "이다"], vec!["을까"]),
        ("뭔지", vec!["뭐이다"], vec!["은지"]),
        ("뭔가", vec!["뭐이다"], vec!["은가"]),
        ("뭘까", vec!["뭐이다"], vec!["을까"]),
        (
            "누군가본다",
            vec!["누구", "이다", "보다"],
            vec!["은가", "는다"],
        ),
        (
            "뭘까싶는다",
            vec!["뭐", "이다", "싶다"],
            vec!["을까", "는다"],
        ),
        ("뭔지다", vec!["뭐", "이다", "이다"], vec!["은지", "다"]),
        ("뭔가다", vec!["뭐", "이다", "이다"], vec!["은가", "다"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}: {lemmas:?} {forms:?}"
        );
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
    }
}
#[test]
fn copula_questions_preserve_existing_particle_and_lexical_alternatives() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("뭘", vec!["뭐"], vec!["를"]),
        ("뭘", vec!["무엇"], vec!["을"]),
        ("뭐가", vec!["뭐"], vec!["가"]),
        ("건", vec!["것"], vec!["는"]),
        ("걸", vec!["것"], vec!["를"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
    let result = engine.analyze_word("왠지").unwrap();
    assert!(
        result
            .analyses
            .iter()
            .any(|a| a.unchanged && a.lemmas[0].text == "왠지")
    );
}
