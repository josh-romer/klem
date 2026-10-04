//! COV-020r: native noun/main-나다 boundaries with immutable raw word readings.
use klem::dictionary::{
    Compatibility, Dictionary, DictionaryMetadata, DictionarySession, Entry, EntrySummary,
    SqliteDictionary, import_krdict,
};
use klem::spacing::{SpacingHypothesis, SpacingLimit, SpacingLimits, suggest};
use klem::{LemmaKind, Lemmatizer, MorphemeKind, Session, WordAnalysis};
use serde_json::Value;
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::PathBuf,
    process::Command,
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "spacing.bare_noun_main_nada";
fn evidence() -> Value {
    serde_json::from_str(include_str!("fixtures/lexical-nada-spacing.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-lexical-nada-{tag}-{}.db", std::process::id()));
        let mut entries = BTreeMap::new();
        for name in [
            "krdict-lexical-nada-spacing.json",
            "krdict-lexical-nada-dependencies.json",
            "krdict-lexical-nada-priority.json",
        ] {
            let data: Value = serde_json::from_str(
                &fs::read_to_string(PathBuf::from("tests/fixtures").join(name)).unwrap(),
            )
            .unwrap();
            for entry in data["LexicalResource"]["Lexicon"]["LexicalEntry"]
                .as_array()
                .unwrap()
            {
                let key = format!("{}:{}", entry["val"], entry["Lemma"]);
                if let Some(previous) = entries.insert(key, entry.clone()) {
                    assert_eq!(previous, *entry);
                }
            }
        }
        let input = path.with_extension("json");
        fs::write(&input, serde_json::to_vec(&serde_json::json!({"LexicalResource":{"Lexicon":{"LexicalEntry":entries.into_values().collect::<Vec<_>>()}}})).unwrap()).unwrap();
        import_krdict(std::slice::from_ref(&input), &path, "lexical-nada-spacing").unwrap();
        fs::remove_file(input).unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn matches(h: &SpacingHypothesis, case: &Value) -> bool {
    h.rule == Some(RULE)
        && h.records.len() == case["segments"].as_array().unwrap().len()
        && h.records
            .iter()
            .zip(case["segments"].as_array().unwrap())
            .all(|(r, expected)| {
                r.record.analysis.as_ref().unwrap().normalized == expected.as_str().unwrap()
            })
}

#[test]
fn native_entries_and_all_389_original_raw_word_paths_are_preserved() {
    let fixture = Fixture::new("source");
    let db = fixture.open();
    let evidence = evidence();
    for entry in evidence["source_entries"].as_array().unwrap() {
        assert_eq!(
            serde_json::to_value(db.entry(entry["id"].as_str().unwrap()).unwrap().unwrap())
                .unwrap(),
            *entry
        );
    }
    for name in [
        "lexical-nada-dependencies.json",
        "lexical-nada-priority-supplement.json",
    ] {
        let native: Value = serde_json::from_str(
            &fs::read_to_string(PathBuf::from("tests/fixtures").join(name)).unwrap(),
        )
        .unwrap();
        for (id, entry) in native["complete_native_entries"].as_object().unwrap() {
            let mut expected = entry.clone();
            for sense in expected["senses"].as_array_mut().unwrap() {
                sense["translations"]
                    .as_array_mut()
                    .unwrap()
                    .retain(|t| t["language"] == "영어");
            }
            assert_eq!(
                serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
                expected,
                "{id}"
            );
        }
    }
    let engine = Lemmatizer::new();
    let mut changed = BTreeSet::new();
    assert_eq!(evidence["before_raw_words"].as_object().unwrap().len(), 389);
    for (surface, before) in evidence["before_raw_words"].as_object().unwrap() {
        let before: WordAnalysis = serde_json::from_value(before.clone()).unwrap();
        for text in [surface.clone(), surface.nfd().collect::<String>()] {
            let actual = engine.analyze_word(&text).unwrap();
            let dependency = match surface.as_str() {
                "나랴" | "연기나랴" => Some(("ending.rya", "으랴")),
                "날라" | "사고날라" => Some(("ending.caution", "을라")),
                _ => None,
            };
            if let Some((rule, form)) = dependency {
                if rule == "ending.caution" {
                    // The separate source freeze retains the same original
                    // raw word. License only these two declared dependencies;
                    // the other 385 originals retain their previous checks.
                    let source: Value =
                        serde_json::from_str(include_str!("fixtures/caution-ending-sources.json"))
                            .unwrap();
                    assert_eq!(
                        serde_json::from_value::<WordAnalysis>(
                            source["before_words"][surface]["analysis"].clone()
                        )
                        .unwrap(),
                        before
                    );
                }
                assert_eq!(actual.normalized, before.normalized);
                assert_eq!(
                    actual
                        .analyses
                        .iter()
                        .filter(|a| before.analyses.contains(a))
                        .collect::<Vec<_>>(),
                    before.analyses.iter().collect::<Vec<_>>()
                );
                let added: Vec<_> = actual
                    .analyses
                    .iter()
                    .filter(|a| !before.analyses.contains(a))
                    .collect();
                assert!(!added.is_empty());
                assert!(added.iter().all(|a| a.rules.iter().any(|r| r == rule)
                    && a.morphemes.iter().any(|m| m.form == form)));
                changed.insert(surface.clone());
            } else {
                assert_eq!(actual, before, "{surface}");
            }
        }
    }
    assert_eq!(
        changed,
        BTreeSet::from([
            "나랴".to_owned(),
            "연기나랴".to_owned(),
            "날라".to_owned(),
            "사고날라".to_owned()
        ])
    );
}

#[test]
fn native_rya_dependency_preserves_allomorphs_irregulars_prefinals_and_copulas() {
    let dependency: Value =
        serde_json::from_str(include_str!("fixtures/lexical-nada-dependencies.json")).unwrap();
    let engine = Lemmatizer::new();
    for case in dependency["required_ending_cases"].as_array().unwrap() {
        for nfd in [false, true] {
            let word = case["surface"].as_str().unwrap();
            let word = if nfd {
                word.nfd().collect::<String>()
            } else {
                word.into()
            };
            let actual = engine.analyze_word(&word).unwrap();
            assert!(
                actual.analyses.iter().any(|a| a
                    .lemmas
                    .last()
                    .is_some_and(|l| l.text == case["lemma"])
                    && a.morphemes.iter().any(|m| m.form == "으랴")
                    && serde_json::to_value(
                        a.morphemes
                            .iter()
                            .filter(|m| m.kind == MorphemeKind::Prefinal)
                            .map(|m| &m.form)
                            .collect::<Vec<_>>()
                    )
                    .unwrap()
                        == case["prefinals"]
                    && a.rules.iter().any(|r| r == "ending.rya")),
                "{}: {:?}",
                case["surface"],
                actual
            );
            for a in actual
                .analyses
                .iter()
                .filter(|a| a.rules.iter().any(|r| r == "ending.rya"))
            {
                assert!(a.breakdown().is_some());
            }
        }
    }
    for (surface, lemma) in [
        ("먹랴", "먹다"),
        ("나으랴", "나다"),
        ("살으랴", "살다"),
        ("좋랴", "좋다"),
    ] {
        for text in [surface.to_owned(), surface.nfd().collect()] {
            let word = engine.analyze_word(&text).unwrap();
            assert!(
                !word
                    .analyses
                    .iter()
                    .any(|a| a.rules.iter().any(|r| r == "ending.rya")
                        && a.lemmas.iter().any(|l| l.text == lemma)),
                "wrong allomorph {surface} for {lemma}"
            );
        }
    }
}

fn fixture_fingerprint(value: &mut Value, fingerprint: &str) {
    match value {
        Value::Object(map) => {
            if let Some(previous) = map.get_mut("fingerprint") {
                assert_eq!(
                    previous,
                    "837de0c1deea1a090c9d9687a9a1fee1425f3dedaaf1c93cc0fcc93870bb7234"
                );
                *previous = fingerprint.into();
            }
            for child in map.values_mut() {
                fixture_fingerprint(child, fingerprint);
            }
        }
        Value::Array(values) => {
            for child in values {
                fixture_fingerprint(child, fingerprint);
            }
        }
        _ => (),
    }
}

#[test]
fn every_native_pair_inflection_prefix_and_exclusion_has_independent_unicode_spans() {
    let fixture = Fixture::new("cases");
    let db = fixture.open();
    let engine = Arc::new(Lemmatizer::new());
    let cases = evidence();
    let mut covered = BTreeSet::new();
    for cache in [0, 1, 4096] {
        let mut words = Session::new(engine.clone(), cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for case in cases["cases"].as_array().unwrap() {
            for nfd in [false, true] {
                let text = case["surface"].as_str().unwrap();
                let text = if nfd {
                    text.nfd().collect::<String>()
                } else {
                    text.into()
                };
                let prefix = "前🙂「";
                let input = format!("{prefix}{text}」");
                let raw = words.analyze_word(&text).unwrap();
                let suggestions = suggest(
                    &mut words,
                    &mut dictionary,
                    &text,
                    prefix.len(),
                    SpacingLimits::default(),
                )
                .unwrap();
                assert!(
                    suggestions.complete,
                    "{}: {:?}",
                    case["id"], suggestions.limited_by
                );
                if case["verdict"] == "forbidden" {
                    assert!(
                        !suggestions
                            .alternatives
                            .iter()
                            .any(|h| h.rule == Some(RULE)),
                        "{}",
                        case["id"]
                    );
                } else {
                    let hypothesis = suggestions
                        .alternatives
                        .iter()
                        .find(|h| matches(h, case))
                        .unwrap_or_else(|| panic!("{}: {:?}", case["id"], suggestions));
                    covered.insert(case["noun_entry"].as_str().unwrap().to_owned());
                    let noun = &hypothesis.records[hypothesis.records.len() - 2];
                    let verb = hypothesis.records.last().unwrap();
                    for (record, expected_id, kind, pos) in [
                        (
                            noun,
                            case["noun_entry"].as_str().unwrap(),
                            LemmaKind::Unclassified,
                            "명사",
                        ),
                        (verb, "krdict:62210", LemmaKind::Predicate, "동사"),
                    ] {
                        let independent = words.analyze_word(&record.record.surface).unwrap();
                        for a in &record.record.analysis.as_ref().unwrap().analyses {
                            assert!(independent.analyses.contains(a));
                            assert_eq!(a.lemmas[0].kind, kind);
                            let own = record.dictionary.assess(a);
                            assert!(
                                own.lemmas[0].entries.iter().any(|e| e.id == expected_id
                                    && e.status != Compatibility::Incompatible)
                            );
                            assert!(record.dictionary.lemmas.iter().any(|l| {
                                l.lemma == a.lemmas[0]
                                    && l.entries
                                        .iter()
                                        .any(|e| e.entry.id == expected_id && e.entry.pos == pos)
                            }));
                        }
                    }
                    assert!(
                        noun.record
                            .analysis
                            .as_ref()
                            .unwrap()
                            .analyses
                            .iter()
                            .all(|a| a.unchanged && a.morphemes.is_empty() && a.lemmas.len() == 1)
                    );
                }
                for h in &suggestions.alternatives {
                    if let Some(rule) = h.rule {
                        assert!(klem::rule_explanation(rule).is_some());
                    }
                    assert_eq!(
                        h.records
                            .iter()
                            .map(|r| r.record.surface.as_str())
                            .collect::<String>(),
                        text
                    );
                    assert_eq!(
                        h.inserted_at,
                        h.records
                            .iter()
                            .skip(1)
                            .map(|r| r.record.span.start)
                            .collect::<Vec<_>>()
                    );
                    for record in &h.records {
                        assert_eq!(&input[record.record.span.clone()], record.record.surface);
                        let independent = words.analyze_word(&record.record.surface).unwrap();
                        assert!(
                            record
                                .record
                                .analysis
                                .as_ref()
                                .unwrap()
                                .analyses
                                .iter()
                                .all(|a| independent.analyses.contains(a))
                        );
                        assert_eq!(
                            record.breakdowns,
                            record
                                .record
                                .analysis
                                .as_ref()
                                .unwrap()
                                .analyses
                                .iter()
                                .map(|a| a.breakdown())
                                .collect::<Vec<_>>()
                        );
                    }
                }
                assert_eq!(words.analyze_word(&text).unwrap(), raw);
                assert!(words.cached_bytes() <= cache && dictionary.cache_bytes() <= cache);
            }
        }
    }
    assert_eq!(covered.len(), 35);
}

struct Provider<'a> {
    db: &'a SqliteDictionary,
    change: Option<(&'a str, &'a str, &'a str)>,
    extra_nominal: bool,
}
impl Dictionary for Provider<'_> {
    fn metadata(&self) -> &DictionaryMetadata {
        self.db.metadata()
    }
    fn fingerprint(&self) -> &str {
        "lexical-nada-adversarial"
    }
    fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
        let mut entries = self.db.lookup(head)?;
        if self.extra_nominal && head == "신경지" {
            entries.push(EntrySummary {
                id: "test:synthetic-case-nominal".into(),
                headword: head.into(),
                homonym: "1".into(),
                pos: "명사".into(),
            });
        }
        if let Some((id, field, value)) = self.change {
            if field == "remove" {
                entries.retain(|e| e.id != id);
            }
            for e in &mut entries {
                if e.id == id {
                    match field {
                        "id" => e.id = value.into(),
                        "headword" => e.headword = value.into(),
                        "homonym" => e.homonym = value.into(),
                        "pos" => e.pos = value.into(),
                        "remove" => (),
                        _ => panic!("unknown mutation"),
                    }
                }
            }
        }
        Ok(entries)
    }
    fn entry(&self, id: &str) -> klem::dictionary::Result<Option<Entry>> {
        self.db.entry(id)
    }
}

