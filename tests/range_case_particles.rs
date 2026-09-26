//! COV-018k: case marking after range particles; retain immediate allomorphs.
use klem::{Analysis, Lemmatizer};
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
fn range_case_particles_preserve_composition_and_allomorphs() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("역사까지를", &["역사"], &["까지", "를"]),
        ("부산까지를", &["부산"], &["까지", "를"]),
        ("중기까지를", &["중기"], &["까지", "를"]),
        ("어디까지가", &["어디"], &["까지", "가"]),
        ("여기까지가", &["여기"], &["까지", "가"]),
        ("사춘기까지가", &["사춘기"], &["까지", "가"]),
        ("오월까지가", &["오월"], &["까지", "가"]),
        ("페이지까지로", &["페이지"], &["까지", "로"]),
        ("번까지로", &["번"], &["까지", "로"]),
        ("6세까지에", &["6세"], &["까지", "에"]),
        (
            "정착되기까지에는",
            &["정착되다"],
            &["기", "까지", "에", "는"],
        ),
        ("되기까지를", &["되다"], &["기", "까지", "를"]),
        ("이르기까지를", &["이르다"], &["기", "까지", "를"]),
        ("출발선부터가", &["출발선"], &["부터", "가"]),
        ("제목부터가", &["제목"], &["부터", "가"]),
        ("근본부터가", &["근본"], &["부터", "가"]),
        ("공기부터가", &["공기"], &["부터", "가"]),
        ("체격부터가", &["체격"], &["부터", "가"]),
        ("먹기부터가", &["먹다"], &["기", "부터", "가"]),
        ("먹었기까지를", &["먹다"], &["었", "기", "까지", "를"]),
        (
            "먹어보기까지를",
            &["먹다", "보다"],
            &["어", "기", "까지", "를"],
        ),
        ("학생이기까지를", &["학생", "이다"], &["기", "까지", "를"]),
        ("교수님들까지가", &["교수"], &["님", "들", "까지", "가"]),
        ("학생들부터가", &["학생"], &["들", "부터", "가"]),
        ("ABC까지가", &["ABC"], &["까지", "가"]),
        ("역사까질", &["역사"], &["까지", "를"]),
        ("역사까지를요", &["역사"], &["까지", "를", "요"]),
        ("출발선부터가요", &["출발선"], &["부터", "가", "요"]),
        ("페이지까지로는", &["페이지"], &["까지", "로", "는"]),
        ("6세까지에도", &["6세"], &["까지", "에", "도"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, lemmas, forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "particle.range_case"));
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        assert!(a.breakdown().is_some());
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        if word == "ABC까지가" {
            assert!(
                !a.rules
                    .iter()
                    .any(|r| r.starts_with("pronunciation.assumed_"))
            );
        }
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
#[test]
fn range_case_particles_reject_wrong_boundaries() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("역사까지을", &["역사"], &["까지", "을"]),
        ("학생까지이", &["학생"], &["까지", "이"]),
        ("페이지까지으로", &["페이지"], &["까지", "으로"]),
        ("제목부터이", &["제목"], &["부터", "이"]),
        ("역사까진를", &["역사"], &["까지", "를"]),
        ("역사까질가", &["역사"], &["까지", "가"]),
        ("먹고까지를", &["먹다"], &["고", "까지", "를"]),
        ("먹어까지가", &["먹다"], &["어", "까지", "가"]),
        ("먹다까지로", &["먹다"], &["다", "까지", "로"]),
        ("먹는까지에", &["먹다"], &["는", "까지", "에"]),
        ("먹다부터가", &["먹다"], &["다", "부터", "가"]),
        ("학생까지를는", &["학생"], &["까지", "를", "는"]),
        ("제목부터가은", &["제목"], &["부터", "가", "은"]),
        ("페이지까지로은", &["페이지"], &["까지", "로", "은"]),
        ("학생까지는가", &["학생"], &["까지", "는", "가"]),
        ("학생까지를를", &["학생"], &["까지", "를", "를"]),
        ("학생까지가가", &["학생"], &["까지", "가", "가"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result.analyses.iter().any(|a| path(a, lemmas, forms)),
            "{word}: {forms:?}"
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
