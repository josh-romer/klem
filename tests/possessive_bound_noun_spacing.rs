use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::spacing::{SpacingLimit, SpacingLimits, suggest};
use klem::{LemmaKind, Lemmatizer, Session};
use std::{path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "spacing.nominal_bound_noun";
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> (SqliteDictionary, Self) {
        let path = std::env::temp_dir().join(format!(
            "klem-possessive-spacing-{name}-{}.db",
            std::process::id()
        ));
        assert!(!path.exists());
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/possessive-bound-noun-native.json",
            )],
            &path,
            "source-backed-bound-nouns",
        )
        .unwrap();
        (SqliteDictionary::open(&path).unwrap(), Self(path))
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn reviewed_profiles_preserve_independent_readings_unicode_and_prefix_witnesses() {
    let (db, _fixture) = Fixture::new("profiles");
    let cases: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/possessive-bound-noun-cases.json")).unwrap();
    assert_eq!(cases["cases"].as_array().unwrap().len(), 42);
    for cache in [0, 4096] {
        let engine = Arc::new(Lemmatizer::new());
        let mut words = Session::new(engine, cache);
        let mut dictionary = DictionarySession::new(&db, cache);
        for case in cases["cases"].as_array().unwrap() {
            let canonical = case["surface"].as_str().unwrap();
            for surface in [canonical.to_owned(), canonical.nfd().collect()] {
                let original = words.analyze_word(&surface).unwrap();
                let prefix = "前🙂「";
                let text = format!("{prefix}{surface}」");
                let result = suggest(
                    &mut words,
                    &mut dictionary,
                    &surface,
                    prefix.len(),
                    SpacingLimits::default(),
                )
                .unwrap();
                assert!(result.complete, "{}: {:?}", case["id"], result.limited_by);
                let hypotheses: Vec<_> = result
                    .alternatives
                    .iter()
                    .filter(|h| h.rule == Some(RULE))
                    .collect();
                let expected = case["required_spaces"].as_array().unwrap();
                if expected.is_empty()
                    && !case["allow_other_spacing_hypotheses"]
                        .as_bool()
                        .unwrap_or(false)
                {
                    assert!(hypotheses.is_empty(), "{}", case["id"]);
                }
                if let Some(forbidden) = case["forbidden_spaces"].as_array() {
                    for spaced in forbidden {
                        assert!(
                            !hypotheses
                                .iter()
                                .any(|h| h.spaced.nfc().collect::<String>()
                                    == spaced.as_str().unwrap()),
                            "{} forbidden {}",
                            case["id"],
                            spaced
                        );
                    }
                }
                for spaced in expected {
                    let found = hypotheses
                        .iter()
                        .any(|h| h.spaced.nfc().collect::<String>() == spaced.as_str().unwrap());
                    if case["known_unmet"].as_bool().unwrap_or(false) {
                        assert_eq!(case["id"], "surname-teacher");
                        assert!(
                            !found,
                            "unrelated gourd/night identities cannot certify the surname"
                        );
                    } else {
                        assert!(found, "{} missing {}", case["id"], spaced);
                    }
                }
                for h in hypotheses {
                    assert!(klem::rule_explanation(RULE).is_some());
                    assert_eq!(
                        h.records
                            .iter()
                            .map(|s| s.record.surface.as_str())
                            .collect::<String>(),
                        surface
                    );
                    assert_eq!(
                        h.inserted_at,
                        h.records
                            .iter()
                            .skip(1)
                            .map(|s| s.record.span.start)
                            .collect::<Vec<_>>()
                    );
                    let mut cursor = prefix.len();
                    for segment in &h.records {
                        assert_eq!(segment.record.span.start, cursor);
                        assert_eq!(&text[segment.record.span.clone()], segment.record.surface);
                        cursor = segment.record.span.end;
                    }
                    assert_eq!(cursor, prefix.len() + surface.len());
                    for segment in h.records.iter().chain(&h.joined_contexts) {
                        assert_eq!(&text[segment.record.span.clone()], segment.record.surface);
                        let mut raw = words
                            .analyze_word(&segment.record.surface)
                            .unwrap()
                            .as_ref()
                            .clone();
                        let mut annotated = dictionary.annotate(&raw).unwrap();
                        annotated.filter(&mut raw, DictionaryFilter::Compatible);
                        assert!(
                            segment
                                .record
                                .analysis
                                .as_ref()
                                .unwrap()
                                .analyses
                                .iter()
                                .all(|a| raw.analyses.contains(a))
                        );
                        assert!(segment.breakdowns.iter().all(Option::is_some));
                    }
                    for context in &h.joined_contexts {
                        assert!(
                            context.record.span.end < prefix.len() + surface.len(),
                            "auxiliary witness must stop before the noun"
                        );
                        assert!(
                            context
                                .record
                                .analysis
                                .as_ref()
                                .unwrap()
                                .analyses
                                .iter()
                                .all(|a| a.lemmas.iter().any(|l| l.kind == LemmaKind::Auxiliary))
                        );
                    }
                }
                assert_eq!(words.analyze_word(&surface).unwrap(), original);
                assert!(words.cached_bytes() <= cache && dictionary.cache_bytes() <= cache);
            }
        }
    }
}

