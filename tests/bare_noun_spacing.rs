//! COV-020q: independent source-attested noun/main-verb spacing alternatives.
use klem::dictionary::{
    Dictionary, DictionaryMetadata, DictionarySession, Entry, EntrySummary, SqliteDictionary,
    import_krdict,
};
use klem::spacing::{SpacingHypothesis, SpacingLimit, SpacingLimits, suggest};
use klem::{Lemmatizer, Session, WordAnalysis};
use serde_json::{Value, json};
use std::{collections::BTreeMap, fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "spacing.bare_noun_lexical_verb";
fn source() -> Value {
    serde_json::from_str(include_str!("fixtures/bare-noun-spacing-sources.json")).unwrap()
}
fn additional() -> Value {
    serde_json::from_str(include_str!(
        "fixtures/bare-noun-spacing-additional-pairs.json"
    ))
    .unwrap()
}
fn ledger() -> Value {
    let mut ledger: Value =
        serde_json::from_str(include_str!("fixtures/bare-noun-spacing-validity.json")).unwrap();
    let updates: Value = serde_json::from_str(include_str!(
        "fixtures/bare-noun-spacing-judgment-updates.json"
    ))
    .unwrap();
    assert_eq!(updates["corrections"].as_array().unwrap().len(), 3);
    for update in updates["corrections"].as_array().unwrap() {
        let case = ledger["cases"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|c| c["id"] == update["id"])
            .unwrap();
        assert_eq!(*case, update["original_case"]);
        *case = update["updated_case"].clone();
    }
    ledger["cases"]
        .as_array_mut()
        .unwrap()
        .extend(additional()["cases"].as_array().unwrap().iter().cloned());
    ledger
}
fn array(v: &Value) -> Vec<&Value> {
    v.as_array().map_or_else(|| vec![v], |a| a.iter().collect())
}
fn feature<'a>(v: &'a Value, name: &str) -> Option<&'a str> {
    array(&v["feat"])
        .into_iter()
        .find(|f| f["att"] == name)
        .and_then(|f| f["val"].as_str())
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-bare-noun-spacing-{tag}-{}.db",
            std::process::id()
        ));
        let mut entries = BTreeMap::new();
        for name in [
            "krdict-bare-noun-spacing.json",
            "krdict-bare-noun-spacing-additional.json",
            "krdict-spacing.json",
            "krdict-continuation-left.json",
        ] {
            let data: Value = serde_json::from_str(
                &fs::read_to_string(PathBuf::from("tests/fixtures").join(name)).unwrap(),
            )
            .unwrap();
            for entry in array(&data["LexicalResource"]["Lexicon"]["LexicalEntry"]) {
                let head = array(&entry["Lemma"])
                    .into_iter()
                    .find_map(|l| feature(l, "writtenForm"))
                    .unwrap();
                let key = format!(
                    "{}:{head}:{}",
                    entry["val"],
                    feature(entry, "partOfSpeech").unwrap_or("품사 없음")
                );
                entries.entry(key).or_insert_with(|| entry.clone());
            }
        }
        let lmf = path.with_extension("json");
        fs::write(
            &lmf,
            serde_json::to_vec(&json!({"LexicalResource":{"Lexicon":{"LexicalEntry":entries.into_values().collect::<Vec<_>>()}}})).unwrap(),
        )
        .unwrap();
        import_krdict(std::slice::from_ref(&lmf), &path, "bare-noun-spacing").unwrap();
        fs::remove_file(lmf).unwrap();
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
fn matches(alternative: &SpacingHypothesis, judgment: &Value) -> bool {
    alternative.rule == Some(RULE)
        && alternative.records.len() == judgment["segments"].as_array().unwrap().len()
        && alternative
            .records
            .iter()
            .zip(judgment["segments"].as_array().unwrap())
            .all(|(record, expected)| {
                record.record.surface == expected["surface"]
                    && record.record.analysis.as_ref().unwrap().analyses.iter().any(|a| {
                        json!(a.lemmas.iter().map(|l| &l.text).collect::<Vec<_>>()) == expected["lemmas"]
                            && json!(a.lemmas.iter().map(|l| l.kind).collect::<Vec<_>>()) == expected["lemma_kinds"]
                            // Exclusions concern the whole named pair/template,
                            // not just a hand-picked ending that might be absent.
                            && (judgment["verdict"] == "forbidden"
                                || json!(a.morphemes.iter().map(|m| &m.form).collect::<Vec<_>>()) == expected["morphemes"])
                    })
            })
}

