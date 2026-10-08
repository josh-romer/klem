use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, ProperNameDictionary, SqliteDictionary,
    import_krdict,
};
use klem::spacing::{SpacingLimit, SpacingLimits, suggest};
use klem::{Lemmatizer, Session};
use std::{path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "spacing.proper_name_title_possession";
const PARK: &str = "ud-ko-kaist:proper-name:park";
struct Fixture(PathBuf);
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
fn fixture(tag: &str) -> (SqliteDictionary, Fixture) {
    let path =
        std::env::temp_dir().join(format!("klem-proper-name-{tag}-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/possessive-bound-noun-native.json",
        )],
        &path,
        "proper-name-regression",
    )
    .unwrap();
    (SqliteDictionary::open(&path).unwrap(), Fixture(path))
}

#[test]
fn corpus_identity_preserves_native_homonyms_and_complete_original_training_contexts() {
    let (db, _cleanup) = fixture("identity");
    let before = db.lookup("박").unwrap();
    let fingerprint = db.fingerprint().to_owned();
    let dictionary = ProperNameDictionary::new(db);
    let after = dictionary.lookup("박").unwrap();
    assert_eq!(
        after
            .iter()
            .filter(|e| e.id != PARK)
            .cloned()
            .collect::<Vec<_>>(),
        before
    );
    let entry = dictionary.entry(PARK).unwrap().unwrap();
    assert_eq!(entry.summary.pos, "PROPN");
    assert!(entry.origins.is_empty(), "POS tags are not lexical origins");
    assert!(entry.notes.iter().any(|note| note == "Original XPOS: nq"));
    assert_eq!(entry.senses.len(), 5);
    let preserved: serde_json::Value = serde_json::from_slice(&{
        use std::io::Read;
        let mut bytes = Vec::new();
        // The source lexicon embeds the preparation's complete sentences verbatim.
        std::fs::File::open("src/dictionary/proper_names.json")
            .unwrap()
            .read_to_end(&mut bytes)
            .unwrap();
        bytes
    })
    .unwrap();
    for (sense, observation) in entry
        .senses
        .iter()
        .zip(preserved["names"][0]["observations"].as_array().unwrap())
    {
        assert_eq!(sense.id, observation["id"].as_str().unwrap());
        assert_eq!(
            sense.examples[0][0],
            observation["complete_original_sentence"].as_str().unwrap()
        );
        let row = observation["original_row"].as_array().unwrap();
        assert_eq!(row[3], "PROPN");
        assert_eq!(row[4], "nq");
        assert_eq!(observation["source_partition"], "train");
        let original = row
            .iter()
            .map(|v| v.as_str().unwrap())
            .collect::<Vec<_>>()
            .join("\t");
        assert!(sense.examples[0][0].lines().any(|line| line == original));
    }
    assert_eq!(dictionary.metadata().supplements[0].license, "CC BY-SA 4.0");
    let projection = serde_json::to_value([&entry]).unwrap();
    use sha2::{Digest, Sha256};
    let projection_sha256 = format!(
        "{:x}",
        Sha256::digest(serde_json::to_vec(&projection).unwrap())
    );
    assert_eq!(
        dictionary.metadata().supplements[0].projection_sha256,
        projection_sha256
    );
    assert_eq!(
        dictionary.fingerprint(),
        format!(
            "{:x}",
            Sha256::digest(format!(
                "{fingerprint}:{}:{projection_sha256}",
                dictionary.metadata().supplements[0].sha256
            ))
        )
    );
    assert_ne!(dictionary.fingerprint(), fingerprint);
    assert_eq!(dictionary.lookup("박 ").unwrap(), Vec::new());
    assert_eq!(
        dictionary.lookup(&"박".nfd().collect::<String>()).unwrap(),
        after
    );
}