#[test]
fn exact_native_fields_cannot_be_borrowed_from_auxiliary_unknown_or_other_homonym_entries() {
    let fixture = Fixture::new("identity");
    let db = fixture.open();
    for id in ["krdict:66370", "krdict:62210"] {
        for (field, value) in [
            ("id", "test:generic-known-entry"),
            ("headword", "another-head"),
            ("homonym", "999"),
            ("pos", ""),
            ("pos", "품사 없음"),
            ("pos", "형용사"),
            ("pos", "보조 동사"),
            ("remove", ""),
        ] {
            let provider = Provider {
                db: &db,
                change: Some((id, field, value)),
                extra_nominal: false,
            };
            let mut dictionary = DictionarySession::new(&provider, 0);
            let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
            let result = suggest(
                &mut words,
                &mut dictionary,
                "사고났다",
                0,
                SpacingLimits::default(),
            )
            .unwrap();
            assert!(result.complete);
            assert!(
                !result.alternatives.iter().any(|h| h.rule == Some(RULE)),
                "{id}/{field}/{value}"
            );
        }
    }
    // The noun's other genuine homonym (thought) and auxiliary 나다 remain
    // present in these removal controls; neither can supply the reviewed IDs.
    assert!(
        db.lookup("사고")
            .unwrap()
            .iter()
            .any(|e| e.id == "krdict:15655")
    );
    assert!(
        db.lookup("나다")
            .unwrap()
            .iter()
            .any(|e| e.id == "krdict:62134")
    );
}

