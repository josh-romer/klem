//! Reviewed mappings for the viewer only; these do not license morphology.
use klem::MorphemeKind;
use klem::dictionary::{Dictionary, DictionarySession, EntrySummary, Result};
use serde::Deserialize;
use std::{collections::BTreeMap, sync::OnceLock};

#[derive(Deserialize)]
pub(super) struct Label {
    pub kind: MorphemeKind,
    pub sources: Vec<Source>,
}

#[derive(Deserialize)]
pub(super) struct Source {
    pub id: u64,
    pub headword: String,
    pub pos: String,
}

impl Source {
    fn matches(&self, entry: &EntrySummary) -> bool {
        entry.id == format!("krdict:{}", self.id)
            && entry.headword == self.headword
            && entry.pos == self.pos
    }
}

pub(super) fn catalog() -> &'static BTreeMap<String, Label> {
    static LABELS: OnceLock<BTreeMap<String, Label>> = OnceLock::new();
    LABELS.get_or_init(|| {
        serde_json::from_str(include_str!("../../../web/src/grammar-labels.json"))
            .expect("validated grammar label catalog")
    })
}

pub(super) fn entry_matches(kind: MorphemeKind, headword: &str, entry: &EntrySummary) -> bool {
    if catalog()
        .get(headword)
        .is_some_and(|label| label.kind != kind)
    {
        return false;
    }
    let pos = match kind {
        MorphemeKind::Particle => "조사",
        MorphemeKind::Suffix | MorphemeKind::Prefix => "접사",
        _ => "어미",
    };
    (entry.headword == headword && entry.pos == pos)
        || catalog().get(headword).is_some_and(|label| {
            label.kind == kind && label.sources.iter().any(|source| source.matches(entry))
        })
}

pub(super) fn lookup<D: Dictionary + ?Sized>(
    session: &mut DictionarySession<'_, D>,
    kind: MorphemeKind,
    headword: &str,
) -> Result<Vec<EntrySummary>> {
    let mut entries: Vec<_> = session
        .lookup(headword)?
        .iter()
        .filter(|entry| entry_matches(kind, headword, entry))
        .cloned()
        .collect();
    if let Some(label) = catalog().get(headword).filter(|label| label.kind == kind) {
        // Some engine components bundle several forms, or omit the space in a
        // dictionary expression. Only explicitly reviewed source IDs may cross
        // that boundary. Keep original dictionary headwords and POS values.
        for source in &label.sources {
            if source.headword == headword {
                continue;
            }
            for entry in session.lookup(&source.headword)?.iter() {
                if source.matches(entry) && !entries.iter().any(|e| e.id == entry.id) {
                    entries.push(entry.clone());
                }
            }
        }
    }
    Ok(entries)
}

/// A pair belongs to this construction only when consecutive in reading order.
pub(super) fn has_double_past(
    morphemes: &[klem::Morpheme],
    order: &[klem::breakdown::Component],
) -> bool {
    let past = |component: Option<&klem::breakdown::Component>| {
        let Some(klem::breakdown::Component::Morpheme(index)) = component else {
            return false;
        };
        morphemes
            .get(*index)
            .is_some_and(|m| m.kind == MorphemeKind::Prefinal && m.form == "었")
    };
    order.windows(2).enumerate().any(|(position, pair)| {
        past(pair.first())
            && past(pair.get(1))
            && !past(position.checked_sub(1).and_then(|i| order.get(i)))
            && !past(order.get(position + 2))
    })
}

