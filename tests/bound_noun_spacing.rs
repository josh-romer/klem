use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::spacing::{SpacingLimit, SpacingLimits, suggest};
use klem::{LemmaKind, Lemmatizer, Session};
use std::{path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "spacing.modifier_bound_noun";
struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> (SqliteDictionary, Self) {
        let path = std::env::temp_dir().join(format!(
            "klem-bound-spacing-{name}-{}.db",
            std::process::id()
        ));
        assert!(!path.exists());
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/bound-noun-spacing-native.json",
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
        serde_json::from_str(include_str!("fixtures/bound-noun-spacing-cases.json")).unwrap();
    assert_eq!(cases["cases"].as_array().unwrap().len(), 50);
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
                if expected.is_empty() {
                    assert!(hypotheses.is_empty(), "{}", case["id"]);
                }
                for spaced in expected {
                    assert!(hypotheses.iter().any(|h| h.spaced.nfc().collect::<String>() == spaced.as_str().unwrap()), "{} missing {}", case["id"], spaced);
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
fn child_search_cannot_exceed_shared_work_or_output_bounds() {
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
                segment_probes: 10,
                ..Default::default()
            },
            SpacingLimit::SegmentProbes,
        ),
        (
            SpacingLimits {
                alternatives: 1,
                ..Default::default()
            },
            SpacingLimit::Alternatives,
        ),
        (
            SpacingLimits {
                alternatives: 0,
                ..Default::default()
            },
            SpacingLimit::Alternatives,
        ),
    ] {
        let s = suggest(&mut words, &mut dictionary, "먹어줘볼것은", 10, limits).unwrap();
        assert!(!s.complete && s.limited_by.contains(&reason), "{s:?}");
        assert!(s.segment_probes <= limits.segment_probes);
        assert!(s.alternatives.len() <= limits.alternatives);
    }
}

#[test]
fn ordinary_or_unknown_nouns_cannot_borrow_a_reviewed_bound_noun_identity() {
    use klem::dictionary::{Dictionary, DictionaryMetadata, Entry, EntrySummary, Result};
    struct Provider<'a> {
        db: &'a SqliteDictionary,
        replacement: &'static str,
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
                if e.pos == "의존 명사" {
                    e.pos = self.replacement.into();
                }
            }
            Ok(entries)
        }
        fn entry(&self, id: &str) -> Result<Option<Entry>> {
            let mut e = self.db.entry(id)?;
            if let Some(e) = e.as_mut()
                && e.summary.pos == "의존 명사"
            {
                e.summary.pos = self.replacement.into();
            }
            Ok(e)
        }
    }
    let (db, _fixture) = Fixture::new("pos");
    for replacement in ["명사", "unreviewed"] {
        let provider = Provider {
            db: &db,
            replacement,
        };
        let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
        let mut dictionary = DictionarySession::new(&provider, 0);
        for word in ["먹어준것은", "공부하기때문에", "먹을수는"] {
            let s = suggest(
                &mut words,
                &mut dictionary,
                word,
                0,
                SpacingLimits::default(),
            )
            .unwrap();
            assert!(s.alternatives.iter().all(|h| h.rule != Some(RULE)));
        }
    }
}

#[test]
fn original_unmet_proposal_is_retained_beside_separately_reviewed_targets() {
    let original: serde_json::Value = serde_json::from_str(include_str!(
        "fixtures/predicate-auxiliary-spacing-owner-cases.json"
    ))
    .unwrap();
    let proposal: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/bound-noun-spacing-cases.json")).unwrap();
    assert_eq!(proposal["original_proposal"], original["cases"][9]);
    assert_eq!(
        proposal["original_proposal"]["required_space"],
        "먹어 준것은"
    );
    let (db, _fixture) = Fixture::new("original");
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 4096);
    let mut dictionary = DictionarySession::new(&db, 4096);
    let s = suggest(
        &mut words,
        &mut dictionary,
        "먹어준것은",
        0,
        SpacingLimits::default(),
    )
    .unwrap();
    assert!(!s.alternatives.iter().any(|h| h.spaced == "먹어 준것은"));
    assert!(s.alternatives.iter().any(|h| h.spaced == "먹어준 것은"));
    assert!(s.alternatives.iter().any(|h| h.spaced == "먹어 준 것은"));
}

#[test]
fn other_bound_noun_homonyms_cannot_supply_the_reviewed_entry_license() {
    use klem::dictionary::{Dictionary, DictionaryMetadata, Entry, EntrySummary, Result};
    struct OtherHomonyms<'a>(&'a SqliteDictionary);
    impl Dictionary for OtherHomonyms<'_> {
        fn metadata(&self) -> &DictionaryMetadata {
            self.0.metadata()
        }
        fn fingerprint(&self) -> &str {
            self.0.fingerprint()
        }
        fn lookup(&self, head: &str) -> Result<Vec<EntrySummary>> {
            Ok(self
                .0
                .lookup(head)?
                .into_iter()
                .filter(|e| e.id != "krdict:15615")
                .collect())
        }
        fn entry(&self, id: &str) -> Result<Option<Entry>> {
            if id == "krdict:15615" {
                Ok(None)
            } else {
                self.0.entry(id)
            }
        }
    }
    let (db, _fixture) = Fixture::new("homonyms");
    let provider = OtherHomonyms(&db);
    let remaining = provider.lookup("수").unwrap();
    assert!(remaining.iter().any(|e| e.pos == "의존 명사"));
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
    let mut dictionary = DictionarySession::new(&provider, 0);
    for word in ["먹은수는", "먹는수는", "먹을수는"] {
        let s = suggest(
            &mut words,
            &mut dictionary,
            word,
            0,
            SpacingLimits::default(),
        )
        .unwrap();
        assert!(
            s.alternatives.iter().all(|h| h.rule != Some(RULE)),
            "{word}"
        );
    }
}