#[test]
fn both_prior_spacing_families_keep_their_hypotheses_and_remaining_budget_priority() {
    let fixture = Fixture::new("priority");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    let evidence = evidence();
    for (surface, before) in evidence["before_legacy_words"].as_object().unwrap() {
        let mut before = before.clone();
        fixture_fingerprint(&mut before, db.fingerprint());
        let result = suggest(
            &mut words,
            &mut dictionary,
            surface,
            0,
            SpacingLimits::default(),
        )
        .unwrap();
        assert!(result.complete);
        let prior: Vec<_> = result
            .alternatives
            .iter()
            .filter(|h| h.rule != Some(RULE))
            .collect();
        assert_eq!(
            serde_json::to_value(prior).unwrap(),
            before["spacing"]["alternatives"],
            "{surface}"
        );
        let budget = before["spacing"]["segment_probes"].as_u64().unwrap() as usize;
        let bounded = suggest(
            &mut words,
            &mut dictionary,
            surface,
            0,
            SpacingLimits {
                segment_probes: budget,
                ..Default::default()
            },
        )
        .unwrap();
        assert_eq!(
            serde_json::to_value(&bounded.alternatives).unwrap(),
            before["spacing"]["alternatives"],
            "{surface}"
        );
        assert!(bounded.segment_probes <= budget);
    }
    let provider = Provider {
        db: &db,
        change: None,
        extra_nominal: true,
    };
    let mut dictionary = DictionarySession::new(&provider, 4096);
    let full = suggest(
        &mut words,
        &mut dictionary,
        "신경질나다",
        0,
        SpacingLimits::default(),
    )
    .unwrap();
    let legacy: Vec<_> = full
        .alternatives
        .iter()
        .filter(|h| h.rule.is_none())
        .cloned()
        .collect();
    assert!(!legacy.is_empty());
    assert!(full.alternatives.iter().any(|h| h.rule == Some(RULE)));
    let bounded = suggest(
        &mut words,
        &mut dictionary,
        "신경질나다",
        0,
        SpacingLimits {
            alternatives: legacy.len(),
            ..Default::default()
        },
    )
    .unwrap();
    assert_eq!(bounded.alternatives, legacy);
    assert!(!bounded.complete && bounded.limited_by.contains(&SpacingLimit::Alternatives));
}

