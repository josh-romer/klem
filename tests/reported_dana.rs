//! Source judgments stay separate from contextual sense and speculative paths.
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn every_source_judgment_and_authored_boundary_is_tracked() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/reported-dana-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.required_total, 36);
    assert_eq!(report.forbidden_total, 6);
}

#[test]
fn source_paths_preserve_every_prior_candidate_and_have_exact_report_companions() {
    let capture: Value =
        serde_json::from_str(include_str!("fixtures/reported-dana-source-captures.json")).unwrap();
    let engine = Lemmatizer::new();
    assert_eq!(capture["words"].as_object().unwrap().len(), 26);
    let mut additions = 0;
    for (word, row) in capture["words"].as_object().unwrap() {
        let before: WordAnalysis = serde_json::from_value(row["before"].clone()).unwrap();
        let parent: WordAnalysis = serde_json::from_value(
            capture["actual_prior_companions"][row["parent_surface"].as_str().unwrap()].clone(),
        )
        .unwrap();
        let now = engine.analyze_word(word).unwrap();
        assert_eq!(
            now,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
        assert_eq!(
            now.analyses
                .iter()
                .filter(|a| before.analyses.contains(a))
                .cloned()
                .collect::<Vec<_>>(),
            before.analyses,
            "{word}"
        );
        for path in now.analyses.iter().filter(|a| !before.analyses.contains(a)) {
            additions += 1;
            assert!(path.rules.iter().any(|r| r == "ending.reported_dana"));
            assert!(path.breakdown().is_some(), "{word}: {path:?}");
            assert!(
                path.rules
                    .iter()
                    .all(|r| klem::rule_explanation(r).is_some())
            );
            let mut inverse: Analysis = path.clone();
            inverse.rules.retain(|r| r != "ending.reported_dana");
            let endings: Vec<_> = inverse
                .morphemes
                .iter_mut()
                .filter(|m| matches!(m.form.as_str(), "다나" | "는다나"))
                .collect();
            assert_eq!(endings.len(), 1);
            for ending in endings {
                ending.form = if ending.form == "다나" {
                    "다고"
                } else {
                    "는다고"
                }
                .into();
            }
            assert!(parent.analyses.contains(&inverse), "{word}: {inverse:?}");
        }
    }
    assert_eq!(additions, 84);
}

fn dictionary(name: &str) -> (klem::dictionary::SqliteDictionary, Cleanup) {
    use klem::dictionary::{SqliteDictionary, import_krdict};
    let path = std::env::temp_dir().join(format!(
        "klem-reported-dana-{name}-{}.db",
        std::process::id()
    ));
    import_krdict(
        &[std::path::PathBuf::from(
            "tests/fixtures/krdict-reported-dana-english.json",
        )],
        &path,
        "reported-dana-source",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    (db, Cleanup(path))
}
struct Cleanup(std::path::PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

#[test]
fn every_native_owner_retains_all_notes_examples_forms_and_english_senses() {
    use klem::dictionary::Dictionary;
    let expected: Value =
        serde_json::from_str(include_str!("fixtures/reported-dana-native.json")).unwrap();
    assert_eq!(expected.as_object().unwrap().len(), 73);
    let (db, _cleanup) = dictionary("native");
    for (id, original) in expected.as_object().unwrap() {
        let mut english = original.clone();
        for sense in english["senses"].as_array_mut().unwrap() {
            sense["translations"]
                .as_array_mut()
                .unwrap()
                .retain(|t| t["language"] == "영어");
        }
        assert_eq!(
            serde_json::to_value(db.entry(id).unwrap().unwrap()).unwrap(),
            english,
            "{id}"
        );
    }
}

#[test]
fn dictionary_classes_belong_to_the_report_owner_and_keep_unlisted_slots_unknown() {
    use klem::dictionary::{Compatibility, DictionarySession};
    let (db, _cleanup) = dictionary("policy");
    let mut session = DictionarySession::new(&db, 1048576);
    let engine = Lemmatizer::new();
    for (word, heads, forms, owner, expected) in [
        (
            "먹는다나",
            vec!["먹다"],
            vec!["는다나"],
            0,
            Compatibility::Compatible,
        ),
        (
            "먹다나",
            vec!["먹다"],
            vec!["다나"],
            0,
            Compatibility::Incompatible,
        ),
        (
            "먹었다나",
            vec!["먹다"],
            vec!["었", "다나"],
            0,
            Compatibility::Compatible,
        ),
        (
            "먹겠다나",
            vec!["먹다"],
            vec!["겠", "다나"],
            0,
            Compatibility::Compatible,
        ),
        (
            "먹으신다나",
            vec!["먹다"],
            vec!["시", "는다나"],
            0,
            Compatibility::Compatible,
        ),
        (
            "먹으시다나",
            vec!["먹다"],
            vec!["시", "다나"],
            0,
            Compatibility::Unknown,
        ),
        (
            "예쁘다나",
            vec!["예쁘다"],
            vec!["다나"],
            0,
            Compatibility::Compatible,
        ),
        (
            "예쁜다나",
            vec!["예쁘다"],
            vec!["는다나"],
            0,
            Compatibility::Incompatible,
        ),
        (
            "학생이다나",
            vec!["학생", "이다"],
            vec!["다나"],
            1,
            Compatibility::Unknown,
        ),
        (
            "학생답다나",
            vec!["학생"],
            vec!["답다", "다나"],
            0,
            Compatibility::Compatible,
        ),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let annotated = session.annotate(&result).unwrap();
        let indices: Vec<_> = result
            .analyses
            .iter()
            .enumerate()
            .filter(|(_, p)| {
                p.rules.iter().any(|r| r == "ending.reported_dana")
                    && p.lemmas
                        .iter()
                        .map(|l| l.text.as_str())
                        .eq(heads.iter().copied())
                    && p.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .map(|(i, _)| i)
            .collect();
        assert!(!indices.is_empty(), "{word}: {result:?}");
        for index in indices {
            assert_eq!(
                annotated.readings[index].lemmas[owner].status, expected,
                "{word}: {:?}",
                annotated.readings[index]
            );
        }
    }
}

#[test]
fn present_report_allomorph_excludes_copulas_and_derived_adjectives_but_assesses_external_paths() {
    use klem::dictionary::{Compatibility, DictionarySession};
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("external-policy");
    let mut session = DictionarySession::new(&db, 1048576);
    for (absent_word, plain_word, heads, forms, owner) in [
        (
            "학생인다나",
            "학생이다나",
            vec!["학생", "이다"],
            vec!["다나"],
            1,
        ),
        (
            "학생답는다나",
            "학생답다나",
            vec!["학생"],
            vec!["답다", "다나"],
            0,
        ),
    ] {
        let absent = engine.analyze_word(absent_word).unwrap();
        assert!(
            !absent.analyses.iter().any(|p| p
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(heads.iter().copied())
                && p.morphemes.iter().any(|m| m.form == "는다나")),
            "{absent_word}"
        );
        // Assess a caller-supplied hypothesis independently of generation.
        let plain = engine.analyze_word(plain_word).unwrap();
        let mut supplied = plain
            .analyses
            .into_iter()
            .find(|p| {
                p.rules.iter().any(|r| r == "ending.reported_dana")
                    && p.lemmas
                        .iter()
                        .map(|l| l.text.as_str())
                        .eq(heads.iter().copied())
                    && p.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
            })
            .unwrap();
        supplied.morphemes.last_mut().unwrap().form = "는다나".into();
        let response = session
            .annotate(&WordAnalysis {
                normalized: absent_word.into(),
                analyses: vec![supplied],
            })
            .unwrap();
        assert_eq!(
            response.readings[0].lemmas[owner].status,
            Compatibility::Incompatible,
            "{absent_word}"
        );
    }
}