#[test]
fn original_requirement_and_inflections_have_exact_witnesses_and_original_utf8_offsets() {
    let (db, _cleanup) = fixture("spacing");
    let dictionary = ProperNameDictionary::new(db);
    for cache in [0, 4096] {
        let mut words = Session::new(Arc::new(Lemmatizer::new()), cache);
        let mut lookup = DictionarySession::new(&dictionary, cache);
        for (surface, expected) in [
            ("박선생님것", "박 선생님 것"),
            ("박선생님것이", "박 선생님 것이"),
            ("박선생님것이다", "박 선생님 것이다"),
            ("박선생님의것", "박 선생님의 것"),
        ] {
            for surface in [surface.to_owned(), surface.nfd().collect::<String>()] {
                let before = words.analyze_word(&surface).unwrap();
                let prefix = "前🙂「";
                let text = format!("{prefix}{surface}」");
                let result = suggest(
                    &mut words,
                    &mut lookup,
                    &surface,
                    prefix.len(),
                    SpacingLimits::default(),
                )
                .unwrap();
                assert!(result.complete, "{surface}: {:?}", result.limited_by);
                let h = result
                    .alternatives
                    .iter()
                    .find(|h| {
                        h.rule == Some(RULE) && h.spaced.nfc().collect::<String>() == expected
                    })
                    .unwrap_or_else(|| panic!("missing {expected}: {result:?}"));
                assert_eq!(h.records.len(), 3);
                assert_eq!(h.records[0].entry_witnesses, [PARK]);
                assert_eq!(h.records[1].entry_witnesses, ["krdict:62818"]);
                assert!(
                    h.records[0].dictionary.lemmas[0]
                        .entries
                        .iter()
                        .any(|e| e.entry.id == "krdict:57518")
                );
                let mut cursor = prefix.len();
                for segment in &h.records {
                    assert_eq!(segment.record.span.start, cursor);
                    assert_eq!(&text[segment.record.span.clone()], segment.record.surface);
                    cursor = segment.record.span.end;
                    for filter in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                        let mut raw = words
                            .analyze_word(&segment.record.surface)
                            .unwrap()
                            .as_ref()
                            .clone();
                        let mut annotation = lookup.annotate(&raw).unwrap();
                        annotation.filter(&mut raw, filter);
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
                    }
                    assert!(segment.breakdowns.iter().all(Option::is_some));
                }
                assert_eq!(cursor, prefix.len() + surface.len());
                assert_eq!(
                    h.inserted_at,
                    h.records
                        .iter()
                        .skip(1)
                        .map(|s| s.record.span.start)
                        .collect::<Vec<_>>()
                );
                assert_eq!(words.analyze_word(&surface).unwrap(), before);
                assert!(klem::rule_explanation(RULE).is_some());
            }
        }
    }
}

#[test]
fn unrelated_homonyms_unknown_names_and_unlisted_templates_cannot_supply_witnesses() {
    let (db, _cleanup) = fixture("boundaries");
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
    let mut lookup = DictionarySession::new(&db, 0);
    assert!(
        !suggest(
            &mut words,
            &mut lookup,
            "박선생님것",
            0,
            SpacingLimits::default()
        )
        .unwrap()
        .alternatives
        .iter()
        .any(|h| h.rule == Some(RULE))
    );
    let dictionary = ProperNameDictionary::new(db);
    let mut lookup = DictionarySession::new(&dictionary, 0);
    for surface in [
        "김선생님것",
        "박친구것",
        "박의원것",
        "박선생님때문에",
        "박선생님일",
        "박선생님들것",
    ] {
        assert!(
            !suggest(
                &mut words,
                &mut lookup,
                surface,
                0,
                SpacingLimits::default()
            )
            .unwrap()
            .alternatives
            .iter()
            .any(|h| h.rule == Some(RULE)),
            "{surface}"
        );
    }
    for (limits, expected) in [
        (
            SpacingLimits {
                segment_probes: 0,
                ..SpacingLimits::default()
            },
            SpacingLimit::SegmentProbes,
        ),
        (
            SpacingLimits {
                alternatives: 0,
                ..SpacingLimits::default()
            },
            SpacingLimit::Alternatives,
        ),
        (
            SpacingLimits {
                token_chars: 2,
                ..SpacingLimits::default()
            },
            SpacingLimit::TokenChars,
        ),
    ] {
        let result = suggest(&mut words, &mut lookup, "박선생님것", 0, limits).unwrap();
        assert!(!result.complete);
        assert!(result.limited_by.contains(&expected));
    }
}

#[test]
fn cli_opt_in_preserves_plain_dictionary_results_and_supplies_spacing_under_both_filters() {
    let (_db, cleanup) = fixture("cli");
    for mode in [None, Some("--dict-only"), Some("--dict-compatible")] {
        let mut args = vec![
            "word",
            "박선생님것",
            "--dictionary",
            cleanup.0.to_str().unwrap(),
            "--suggest-spacing",
        ];
        if let Some(mode) = mode {
            args.push(mode);
        }
        let run = |args: &[&str]| {
            let output = std::process::Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(args)
                .output()
                .unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            serde_json::from_slice::<serde_json::Value>(&output.stdout).unwrap()
        };
        let plain = run(&args);
        args.push("--proper-names");
        let supplemented = run(&args);
        assert_eq!(plain["analyses"], supplemented["analyses"]);
        assert!(
            !plain["spacing"]["alternatives"]
                .as_array()
                .unwrap()
                .iter()
                .any(|h| h["rule"] == RULE)
        );
        assert!(
            supplemented["spacing"]["alternatives"]
                .as_array()
                .unwrap()
                .iter()
                .any(|h| h["rule"] == RULE && h["spaced"] == "박 선생님 것")
        );
    }
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_klem"))
        .args(["word", "박", "--proper-names"])
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(String::from_utf8_lossy(&output.stderr).contains("requires --dictionary"));
}
