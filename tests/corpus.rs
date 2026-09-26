#[path = "../tools/corpus.rs"]
mod corpus;
use corpus::{Conversion, Corpus};

#[test]
fn question_copulas_recover_two_new_cases_and_preserve_explicit_copulas() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-question-copulas.conllu").as_slice(),
            vec![
                ("id:MH2_0159-s366/17", "무엇일까", vec!["무엇", "이다"]),
                ("id:MH2_0169-s31/7", "일부인지", vec!["일부", "이다"]),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-question-copulas.conllu").as_slice(),
            vec![
                ("id:dev-s219/2", "뭔지", vec!["뭐", "이다"]),
                ("id:dev-s842/1", "뭔가", vec!["뭐", "이다"]),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "question-copulas").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn retrospective_adnominals_preserve_four_unchanged_annotated_cases() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-retrospective-adnominals.conllu").as_slice(),
            vec![
                ("id:MH2_0149-s133/2", "정도였던가", vec!["정도", "이다"]),
                ("id:MH2_0159-s167/14", "아니었던가요", vec!["아니다"]),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-retrospective-adnominals.conllu").as_slice(),
            vec![
                ("id:dev-s120/2", "먹던", vec!["먹다"]),
                ("id:dev-s138/6", "별로였던", vec!["별로", "이다"]),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "retrospective-adnominals").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn retrospective_connectives_preserve_four_unchanged_annotated_cases() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-retrospective-connectives.conllu").as_slice(),
            vec![
                ("id:M2TA_069-s11/3", "장손이기", vec!["장손", "이다"]),
                (
                    "id:MH2_0149-s147/14",
                    "제한적이었음을",
                    vec!["제한적", "이다"],
                ),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-retrospective-connectives.conllu").as_slice(),
            vec![
                ("id:dev-s670/5", "먹게", vec!["먹다"]),
                ("id:dev-s822/3", "먹기", vec!["먹다"]),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "retrospective-connectives").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn retrospective_licenses_preserve_four_unchanged_annotated_cases() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-retrospective-licenses.conllu").as_slice(),
            vec![
                ("id:M2TA_089-s34/5", "않더라도", vec!["않다"]),
                ("id:MH2_0209-s16/6", "맞더니", vec!["맞다"]),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-retrospective-licenses.conllu").as_slice(),
            vec![
                ("id:dev-s143/7", "가져가시더니", vec!["가져가다"]),
                ("id:dev-s600/20", "시켜주더군요", vec!["시키다", "주다"]),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "retrospective-licenses").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn prefinal_copula_omission_recovers_three_unchanged_annotated_cases() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-prefinal-copulas.conllu").as_slice(),
            vec![(
                "id:MH2_0169-s454/2",
                "마찬가지겠지만",
                vec!["마찬가지", "이다"],
            )],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-prefinal-copulas.conllu").as_slice(),
            vec![
                ("id:dev-s13/14", "최고더군요", vec!["최고", "이다"]),
                ("id:dev-s635/4", "어디더라", vec!["어디", "이다"]),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "prefinal-copulas").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn seo_connectives_recover_nine_unchanged_annotated_cases() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-seo-connectives.conllu").as_slice(),
        Corpus::Kaist,
        "seo-connectives",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:MH2_0069-s196/10", "나오면서부터", "나오다"),
        ("id:MH2_0069-s247/7", "통해서보다는", "통하다"),
        ("id:MH2_0069-s311/5", "기록하면서부터", "기록하다"),
        ("id:MH2_0069-s494/3", "되어서야", "되다"),
        ("id:MH2_0069-s75/14", "가지고서", "가지다"),
        ("id:MH2_0149-s20/16", "돌리고서는", "돌리다"),
        ("id:MH2_0159-s141/7", "주면서부터", "주다"),
        ("id:MH2_0159-s227/3", "이르러서야", "이르다"),
        ("id:MH2_0169-s321/14", "가서야", "가다"),
    ] {
        let case = &report.cases[id];
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, [expected]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn honorific_copula_omission_preserves_annotated_lexical_verbs() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-honorific-copulas.conllu").as_slice(),
            vec![("id:MH2_0209-s66/14", "마셨다", "마시다")],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-honorific-copulas.conllu").as_slice(),
            vec![
                ("id:dev-s236/10", "주셨습니다", "주다"),
                ("id:dev-s932/14", "주셨어요", "주다"),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "honorific-copulas").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [expected]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn omitted_connectives_recover_saved_groups_and_keep_annotation_caveats() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-omitted-connectives.conllu").as_slice(),
            vec![
                ("id:M2TA_089-s65/9", "어디서고", "어디"),
                ("id:MH2_0159-s200/3", "엘리트주의니", "엘리트주의"),
                ("id:MH2_0169-s179/10", "일쑤고", "일쑤"),
                ("id:MH2_0169-s615/5", "치료니", "치료"),
                ("id:MH2_0169-s650/2", "살인자니까", "살인자"),
                ("id:MH2_0169-s698/2", "노동자니까", "노동자"),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-omitted-connectives.conllu").as_slice(),
            vec![
                ("id:dev-s461/6", "최고네요", "최고"),
                // This source sentence uses the place name Terni. Its existing
                // annotation is an incidental match, not a correctness claim.
                ("id:dev-s570/4", "테르니", "테르"),
                ("id:dev-s842/9", "이야기고", "이야기"),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "omitted-connectives").unwrap();
        for (id, surface, base) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [base, "이다"]);
            assert!(case.matched, "{id}");
        }
    }
    assert!(
        klem::Lemmatizer::new()
            .analyze_word("테르니")
            .unwrap()
            .analyses
            .iter()
            .any(|a| a.unchanged && a.lemmas[0].text == "테르니")
    );
}

#[test]
fn enumerative_da_preserves_annotated_copula_instead_of_replacing_it() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/gsd-enumerative-da.conllu").as_slice(),
        Corpus::Gsd,
        "enumerative-da",
    )
    .unwrap();
    let case = &report.cases["id:train-s1156/5"];
    assert_eq!(case.surface, "옷이다");
    assert_eq!(case.expected, ["옷", "이다"]);
    assert!(case.matched);
    // This sentence asserts a copula, not enumeration. The dictionary licenses
    // an additional token-level particle hypothesis; gold must stay unchanged.
    let word = klem::Lemmatizer::new().analyze_word(&case.surface).unwrap();
    assert!(word.analyses.iter().any(|a| a.lemmas.len() == 1
        && a.lemmas[0].text == "옷"
        && a.morphemes.len() == 1
        && a.morphemes[0].form == "이다"
        && a.morphemes[0].kind == klem::MorphemeKind::Particle));
}