#[test]
fn repeated_ambiguous_prefixes_and_explicit_limits_remain_bounded() {
    let fixture = Fixture::new("bounds");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    for (limits, reason) in [
        (
            SpacingLimits {
                token_chars: 1,
                ..Default::default()
            },
            SpacingLimit::TokenChars,
        ),
        (
            SpacingLimits {
                segment_probes: 0,
                ..Default::default()
            },
            SpacingLimit::SegmentProbes,
        ),
        (
            SpacingLimits {
                alternatives: 0,
                ..Default::default()
            },
            SpacingLimit::Alternatives,
        ),
    ] {
        let result = suggest(&mut words, &mut dictionary, "사고났다", 0, limits).unwrap();
        assert!(!result.complete && result.limited_by.contains(&reason));
        assert!(result.segment_probes <= limits.segment_probes);
        assert!(result.alternatives.len() <= limits.alternatives);
    }
    let limits = SpacingLimits {
        token_chars: 128,
        segment_probes: 16384,
        alternatives: 16,
    };
    let prefix = "지식인들을".repeat(24);
    let dead = suggest(
        &mut words,
        &mut dictionary,
        &(prefix.clone() + "교통사고ZZZ"),
        0,
        limits,
    )
    .unwrap();
    assert!(dead.complete && dead.alternatives.is_empty());
    let live = suggest(
        &mut words,
        &mut dictionary,
        &(prefix + "교통사고났다"),
        0,
        limits,
    )
    .unwrap();
    assert_eq!(live.alternatives.len(), limits.alternatives);
    assert!(!live.complete && live.limited_by.contains(&SpacingLimit::Alternatives));
    assert!(live.alternatives.iter().all(|h| h.rule == Some(RULE)));
    assert_eq!(
        live.alternatives
            .iter()
            .map(|h| &h.inserted_at)
            .collect::<BTreeSet<_>>()
            .len(),
        limits.alternatives
    );
    assert!(words.cached_bytes() <= 4096 && dictionary.cache_bytes() <= 4096);
}

