use klem::dictionary::{DictionarySession, ProperNameDictionary, SqliteDictionary, import_krdict};
use klem::spacing::{SpacingLimits, suggest};
use klem::{Lemmatizer, Session};
use std::{path::PathBuf, sync::Arc};
use unicode_normalization::UnicodeNormalization;

const RULE: &str = "spacing.proper_name_title";
struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}
fn fixture(tag: &str) -> (SqliteDictionary, Cleanup) {
    let path =
        std::env::temp_dir().join(format!("klem-named-title-{tag}-{}.db", std::process::id()));
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/possessive-bound-noun-native.json",
        )],
        &path,
        "named-title-source",
    )
    .unwrap();
    (SqliteDictionary::open(&path).unwrap(), Cleanup(path))
}

#[test]
fn actual_novel_honorific_case_and_independent_title_particles_retain_exact_name_witnesses() {
    let (db, _cleanup) = fixture("cases");
    let dictionary = ProperNameDictionary::new(db);
    for cache in [0, 4096] {
        let mut words = Session::new(Arc::new(Lemmatizer::new()), cache);
        let mut lookup = DictionarySession::new(&dictionary, cache);
        for (surface, expected) in [
            ("박선생님께서", "박 선생님께서"),
            ("박선생님", "박 선생님"),
            ("박선생님께", "박 선생님께"),
            ("박선생님의", "박 선생님의"),
            ("박선생님을", "박 선생님을"),
        ] {
            for surface in [surface.to_owned(), surface.nfd().collect::<String>()] {
                let original = words.analyze_word(&surface).unwrap();
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
                assert_eq!(h.records.len(), 2);
                assert_eq!(
                    h.records[0].entry_witnesses,
                    ["ud-ko-kaist:proper-name:park"]
                );
                assert_eq!(h.records[1].entry_witnesses, ["krdict:62818"]);
                for segment in &h.records {
                    assert_eq!(&text[segment.record.span.clone()], segment.record.surface);
                    assert!(segment.breakdowns.iter().all(Option::is_some));
                }
                assert_eq!(h.inserted_at, [h.records[1].record.span.start]);
                assert_eq!(words.analyze_word(&surface).unwrap(), original);
            }
        }
    }
    assert!(klem::rule_explanation(RULE).is_some());
}

#[test]
fn same_head_gourd_and_unreviewed_names_or_titles_cannot_supply_the_named_title() {
    let (db, _cleanup) = fixture("boundaries");
    let mut words = Session::new(Arc::new(Lemmatizer::new()), 0);
    let mut plain = DictionarySession::new(&db, 0);
    assert!(
        !suggest(
            &mut words,
            &mut plain,
            "박선생님께서",
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
    for surface in ["김선생님께서", "박친구께서", "박의원께서", "박선생님것"] {
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
    let result = suggest(
        &mut words,
        &mut lookup,
        "박선생님것",
        0,
        SpacingLimits::default(),
    )
    .unwrap();
    assert!(
        result
            .alternatives
            .iter()
            .any(|h| h.rule == Some("spacing.proper_name_title_possession")
                && h.spaced == "박 선생님 것")
    );
}
