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

#[cfg(test)]
mod tests {
    use super::*;
    use klem::dictionary::{SqliteDictionary, import_krdict};
    use std::{fs, path::PathBuf};

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
