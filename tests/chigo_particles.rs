//! COV-018j: noun-attached 치고 family; preserve lexical predicate alternatives.
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
fn chigo_particles_preserve_nominals_plurals_and_bundles() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("아파트치고", &["아파트"], &["치고"]),
        ("학생치고", &["학생"], &["치고"]),
        ("외국인치고", &["외국인"], &["치고"]),
        ("사람치고", &["사람"], &["치고"]),
        ("음식치고", &["음식"], &["치고"]),
        ("아이들치고", &["아이"], &["들", "치고"]),
        ("교수님들치고", &["교수님"], &["들", "치고"]),
        ("아파트치고는", &["아파트"], &["치고는"]),
        ("학생치고는", &["학생"], &["치고는"]),
        ("외국인치고는", &["외국인"], &["치고는"]),
        ("사람치고는", &["사람"], &["치고는"]),
        ("음식치고는", &["음식"], &["치고는"]),
        ("아이들치고는", &["아이"], &["들", "치고는"]),
        ("교수님들치고는", &["교수님"], &["들", "치고는"]),
        ("아파트치고서", &["아파트"], &["치고서"]),
        ("학생치고서", &["학생"], &["치고서"]),
        ("외국인치고서", &["외국인"], &["치고서"]),
        ("사람치고서", &["사람"], &["치고서"]),
        ("음식치고서", &["음식"], &["치고서"]),
        ("아이들치고서", &["아이"], &["들", "치고서"]),
        ("교수님들치고서", &["교수님"], &["들", "치고서"]),
        ("학생치고는", &["학생"], &["치고", "는"]),
        ("사람치고서는", &["사람"], &["치고서", "는"]),
        ("아이들치고는", &["아이"], &["들", "치고", "는"]),
        ("교수님들치고서는", &["교수님"], &["들", "치고서", "는"]),
        ("아파트치고요", &["아파트"], &["치고", "요"]),
        ("학생치고는요", &["학생"], &["치고는", "요"]),
        ("음식치고서요", &["음식"], &["치고서", "요"]),
        ("교수님들치고", &["교수"], &["님", "들", "치고"]),
        ("교수님들치고는", &["교수"], &["님", "들", "치고는"]),
        ("교수님들치고서", &["교수"], &["님", "들", "치고서"]),
        ("교수님들치고서는", &["교수"], &["님", "들", "치고서", "는"]),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, lemmas, forms))
            .expect(word);
        assert!(a.rules.iter().any(|r| r == "particle.chigo"));
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
    }
}
#[test]
fn chigo_particles_reject_case_and_predicate_bases() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("학생이치고", &["학생"], &["이", "치고"]),
        ("학교에서치고", &["학교"], &["에서", "치고"]),
        ("학생을치고", &["학생"], &["을", "치고"]),
        ("친구와치고", &["친구"], &["와", "치고"]),
        ("학생만치고", &["학생"], &["만", "치고"]),
        ("먹고치고", &["먹다"], &["고", "치고"]),
        ("먹어치고", &["먹다"], &["어", "치고"]),
        ("좋다치고", &["좋다"], &["다", "치고"]),
        ("학생이치고는", &["학생"], &["이", "치고는"]),
        ("학교에서치고는", &["학교"], &["에서", "치고는"]),
        ("학생을치고는", &["학생"], &["을", "치고는"]),
        ("친구와치고는", &["친구"], &["와", "치고는"]),
        ("학생만치고는", &["학생"], &["만", "치고는"]),
        ("먹고치고는", &["먹다"], &["고", "치고는"]),
        ("먹어치고는", &["먹다"], &["어", "치고는"]),
        ("좋다치고는", &["좋다"], &["다", "치고는"]),
        ("학생이치고서", &["학생"], &["이", "치고서"]),
        ("학교에서치고서", &["학교"], &["에서", "치고서"]),
        ("학생을치고서", &["학생"], &["을", "치고서"]),
        ("친구와치고서", &["친구"], &["와", "치고서"]),
        ("학생만치고서", &["학생"], &["만", "치고서"]),
        ("먹고치고서", &["먹다"], &["고", "치고서"]),
        ("먹어치고서", &["먹다"], &["어", "치고서"]),
        ("좋다치고서", &["좋다"], &["다", "치고서"]),
        ("학생치고은", &["학생"], &["치고", "은"]),
        ("학생치고서은", &["학생"], &["치고서", "은"]),
        ("학생치고치고", &["학생"], &["치고", "치고"]),
        ("학생치고는치고서", &["학생"], &["치고는", "치고서"]),
        ("학생치고서", &["학생"], &["치고", "서"]),
        ("학생치고다", &["학생", "이다"], &["치고", "다"]),
        ("먹치고", &["먹다"], &["치고"]),
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
#[test]
fn chigo_spelling_keeps_lexical_predicate_alternatives() {
    let engine = Lemmatizer::new();
    for (word, lemma, forms) in [
        ("치고", "치다", vec!["고"]),
        ("치고는", "치다", vec!["고", "는"]),
        ("치고서", "치다", vec!["고서"]),
        ("고치고", "고치다", vec!["고"]),
        ("놓치고는", "놓치다", vec!["고", "는"]),
    ] {
        let a = engine.analyze_word(word).unwrap();
        assert!(
            a.analyses.iter().any(|a| path(a, &[lemma], &forms)),
            "{word}"
        );
    }
}
