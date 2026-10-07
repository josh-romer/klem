//! Proposed whole connective readings preserve all older particle alternatives.
use klem::dictionary::{
    Dictionary, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::path::PathBuf;
use unicode_normalization::UnicodeNormalization;

#[path = "../tools/validity.rs"]
mod validity;

#[test]
fn original_and_authored_structural_judgments_have_individual_ledger_ids() {
    let suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/declarative-contrast-validity.json")).unwrap();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(report.cases, 42);
    assert_eq!(report.required_total, 32);
    assert_eq!(report.forbidden_total, 10);
    assert_eq!(
        suite
            .cases
            .iter()
            .filter(|c| c.id.starts_with("declarative-contrast-original-"))
            .count(),
        24
    );
}

fn matches(a: &Analysis, expected: &Value) -> bool {
    let data = serde_json::to_value(a).unwrap();
    data["lemmas"]
        .as_array()
        .unwrap()
        .iter()
        .map(|l| l["text"].as_str().unwrap())
        .eq(expected["lemmas"]
            .as_array()
            .unwrap()
            .iter()
            .map(|l| l.as_str().unwrap()))
        && data["lemmas"]
            .as_array()
            .unwrap()
            .iter()
            .map(|l| l["kind"].as_str().unwrap())
            .eq(expected["lemma_kinds"]
                .as_array()
                .unwrap()
                .iter()
                .map(|l| l.as_str().unwrap()))
        && data["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| m["form"].as_str().unwrap())
            .eq(expected["morphemes"]
                .as_array()
                .unwrap()
                .iter()
                .map(|m| m.as_str().unwrap()))
        && data["morphemes"]
            .as_array()
            .unwrap()
            .iter()
            .map(|m| m["kind"].as_str().unwrap())
            .eq(expected["morpheme_kinds"]
                .as_array()
                .unwrap()
                .iter()
                .map(|m| m.as_str().unwrap()))
        && expected["required_rules"]
            .as_array()
            .unwrap()
            .iter()
            .all(|r| a.rules.iter().any(|rule| rule == r.as_str().unwrap()))
}

struct Cleanup(PathBuf);
impl Drop for Cleanup {
    fn drop(&mut self) {
        let _ = std::fs::remove_file(&self.0);
    }
}

fn dictionary(name: &str) -> (SqliteDictionary, Cleanup) {
    let path = std::env::temp_dir().join(format!(
        "klem-contrast-prototype-{name}-{}.db",
        std::process::id()
    ));
    let cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/declarative-contrast-boundary-english.json",
        )],
        &path,
        "contrast-source",
    )
    .unwrap();
    (SqliteDictionary::open(path).unwrap(), cleanup)
}

#[test]
fn every_original_target_keeps_all_particle_paths_and_recovers_the_whole_connective() {
    let cases: Vec<Value> = serde_json::from_str(include_str!(
        "fixtures/declarative-contrast-original-cases.json"
    ))
    .unwrap();
    assert_eq!(cases.len(), 24);
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("originals");
    let mut session = DictionarySession::new(&db, 1024);
    for c in cases {
        let old: WordAnalysis = serde_json::from_value(c["before"].clone()).unwrap();
        let word = c["surface"].as_str().unwrap();
        for surface in [word.to_string(), word.nfd().collect()] {
            let raw = engine.analyze_word(&surface).unwrap();
            assert_eq!(
                raw.analyses
                    .iter()
                    .filter(|a| old.analyses.contains(a))
                    .cloned()
                    .collect::<Vec<_>>(),
                old.analyses,
                "{word}: preserve old order"
            );
            let a = raw
                .analyses
                .iter()
                .find(|a| matches(a, &c["expected"]))
                .unwrap_or_else(|| panic!("{word}: missing whole source-owned connective"));
            assert!(a.breakdown().is_some(), "{word}");
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
            assert!(
                raw.analyses
                    .iter()
                    .any(|a| a.rules.iter().any(|r| r == "particle.concessive")),
                "{word}: older reading remains"
            );
            for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                let mut filtered = raw.clone();
                let mut annotation = session.annotate(&raw).unwrap();
                annotation.filter(&mut filtered, mode);
                assert!(
                    filtered.analyses.iter().any(|a| matches(a, &c["expected"])),
                    "{word}: {mode:?} preserves required source path"
                );
            }
        }
    }
}

