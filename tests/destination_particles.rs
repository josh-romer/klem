//! COV-018f: emphatic destinations/recipients and separately licensed 다/다가.
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
fn destination_particles_preserve_bundles_components_and_nominal_composition() {
    for (word, lemmas, forms) in [
        ("강에다", vec!["강"], vec!["에다"]),
        ("강에다", vec!["강"], vec!["에", "다"]),
        ("거기에다", vec!["거기"], vec!["에다"]),
        ("학교에다가", vec!["학교"], vec!["에다가"]),
        ("학교에다가", vec!["학교"], vec!["에", "다가"]),
        ("친구에게다", vec!["친구"], vec!["에게다"]),
        ("친구에게다", vec!["친구"], vec!["에게", "다"]),
        ("친구에게다가", vec!["친구"], vec!["에게다가"]),
        ("친구에게다가", vec!["친구"], vec!["에게", "다가"]),
        ("친구한테다", vec!["친구"], vec!["한테다"]),
        ("친구한테다", vec!["친구"], vec!["한테", "다"]),
        ("친구한테다가", vec!["친구"], vec!["한테다가"]),
        ("친구한테다가", vec!["친구"], vec!["한테", "다가"]),
        ("서울로다가", vec!["서울"], vec!["로다가"]),
        ("서울로다가", vec!["서울"], vec!["로", "다가"]),
        ("손으로다가", vec!["손"], vec!["으로다가"]),
        ("손으로다가", vec!["손"], vec!["으로", "다가"]),
        ("손으로다", vec!["손"], vec!["으로", "다"]),
        ("학교로다가도", vec!["학교"], vec!["로다가", "도"]),
        ("학교로다가도", vec!["학교"], vec!["로", "다가", "도"]),
        ("강에다는", vec!["강"], vec!["에다", "는"]),
        ("강에다는", vec!["강"], vec!["에", "다", "는"]),
        ("학교에다가요", vec!["학교"], vec!["에다가", "요"]),
        ("노동자보고", vec!["노동자"], vec!["보고"]),
        ("나더러", vec!["나"], vec!["더러"]),
        ("친구보고는", vec!["친구"], vec!["보고", "는"]),
        ("친구더러도", vec!["친구"], vec!["더러", "도"]),
        ("학생들한테다가", vec!["학생"], vec!["들", "한테다가"]),
        ("선생님에게다", vec!["선생"], vec!["님", "에게다"]),
        ("선생님께다가", vec!["선생"], vec!["님", "께", "다가"]),
        ("먹기에다", vec!["먹다"], vec!["기", "에다"]),
        ("먹기에다", vec!["먹다"], vec!["기", "에", "다"]),
        ("먹음으로다가", vec!["먹다"], vec!["음", "으로다가"]),
        ("먹음으로다가", vec!["먹다"], vec!["음", "으로", "다가"]),
        (
            "먹어보기에다가",
            vec!["먹다", "보다"],
            vec!["어", "기", "에다가"],
        ),
        ("학생다움에다가", vec!["학생"], vec!["답다", "음", "에다가"]),
        ("학교에서다가", vec!["학교"], vec!["에서", "다가"]),
    ] {
        let engine = Lemmatizer::new();
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| path(a, &lemmas, &forms))
            .expect(word);
        assert_eq!(a.morphemes.last().unwrap().kind, MorphemeKind::Particle);
        assert!(
            a.rules.iter().any(|r| matches!(
                r.as_str(),
                "particle.emphatic_adverbial"
                    | "particle.emphatic_destination"
                    | "particle.recipient"
            )),
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
    for (base, kind) in [
        ("여기", LemmaKind::Nominal),
        ("거기", LemmaKind::Nominal),
        ("저기", LemmaKind::Nominal),
        ("어디", LemmaKind::Nominal),
        ("이리", LemmaKind::Adverbial),
        ("그리", LemmaKind::Adverbial),
        ("저리", LemmaKind::Adverbial),
    ] {
        for form in ["다", "다가"] {
            let word = format!("{base}{form}");
            assert!(
                Lemmatizer::new()
                    .analyze_word(&word)
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| path(a, &[base], &[form])
                        && a.lemmas[0].kind == kind
                        && a.morphemes[0].kind == MorphemeKind::Particle),
                "{word}"
            );
        }
    }
    for (word, form, rule) in [
        (
            "ABC로다가",
            "로다가",
            "pronunciation.assumed_vowel_or_rieul",
        ),
        (
            "ABC으로다가",
            "으로다가",
            "pronunciation.assumed_non_rieul_consonant",
        ),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &["ABC"], &[form]) && a.rules.iter().any(|r| r == rule))
        );
    }
}

#[test]
fn emphatic_particles_do_not_consume_unlicensed_bases_or_replace_predicates() {
    for (word, lemmas, forms) in [
        ("학생로다가", vec!["학생"], vec!["로다가"]),
        ("학교으로다가", vec!["학교"], vec!["으로다가"]),
        ("길으로다가", vec!["길"], vec!["으로다가"]),
        ("학생이다가", vec!["학생"], vec!["이", "다가"]),
        ("학생을다가", vec!["학생"], vec!["을", "다가"]),
        ("학생만다가", vec!["학생"], vec!["만", "다가"]),
        ("학교에다다가", vec!["학교"], vec!["에다", "다가"]),
        ("학교에다다", vec!["학교"], vec!["에", "다", "다"]),
        ("먹고에다", vec!["먹다"], vec!["고", "에다"]),
        ("먹기다가", vec!["먹다"], vec!["기", "다가"]),
        ("먹는다가", vec!["먹다"], vec!["는다", "다가"]),
    ] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)),
            "{word}"
        );
    }
    // This is an exclusion of the emphatic source sense only: enumeration
    // particle 다 is another entry, whose implementation remains separate.
    for word in ["학교다", "학교다가", "빨리다가", "먹다가"] {
        assert!(
            !Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "particle.emphatic_adverbial")),
            "{word}"
        );
    }
    for (word, lemmas, forms) in [
        ("먹다가", vec!["먹다"], vec!["다가"]),
        ("돌보고", vec!["돌보다"], vec!["고"]),
        ("저기다", vec!["저기", "이다"], vec!["다"]),
    ] {
        assert!(
            Lemmatizer::new()
                .analyze_word(word)
                .unwrap()
                .analyses
                .iter()
                .any(|a| path(a, &lemmas, &forms)
                    && a.morphemes.last().unwrap().kind == MorphemeKind::Ending),
            "{word}"
        );
    }
}