/// Source-listed modal + literary assertion must be adjacent in this reading.
pub(super) fn has_literary_ri_assertion(
    morphemes: &[klem::Morpheme],
    order: &[klem::breakdown::Component],
) -> bool {
    order.windows(2).any(|pair| {
        let [
            klem::breakdown::Component::Morpheme(first),
            klem::breakdown::Component::Morpheme(second),
        ] = pair
        else {
            return false;
        };
        morphemes
            .get(*first)
            .is_some_and(|m| m.kind == MorphemeKind::Prefinal && m.form == "으리")
            && morphemes
                .get(*second)
                .is_some_and(|m| m.kind == MorphemeKind::Ending && m.form == "으니라")
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn literary_ri_assertion_requires_same_reading_adjacency_and_kinds() {
        use klem::breakdown::Component::{Lemma, Morpheme};
        let mut morphs = klem::Lemmatizer::new()
            .analyze_word("가리니라")
            .unwrap()
            .analyses
            .into_iter()
            .find(|a| {
                a.lemmas[0].text == "가다"
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(["으리", "으니라"])
            })
            .unwrap()
            .morphemes;
        let order = [Lemma(0), Morpheme(0), Morpheme(1)];
        assert!(has_literary_ri_assertion(&morphs, &order));
        assert!(!has_literary_ri_assertion(
            &morphs,
            &[Lemma(0), Morpheme(0), Lemma(1), Morpheme(1)]
        ));
        assert!(!has_literary_ri_assertion(
            &morphs,
            &[Lemma(0), Morpheme(1)]
        ));
        assert!(!has_literary_ri_assertion(
            &morphs,
            &[Lemma(0), Morpheme(1), Morpheme(0)]
        ));
        morphs[0].kind = MorphemeKind::Ending;
        assert!(!has_literary_ri_assertion(&morphs, &order));
        morphs[0].kind = MorphemeKind::Prefinal;
        morphs[1].kind = MorphemeKind::Prefinal;
        assert!(!has_literary_ri_assertion(&morphs, &order));
    }
    #[test]
    fn double_past_sources_require_exactly_two_adjacent_reading_components() {
        use klem::breakdown::Component::{Lemma, Morpheme};
        let mut morphs = klem::Lemmatizer::new()
            .analyze_word("먹었었다")
            .unwrap()
            .analyses
            .into_iter()
            .find(|a| a.lemmas[0].text == "먹다" && a.morphemes.len() == 3)
            .unwrap()
            .morphemes;
        assert!(has_double_past(
            &morphs,
            &[Lemma(0), Morpheme(0), Morpheme(1), Morpheme(2)]
        ));
        assert!(!has_double_past(
            &morphs,
            &[Lemma(0), Morpheme(0), Lemma(1), Morpheme(1), Morpheme(2)]
        ));
        assert!(!has_double_past(
            &morphs,
            &[Lemma(0), Morpheme(0), Morpheme(2)]
        ));
        morphs.push(morphs[0].clone());
        assert!(!has_double_past(
            &morphs,
            &[Lemma(0), Morpheme(0), Morpheme(1), Morpheme(3), Morpheme(2)]
        ));
        morphs[1].kind = MorphemeKind::Ending;
        assert!(!has_double_past(
            &morphs,
            &[Lemma(0), Morpheme(0), Morpheme(1), Morpheme(2)]
        ));
    }

    use klem::dictionary::{SqliteDictionary, import_krdict};
    use std::{fs, path::PathBuf};

    #[test]
    fn canonical_past_lookup_keeps_all_three_original_allomorph_entries() {
        let path = std::env::temp_dir().join(format!("klem-past-labels-{}.db", std::process::id()));
        struct Cleanup(PathBuf);
        impl Drop for Cleanup {
            fn drop(&mut self) {
                let _ = fs::remove_file(&self.0);
            }
        }
        let _cleanup = Cleanup(path.clone());
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-past-prefinal-english.json",
            )],
            &path,
            "past-allomorph-source-test",
        )
        .unwrap();
        let db = SqliteDictionary::open(path).unwrap();
        let mut session = DictionarySession::new(&db, 1024 * 1024);
        let sources = lookup(&mut session, MorphemeKind::Prefinal, "-었-").unwrap();
        assert_eq!(
            sources.iter().map(|e| e.id.as_str()).collect::<Vec<_>>(),
            ["krdict:68719", "krdict:66954", "krdict:68723"]
        );
        for source in &sources {
            let native = db.entry(&source.id).unwrap().unwrap();
            assert_eq!(native.senses.len(), 3);
            assert!(native.senses[2].definition.contains("미래"));
        }
        for kind in [
            MorphemeKind::Ending,
            MorphemeKind::Particle,
            MorphemeKind::Suffix,
            MorphemeKind::Prefix,
        ] {
            assert!(lookup(&mut session, kind, "-었-").unwrap().is_empty());
        }
    }

    #[test]
    fn every_label_source_resolves_from_the_attributed_offline_dictionary() {
        let path = std::env::temp_dir().join(format!("klem-labels-{}.db", std::process::id()));
        struct Cleanup(PathBuf);
        impl Drop for Cleanup {
            fn drop(&mut self) {
                let _ = fs::remove_file(&self.0);
            }
        }
        let _cleanup = Cleanup(path.clone());
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-grammar-labels.json"),
                PathBuf::from("tests/fixtures/krdict-reported-retrospective-labels.json"),
                PathBuf::from("tests/fixtures/krdict-gam-question-labels.json"),
                PathBuf::from("tests/fixtures/krdict-emphatic-ending-labels.json"),
                PathBuf::from("tests/fixtures/krdict-doeda-suffix-labels.json"),
                PathBuf::from("tests/fixtures/krdict-nominal-si-labels.json"),
                PathBuf::from("tests/fixtures/krdict-nominal-hwa-labels.json"),
                PathBuf::from("tests/fixtures/krdict-hada-suffix-labels.json"),
                PathBuf::from("tests/fixtures/krdict-ssik-english.json"),
                PathBuf::from("tests/fixtures/krdict-friendly-command-labels.json"),
                PathBuf::from("tests/fixtures/krdict-degree-expectation-labels.json"),
                PathBuf::from("tests/fixtures/krdict-deoniman-labels.json"),
                PathBuf::from("tests/fixtures/krdict-reported-command-deoni-english.json"),
                PathBuf::from("tests/fixtures/krdict-reported-dana-labels.json"),
                PathBuf::from("tests/fixtures/krdict-past-prefinal-labels.json"),
                PathBuf::from("tests/fixtures/krdict-double-past-prefinal-labels.json"),
                PathBuf::from("tests/fixtures/krdict-declarative-contrast-labels.json"),
                PathBuf::from("tests/fixtures/krdict-ostensible-reason-labels.json"),
                PathBuf::from("tests/fixtures/krdict-literary-question-go-labels.json"),
                PathBuf::from("tests/fixtures/krdict-literary-future-kko-labels.json"),
            ],
            &path,
            "grammar-label-source-test",
        )
        .unwrap();
        let dictionary = SqliteDictionary::open(path).unwrap();
        let mut session = DictionarySession::new(&dictionary, 1024 * 1024);
        for (key, label) in catalog() {
            let entries = lookup(&mut session, label.kind, key).unwrap();
            for source in &label.sources {
                let entry = dictionary
                    .entry(&format!("krdict:{}", source.id))
                    .unwrap()
                    .expect(key);
                assert!(source.matches(&entry.summary), "{key}: {}", source.id);
                assert!(!entry.senses.is_empty(), "{key}");
                assert!(
                    entries.iter().any(|e| source.matches(e)),
                    "{key}: {}",
                    source.id
                );
                if source.headword != *key || source.pos == "품사 없음" {
                    for kind in [
                        MorphemeKind::Particle,
                        MorphemeKind::Ending,
                        MorphemeKind::Suffix,
                        MorphemeKind::Prefix,
                        MorphemeKind::Prefinal,
                    ] {
                        if kind != label.kind {
                            assert!(!entry_matches(kind, key, &entry.summary), "{key}");
                        }
                    }
                    let mut wrong = entry.summary.clone();
                    wrong.id = "krdict:0".into();
                    assert!(!entry_matches(label.kind, key, &wrong), "{key}");
                    wrong = entry.summary.clone();
                    wrong.headword = "unreviewed spelling".into();
                    assert!(!entry_matches(label.kind, key, &wrong), "{key}");
                    wrong = entry.summary.clone();
                    wrong.pos = "명사".into();
                    assert!(!entry_matches(label.kind, key, &wrong), "{key}");
                }
            }
        }
        // Exact homonyms and component sources coexist. Mapping a bundled
        // form does not broaden lookup to arbitrary expressions or suffixes.
        assert!(
            lookup(&mut session, MorphemeKind::Ending, "-기는")
                .unwrap()
                .iter()
                .any(|e| e.id == "krdict:78756")
        );
        assert!(
            lookup(&mut session, MorphemeKind::Suffix, "-는데다가")
                .unwrap()
                .is_empty()
        );
        assert!(
            lookup(&mut session, MorphemeKind::Ending, "-없는표현")
                .unwrap()
                .is_empty()
        );
        // A primary research reference does not impersonate a KRDict entry.
        assert!(catalog()["-으리다"].sources.is_empty());
        assert!(
            lookup(&mut session, MorphemeKind::Ending, "-으리다")
                .unwrap()
                .is_empty()
        );
        for key in [
            "-사옵-",
            "-삽-",
            "-으옵시-",
            "-사옵시-",
            "-자옵-",
            "-잡-",
            "-자옵시-",
        ] {
            assert!(catalog()[key].sources.is_empty());
            assert!(
                lookup(&mut session, MorphemeKind::Prefinal, key)
                    .unwrap()
                    .is_empty()
            );
        }
        assert!(catalog()["-나이다"].sources.is_empty());
        assert!(
            lookup(&mut session, MorphemeKind::Ending, "-나이다")
                .unwrap()
                .is_empty()
        );
        assert!(catalog()["-나이까"].sources.is_empty());
        assert!(
            lookup(&mut session, MorphemeKind::Ending, "-나이까")
                .unwrap()
                .is_empty()
        );
        assert!(catalog()["-으리까"].sources.is_empty());
        assert!(
            lookup(&mut session, MorphemeKind::Ending, "-으리까")
                .unwrap()
                .is_empty()
        );
    }
}