#[test]
fn complete_source_and_lexical_native_fields_survive_the_production_importer() {
    let originals: Value =
        serde_json::from_str(include_str!("fixtures/declarative-contrast-native.json")).unwrap();
    assert_eq!(originals.as_object().unwrap().len(), 63);
    let (db, _cleanup) = dictionary("native");
    for (id, original) in originals.as_object().unwrap() {
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

fn path<'a>(word: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> Option<&'a Analysis> {
    word.analyses.iter().find(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(heads.iter().copied())
            && a.morphemes
                .iter()
                .map(|m| m.form.as_str())
                .eq(forms.iter().copied())
            && a.rules.iter().any(|r| r == "ending.declarative_contrast")
    })
}

#[test]
fn authored_stem_and_marker_boundaries_do_not_remove_particle_alternatives() {
    let engine = Lemmatizer::new();
    for suffix in ["마는", "만"] {
        let ending = format!("는다{suffix}");
        for (base, head) in [
            ("가는다", "가다"),
            ("살는다", "살다"),
            ("먹었는다", "먹다"),
            ("먹겠는다", "먹다"),
            ("도운다", "돕다"),
        ] {
            let surface = format!("{base}{suffix}");
            for s in [surface.clone(), surface.nfd().collect()] {
                let w = engine.analyze_word(&s).unwrap();
                assert!(
                    !w.analyses
                        .iter()
                        .any(|a| a.lemmas.iter().map(|l| l.text.as_str()).eq([head])
                            && a.morphemes.last().is_some_and(|m| m.form == ending)
                            && a.rules.iter().any(|r| r == "ending.declarative_contrast")),
                    "{surface}: forbidden stem/marker hypothesis"
                );
            }
        }
        for (base, head, present) in [
            ("간다", "가다", true),
            ("산다", "살다", true),
            ("먹는다", "먹다", true),
            ("돕는다", "돕다", true),
            ("먹다", "먹다", false),
        ] {
            let surface = format!("{base}{suffix}");
            let form = if present {
                format!("는다{suffix}")
            } else {
                format!("다{suffix}")
            };
            for s in [surface.clone(), surface.nfd().collect()] {
                let w = engine.analyze_word(&s).unwrap();
                assert!(
                    path(&w, &[head], &[&form]).is_some(),
                    "{surface}: retain raw hypothesis"
                );
                assert!(
                    w.analyses
                        .iter()
                        .any(|a| a.rules.iter().any(|r| r == "particle.concessive")),
                    "{surface}: retain particle alternatives"
                );
            }
        }
    }
}

#[test]
fn dictionary_attachment_is_per_owner_and_keeps_all_homonym_assessments() {
    use klem::dictionary::Compatibility::{Compatible, Incompatible};
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("boundaries");
    let mut session = DictionarySession::new(&db, 1024);
    for suffix in ["마는", "만"] {
        let plain = format!("다{suffix}");
        let present = format!("는다{suffix}");
        for (base, head, pref, is_present, status) in [
            ("먹다", "먹다", None, false, Incompatible),
            ("예쁜다", "예쁘다", None, true, Incompatible),
            ("높는다", "높다", None, true, Incompatible),
            ("좋다", "좋다", None, false, Compatible),
            ("먹었다", "먹다", Some("었"), false, Compatible),
            ("먹겠다", "먹다", Some("겠"), false, Compatible),
            ("먹으시다", "먹다", Some("시"), false, Compatible),
            ("먹으신다", "먹다", Some("시"), true, Compatible),
            ("멀다", "멀다", None, false, Compatible),
            ("먼다", "멀다", None, true, Compatible),
            ("간다", "갈다", None, true, Compatible),
            ("간다", "가다", None, true, Compatible),
            ("쓴다", "쓸다", None, true, Compatible),
            ("쓴다", "쓰다", None, true, Compatible),
            ("안다", "안다", None, false, Incompatible),
            ("안다", "알다", None, true, Compatible),
        ] {
            let surface = format!("{base}{suffix}");
            let form = if is_present { &present } else { &plain };
            let mut forms = Vec::new();
            if let Some(p) = pref {
                forms.push(p);
            }
            forms.push(form.as_str());
            for s in [surface.clone(), surface.nfd().collect()] {
                let raw = engine.analyze_word(&s).unwrap();
                let a = path(&raw, &[head], &forms)
                    .unwrap_or_else(|| panic!("{surface}: missing {head}/{forms:?}"));
                let annotation = session.annotate(&raw).unwrap();
                let assessed = annotation.assess(a);
                assert_eq!(assessed.status, status, "{surface}: {head}: {assessed:?}");
                let matched = annotation
                    .lemmas
                    .iter()
                    .find(|l| l.lemma == a.lemmas[0])
                    .unwrap();
                assert_eq!(
                    assessed.lemmas[0]
                        .entries
                        .iter()
                        .map(|e| e.id.as_str())
                        .collect::<Vec<_>>(),
                    matched
                        .entries
                        .iter()
                        .map(|e| e.entry.id.as_str())
                        .collect::<Vec<_>>(),
                    "retain every homonym"
                );
                if head == "멀다" {
                    for (id, expected) in [
                        (
                            "krdict:54855",
                            if is_present { Compatible } else { Incompatible },
                        ),
                        (
                            "krdict:26833",
                            if is_present { Incompatible } else { Compatible },
                        ),
                    ] {
                        assert_eq!(
                            assessed.lemmas[0]
                                .entries
                                .iter()
                                .find(|e| e.id == id)
                                .unwrap()
                                .status,
                            expected,
                            "{surface}: {id}"
                        );
                    }
                }
                for mode in [DictionaryFilter::Headword, DictionaryFilter::Compatible] {
                    let mut filtered = raw.clone();
                    let mut annotated = annotation.clone();
                    annotated.filter(&mut filtered, mode);
                    assert_eq!(
                        path(&filtered, &[head], &forms).is_some(),
                        mode == DictionaryFilter::Headword || status != Incompatible,
                        "{surface}: {head}: {mode:?}"
                    );
                    // Malformed present adjective readings may already have
                    // no compatible particle path. The separate frozen
                    // baseline test checks exact preservation for each mode.
                }
            }
        }
    }
}

#[test]
fn complete_boundary_owner_closure_survives_the_production_importer() {
    let originals: Value = serde_json::from_str(include_str!(
        "fixtures/declarative-contrast-boundary-native.json"
    ))
    .unwrap();
    assert_eq!(originals.as_object().unwrap().len(), 98);
    let (db, _cleanup) = dictionary("complete-boundaries");
    for (id, original) in originals.as_object().unwrap() {
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
fn every_authored_word_preserves_all_actual_prior_paths_and_assessments_in_every_mode() {
    let capture: Value = serde_json::from_str(include_str!(
        "fixtures/declarative-contrast-boundary-before.json"
    ))
    .unwrap();
    assert_eq!(capture["word_count"], 62);
    assert_eq!(capture["normalization_calls"], 372);
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("prior-boundaries");
    let mut session = DictionarySession::new(&db, 1024);
    for (word, row) in capture["words"].as_object().unwrap() {
        for s in [word.to_string(), word.nfd().collect()] {
            let raw = engine.analyze_word(&s).unwrap();
            for (mode, filter) in [
                ("raw", None),
                ("headword", Some(DictionaryFilter::Headword)),
                ("compatible", Some(DictionaryFilter::Compatible)),
            ] {
                let old: WordAnalysis = serde_json::from_value(row[mode].clone()).unwrap();
                let mut current = raw.clone();
                let mut annotation = session.annotate(&raw).unwrap();
                if let Some(f) = filter {
                    annotation.filter(&mut current, f);
                }
                assert_eq!(current.normalized, old.normalized);
                let retained = current
                    .analyses
                    .iter()
                    .filter(|a| old.analyses.contains(a))
                    .cloned()
                    .collect::<Vec<_>>();
                assert_eq!(
                    retained, old.analyses,
                    "{word}: {mode}: every older path and its order"
                );
                for (old_index, a) in old.analyses.iter().enumerate() {
                    let current_index = current.analyses.iter().position(|p| p == a).unwrap();
                    assert_eq!(
                        serde_json::to_value(&annotation.readings[current_index]).unwrap(),
                        row[mode]["dictionary"]["readings"][old_index],
                        "{word}: {mode}: old entry assessments"
                    );
                }
            }
        }
    }
}

#[test]
fn an_auxiliarys_connector_and_native_homonym_determine_its_own_contrast_attachment() {
    use klem::dictionary::Compatibility::{Compatible, Incompatible};
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("auxiliary-owners");
    let mut session = DictionarySession::new(&db, 1024);
    for suffix in ["마는", "만"] {
        let plain = format!("다{suffix}");
        let present = format!("는다{suffix}");
        for (base, heads, left, is_present) in [
            ("좋게한다", vec!["좋다", "하다"], vec!["게"], true),
            ("먹기는하다", vec!["먹다", "하다"], vec!["기", "는"], false),
            ("먹기는하다", vec!["먹다", "하다"], vec!["기는"], false),
            ("좋기는하다", vec!["좋다", "하다"], vec!["기", "는"], false),
            ("좋기는하다", vec!["좋다", "하다"], vec!["기는"], false),
        ] {
            let word = format!("{base}{suffix}");
            let mut forms = left;
            forms.push(if is_present { &present } else { &plain });
            for s in [word.clone(), word.nfd().collect()] {
                let w = engine.analyze_word(&s).unwrap();
                let a = path(&w, &heads, &forms)
                    .unwrap_or_else(|| panic!("{word}: missing owned path"));
                assert_eq!(a.lemmas[1].kind, klem::LemmaKind::Auxiliary);
                let annotation = session.annotate(&w).unwrap();
                let assessed = annotation.assess(a);
                assert_eq!(assessed.status, Compatible, "{word}: {assessed:?}");
                for (id, expected) in [
                    (
                        "krdict:62888",
                        if is_present { Compatible } else { Incompatible },
                    ),
                    (
                        "krdict:62899",
                        if is_present { Incompatible } else { Compatible },
                    ),
                    ("krdict:73277", Incompatible),
                ] {
                    assert_eq!(
                        assessed.lemmas[1]
                            .entries
                            .iter()
                            .find(|e| e.id == id)
                            .unwrap()
                            .status,
                        expected,
                        "{word}: distinct Native owner {id}"
                    );
                }
            }
        }
        let w = engine.analyze_word(&format!("좋게하다{suffix}")).unwrap();
        assert!(
            path(&w, &["좋다", "하다"], &["게", &plain]).is_none(),
            "The earlier adjective cannot license plain -다 on a verbal causative auxiliary"
        );
    }
}

#[test]
fn unreviewed_stative_negative_and_copular_extensions_remain_unknown_and_filterable() {
    use klem::dictionary::Compatibility::Unknown;
    let engine = Lemmatizer::new();
    let (db, _cleanup) = dictionary("unreviewed-owners");
    let mut session = DictionarySession::new(&db, 1024);
    for suffix in ["마는", "만"] {
        let plain = format!("다{suffix}");
        for (base, heads, left, native_id) in [
            ("먹고있다", vec!["먹다", "있다"], vec!["고"], "krdict:62595"),
            (
                "좋지는않다",
                vec!["좋다", "않다"],
                vec!["지", "는"],
                "krdict:71583",
            ),
            (
                "먹지는않다",
                vec!["먹다", "않다"],
                vec!["지", "는"],
                "krdict:71581",
            ),
            ("학생이다", vec!["학생", "이다"], vec![], "krdict:86232"),
            (
                "학생이었다",
                vec!["학생", "이다"],
                vec!["었"],
                "krdict:86232",
            ),
            (
                "학생이시다",
                vec!["학생", "이다"],
                vec!["시"],
                "krdict:86232",
            ),
        ] {
            let word = format!("{base}{suffix}");
            let mut forms = left;
            forms.push(&plain);
            for s in [word.clone(), word.nfd().collect()] {
                let w = engine.analyze_word(&s).unwrap();
                let a = path(&w, &heads, &forms)
                    .unwrap_or_else(|| panic!("{word}: preserve unreviewed path"));
                let annotation = session.annotate(&w).unwrap();
                let assessed = annotation.assess(a);
                assert_eq!(assessed.lemmas[1].status, Unknown, "{word}: {assessed:?}");
                assert_eq!(
                    assessed.lemmas[1]
                        .entries
                        .iter()
                        .find(|e| e.id == native_id)
                        .unwrap()
                        .status,
                    Unknown,
                    "{word}: no contextual license inferred from an unrelated entry"
                );
                let mut filtered = w.clone();
                let mut annotated = annotation.clone();
                annotated.filter(&mut filtered, DictionaryFilter::Compatible);
                assert!(
                    path(&filtered, &heads, &forms).is_some(),
                    "{word}: Unknown remains compatible-filter eligible"
                );
            }
        }
    }
}

#[test]
fn every_actual_source_alternative_has_a_complete_imported_native_owner() {
    let originals: Value = serde_json::from_str(include_str!(
        "fixtures/declarative-contrast-source-owner-native.json"
    ))
    .unwrap();
    assert_eq!(originals.as_object().unwrap().len(), 105);
    let path = std::env::temp_dir().join(format!(
        "klem-contrast-source-alternatives-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/declarative-contrast-source-owner-english.json",
        )],
        &path,
        "contrast-source-alternatives",
    )
    .unwrap();
    let db = SqliteDictionary::open(path).unwrap();
    for (id, original) in originals.as_object().unwrap() {
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
fn every_broad_replay_alternative_has_a_complete_imported_native_owner() {
    let originals: Value = serde_json::from_str(include_str!(
        "fixtures/declarative-contrast-broad-owner-native.json"
    ))
    .unwrap();
    assert_eq!(originals.as_object().unwrap().len(), 115);
    let path = std::env::temp_dir().join(format!(
        "klem-contrast-broad-alternatives-{}.db",
        std::process::id()
    ));
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/declarative-contrast-broad-owner-english.json",
        )],
        &path,
        "contrast-broad-alternatives",
    )
    .unwrap();
    let db = SqliteDictionary::open(path).unwrap();
    for (id, original) in originals.as_object().unwrap() {
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
