//! COV-014: spelling-preserving, explicitly conditional pronunciation boundaries.
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
fn assumptions(a: &Analysis) -> Vec<&str> {
    a.rules
        .iter()
        .map(String::as_str)
        .filter(|r| r.starts_with("pronunciation."))
        .collect()
}

#[test]
fn foreign_particle_allomorphs_state_the_required_pronunciation() {
    let engine = Lemmatizer::new();
    for base in [
        "ABC",
        "3",
        "2026",
        "café",
        "cafe\u{301}",
        "模型",
        "３",
        "X9",
        "새이름X",
    ] {
        let normalized: String = base.nfc().collect();
        for (particle, condition) in [
            ("은", "consonant"),
            ("는", "vowel"),
            ("이", "consonant"),
            ("가", "vowel"),
            ("을", "consonant"),
            ("를", "vowel"),
            ("과", "consonant"),
            ("와", "vowel"),
            ("이나", "consonant"),
            ("나", "vowel"),
            ("이라도", "consonant"),
            ("라도", "vowel"),
            ("이든지", "consonant"),
            ("든지", "vowel"),
            ("이라고", "consonant"),
            ("라고", "vowel"),
            ("이랑", "consonant"),
            ("랑", "vowel"),
            ("이야", "consonant"),
            ("야", "vowel"),
            ("아", "consonant"),
            ("여", "vowel"),
            ("서", "vowel"),
            ("으로", "non_rieul_consonant"),
            ("로", "vowel_or_rieul"),
            ("으로서", "non_rieul_consonant"),
            ("로서", "vowel_or_rieul"),
            ("으로써", "non_rieul_consonant"),
            ("로써", "vowel_or_rieul"),
        ] {
            let word = format!("{base}{particle}");
            let result = engine.analyze_word(&word).unwrap();
            let a = result
                .analyses
                .iter()
                .find(|a| {
                    path(a, &[&normalized], &[particle]) && a.lemmas[0].kind == LemmaKind::Nominal
                })
                .expect(&word);
            assert_eq!(a.morphemes[0].kind, MorphemeKind::Particle);
            assert_eq!(
                assumptions(a),
                [format!("pronunciation.assumed_{condition}")]
            );
            assert!(result.analyses.iter().any(|a| a.unchanged));
            assert_eq!(
                result,
                engine
                    .analyze_word(&word.nfd().collect::<String>())
                    .unwrap()
            );
            assert!(a.breakdown().is_some(), "{word}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn uncertainty_stays_at_the_foreign_boundary_and_preserves_chain_licenses() {
    let engine = Lemmatizer::new();
    for (word, lemma, forms, assumption) in [
        (
            "ABC로만은",
            "ABC",
            vec!["로", "만", "은"],
            Some("vowel_or_rieul"),
        ),
        (
            "3으로는",
            "3",
            vec!["으로", "는"],
            Some("non_rieul_consonant"),
        ),
        ("ABC는요", "ABC", vec!["는", "요"], Some("vowel")),
        ("ABC에는", "ABC", vec!["에", "는"], None),
        ("ABC들로", "ABC", vec!["들", "로"], None),
        ("ABC님은", "ABC", vec!["님", "은"], None),
        ("김민수는", "김민수", vec!["는"], None),
        ("2026년은", "2026년", vec!["은"], None),
        ("모델X에게는", "모델X", vec!["에게", "는"], None),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &[lemma], &forms))
            .expect(word);
        assert_eq!(
            assumptions(a),
            assumption
                .map(|s| format!("pronunciation.assumed_{s}"))
                .into_iter()
                .collect::<Vec<_>>()
        );
        assert!(a.breakdown().is_some());
    }
    for (word, lemma, forms) in [
        ("ABC은는", "ABC", vec!["은", "는"]),
        ("ABC으로로", "ABC", vec!["으로", "로"]),
        ("김민수은", "김민수", vec!["은"]),
        ("2026년는", "2026년", vec!["는"]),
    ] {
        assert!(
            !engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &[lemma], &forms)),
            "{word}"
        );
    }
    for word in [
        "🙂는",
        "!은",
        "\u{301}은",
        "A.B는",
        "ABC고",
        "3으면",
        "ABC케",
    ] {
        assert!(
            engine
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .all(|a| assumptions(a).is_empty()),
            "{word}"
        );
    }
}

#[test]
fn foreign_copulas_distinguish_explicit_i_from_vowel_dependent_omission() {
    let engine = Lemmatizer::new();
    for (word, forms, conditional) in [
        ("ABC다", vec!["다"], true),
        ("ABC라면", vec!["라면"], true),
        ("ABC예요", vec!["에요"], true),
        ("ABC야", vec!["야"], true),
        ("ABC였다", vec!["었", "다"], true),
        ("ABC여요", vec!["어요"], true),
        ("ABC이다", vec!["다"], false),
        ("ABC이라면", vec!["라면"], false),
        ("ABC이에요", vec!["에요"], false),
        ("ABC이야", vec!["야"], false),
        ("ABC이었다", vec!["었", "다"], false),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &["ABC", "이다"], &forms))
            .expect(word);
        assert_eq!(
            assumptions(a),
            if conditional {
                vec!["pronunciation.assumed_vowel"]
            } else {
                vec![]
            },
            "{word}"
        );
        assert!(a.breakdown().is_some());
        assert_eq!(a.lemmas[1].kind, LemmaKind::Copula);
    }
    // A contraction in the later auxiliary cannot supply the copula's
    // pronunciation condition merely because both share rule provenance.
    for (word, conditional) in [("ABC이었나봐요", false), ("ABC였나봐요", true)] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &["ABC", "이다", "보다"], &["었", "나", "어요"]))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "contraction.vowel"));
        assert_eq!(assumptions(a).len(), usize::from(conditional));
    }
}