#[test]
fn full_native_source_pairs_and_original_raw_candidates_are_preserved() {
    let fixture = Fixture::new("source");
    let db = fixture.open();
    let source = source();
    assert_eq!(source["source_entries"].as_array().unwrap().len(), 33);
    assert_eq!(source["pair_reviews"].as_array().unwrap().len(), 16);
    let additional = additional();
    assert_eq!(additional["source_entries"].as_array().unwrap().len(), 2);
    for evidence in [&source, &additional] {
        for entry in evidence["source_entries"].as_array().unwrap() {
            let id = entry["id"].as_str().unwrap();
            assert_eq!(
                serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
                *entry
            );
            let mut projected = evidence["complete_native_entries"][id].clone();
            for sense in projected["senses"].as_array_mut().unwrap() {
                sense["translations"]
                    .as_array_mut()
                    .unwrap()
                    .retain(|t| t["language"] == "영어");
            }
            assert_eq!(projected, *entry);
        }
    }
    let engine = Lemmatizer::new();
    assert_eq!(source["before_words"].as_object().unwrap().len(), 88);
    assert_eq!(additional["before_words"].as_object().unwrap().len(), 8);
    for (surface, modes) in [&source, &additional]
        .into_iter()
        .flat_map(|e| e["before_words"].as_object().unwrap())
    {
        let mut value = modes["all"].clone();
        value.as_object_mut().unwrap().remove("dictionary");
        value.as_object_mut().unwrap().remove("spacing");
        let before: WordAnalysis = serde_json::from_value(value).unwrap();
        assert_eq!(engine.analyze_word(surface).unwrap(), before, "{surface}");
        assert_eq!(
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap(),
            before
        );
    }
}

#[test]
fn all_source_scoped_pairs_keep_independent_roles_and_original_unicode_spans() {
    let fixture = Fixture::new("judgments");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    let mut counts = [0, 0];
    for case in ledger()["cases"].as_array().unwrap() {
        for nfd in [false, true] {
            let text = case["surface"].as_str().unwrap();
            let surface = if nfd {
                text.nfd().collect::<String>()
            } else {
                text.into()
            };
            let prefix = "前🙂「";
            let input = format!("{prefix}{surface}」");
            let raw = words.analyze_word(&surface).unwrap();
            let actual = suggest(
                &mut words,
                &mut dictionary,
                &surface,
                prefix.len(),
                SpacingLimits::default(),
            )
            .unwrap();
            assert!(actual.complete, "{}: {:?}", case["id"], actual.limited_by);
            for original in case["judgments"].as_array().unwrap() {
                let mut judgment = original.clone();
                if nfd {
                    for s in judgment["segments"].as_array_mut().unwrap() {
                        s["surface"] =
                            json!(s["surface"].as_str().unwrap().nfd().collect::<String>());
                    }
                }
                let required = judgment["verdict"] == "required";
                if !nfd {
                    counts[usize::from(!required)] += 1;
                }
                assert_eq!(
                    actual.alternatives.iter().any(|a| matches(a, &judgment)),
                    required,
                    "{}",
                    case["id"]
                );
            }
            for a in actual.alternatives {
                if let Some(rule) = a.rule {
                    assert!(klem::rule_explanation(rule).is_some());
                }
                assert_eq!(
                    a.records
                        .iter()
                        .map(|r| r.record.surface.as_str())
                        .collect::<String>(),
                    surface
                );
                assert_eq!(
                    a.inserted_at,
                    a.records
                        .iter()
                        .skip(1)
                        .map(|r| r.record.span.start)
                        .collect::<Vec<_>>()
                );
                for r in a.records {
                    assert_eq!(&input[r.record.span.clone()], r.record.surface);
                    let independent = words.analyze_word(&r.record.surface).unwrap();
                    for path in &r.record.analysis.as_ref().unwrap().analyses {
                        assert!(independent.analyses.contains(path));
                    }
                    assert_eq!(
                        r.breakdowns,
                        r.record
                            .analysis
                            .as_ref()
                            .unwrap()
                            .analyses
                            .iter()
                            .map(|a| a.breakdown())
                            .collect::<Vec<_>>()
                    );
                    assert!(r.breakdowns.iter().all(Option::is_some));
                }
            }
            assert_eq!(words.analyze_word(&surface).unwrap(), raw);
            assert!(words.cached_bytes() <= 4096 && dictionary.cache_bytes() <= 4096);
        }
    }
    assert_eq!(counts, [44, 23]);
}

