//! Recorded lexical identity remains separate from exhaustive grammar candidates.
use klem::dictionary::{
    DictionaryFilter, DictionarySession, OriginRelation, SqliteDictionary, import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{fs, path::PathBuf, sync::OnceLock};
use unicode_normalization::UnicodeNormalization;

fn source() -> &'static Value {
    static DATA: OnceLock<Value> = OnceLock::new();
    DATA.get_or_init(|| {
        serde_json::from_str(include_str!("fixtures/doeda-identity-sources.json")).unwrap()
    })
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-doeda-identity-{tag}-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict-doeda-native.json")],
            &path,
            "identity-source-test",
        )
        .unwrap();
        Self(path)
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

fn split(word: &WordAnalysis, head: &Value, variant: &Value) -> usize {
    word.analyses
        .iter()
        .position(|a| {
            a.lemmas[0].text == head["base"].as_str().unwrap()
                && a.lemmas[0].kind == LemmaKind::Nominal
                && a.rules.iter().any(|r| r == "suffix.verb.doeda")
                && a.morphemes[0].form == "되다"
                && a.morphemes
                    .iter()
                    .skip(1)
                    .map(|m| m.form.as_str())
                    .eq(variant["morphemes"]
                        .as_array()
                        .unwrap()
                        .iter()
                        .map(|v| v.as_str().unwrap()))
        })
        .expect("source-owned split")
}

#[test]
fn every_recorded_pair_and_matching_alternative_has_its_own_identity_in_unicode() {
    let fixture = Fixture::new("all");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4 * 1024 * 1024);
    let engine = Lemmatizer::new();
    let mut differences = 0;
    for head in source()["heads"].as_array().unwrap() {
        for variant in source()["variants"].as_array().unwrap() {
            let surface = format!(
                "{}{}",
                head["base"].as_str().unwrap(),
                variant["tail"].as_str().unwrap()
            );
            for text in [surface.clone(), surface.nfd().collect()] {
                let raw = engine.analyze_word(&text).unwrap();
                let i = split(&raw, head, variant);
                let annotation = dictionary.annotate(&raw).unwrap();
                let assessed = &annotation.readings[i].lemmas[0];
                for expected in head["base_entries"].as_array().unwrap() {
                    let entry = assessed
                        .entries
                        .iter()
                        .find(|e| e.id == expected["entry_id"].as_str().unwrap())
                        .unwrap();
                    let identity = entry.derivational_identity.as_ref().unwrap();
                    assert_eq!(
                        serde_json::to_value(identity.relation).unwrap(),
                        expected["relation"]
                    );
                    assert_eq!(identity.morpheme_index, 0);
                    assert_eq!(
                        serde_json::to_value(&identity.expected_origins).unwrap(),
                        head["expected_origins"]
                    );
                    assert_eq!(
                        serde_json::to_value(&identity.whole_entries).unwrap(),
                        head["whole_entries"]
                    );
                    assert_eq!(
                        identity.whole_origins_complete,
                        head["whole_origins_complete"].as_bool().unwrap()
                    );
                    // Recorded differences are not independent grammar judgments.
                    assert!(entry.conflicts.is_empty(), "{}", entry.id);
                    if identity.relation == OriginRelation::RecordedDifference {
                        differences += 1;
                    }
                }
                assert!(
                    annotation.readings[i]
                        .lemmas
                        .iter()
                        .skip(1)
                        .flat_map(|l| &l.entries)
                        .all(|e| e.derivational_identity.is_none())
                );
                for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                    let mut filtered = raw.clone();
                    let mut native = annotation.clone();
                    native.filter(&mut filtered, mode);
                    assert!(
                        filtered.analyses.contains(&raw.analyses[i]),
                        "{surface}: {mode:?}"
                    );
                }
            }
        }
    }
    assert_eq!(differences, 232 * 10 * 2);
}

#[test]
fn lazy_origin_upgrade_respects_cache_budgets_and_does_not_annotate_plain_nouns() {
    let fixture = Fixture::new("cache");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    for budget in [0, 1, 1024, 4 * 1024 * 1024] {
        let mut dictionary = DictionarySession::new(&db, budget);
        for head in source()["heads"].as_array().unwrap() {
            let base = head["base"].as_str().unwrap();
            dictionary.lookup(base).unwrap();
            let derived = engine.analyze_word(&format!("{base}되었다")).unwrap();
            let first = dictionary.annotate(&derived).unwrap();
            assert_eq!(first, dictionary.annotate(&derived).unwrap());
            assert!(dictionary.cache_bytes() <= budget);
            for surface in [base.to_owned(), format!("{base}은")] {
                let ordinary = engine.analyze_word(&surface).unwrap();
                let native = dictionary.annotate(&ordinary).unwrap();
                assert!(
                    native
                        .readings
                        .iter()
                        .flat_map(|r| &r.lemmas)
                        .flat_map(|l| &l.entries)
                        .all(|e| e.derivational_identity.is_none())
                );
                assert!(
                    native
                        .lemmas
                        .iter()
                        .filter(|s| s.lemma.kind == LemmaKind::Nominal)
                        .flat_map(|s| &s.entries)
                        .all(|e| e.origins.is_none())
                );
            }
        }
    }
}

#[test]
fn missing_origins_and_legacy_annotations_remain_inconclusive() {
    let fixture = Fixture::new("unknown");
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let word = engine.analyze_word("반감됐다").unwrap();
    let index = word
        .analyses
        .iter()
        .position(|a| {
            a.lemmas[0].text == "반감" && a.rules.iter().any(|r| r == "suffix.verb.doeda")
        })
        .unwrap();
    let path: &Analysis = &word.analyses[index];
    let annotation = dictionary.annotate(&word).unwrap();
    let original = annotation.readings[index].clone();
    assert_eq!(
        original.lemmas[0].entries[0]
            .derivational_identity
            .as_ref()
            .unwrap()
            .relation,
        OriginRelation::RecordedDifference
    );
    for origins in [None, Some(Vec::new())] {
        let mut sparse = annotation.clone();
        let slot = sparse
            .lemmas
            .iter_mut()
            .find(|s| s.lemma == path.lemmas[0])
            .unwrap();
        slot.entries[0].origins = origins;
        let assessed = sparse.assess(path);
        assert_eq!(assessed.status, original.status);
        assert_eq!(
            assessed.lemmas[0].entries[0]
                .derivational_identity
                .as_ref()
                .unwrap()
                .relation,
            OriginRelation::Unknown
        );
    }
    let mut mixed = annotation.clone();
    mixed
        .lemmas
        .iter_mut()
        .find(|s| s.lemma == path.lemmas[0])
        .unwrap()
        .entries[0]
        .origins = Some(vec!["反感".into(), "半減".into()]);
    assert_eq!(
        mixed.assess(path).lemmas[0].entries[0]
            .derivational_identity
            .as_ref()
            .unwrap()
            .relation,
        OriginRelation::RecordedMatch
    );
    let legacy: klem::dictionary::EntryAssessment = serde_json::from_value(
        serde_json::json!({"id":"legacy", "status":"unknown", "conflicts":[]}),
    )
    .unwrap();
    assert!(legacy.derivational_identity.is_none());
}