#[test]
fn cli_filters_preserve_original_words_and_every_separate_spacing_option() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    for case in evidence()["cases"].as_array().unwrap() {
        for nfd in [false, true] {
            let text = case["surface"].as_str().unwrap();
            let text = if nfd {
                text.nfd().collect::<String>()
            } else {
                text.into()
            };
            let expected = suggest(
                &mut words,
                &mut dictionary,
                &text,
                0,
                SpacingLimits::default(),
            )
            .unwrap();
            for flag in [None, Some("--dict-only"), Some("--dict-compatible")] {
                let run = |spacing| {
                    let mut c = Command::new(env!("CARGO_BIN_EXE_klem"));
                    c.args(["word", &text, "--dictionary"]).arg(&fixture.0);
                    if spacing {
                        c.arg("--suggest-spacing");
                    }
                    if let Some(flag) = flag {
                        c.arg(flag);
                    }
                    let result = c.output().unwrap();
                    assert!(result.status.success(), "{:?}", result.stderr);
                    serde_json::from_slice::<Value>(&result.stdout).unwrap()
                };
                let mut actual = run(true);
                assert_eq!(actual["spacing"], serde_json::to_value(&expected).unwrap());
                actual.as_object_mut().unwrap().remove("spacing");
                assert_eq!(actual, run(false));
            }
        }
    }
}
