//! COV-019f: known left classes before continuative/resultative 있다/계시다.
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
fn continuatives_reject_known_adjectives_copulas_and_inherited_classes() {
    let engine = Lemmatizer::new();
    // Both connectors and both auxiliaries must check the immediate left role.
    for (base, vowel, lemmas, prefix) in [
        ("먹고싶", "먹고싶어", vec!["먹다", "싶다"], vec!["고"]),
        ("먹을만하", "먹을만해", vec!["먹다", "만하다"], vec!["을"]),
        ("먹을듯하", "먹을듯해", vec!["먹다", "듯하다"], vec!["을"]),
        ("먹을법하", "먹을법해", vec!["먹다", "법하다"], vec!["을"]),
        ("먹을뻔하", "먹을뻔해", vec!["먹다", "뻔하다"], vec!["을"]),
        ("먹을성싶", "먹을성싶어", vec!["먹다", "성싶다"], vec!["을"]),
        ("먹음직하", "먹음직해", vec!["먹다", "직하다"], vec!["음"]),
        ("먹는가보", "먹는가봐", vec!["먹다", "보다"], vec!["는가"]),
        ("참다못하", "참다못해", vec!["참다", "못하다"], vec!["다"]),
        ("학생이", "학생이어", vec!["학생", "이다"], vec![]),
        ("먹기이", "먹기이어", vec!["먹다", "이다"], vec!["기"]),
    ] {
        for connector in ["어", "고"] {
            for (aux, tail) in [("있다", "있다"), ("계시다", "계신다")] {
                let word = if connector == "어" {
                    format!("{vowel}{tail}")
                } else {
                    format!("{base}{connector}{tail}")
                };
                let mut ls = lemmas.clone();
                ls.push(aux);
                let mut fs = prefix.clone();
                fs.extend([connector, if aux == "있다" { "다" } else { "는다" }]);
                let result = engine.analyze_word(&word).unwrap();
                assert!(!result.analyses.iter().any(|a| path(a, &ls, &fs)), "{word}");
                assert!(result.analyses.iter().any(|a| a.unchanged));
            }
        }
    }
    for (word, lemmas, forms) in [
        (
            "먹고는싶어있는다",
            vec!["먹다", "싶다", "있다"],
            vec!["고", "는", "어", "는다"],
        ),
        (
            "먹곤싶어계신다",
            vec!["먹다", "싶다", "계시다"],
            vec!["고", "는", "어", "는다"],
        ),
        (
            "먹고싶지않고있다",
            vec!["먹다", "싶다", "않다", "있다"],
            vec!["고", "지", "고", "다"],
        ),
        (
            "먹고싶지는않아있다",
            vec!["먹다", "싶다", "않다", "있다"],
            vec!["고", "지", "는", "어", "다"],
        ),
        (
            "먹고싶잖아계신다",
            vec!["먹다", "싶다", "않다", "계시다"],
            vec!["고", "지", "어", "는다"],
        ),
        (
            "먹고싶지아니하고계신다",
            vec!["먹다", "싶다", "아니하다", "계시다"],
            vec!["고", "지", "고", "는다"],
        ),
        (
            "먹고싶지못해있다",
            vec!["먹다", "싶다", "못하다", "있다"],
            vec!["고", "지", "어", "다"],
        ),
        (
            "먹고싶어도있다",
            vec!["먹다", "싶다", "있다"],
            vec!["고", "어", "도", "다"],
        ),
        (
            "먹고싶었고있다",
            vec!["먹다", "싶다", "있다"],
            vec!["고", "었", "고", "다"],
        ),
        (
            "학생이시고계신다",
            vec!["학생", "이다", "계시다"],
            vec!["시", "고", "는다"],
        ),
        (
            "학생이었어있다",
            vec!["학생", "이다", "있다"],
            vec!["었", "어", "다"],
        ),
        ("의사고있다", vec!["의사", "이다", "있다"], vec!["고", "다"]),
        (
            "의사셔계신다",
            vec!["의사", "이다", "계시다"],
            vec!["시", "어", "는다"],
        ),
        (
            "의사고도계신다",
            vec!["의사", "이다", "계시다"],
            vec!["고", "도", "는다"],
        ),
        (
            "학생답고있다",
            vec!["학생", "있다"],
            vec!["답다", "고", "다"],
        ),
        (
            "학생다워있다",
            vec!["학생", "있다"],
            vec!["답다", "어", "다"],
        ),
        (
            "학생다워계신다",
            vec!["학생", "계시다"],
            vec!["답다", "어", "는다"],
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, &lemmas, &forms)),
            "{word}"
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
fn continuatives_keep_verbs_changed_classes_and_unknown_lexical_heads() {
    let engine = Lemmatizer::new();
    for (word, lemmas, forms) in [
        ("앉아있다", vec!["앉다", "있다"], vec!["어", "다"]),
        ("앉아계신다", vec!["앉다", "계시다"], vec!["어", "는다"]),
        ("살아있다", vec!["살다", "있다"], vec!["어", "다"]),
        ("먹고있다", vec!["먹다", "있다"], vec!["고", "다"]),
        ("먹고계신다", vec!["먹다", "계시다"], vec!["고", "는다"]),
        (
            "먹어보고있다",
            vec!["먹다", "보다", "있다"],
            vec!["어", "고", "다"],
        ),
        (
            "먹고싶어하고있다",
            vec!["먹다", "싶다", "하다", "있다"],
            vec!["고", "어", "고", "다"],
        ),
        (
            "먹고는싶어하고계신다",
            vec!["먹다", "싶다", "하다", "계시다"],
            vec!["고", "는", "어", "고", "는다"],
        ),
        (
            "학생답게하고있다",
            vec!["학생", "하다", "있다"],
            vec!["답다", "게", "고", "다"],
        ),
        (
            "학생다워하고있다",
            vec!["학생", "하다", "있다"],
            vec!["답다", "어", "고", "다"],
        ),
        (
            "먹어보지않고있다",
            vec!["먹다", "보다", "않다", "있다"],
            vec!["어", "지", "고", "다"],
        ),
        (
            "먹어보지는않고계신다",
            vec!["먹다", "보다", "않다", "계시다"],
            vec!["어", "지", "는", "고", "는다"],
        ),
        (
            "먹어보잖고있다",
            vec!["먹다", "보다", "않다", "있다"],
            vec!["어", "지", "고", "다"],
        ),
        (
            "먹어보지못하고있다",
            vec!["먹다", "보다", "못하다", "있다"],
            vec!["어", "지", "고", "다"],
        ),
        ("먹고도있다", vec!["먹다", "있다"], vec!["고", "도", "다"]),
        (
            "먹어보고도있다",
            vec!["먹다", "보다", "있다"],
            vec!["어", "고", "도", "다"],
        ),
        (
            "먹어보고있어요",
            vec!["먹다", "보다", "있다"],
            vec!["어", "고", "어", "요"],
        ),
        (
            "학생이고싶다",
            vec!["학생", "이다", "싶다"],
            vec!["고", "다"],
        ),
        (
            "학생이고는싶다",
            vec!["학생", "이다", "싶다"],
            vec!["고", "는", "다"],
        ),
        ("좋아있다", vec!["좋다", "있다"], vec!["어", "다"]),
        ("예쁘고있다", vec!["예쁘다", "있다"], vec!["고", "다"]),
        ("이고있다", vec!["이다", "있다"], vec!["고", "다"]),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        if word == "이고있다" {
            assert_eq!(a.lemmas[0].kind, LemmaKind::Predicate);
        }
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    // Unknown lexical heads (including possible lexical 이다) are preservation
    // tests only. Dictionary membership must not be mistaken for sense/class.
}