struct Provider<'a> {
    native: &'a SqliteDictionary,
    noun_pos: &'a str,
    verb_pos: &'a str,
    auxiliary_homonym: bool,
    extra_case_nominal: bool,
}

#[test]
fn existing_case_phrases_can_precede_every_exact_pair_without_changing_raw_words() {
    let fixture = Fixture::new("prefixes");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 0);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
    for (noun, tail, verb) in [
        ("신경질", "내며", "내다"),
        ("용기", "내서", "내다"),
        ("짜증", "낼", "내다"),
        ("기분", "내키는", "내키다"),
    ] {
        for nfd in [false, true] {
            let surface = format!("학교에서{noun}{tail}");
            let surface = if nfd {
                surface.nfd().collect::<String>()
            } else {
                surface
            };
            let raw = words.analyze_word(&surface).unwrap();
            let result = suggest(
                &mut words,
                &mut dictionary,
                &surface,
                7,
                SpacingLimits::default(),
            )
            .unwrap();
            assert!(result.complete);
            let hypothesis = result
                .alternatives
                .iter()
                .find(|h| h.rule == Some(RULE) && h.records.len() == 3)
                .unwrap();
            assert_eq!(
                hypothesis.records[0]
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .normalized,
                "학교에서"
            );
            assert_eq!(
                hypothesis.records[1]
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .normalized,
                noun
            );
            assert!(
                hypothesis.records[2]
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .iter()
                    .all(|a| a.lemmas[0].text == verb)
            );
            assert_eq!(
                hypothesis.inserted_at,
                vec![
                    7 + hypothesis.records[0].record.surface.len(),
                    7 + hypothesis.records[0].record.surface.len()
                        + hypothesis.records[1].record.surface.len()
                ]
            );
            assert_eq!(words.analyze_word(&surface).unwrap(), raw);
        }
    }
    assert_eq!(words.cached_bytes(), 0);
    assert_eq!(dictionary.cache_bytes(), 0);
}
impl Dictionary for Provider<'_> {
    fn metadata(&self) -> &DictionaryMetadata {
        self.native.metadata()
    }
    fn fingerprint(&self) -> &str {
        "test-bare-noun-classes"
    }
    fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
        let pos = if matches!(head, "신경질" | "용기" | "짜증" | "기분")
            || (self.extra_case_nominal && head == "신경지")
        {
            self.noun_pos
        } else {
            self.verb_pos
        };
        if pos == "absent" {
            return Ok(Vec::new());
        }
        let mut entries = vec![EntrySummary {
            id: format!("test:{head}"),
            headword: head.into(),
            homonym: "1".into(),
            pos: pos.into(),
        }];
        if head == "내다" && self.auxiliary_homonym {
            entries.push(EntrySummary {
                id: "test:auxiliary".into(),
                headword: head.into(),
                homonym: "2".into(),
                pos: "보조 동사".into(),
            });
        }
        Ok(entries)
    }
    fn entry(&self, _: &str) -> klem::dictionary::Result<Option<Entry>> {
        Ok(None)
    }
}

#[test]
fn dictionary_classes_require_a_real_noun_and_main_verb_without_borrowing_homonyms() {
    let fixture = Fixture::new("classes");
    let db = fixture.open();
    for (noun, verb, auxiliary, expected) in [
        ("명사", "동사", true, true),
        ("명사", "보조 동사", true, false),
        ("명사", "형용사", false, false),
        ("명사", "", true, false),
        ("동사", "동사", false, false),
        ("", "동사", false, false),
        ("품사 없음", "동사", false, false),
        ("absent", "동사", false, false),
        ("명사", "absent", false, false),
    ] {
        let provider = Provider {
            native: &db,
            noun_pos: noun,
            verb_pos: verb,
            auxiliary_homonym: auxiliary,
            extra_case_nominal: false,
        };
        let mut dictionary = DictionarySession::new(&provider, 0);
        let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
        for surface in ["짜증낼", "기분내키는"] {
            let result = suggest(
                &mut words,
                &mut dictionary,
                surface,
                0,
                SpacingLimits::default(),
            )
            .unwrap();
            assert_eq!(
                result.alternatives.iter().any(|a| a.rule == Some(RULE)),
                expected,
                "noun={noun},verb={verb}"
            );
        }
        for input in ["짜증나다", "짜증읽다", "짜증내키는", "기분내다", "화내다"]
        {
            let result = suggest(
                &mut words,
                &mut dictionary,
                input,
                0,
                SpacingLimits::default(),
            )
            .unwrap();
            assert!(
                !result.alternatives.iter().any(|a| a.rule == Some(RULE)),
                "{input}"
            );
        }
    }
}