#[test]
fn nominal_phrases_obey_shared_limits_and_report_truncation() {
    let (db, _fixture) = Fixture::new("limits");
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
    let mut dictionary = DictionarySession::new(&db, 0);
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
                segment_probes: 3,
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
        let result = suggest(&mut words, &mut dictionary, "가족때문에", 10, limits).unwrap();
        assert!(
            !result.complete && result.limited_by.contains(&reason),
            "{result:?}"
        );
        assert!(result.segment_probes <= limits.segment_probes);
        assert!(result.alternatives.len() <= limits.alternatives);
    }
    let stress = format!("{}미등록어때문에", "가족".repeat(20));
    let result = suggest(
        &mut words,
        &mut dictionary,
        &stress,
        0,
        SpacingLimits::default(),
    )
    .unwrap();
    assert!(result.segment_probes <= 256 && result.alternatives.len() <= 16);
}

#[test]
fn source_identity_and_known_pos_are_required_for_both_sides() {
    use klem::dictionary::{Dictionary, DictionaryMetadata, Entry, EntrySummary, Result};
    struct Provider<'a> {
        db: &'a SqliteDictionary,
        mode: u8,
    }
    impl Dictionary for Provider<'_> {
        fn metadata(&self) -> &DictionaryMetadata {
            self.db.metadata()
        }
        fn fingerprint(&self) -> &str {
            self.db.fingerprint()
        }
        fn lookup(&self, head: &str) -> Result<Vec<EntrySummary>> {
            let mut entries = self.db.lookup(head)?;
            for e in &mut entries {
                if matches!(head, "것" | "때문") {
                    match self.mode {
                        0 => e.pos = "명사".into(),
                        1 => e.pos = "unreviewed".into(),
                        2 => e.id = format!("other:{}", e.id),
                        _ => {}
                    }
                } else if self.mode == 3 {
                    e.pos = "unreviewed".into();
                }
            }
            Ok(entries)
        }
        fn entry(&self, id: &str) -> Result<Option<Entry>> {
            self.db.entry(id)
        }
    }
    let (db, _fixture) = Fixture::new("provider");
    for mode in 0..4 {
        let provider = Provider { db: &db, mode };
        let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
        let mut dictionary = DictionarySession::new(&provider, 0);
        for word in ["내것은", "친구것", "건강때문에", "아버지건강때문에"] {
            let result = suggest(
                &mut words,
                &mut dictionary,
                word,
                0,
                SpacingLimits::default(),
            )
            .unwrap();
            assert!(
                result.alternatives.iter().all(|h| h.rule != Some(RULE)),
                "mode {mode}, {word}"
            );
        }
    }
}
