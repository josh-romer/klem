//! COV-018m: comparison/extent particles and source-listed 어서 attachment.
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
fn extent_particles_preserve_nominal_and_seo_composition() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("필생토록", &["필생"], &["토록"]),
        ("평생토록", &["평생"], &["토록"]),
        ("일생토록", &["일생"], &["토록"]),
        ("종일토록", &["종일"], &["토록"]),
        ("영원토록", &["영원"], &["토록"]),
        ("이토록", &["이"], &["토록"]),
        ("그토록", &["그"], &["토록"]),
        ("저토록", &["저"], &["토록"]),
        ("아이마냥", &["아이"], &["마냥"]),
        ("새마냥", &["새"], &["마냥"]),
        ("애마냥", &["애"], &["마냥"]),
        ("것마냥", &["것"], &["마냥"]),
        ("학생마냥", &["학생"], &["마냥"]),
        ("그만치", &["그"], &["만치"]),
        ("나만치", &["나"], &["만치"]),
        ("너만치", &["너"], &["만치"]),
        ("작년만치", &["작년"], &["만치"]),
        ("어제만치", &["어제"], &["만치"]),
        ("오늘만치", &["오늘"], &["만치"]),
        ("아이들마냥", &["아이"], &["들", "마냥"]),
        ("교수님마냥", &["교수"], &["님", "마냥"]),
        ("평생토록은", &["평생"], &["토록", "은"]),
        ("종일토록도", &["종일"], &["토록", "도"]),
        ("필생토록요", &["필생"], &["토록", "요"]),
        ("학생마냥은", &["학생"], &["마냥", "은"]),
        ("아이마냥요", &["아이"], &["마냥", "요"]),
        ("오늘만치는", &["오늘"], &["만치", "는"]),
        ("오늘만치도", &["오늘"], &["만치", "도"]),
        ("학교에서만치", &["학교"], &["에서", "만치"]),
        ("학교로만치", &["학교"], &["로", "만치"]),
        ("학교에서만치는", &["학교"], &["에서", "만치", "는"]),
        ("있어서만치는", &["있다"], &["어서", "만치", "는"]),
        ("있어서만큼은", &["있다"], &["어서", "만큼", "은"]),
        ("좋아서만큼은", &["좋다"], &["어서", "만큼", "은"]),
        ("일해서만치는", &["일하다"], &["어서", "만치", "는"]),
        (
            "학생이어서만큼은",
            &["학생", "이다"],
            &["어서", "만큼", "은"],
        ),
        (
            "먹어봐서만치는",
            &["먹다", "보다"],
            &["어", "어서", "만치", "는"],
        ),
        (
            "학생다워서만큼은",
            &["학생"],
            &["답다", "어서", "만큼", "은"],
        ),
    ];
    for &(word, lemmas, forms) in cases {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, lemmas, forms))
            .expect(word);
        assert!(
            a.rules
                .iter()
                .any(|r| r == "particle.comparison_extent" || r == "particle.comparison_seo")
        );
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
fn extent_particles_reject_wrong_roles_and_boundaries() {
    let engine = Lemmatizer::new();
    let cases: &[(&str, &[&str], &[&str])] = &[
        ("학생이토록", &["학생"], &["이", "토록"]),
        ("학교에서토록", &["학교"], &["에서", "토록"]),
        ("학생을토록", &["학생"], &["을", "토록"]),
        ("친구와토록", &["친구"], &["와", "토록"]),
        ("학생만토록", &["학생"], &["만", "토록"]),
        ("먹어서토록", &["먹다"], &["어서", "토록"]),
        ("먹고토록", &["먹다"], &["고", "토록"]),
        ("먹다토록", &["먹다"], &["다", "토록"]),
        ("학생이마냥", &["학생"], &["이", "마냥"]),
        ("학교에서마냥", &["학교"], &["에서", "마냥"]),
        ("학생을마냥", &["학생"], &["을", "마냥"]),
        ("친구와마냥", &["친구"], &["와", "마냥"]),
        ("학생만마냥", &["학생"], &["만", "마냥"]),
        ("먹어서마냥", &["먹다"], &["어서", "마냥"]),
        ("먹고마냥", &["먹다"], &["고", "마냥"]),
        ("먹다마냥", &["먹다"], &["다", "마냥"]),
        ("평생토록는", &["평생"], &["토록", "는"]),
        ("학생마냥는", &["학생"], &["마냥", "는"]),
        ("오늘만치은", &["오늘"], &["만치", "은"]),
        ("있어서만치은", &["있다"], &["어서", "만치", "은"]),
        ("있어서만큼는", &["있다"], &["어서", "만큼", "는"]),
        ("먹을만치", &["먹다"], &["을", "만치"]),
        ("먹는만치", &["먹다"], &["는", "만치"]),
        ("먹을만큼", &["먹다"], &["을", "만큼"]),
        ("먹는만큼", &["먹다"], &["는", "만큼"]),
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
fn extent_spellings_keep_lexical_words_and_shortened_hada() {
    let engine = Lemmatizer::new();
    for w in ["이토록", "그토록", "저토록", "마냥", "만치", "만큼"] {
        assert!(
            engine
                .analyze_word(w)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.unchanged && a.lemmas[0].text == w)
        );
    }
    for (w, l, m) in [
        ("연구토록", vec!["연구하다"], vec!["도록"]),
        ("분발토록", vec!["분발하다"], vec!["도록"]),
        ("학교에서만큼은", vec!["학교"], vec!["에서", "만큼", "은"]),
    ] {
        assert!(
            engine
                .analyze_word(w)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &l, &m)),
            "{w}"
        );
    }
}