#[test]
fn destination_particles_recover_saved_development_groups() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-destination-particles.conllu").as_slice(),
            vec![
                ("id:MH2_0149-s138/2", "강에다", "강"),
                ("id:MH2_0169-s706/11", "노동자보고", "노동자"),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-destination-particles.conllu").as_slice(),
            vec![("id:dev-s127/1", "거기에다", "거기")],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "destination-particles").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [expected]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn enumerative_particles_recover_saved_training_groups_without_extra_copulas() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-enumerative-particles.conllu").as_slice(),
        Corpus::Kaist,
        "enumerative-particles",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:MH2_0014-s474/4", "것이라든가", "것"),
        ("id:MH2_0024-s81/9", "않든가", "않다"),
        ("id:MH2_0024-s173/11", "취미라든가", "취미"),
    ] {
        let case = &report.cases[id];
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, [expected]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn quoted_alternatives_recover_saved_development_groups() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-quoted-alternatives.conllu").as_slice(),
            vec![
                ("id:MH2_0159-s14/5", "경시한다든가", "경시하다"),
                ("id:MH2_0159-s161/8", "해방시킨다거나", "해방시키다"),
                ("id:MH2_0159-s161/13", "된다거나", "되다"),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-quoted-alternatives.conllu").as_slice(),
            vec![("id:dev-s330/4", "세련되었다든가", "세련되다")],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "quoted-alternatives").unwrap();
        for (id, surface, lemma) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn causal_endings_recover_saved_gsd_groups() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/gsd-causal.conllu").as_slice(),
        Corpus::Gsd,
        "causal",
    )
    .unwrap();
    for (id, surface, lemma) in [
        ("id:dev-s485/4", "추천하길래", "추천하다"),
        ("id:dev-s836/10", "뽑길래", "뽑다"),
    ] {
        let c = &report.cases[id];
        assert_eq!(c.surface, surface);
        assert_eq!(c.expected, [lemma]);
        assert!(c.matched, "{id}");
    }
}

#[test]
fn enumerative_copula_yo_recovers_annotated_groups() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-copula-yo.conllu").as_slice(),
        Corpus::Kaist,
        "copula-yo",
    )
    .unwrap();
    for (id, surface, lemmas) in [
        ("id:MH2_0069-s406/4", "선배요", vec!["선배", "이다"]),
        ("id:MH2_0109-s3/8", "아니요", vec!["아니다"]),
        ("id:MH2_0159-s181/23", "연장이요", vec!["연장", "이다"]),
        ("id:MH2_0159-s263/7", "자화상이요", vec!["자화상", "이다"]),
        ("id:MH2_0159-s354/2", "아비요", vec!["아비", "이다"]),
    ] {
        let c = &report.cases[id];
        assert_eq!(c.surface, surface);
        assert_eq!(c.expected, lemmas);
        assert!(c.matched, "{id}");
    }
}

#[test]
fn polite_reporting_endings_recover_annotated_predicates() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-reporting.conllu").as_slice(),
            vec![
                ("id:M2TA_069-s20/11", "넘었답니다", "넘다"),
                ("id:M2TA_069-s27/14", "묻었답니다", "묻다"),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-reporting.conllu").as_slice(),
            vec![
                ("id:dev-s287/5", "물어본답니다", "물어보다"),
                ("id:dev-s650/8", "좋았답니다", "좋다"),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "reporting").unwrap();
        for (id, surface, lemma) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn shortened_hada_nominalizations_recover_annotated_predicates() {
    for (corpus, input, id, surface, lemma) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-hada-ki.conllu").as_slice(),
            "id:MH2_0209-s34/14",
            "강구키",
            "강구하다",
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-hada-ki.conllu").as_slice(),
            "id:dev-s629/12",
            "조성키로",
            "조성하다",
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "hada-ki").unwrap();
        let case = &report.cases[id];
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, [lemma]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn lexicalized_adverb_gold_is_preserved_alongside_optional_derivations() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-adverb-roots.conllu").as_slice(),
            vec![
                ("id:MH2_0069-s237/1", "더욱이"),
                ("id:MH2_0159-s132/15", "일일이"),
                ("id:MH2_0159-s369/16", "익히"),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-adverb-roots.conllu").as_slice(),
            vec![("id:dev-s174/9", "특히")],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "adverb-roots").unwrap();
        for (id, surface) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [surface]);
            assert!(case.matched, "{id}");
            let result = klem::Lemmatizer::new().analyze_word(surface).unwrap();
            assert!(result.analyses.iter().any(|a| a.unchanged));
            assert!(result.analyses.iter().any(|a| {
                a.morphemes
                    .iter()
                    .any(|m| m.kind == klem::MorphemeKind::Suffix)
            }));
        }
    }
}

#[test]
fn omitted_copulas_recover_annotated_short_and_full_nominal_groups() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-omitted-copulas.conllu").as_slice(),
            vec![
                ("id:M2TA_069-s16/4", "겁니다", "거"),
                ("id:M2TA_089-s3/2", "과거지요", "과거"),
                ("id:MH2_0159-s204/15", "겁니다", "것"),
                ("id:MH2_0169-s304/6", "때면", "때"),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-omitted-copulas.conllu").as_slice(),
            vec![
                ("id:dev-s181/4", "시면", "시"),
                ("id:dev-s211/4", "건데", "것"),
                ("id:dev-s681/10", "거죠", "것"),
                ("id:dev-s744/4", "거면", "거"),
                ("id:dev-s895/14", "겁니다", "것"),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "omitted-copulas").unwrap();
        for (id, surface, nominal) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [nominal, "이다"]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn quoted_experience_keeps_gold_when_invalid_command_paths_are_removed() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-prefinal-licenses.conllu").as_slice(),
        Corpus::Kaist,
        "prefinal-licenses",
    )
    .unwrap();
    let case = &report.cases["id:MH2_0110-s324/14"];
    assert_eq!(case.surface, "못하더라는");
    assert_eq!(case.expected, ["못하다"]);
    assert!(case.matched);
    let result = klem::Lemmatizer::new().analyze_word(&case.surface).unwrap();
    assert!(
        result
            .analyses
            .iter()
            .any(|a| a.lemmas.iter().map(|l| l.text.as_str()).eq(["못하다"])
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["더라는"]))
    );
    assert!(!result.analyses.iter().any(|a| {
        a.lemmas.iter().map(|l| l.text.as_str()).eq(["못하다"])
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(["더", "으라는"])
    }));
}