#[test]
fn new_pair_search_cannot_displace_a_legacy_case_hypothesis_at_the_output_limit() {
    let fixture = Fixture::new("priority");
    let db = fixture.open();
    // Synthetic nominal spelling creates a competing contracted 를 reading.
    // This is an adversarial boundary test, not Korean vocabulary evidence.
    let provider = Provider {
        native: &db,
        noun_pos: "명사",
        verb_pos: "동사",
        auxiliary_homonym: true,
        extra_case_nominal: true,
    };
    let mut dictionary = DictionarySession::new(&provider, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    let complete = suggest(
        &mut words,
        &mut dictionary,
        "신경질내다",
        0,
        SpacingLimits::default(),
    )
    .unwrap();
    assert!(complete.complete);
    let legacy: Vec<_> = complete
        .alternatives
        .iter()
        .filter(|a| a.rule.is_none())
        .cloned()
        .collect();
    assert!(!legacy.is_empty());
    assert!(complete.alternatives.iter().any(|a| a.rule == Some(RULE)));
    let bounded = suggest(
        &mut words,
        &mut dictionary,
        "신경질내다",
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
fn finite_prefixes_obey_explicit_limits_and_keep_long_unknown_suffixes_bounded() {
    let fixture = Fixture::new("limits");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 0);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
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
        let s = suggest(&mut words, &mut dictionary, "짜증낼", 0, limits).unwrap();
        assert!(!s.complete && s.limited_by.contains(&reason));
        assert!(
            s.segment_probes <= limits.segment_probes
                && s.alternatives.len() <= limits.alternatives
        );
    }
    let long = "짜증".repeat(256) + "낼";
    let s = suggest(
        &mut words,
        &mut dictionary,
        &long,
        0,
        SpacingLimits {
            token_chars: 1024,
            segment_probes: 16,
            alternatives: 16,
        },
    )
    .unwrap();
    assert!(s.complete && s.alternatives.is_empty());
    assert!(s.segment_probes < 8, "{:?}", s);
    assert_eq!(words.cached_bytes(), 0);
    assert_eq!(dictionary.cache_bytes(), 0);
}

#[test]
fn cli_spacing_is_opt_in_and_preserves_every_default_dictionary_record() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    for case in ledger()["cases"].as_array().unwrap() {
        for nfd in [false, true] {
            let surface = case["surface"].as_str().unwrap();
            let surface = if nfd {
                surface.nfd().collect::<String>()
            } else {
                surface.into()
            };
            let expected = suggest(
                &mut words,
                &mut dictionary,
                &surface,
                0,
                SpacingLimits::default(),
            )
            .unwrap();
            for flag in [None, Some("--dict-only"), Some("--dict-compatible")] {
                let run = |spacing| {
                    let mut c = Command::new(env!("CARGO_BIN_EXE_klem"));
                    c.args(["word", &surface, "--dictionary"]).arg(&fixture.0);
                    if spacing {
                        c.arg("--suggest-spacing");
                    }
                    if let Some(flag) = flag {
                        c.arg(flag);
                    }
                    let output = c.output().unwrap();
                    assert!(output.status.success(), "{:?}", output.stderr);
                    serde_json::from_slice::<Value>(&output.stdout).unwrap()
                };
                let mut actual = run(true);
                assert_eq!(actual["spacing"], serde_json::to_value(&expected).unwrap());
                actual.as_object_mut().unwrap().remove("spacing");
                assert_eq!(actual, run(false));
            }
        }
    }
}
