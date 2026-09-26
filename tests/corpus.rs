#[path = "../tools/corpus.rs"]
mod corpus;
use corpus::{Conversion, Corpus};

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