#[test]
fn annotated_obligation_bundles_keep_implicit_auxiliary_differences_visible() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-obligation.conllu").as_slice(),
            vec![
                ("id:M2TA_069-s33/16", "말해야겠다", "말하다"),
                ("id:M2TA_069-s44/11", "이야기해야겠다", "이야기하다"),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-obligation.conllu").as_slice(),
            vec![("id:dev-s211/8", "먹어야겠네요", "먹다")],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "obligation").unwrap();
        for (id, surface, lemma) in cases {
            let case = report.cases.get(id).unwrap();
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
        if matches!(corpus, Corpus::Gsd) {
            for (id, lemmas) in [
                ("id:dev-s361/10", vec!["오다", "하다"]),
                ("id:dev-s475/7", vec!["세척하다", "하다"]),
            ] {
                assert_eq!(report.cases[id].expected, lemmas);
                // Preserve the annotated implicit 하다 instead of rewriting
                // the corpus adapter to match this program's bundle.
            }
        }
    }
}

#[test]
fn annotated_omitted_copula_fragments_recover_without_token_joining() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-copula-fragments.conllu").as_slice(),
        Corpus::Kaist,
        "copula-fragments",
    )
    .unwrap();
    for id in ["id:MH2_0209-s39/4", "id:MH2_0209-s122/4"] {
        let case = report.cases.get(id).unwrap();
        assert_eq!(case.surface, "라는");
        assert_eq!(case.expected, ["이다"]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn annotated_definitions_preserve_particle_and_copular_gold_groups() {
    let selected: Vec<serde_json::Value> =
        serde_json::from_str(include_str!("fixtures/quoted-definition-gold.json")).unwrap();
    assert_eq!(selected.len(), 26);
    for (name, input) in [
        (
            "kaist",
            include_bytes!("fixtures/kaist-quoted-definitions.conllu").as_slice(),
        ),
        (
            "gsd",
            include_bytes!("fixtures/gsd-quoted-definitions.conllu").as_slice(),
        ),
    ] {
        let report = corpus::evaluate(input, Corpus::parse(name).unwrap(), name).unwrap();
        for selected in selected.iter().filter(|v| v["corpus"] == name) {
            let id = selected["id"].as_str().unwrap();
            let case = report.cases.get(id).unwrap();
            assert_eq!(case.surface, selected["surface"].as_str().unwrap());
            assert_eq!(
                serde_json::to_value(&case.expected).unwrap(),
                selected["expected"]
            );
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn annotated_emphatic_particles_recover_nominals_and_nominalizations() {
    for (name, input, selected) in [
        (
            "kaist",
            include_bytes!("fixtures/kaist-emphatic-particles.conllu").as_slice(),
            vec![
                ("id:MH2_0159-s104/2", "명제야말로", "명제"),
                ("id:MH2_0159-s117/1", "문학연구야말로", "문학연구"),
                ("id:MH2_0159-s177/17", "교육이야말로", "교육"),
                ("id:MH2_0159-s90/12", "일시적으로나마", "일시적"),
                ("id:MH2_0169-s126/3", "포지티브야말로", "포지티브"),
                ("id:MH2_0169-s458/2", "칭찬하기는커녕", "칭찬하다"),
                ("id:MH2_0169-s554/4", "시설투자는커녕", "시설투자"),
                ("id:MH2_0169-s579/5", "보호하기는커녕", "보호하다"),
                ("id:MH2_0169-s584/6", "발전시키기는커녕", "발전시키다"),
                ("id:MH2_0169-s595/3", "안에서나마", "안"),
                ("id:MH2_0209-s29/2", "작품이야말로", "작품"),
                ("id:MH2_0209-s40/9", "긴장이야말로", "긴장"),
            ],
        ),
        (
            "gsd",
            include_bytes!("fixtures/gsd-emphatic-particles.conllu").as_slice(),
            vec![("id:dev-s768/1", "서울서", "서울")],
        ),
    ] {
        let report = corpus::evaluate(input, Corpus::parse(name).unwrap(), name).unwrap();
        for (id, surface, lemma) in selected {
            let case = report.cases.get(id).unwrap();
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
        if name == "gsd" {
            // Preserve the annotation for review, without making it a required
            // linguistic judgment: this sentence concerns a written pledge.
            let case = report.cases.get("id:dev-s934/6").unwrap();
            assert_eq!(case.surface, "확약서");
            assert_eq!(case.expected, ["확약"]);
        }
    }
}

#[test]
fn annotated_intention_and_concession_endings_recover_missing_groups() {
    for (name, input, selected) in [
        (
            "kaist",
            include_bytes!("fixtures/kaist-intention-endings.conllu").as_slice(),
            vec![
                ("id:M2TA_069-s49/7", "되리라고", "되다"),
                ("id:MH2_0069-s146/2", "들자면", "들다"),
                ("id:MH2_0069-s42/2", "들자면", "들다"),
                ("id:MH2_0069-s5/5", "할지라도", "하다"),
                ("id:MH2_0159-s129/4", "말하자면", "말하다"),
                ("id:MH2_0159-s194/14", "되리라고", "되다"),
                ("id:MH2_0159-s203/7", "관련하자면", "관련하다"),
                ("id:MH2_0159-s64/3", "할지라도", "하다"),
                ("id:MH2_0169-s63/5", "얻으리라고", "얻다"),
                ("id:MH2_0169-s739/4", "바뀌리라고", "바뀌다"),
            ],
        ),
        (
            "gsd",
            include_bytes!("fixtures/gsd-intention-endings.conllu").as_slice(),
            vec![("id:dev-s851/7", "할지라도", "하다")],
        ),
    ] {
        let report = corpus::evaluate(input, Corpus::parse(name).unwrap(), name).unwrap();
        for (id, surface, lemma) in selected {
            let case = report.cases.get(id).unwrap();
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn annotated_foreign_nominals_recover_spelling_without_inventing_pronunciation() {
    let selected: Vec<serde_json::Value> =
        serde_json::from_str(include_str!("fixtures/foreign-nominal-gold.json")).unwrap();
    assert_eq!(selected.len(), 39);
    for (name, input) in [
        (
            "kaist",
            include_bytes!("fixtures/kaist-foreign-nominals.conllu").as_slice(),
        ),
        (
            "gsd",
            include_bytes!("fixtures/gsd-foreign-nominals.conllu").as_slice(),
        ),
    ] {
        let report = corpus::evaluate(input, Corpus::parse(name).unwrap(), name).unwrap();
        for selected in selected.iter().filter(|v| v["corpus"] == name) {
            let id = selected["id"].as_str().unwrap();
            let case = report.cases.get(id).unwrap();
            assert_eq!(case.surface, selected["surface"].as_str().unwrap());
            assert_eq!(
                serde_json::to_value(&case.expected).unwrap(),
                selected["expected"]
            );
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn annotated_propositive_preserves_the_lexical_recovery() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-propositive.conllu").as_slice(),
        Corpus::Kaist,
        "kaist",
    )
    .unwrap();
    let case = report.cases.get("id:MH2_0159-s160/11").unwrap();
    assert_eq!(case.surface, "봅시다");
    assert_eq!(case.expected, ["보다"]);
    assert!(case.matched);
}

#[test]
fn annotated_auxiliary_adjectives_keep_their_licensed_inflections() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/gsd-auxiliary-classes.conllu").as_slice(),
        Corpus::parse("gsd").unwrap(),
        "gsd",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:dev-s112/1", "먹을만한", ["먹다", "만하다"]),
        ("id:dev-s388/4", "참을만한데", ["참다", "만하다"]),
        ("id:dev-s572/4", "보고싶다", ["보다", "싶다"]),
        ("id:dev-s791/3", "보고싶습니다", ["보다", "싶다"]),
    ] {
        let case = report.cases.get(id).unwrap();
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, expected);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn annotated_short_prohibition_recovers_malda() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/gsd-negative-auxiliaries.conllu").as_slice(),
        Corpus::parse("gsd").unwrap(),
        "gsd",
    )
    .unwrap();
    let case = report.cases.get("id:dev-s312/4").unwrap();
    assert_eq!(case.surface, "마라");
    assert_eq!(case.expected, ["말다"]);
    assert!(case.matched);
}

#[test]
fn annotated_additional_adverbs_recover_predicate_lemmas() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-adverb-expansion.conllu").as_slice(),
        Corpus::parse("kaist").unwrap(),
        "kaist",
    )
    .unwrap();
    for (id, surface, lemma) in [
        ("id:MH2_0159-s128/13", "다분히", "다분하다"),
        ("id:MH2_0159-s341/12", "가벼이", "가볍다"),
        ("id:MH2_0159-s358/4", "적잖이", "적잖다"),
        ("id:MH2_0159-s53/3", "상당히", "상당하다"),
    ] {
        let case = report.cases.get(id).unwrap();
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, [lemma]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn annotated_negative_contraction_recovers_both_lemmas() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-negative-contractions.conllu").as_slice(),
        Corpus::parse("kaist").unwrap(),
        "kaist",
    )
    .unwrap();
    let case = report.cases.get("id:MH2_0159-s86/12").unwrap();
    assert_eq!(case.surface, "적잖은");
    assert_eq!(case.expected, ["적다", "않다"]);
    assert!(case.matched);
}

#[test]
fn annotated_direct_nominalization_recovers_omitted_copula() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-nominal-copulas.conllu").as_slice(),
        Corpus::parse("kaist").unwrap(),
        "kaist",
    )
    .unwrap();
    let case = report.cases.get("id:MH2_0169-s271/6").unwrap();
    assert_eq!(case.surface, "떠먹이기다");
    assert_eq!(case.expected, ["떠먹이다", "이다"]);
    assert!(case.matched);
}

#[test]
fn annotated_auxiliary_inventory_cases_recover_whole_groups() {
    for (name, input, cases) in [
        (
            "kaist",
            include_str!("fixtures/kaist-auxiliary-inventory.conllu"),
            vec![
                ("id:M2TA_069-s25/2", "착하다보니", vec!["착하다", "보다"]),
                ("id:MH2_0069-s198/7", "늘어났다", vec!["늘다", "나다"]),
                (
                    "id:MH2_0069-s422/19",
                    "번져나갔다",
                    vec!["번지다", "나가다"],
                ),
                ("id:MH2_0169-s332/8", "해달라고", vec!["하다", "달다"]),
            ],
        ),
        (
            "gsd",
            include_str!("fixtures/gsd-auxiliary-inventory.conllu"),
            vec![("id:dev-s112/1", "먹을만한", vec!["먹다", "만하다"])],
        ),
    ] {
        let report =
            corpus::evaluate(input.as_bytes(), Corpus::parse(name).unwrap(), name).unwrap();
        for (id, surface, expected) in cases {
            let case = report.cases.get(id).expect(id);
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn annotated_particle_chains_preserve_nominal_and_nominalized_groups() {
    for (name, input, cases) in [
        (
            "kaist",
            include_str!("fixtures/kaist-particle-chains.conllu"),
            vec![
                ("id:M2TA_089-s52/8", "어디까지나", "어디"),
                ("id:MH2_0069-s295/3", "이제부터라도", "이제"),
                ("id:MH2_0169-s490/8", "사회주의라고", "사회주의"),
            ],
        ),
        (
            "gsd",
            include_str!("fixtures/gsd-particle-chains.conllu"),
            vec![("id:dev-s471/9", "넣기라도", "넣다")],
        ),
    ] {
        let report =
            corpus::evaluate(input.as_bytes(), Corpus::parse(name).unwrap(), name).unwrap();
        for (id, surface, lemma) in cases {
            let case = report.cases.get(id).expect(id);
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn annotated_post_ending_particles_recover_grouped_cases() {
    for (name, input, cases) in [
        (
            "kaist",
            include_str!("fixtures/kaist-post-ending-particles.conllu"),
            vec![
                ("id:MH2_0159-s132/9", "있습니다만", vec!["있다"]),
                ("id:MH2_0069-s174/9", "통해서만", vec!["통하다"]),
                ("id:M2TA_089-s15/2", "빼고는", vec!["빼다"]),
                ("id:MH2_0169-s548/10", "대주고는", vec!["대다", "주다"]),
            ],
        ),
        (
            "gsd",
            include_str!("fixtures/gsd-post-ending-particles.conllu"),
            vec![("id:dev-s320/3", "하면서도", vec!["하다"])],
        ),
    ] {
        let report =
            corpus::evaluate(input.as_bytes(), Corpus::parse(name).unwrap(), name).unwrap();
        for (id, surface, expected) in cases {
            let case = report.cases.get(id).expect(id);
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn annotated_quoted_questions_recover_negative_copula_and_past_groups() {
    let report = corpus::evaluate(
        std::io::Cursor::new(include_str!("fixtures/kaist-quoted-questions.conllu")),
        Corpus::Kaist,
        "kaist-quoted-questions.conllu",
    )
    .unwrap();
    for (id, surface, lemma) in [
        ("id:MH2_0069-s250/18", "아니냐는", "아니다"),
        ("id:MH2_0169-s383/9", "했느냐는", "하다"),
    ] {
        let case = report.cases.get(id).expect(id);
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, [lemma]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn annotated_daga_past_cases_recover_gold_without_relabeling_a_quoted_subject() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_str!("fixtures/kaist-daga.conllu"),
            vec![
                ("id:MH2_0169-s159/3", "불렀다가", "부르다"),
                ("id:MH2_0169-s718/5", "침략했다가", "침략하다"),
            ],
        ),
        (
            Corpus::Gsd,
            include_str!("fixtures/gsd-daga.conllu"),
            vec![("id:dev-s616/3", "갔다가", "가다")],
        ),
    ] {
        let report = corpus::evaluate(std::io::Cursor::new(input), corpus, "daga.conllu").unwrap();
        for (id, surface, lemma) in cases {
            let case = report.cases.get(id).expect(id);
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
    }
    // Preserve the annotation that distinguishes this quotation from -다가.
    // A future 다 + 가 rule may recover its group, so do not require a miss.
    let row = include_str!("fixtures/kaist-daga.conllu")
        .lines()
        .find(|line| line.starts_with("3\t살겠다가\t"))
        .unwrap();
    let cols: Vec<_> = row.split('\t').collect();
    assert_eq!(cols[2], "살+겠+다+가");
    assert_eq!(cols[4], "pvg+ep+ef+jcs");
}

#[test]
fn annotated_shortened_adnominals_recover_lexical_and_auxiliary_groups() {
    let report = corpus::evaluate(
        std::io::Cursor::new(include_str!("fixtures/kaist-adnominal.conllu")),
        Corpus::Kaist,
        "kaist-adnominal.conllu",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:MH2_0069-s151/10", "절약하려는", vec!["절약하다"]),
        ("id:M2TA_089-s4/3", "배우자는", vec!["배우다"]),
        ("id:MH2_0169-s111/4", "바꿔보자는", vec!["바꾸다", "보다"]),
    ] {
        let case = report.cases.get(id).expect(id);
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, expected);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn annotated_present_conditionals_recover_stable_development_cases() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_str!("fixtures/kaist-conditional.conllu"),
            vec![
                ("id:MH2_0069-s53/7", "한다면", "하다"),
                ("id:MH2_0149-s14/11", "않는다면", "않다"),
            ],
        ),
        (
            Corpus::Gsd,
            include_str!("fixtures/gsd-conditional.conllu"),
            vec![("id:dev-s153/3", "들리신다면", "들리다")],
        ),
    ] {
        let report =
            corpus::evaluate(std::io::Cursor::new(input), corpus, "conditional.conllu").unwrap();
        for (id, surface, lemma) in cases {
            let case = report.cases.get(id).expect(id);
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, [lemma]);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn annotated_comparative_endings_recover_both_saved_bodeusi_misses() {
    let report = corpus::evaluate(
        std::io::Cursor::new(include_str!("fixtures/kaist-comparative.conllu")),
        Corpus::Kaist,
        "kaist-comparative.conllu",
    )
    .unwrap();
    for id in ["id:MH2_0069-s183/2", "id:MH2_0069-s60/2"] {
        let case = report.cases.get(id).expect(id);
        assert_eq!(case.surface, "보듯이");
        assert_eq!(case.expected, ["보다"]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn annotated_adverb_derivations_recover_previously_missed_gold_cases() {
    let report = corpus::evaluate(
        std::io::Cursor::new(include_str!("fixtures/kaist-adverbs.conllu")),
        Corpus::Kaist,
        "kaist-adverbs.conllu",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:M2TA_069-s19/2", "같이", "같다"),
        ("id:M2TA_089-s68/8", "없이", "없다"),
        ("id:MH2_0069-s41/7", "달리", "다르다"),
    ] {
        let case = report.cases.get(id).expect(id);
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, [expected]);
        assert!(case.matched, "{id}");
    }
}

fn row(surface: &str, lemmas: &str, tags: &str, misc: &str) -> String {
    format!("1\t{surface}\t{lemmas}\tVERB\t{tags}\t_\t0\troot\t_\t{misc}")
}

#[test]
fn adapters_preserve_vocabulary_units_and_recover_origlemma() {
    for (name, form, lemmas, tags, misc, expected) in [
        (
            "kaist",
            "공부했다",
            "공부+하+었+다",
            "ncpa+xsv+ep+ef",
            "_",
            vec!["공부하다"],
        ),
        (
            "kaist",
            "필요하다",
            "필요+하+다",
            "ncps+xsm+ef",
            "_",
            vec!["필요하다"],
        ),
        (
            "kaist",
            "간단히",
            "간단+히",
            "ncps+xsa",
            "_",
            vec!["간단히"],
        ),
        (
            "kaist",
            "없었다",
            "없",
            "px+ep+ef",
            "OrigLemma=없+었+다",
            vec!["없다"],
        ),
        (
            "kaist",
            "설치되어있어서",
            "설치+되+어+있+어서",
            "ncpa+xsv+ecx+px+ecs",
            "_",
            vec!["설치되다", "있다"],
        ),
        (
            "gsd",
            "공부했다",
            "공부+하+었+다",
            "NNG+XSV+EP+EF",
            "_",
            vec!["공부하다"],
        ),
        (
            "gsd",
            "아담한",
            "아담+하+ㄴ",
            "XR+XSA+ETM",
            "_",
            vec!["아담하다"],
        ),
        (
            "gsd",
            "관광공사와",
            "관광+공사+와",
            "NNG+NNG+JC",
            "_",
            vec!["관광공사"],
        ),
        (
            "gsd",
            "학생이었다",
            "학생+이+었+다",
            "NNG+VCP+EP+EF",
            "_",
            vec!["학생", "이다"],
        ),
    ] {
        let input = row(form, lemmas, tags, misc);
        assert_eq!(
            corpus::convert(
                &input.split('\t').collect::<Vec<_>>(),
                Corpus::parse(name).unwrap()
            ),
            Conversion::Gold(expected.into_iter().map(str::to_owned).collect())
        );
    }
}

#[test]
fn malformed_and_unsupported_data_are_counted() {
    for (lemmas, tags, reason) in [
        ("하", "pvg+ef", "morpheme_tag_alignment"),
        ("하", "nonsense", "unsupported_tag"),
        ("_", "pvg", "missing_morphology"),
    ] {
        let input = row("하다", lemmas, tags, "_");
        assert_eq!(
            corpus::convert(&input.split('\t').collect::<Vec<_>>(), Corpus::Kaist),
            Conversion::Unsupported(reason)
        );
    }
    let text = format!("bad\nbad.row\n{}\n", row("하다", "하", "pvg+ef", "_"));
    let report = corpus::evaluate(text.as_bytes(), Corpus::Kaist, "synthetic").unwrap();
    assert_eq!(report.malformed_rows, 2);
    assert_eq!(report.unsupported["morpheme_tag_alignment"], 1);
    assert_eq!(report.adapter_coverage, 0.0);
}

fn two_cases() -> corpus::Report {
    let input = format!(
        "# sent_id = a\n{}\n\n# sent_id = b\n{}\n",
        row("먹고", "먹+고", "pvg+ecx", "_"),
        row("가고", "가+고", "pvg+ecx", "_")
    );
    corpus::evaluate(input.as_bytes(), Corpus::Kaist, "synthetic").unwrap()
}

fn lose(report: &mut corpus::Report, id: &str) {
    let case = report.cases.get_mut(id).unwrap();
    case.matched = false;
    case.recovered = 0;
    case.recovered_sets.clear();
    report.grouped_matches -= 1;
    report.recovered_gold_lemmas -= 1;
    report.transformed_matches -= 1;
}

#[test]
fn individual_loss_cannot_be_offset_by_another_gain() {
    let mut old = two_cases();
    lose(&mut old, "id:b/1");
    let mut actual = two_cases();
    lose(&mut actual, "id:a/1");
    assert_eq!(old.grouped_matches, actual.grouped_matches);
    assert_eq!(old.recovered_gold_lemmas, actual.recovered_gold_lemmas);
    let error = corpus::check_baseline(&actual, &old).unwrap_err();
    assert!(
        error.contains("id:a/1") && error.contains("먹고"),
        "{error}"
    );
    assert!(corpus::check_baseline(&two_cases(), &old).is_ok());
}

#[test]
fn partial_losses_and_adapter_changes_are_detected() {
    let input = format!(
        "# sent_id = grouped\n{}\n",
        row(
            "설치되어있어서",
            "설치+되+어+있+어서",
            "ncpa+xsv+ecx+px+ecs",
            "_"
        )
    );
    let mut old = corpus::evaluate(input.as_bytes(), Corpus::Kaist, "synthetic").unwrap();
    old.cases.get_mut("id:grouped/1").unwrap().matched = false;
    old.cases.get_mut("id:grouped/1").unwrap().recovered = 1;
    old.cases.get_mut("id:grouped/1").unwrap().recovered_sets = vec![vec![0]];
    old.grouped_matches = 0;
    old.transformed_matches = 0;
    old.recovered_gold_lemmas = 1;
    let mut bytes = vec![];
    corpus::write_report(&mut bytes, &old).unwrap();
    let mut actual = corpus::read_report(bytes.as_slice()).unwrap();
    actual.cases.get_mut("id:grouped/1").unwrap().recovered = 0;
    actual
        .cases
        .get_mut("id:grouped/1")
        .unwrap()
        .recovered_sets
        .clear();
    actual.recovered_gold_lemmas = 0;
    assert!(
        corpus::check_baseline(&actual, &old)
            .unwrap_err()
            .contains("previously 1")
    );
    let old = two_cases();
    let mut actual = two_cases();
    actual.cases.get_mut("id:a/1").unwrap().expected = vec!["다른말".into()];
    assert!(
        corpus::check_baseline(&actual, &old)
            .unwrap_err()
            .contains("expected lemmas changed")
    );
    let mut actual = two_cases();
    let mut case = actual.cases.remove("id:a/1").unwrap();
    case.id = "id:replacement/1".into();
    actual.cases.insert(case.id.clone(), case);
    assert!(
        corpus::check_baseline(&actual, &old)
            .unwrap_err()
            .contains("no longer converted")
    );
}

#[test]
fn corpus_identity_and_snapshot_integrity() {
    let report = two_cases();
    let mut bytes = vec![];
    corpus::write_report(&mut bytes, &report).unwrap();
    let loaded = corpus::read_report(bytes.as_slice()).unwrap();
    assert_eq!(report.cases, loaded.cases);
    corpus::check_baseline(&loaded, &report).unwrap();
    let mut changed = two_cases();
    changed.input_sha256 = "0".repeat(64);
    assert!(
        corpus::check_baseline(&changed, &report)
            .unwrap_err()
            .contains("SHA-256")
    );
    let mut changed = two_cases();
    changed.schema_version = 99;
    assert!(
        corpus::check_baseline(&changed, &report)
            .unwrap_err()
            .contains("schema")
    );
    let first_newline = bytes.iter().position(|b| *b == b'\n').unwrap();
    assert!(corpus::read_report(&bytes[..=first_newline]).is_err()); // truncated snapshot
    let duplicate = [&bytes[..], &bytes[first_newline + 1..]].concat();
    assert!(
        corpus::read_report(duplicate.as_slice())
            .unwrap_err()
            .to_string()
            .contains("duplicate")
    );
    assert!(corpus::read_report(&b"{\"corpus\":\"kaist\",\"rows\":2}\n"[..]).is_err());
    let input = format!(
        "# sent_id = a\n{}\n{}\n",
        row("먹고", "먹+고", "pvg+ecx", "_"),
        row("가고", "가+고", "pvg+ecx", "_")
    );
    assert!(
        corpus::evaluate(input.as_bytes(), Corpus::Kaist, "duplicate")
            .unwrap_err()
            .to_string()
            .contains("duplicate case ID")
    );
}

#[test]
fn hashes_cover_exact_input_and_case_ids_do_not_depend_on_file_paths() {
    let input = format!(
        "# sent_id = stable\n{}\n",
        row("먹고", "먹+고", "pvg+ecx", "_")
    );
    let a = corpus::evaluate(input.as_bytes(), Corpus::Kaist, "one/path").unwrap();
    let b = corpus::evaluate(input.as_bytes(), Corpus::Kaist, "other/path").unwrap();
    corpus::check_baseline(&b, &a).unwrap();
    let changed = input.replace("먹+고", "먹+지");
    let b = corpus::evaluate(changed.as_bytes(), Corpus::Kaist, "one/path").unwrap();
    assert_eq!(a.cases, b.cases); // same lemmas, different annotation bytes
    assert!(corpus::check_baseline(&b, &a).is_err());
}

fn partial_report(sets: Vec<Vec<usize>>) -> corpus::Report {
    let input = format!(
        "# sent_id = components\n{}\n",
        row(
            "먹어보고있다",
            "먹+어+보+고+있+다",
            "pvg+ecx+px+ecx+px+ef",
            "_"
        )
    );
    let mut report = corpus::evaluate(input.as_bytes(), Corpus::Kaist, "synthetic").unwrap();
    let case = report.cases.get_mut("id:components/1").unwrap();
    assert_eq!(case.expected, ["먹다", "보다", "있다"]);
    case.matched = false;
    case.recovered = sets.iter().map(Vec::len).max().unwrap_or(0);
    case.recovered_sets = sets;
    report.grouped_matches = 0;
    report.transformed_matches = 0;
    report.recovered_gold_lemmas = case.recovered;
    report
}

#[test]
fn component_substitution_cannot_hide_behind_equal_or_better_counts() {
    let old = partial_report(vec![vec![0, 1]]);
    let swapped = partial_report(vec![vec![0, 2]]);
    let error = corpus::check_baseline(&swapped, &old).unwrap_err();
    assert!(
        error.contains("co-recovered gold indices [0, 1]") && error.contains("보다"),
        "{error}"
    );
    assert!(
        corpus::check_baseline(
            &partial_report(vec![vec![1, 2]]),
            &partial_report(vec![vec![0]])
        )
        .is_err()
    );
    assert!(corpus::check_baseline(&partial_report(vec![vec![0], vec![1]]), &old).is_err());
    assert!(corpus::check_baseline(&partial_report(vec![vec![0, 1, 2]]), &old).is_ok());
    assert!(corpus::check_baseline(&old, &partial_report(vec![vec![0], vec![1]])).is_ok());
}

#[test]
fn component_sets_keep_multiplicity_and_do_not_union_alternatives() {
    let gold = ["하다", "하다", "보다"].map(str::to_owned);
    let sets = corpus::component_sets(
        &gold,
        [
            vec!["하다".into()],
            vec!["하다".into(), "보다".into()],
            vec!["하다".into(), "하다".into()],
        ],
    );
    assert_eq!(sets, [vec![0, 1], vec![0, 2]]);
    assert_eq!(
        corpus::component_sets(&gold, [vec!["미지어".into()]]),
        Vec::<Vec<usize>>::new()
    );
    for invalid in [
        vec![vec![3]],
        vec![vec![1, 0]],
        vec![vec![0, 0]],
        vec![vec![0], vec![0]],
        vec![vec![0], vec![0, 1]],
        vec![vec![]],
    ] {
        assert!(corpus::write_report(Vec::new(), &partial_report(invalid)).is_err());
    }
    let mut bytes = vec![];
    corpus::write_report(&mut bytes, &partial_report(vec![vec![0, 1], vec![0, 2]])).unwrap();
    let legacy = String::from_utf8(bytes)
        .unwrap()
        .replace("\"schema_version\":2", "\"schema_version\":1");
    assert!(
        corpus::read_report(legacy.as_bytes())
            .unwrap_err()
            .to_string()
            .contains("version 2")
    );
}

#[test]
fn annotated_fixtures_recover_every_convertible_gold_group() {
    for (name, fixture, count) in [
        ("kaist", include_str!("fixtures/kaist.conllu"), 28),
        ("gsd", include_str!("fixtures/gsd.conllu"), 39),
    ] {
        let report =
            corpus::evaluate(fixture.as_bytes(), Corpus::parse(name).unwrap(), name).unwrap();
        assert_eq!(report.converted_rows, count);
        assert_eq!(report.grouped_matches, count);
        assert!(corpus::check_baseline(&report, &report).is_ok());
        let mut regressed =
            corpus::evaluate(fixture.as_bytes(), Corpus::parse(name).unwrap(), name).unwrap();
        regressed.grouped_matches -= 1;
        assert!(corpus::check_baseline(&regressed, &report).is_err());
    }
}

#[test]
#[ignore = "requires explicitly downloaded corpora; run fetch-corpora.sh first"]
fn pinned_full_corpus_regressions() {
    for corpus in [Corpus::Kaist, Corpus::Gsd] {
        for split in ["dev", "test"] {
            let input = format!("data/corpora/{0}/ko_{0}-ud-{split}.conllu", corpus.name());
            let baseline = format!("data/baselines/{}-{split}.jsonl", corpus.name());
            let old = corpus::read_report(std::io::BufReader::new(
                std::fs::File::open(baseline).unwrap(),
            ))
            .unwrap();
            let actual = corpus::evaluate(
                std::io::BufReader::new(std::fs::File::open(input).unwrap()),
                corpus,
                split,
            )
            .unwrap();
            corpus::check_baseline(&actual, &old).unwrap();
        }
    }
}

#[test]
fn noh_contraction_recovers_double_past_and_preserves_full_compound() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-noh-contraction.conllu").as_slice(),
        Corpus::Kaist,
        "noh-contraction",
    )
    .unwrap();
    for (id, surface, lemma) in [
        ("id:M2TA_069-s13/4", "놨었지요", "놓다"),
        ("id:MH2_0169-s453/6", "내놓아야", "내놓다"),
    ] {
        let case = &report.cases[id];
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, vec![lemma]);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn report_ne_endings_recover_five_new_annotated_groups() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-report-ne.conllu").as_slice(),
            vec![
                (
                    "id:M2TA_089-s28/5",
                    "대부분이라는데",
                    vec!["대부분", "이다"],
                ),
                ("id:MH2_0149-s30/17", "풍속이었다네", vec!["풍속", "이다"]),
                ("id:MH2_0209-s94/14", "있다는데", vec!["있다"]),
            ],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-report-ne.conllu").as_slice(),
            vec![
                ("id:dev-s340/3", "판매한다네요", vec!["판매하다"]),
                ("id:dev-s854/4", "단골집이라는데", vec!["단골집", "이다"]),
            ],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "report-ne").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn doe_endings_recover_past_and_plain_annotated_groups() {
    for (corpus, input, cases) in [
        (
            Corpus::Kaist,
            include_bytes!("fixtures/kaist-doe.conllu").as_slice(),
            vec![("id:MH2_0149-s40/4", "치렀으되", vec!["치르다"])],
        ),
        (
            Corpus::Gsd,
            include_bytes!("fixtures/gsd-doe.conllu").as_slice(),
            vec![("id:dev-s267/5", "그리되", vec!["그리다"])],
        ),
    ] {
        let report = corpus::evaluate(input, corpus, "doe").unwrap();
        for (id, surface, expected) in cases {
            let case = &report.cases[id];
            assert_eq!(case.surface, surface);
            assert_eq!(case.expected, expected);
            assert!(case.matched, "{id}");
        }
    }
}

#[test]
fn chigo_particle_recovers_annotated_apartment() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/gsd-chigo.conllu").as_slice(),
        Corpus::Gsd,
        "chigo",
    )
    .unwrap();
    let case = &report.cases["id:dev-s33/5"];
    assert_eq!(case.surface, "아파트치고");
    assert_eq!(case.expected, ["아파트"]);
    assert!(case.matched);
}

#[test]
fn range_case_particles_recover_annotated_history() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-range-case.conllu").as_slice(),
        Corpus::Kaist,
        "range-case",
    )
    .unwrap();
    let case = &report.cases["id:MH2_0149-s122/6"];
    assert_eq!(case.surface, "역사까지를");
    assert_eq!(case.expected, ["역사"]);
    assert!(case.matched);
    // The second complete sentence preserves the observed 마다 + 에 gap.
    // Its disputed attachment is deliberately not a required/forbidden judgment.
    assert_eq!(report.cases["id:MH2_0159-s285/15"].surface, "편마다에도");
}

#[test]
fn extent_particles_recover_duration_and_preserve_lexical_adverb_gold() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-extent.conllu").as_slice(),
        Corpus::Kaist,
        "extent",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:MH2_0159-s121/11", "필생토록", vec!["필생"]),
        ("id:M2TA_089-s30/5", "그토록", vec!["그토록"]),
    ] {
        let case = &report.cases[id];
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, expected);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn approximation_suffix_recovers_annotated_count_noun() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-approximation.conllu").as_slice(),
        Corpus::Kaist,
        "approximation",
    )
    .unwrap();
    let case = &report.cases["id:MH2_0159-s86/17"];
    assert_eq!(case.surface, "번쯤");
    assert_eq!(case.expected, vec!["번"]);
    assert!(case.matched);
}

#[test]
fn kaist_report_myeo_recovers_annotated_quotations() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/kaist-report-myeo.conllu").as_slice(),
        Corpus::Kaist,
        "report-myeo",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:MH2_0169-s260/11", "지원한다며", vec!["지원하다"]),
        ("id:MH2_0169-s40/8", "필요하다면서", vec!["필요하다"]),
        ("id:MH2_0169-s516/5", "모자란다면서도", vec!["모자라다"]),
    ] {
        let case = &report.cases[id];
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, expected);
        assert!(case.matched, "{id}");
    }
}

#[test]
fn gsd_report_myeo_recovers_annotated_quotations() {
    let report = corpus::evaluate(
        include_bytes!("fixtures/gsd-report-myeo.conllu").as_slice(),
        Corpus::Gsd,
        "report-myeo",
    )
    .unwrap();
    for (id, surface, expected) in [
        ("id:dev-s737/6", "줄이라며", vec!["줄이다"]),
        ("id:dev-s750/26", "현실이라며", vec!["현실", "이다"]),
        ("id:dev-s926/19", "극복하겠다며", vec!["극복하다"]),
    ] {
        let case = &report.cases[id];
        assert_eq!(case.surface, surface);
        assert_eq!(case.expected, expected);
        assert!(case.matched, "{id}");
    }
}
