//! COV-020p: independent-word hypotheses with original byte spans, not auxiliary chains.
use klem::dictionary::{DictionarySession, SqliteDictionary, import_krdict};
use klem::spacing::{SpacingHypothesis, SpacingLimit, SpacingLimits, suggest};
use klem::{Lemmatizer, Session};
use serde::Deserialize;
use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::PathBuf,
    process::Command,
    sync::Arc,
};
use unicode_normalization::UnicodeNormalization;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Suite {
    schema_version: u32,
    review_status: String,
    sources: BTreeMap<String, String>,
    cases: Vec<Case>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Case {
    id: String,
    surface: String,
    source: String,
    judgments: Vec<Judgment>,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Judgment {
    id: String,
    verdict: String,
    segments: Vec<ExpectedSegment>,
    reason: String,
}
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ExpectedSegment {
    surface: String,
    lemmas: Vec<String>,
    lemma_kinds: Vec<klem::LemmaKind>,
    morphemes: Vec<String>,
}
fn suite() -> Suite {
    serde_json::from_str(include_str!("fixtures/spacing-validity.json")).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let p = std::env::temp_dir().join(format!("klem-spacing-{}-{name}.db", std::process::id()));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-spacing.json")],
            &p,
            "spacing-fixture",
        )
        .unwrap();
        Self(p)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}
fn matches(a: &SpacingHypothesis, j: &Judgment) -> bool {
    a.records.len() == j.segments.len()
        && a.records.iter().zip(&j.segments).all(|(r, s)| {
            r.record.surface == s.surface
                && r.record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .iter()
                    .any(|a| {
                        a.lemmas.iter().map(|l| &l.text).eq(s.lemmas.iter())
                            && a.lemmas
                                .iter()
                                .map(|l| l.kind)
                                .eq(s.lemma_kinds.iter().copied())
                            && a.morphemes.iter().map(|m| &m.form).eq(s.morphemes.iter())
                    })
        })
}
#[test]
fn source_backed_spacing_judgments_preserve_independent_words_and_all_alternatives() {
    let fixture = Fixture::new("judgments");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Arc::new(Lemmatizer::new());
    let mut words = Session::new(engine.clone(), 4096);
    let suite = suite();
    assert_eq!(suite.schema_version, 1);
    assert!(!suite.review_status.is_empty());
    let mut ids = BTreeSet::new();
    let mut counts = [0, 0];
    for c in suite.cases {
        assert!(ids.insert(c.id.clone()));
        assert!(suite.sources[&c.source].starts_with("https://"));
        let original = words.analyze_word(&c.surface).unwrap();
        let suggestions = suggest(
            &mut words,
            &mut dictionary,
            &c.surface,
            0,
            SpacingLimits::default(),
        )
        .unwrap();
        assert!(
            suggestions.complete,
            "{}: {:?}",
            c.id, suggestions.limited_by
        );
        assert_eq!(suggestions.rule, "spacing.nominal_case_predicate");
        assert!(klem::rule_explanation(suggestions.rule).is_some());
        for j in c.judgments {
            assert!(!j.id.is_empty() && !j.reason.is_empty());
            assert!(matches!(j.verdict.as_str(), "required" | "forbidden"));
            let required = j.verdict == "required";
            counts[usize::from(!required)] += 1;
            assert_eq!(
                suggestions.alternatives.iter().any(|a| matches(a, &j)),
                required,
                "{} / {}",
                c.id,
                j.id
            );
        }
        for alternative in suggestions.alternatives {
            assert!(alternative.records.len() >= 2);
            assert_eq!(
                alternative.spaced,
                alternative
                    .records
                    .iter()
                    .map(|r| r.record.surface.as_str())
                    .collect::<Vec<_>>()
                    .join(" ")
            );
            assert_eq!(
                alternative.inserted_at,
                alternative
                    .records
                    .iter()
                    .skip(1)
                    .map(|r| r.record.span.start)
                    .collect::<Vec<_>>()
            );
            assert_eq!(
                alternative
                    .records
                    .iter()
                    .map(|r| r.record.surface.as_str())
                    .collect::<String>(),
                c.surface
            );
            for r in alternative.records {
                let w = r.record.analysis.unwrap();
                let raw = engine.analyze_word(&r.record.surface).unwrap();
                assert_eq!(w.normalized, raw.normalized);
                assert_eq!(
                    r.breakdowns,
                    w.analyses.iter().map(|a| a.breakdown()).collect::<Vec<_>>()
                );
                assert!(r.breakdowns.iter().all(Option::is_some));
                for a in &w.analyses {
                    assert!(raw.analyses.contains(a));
                }
                assert!(
                    r.dictionary
                        .readings
                        .iter()
                        .all(|r| r.status != klem::dictionary::Compatibility::Incompatible)
                );
                assert!(
                    w.analyses
                        .iter()
                        .all(|a| a.lemmas.iter().all(|l| r.dictionary.has_match(l, false)))
                );
            }
        }
        assert_eq!(original, words.analyze_word(&c.surface).unwrap());
        assert!(words.cached_bytes() <= 4096);
        assert!(dictionary.cache_bytes() <= 4096);
    }
    assert_eq!(counts, [14, 6]);
}
#[test]
fn spacing_offsets_preserve_original_utf8_and_decomposed_hangul() {
    let fixture = Fixture::new("unicode");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 0);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
    for word in [
        "결혼을하라느니".to_string(),
        "결혼을하라느니".nfd().collect::<String>(),
    ] {
        let prefix = "「前🙂」";
        let text = format!("{prefix}{word}!\n");
        let suggestions = suggest(
            &mut words,
            &mut dictionary,
            &word,
            prefix.len(),
            SpacingLimits::default(),
        )
        .unwrap();
        assert!(suggestions.complete);
        assert!(
            suggestions
                .alternatives
                .iter()
                .any(|a| a.spaced.nfc().collect::<String>() == "결혼을 하라느니")
        );
        for a in suggestions.alternatives {
            let mut offset = prefix.len();
            for r in a.records {
                assert_eq!(r.record.span.start, offset);
                assert_eq!(&text[r.record.span.clone()], r.record.surface);
                assert!(
                    text.is_char_boundary(r.record.span.start)
                        && text.is_char_boundary(r.record.span.end)
                );
                offset = r.record.span.end;
            }
            assert_eq!(offset, prefix.len() + word.len());
        }
    }
    assert_eq!(words.cached_bytes(), 0);
    assert_eq!(dictionary.cache_bytes(), 0);
}
#[test]
fn spacing_reports_work_output_and_token_limits_without_mutating_candidates() {
    let fixture = Fixture::new("limits");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    let input = "결혼을하라느니";
    let original = words.analyze_word(input).unwrap();
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
        (
            SpacingLimits {
                alternatives: 1,
                ..Default::default()
            },
            SpacingLimit::Alternatives,
        ),
    ] {
        let s = suggest(&mut words, &mut dictionary, input, 0, limits).unwrap();
        assert!(!s.complete);
        assert!(s.limited_by.contains(&reason));
        assert!(s.alternatives.len() <= limits.alternatives);
        assert!(s.segment_probes <= limits.segment_probes);
        assert_eq!(original, words.analyze_word(input).unwrap());
    }
    let long = "가".repeat(1024);
    let s = suggest(
        &mut words,
        &mut dictionary,
        &long,
        0,
        SpacingLimits::default(),
    )
    .unwrap();
    assert_eq!(s.limited_by, [SpacingLimit::TokenChars]);
    assert_eq!(s.segment_probes, 0);
    assert!(s.alternatives.is_empty());
    for word in ["", "학교에 가요"] {
        assert!(
            suggest(
                &mut words,
                &mut dictionary,
                word,
                0,
                SpacingLimits::default()
            )
            .is_err()
        );
    }
    assert!(
        suggest(
            &mut words,
            &mut dictionary,
            input,
            usize::MAX,
            SpacingLimits::default()
        )
        .is_err()
    );
}
#[test]
fn spacing_sources_keep_the_original_malformed_primary_group() {
    let source: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/spacing-sources.json")).unwrap();
    let native: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-spacing.json")).unwrap();
    let previous: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/krdict-quoted-neuni.json")).unwrap();
    let es = native["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap();
    assert_eq!(es.len(), 47);
    let primary = es.iter().find(|e| e["val"] == "86079").unwrap();
    assert_eq!(
        primary,
        previous["LexicalResource"]["Lexicon"]["LexicalEntry"]
            .as_array()
            .unwrap()
            .iter()
            .find(|e| e["val"] == "86079")
            .unwrap()
    );
    assert_eq!(source["source_observation"]["original"], "결혼을하라느니");
    let sense = primary["Sense"]
        .as_array()
        .unwrap()
        .iter()
        .find(|s| s["val"] == "2")
        .unwrap();
    assert_eq!(
        source["source_observation"]["native_group"],
        sense["SenseExample"][4]
    );
    assert!(
        serde_json::to_string(&sense["SenseExample"][4])
            .unwrap()
            .contains("결혼을하라느니")
    );
}
#[test]
fn cli_spacing_word_and_stream_exports_match_the_library_and_preserve_default_records() {
    let fixture = Fixture::new("cli");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Arc::new(Lemmatizer::new());
    let mut words = Session::new(engine, 4096);
    for case in suite().cases {
        let expected = suggest(
            &mut words,
            &mut dictionary,
            &case.surface,
            0,
            SpacingLimits::default(),
        )
        .unwrap();
        for flag in [None, Some("--dict-only"), Some("--dict-compatible")] {
            let mut cmd = Command::new(env!("CARGO_BIN_EXE_klem"));
            cmd.args(["word", &case.surface, "--dictionary"])
                .arg(&fixture.0)
                .arg("--suggest-spacing");
            if let Some(flag) = flag {
                cmd.arg(flag);
            }
            let output = cmd.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let mut value: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(value["spacing"], serde_json::to_value(&expected).unwrap());
            value.as_object_mut().unwrap().remove("spacing");
            let mut old = Command::new(env!("CARGO_BIN_EXE_klem"));
            old.args(["word", &case.surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                old.arg(flag);
            }
            let output = old.output().unwrap();
            assert!(output.status.success());
            assert_eq!(
                value,
                serde_json::from_slice::<serde_json::Value>(&output.stdout).unwrap()
            );
        }
    }
    let nfd = "結🙂結婚";
    let input = format!(
        "{nfd} 결혼을하라느니!\n{}",
        "책을읽어요".nfd().collect::<String>()
    );
    let file = fixture.0.with_extension("txt");
    fs::write(&file, &input).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_klem"))
        .arg("text")
        .arg(&file)
        .arg("--dictionary")
        .arg(&fixture.0)
        .arg("--suggest-spacing")
        .output()
        .unwrap();
    fs::remove_file(file).unwrap();
    assert!(output.status.success());
    let records = String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|l| serde_json::from_str::<serde_json::Value>(l).unwrap())
        .collect::<Vec<_>>();
    let source = klem::Tokenizer::new(&input).collect::<Vec<_>>();
    assert_eq!(records.len(), source.len());
    for (r, (span, kind, surface)) in records.iter().zip(source) {
        assert_eq!(r["surface"], surface);
        assert_eq!(r["span"], serde_json::to_value(&span).unwrap());
        if kind == klem::TokenKind::Word {
            assert_eq!(
                r["spacing"],
                serde_json::to_value(
                    suggest(
                        &mut words,
                        &mut dictionary,
                        surface,
                        span.start,
                        SpacingLimits::default()
                    )
                    .unwrap()
                )
                .unwrap()
            );
        } else {
            assert!(r.get("spacing").is_none());
        }
    }
    for args in [
        vec!["word", "책을읽어요", "--suggest-spacing"],
        vec!["word", "책을읽어요", "--spacing-limit", "1"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(args)
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(!output.stderr.is_empty());
    }
}

#[test]
fn ambiguous_case_prefixes_exhaust_dead_suffixes_without_enumerating_prefix_products() {
    let fixture = Fixture::new("ambiguous-dead-ends");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    // Multiple case-phrase partitions per repetition have exponentially many
    // possible prefixes. None can make the dictionary-missing suffix a predicate.
    // This is an engineering stress input, not a grammatical Korean sentence.
    let prefix = "지식인들을".repeat(24);
    let input = format!("{prefix}ZZZ");
    let original = words.analyze_word(&input).unwrap();
    let limits = SpacingLimits {
        token_chars: 128,
        segment_probes: 16384,
        alternatives: 16,
    };
    let suggestions = suggest(&mut words, &mut dictionary, &input, 0, limits).unwrap();
    assert!(suggestions.complete);
    assert!(suggestions.alternatives.is_empty());
    assert!(suggestions.segment_probes <= limits.segment_probes);
    assert_eq!(original, words.analyze_word(&input).unwrap());
    // A successful final predicate must still retain distinct prefixes. Failed
    // suffix memoization cannot turn into a one-path segmentation shortcut.
    let input = format!("{prefix}봐요");
    let suggestions = suggest(&mut words, &mut dictionary, &input, 0, limits).unwrap();
    assert_eq!(suggestions.alternatives.len(), limits.alternatives);
    assert!(suggestions.limited_by.contains(&SpacingLimit::Alternatives));
    assert!(
        suggestions
            .alternatives
            .iter()
            .all(|h| h.records.last().unwrap().record.surface == "봐요")
    );
    assert_eq!(
        suggestions
            .alternatives
            .iter()
            .map(|h| &h.inserted_at)
            .collect::<BTreeSet<_>>()
            .len(),
        limits.alternatives
    );
    assert!(words.cached_bytes() <= 4096);
    assert!(dictionary.cache_bytes() <= 4096);
}
