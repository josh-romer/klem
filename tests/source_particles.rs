//! COV-018u: source compounds, role/means cases and locative 서.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict};
use klem::{Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("source-particles-"));
    suite
}

#[test]
fn source_particles_preserves_class_boundaries_and_ordered_components() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (73, 26));
    let engine = Lemmatizer::new();
    for case in suite.cases {
        let result = engine.analyze_word(&case.surface).unwrap();
        assert_eq!(
            result,
            engine
                .analyze_word(&case.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(result.analyses.iter().any(|a| a.unchanged));
        for a in result.analyses {
            assert!(a.breakdown().is_some(), "{}: {a:?}", case.surface);
            assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        }
    }
}

#[test]
fn source_particles_dictionary_filters_preserve_roles_and_cli_parity() {
    let path =
        std::env::temp_dir().join(format!("klem-source-particles-{}.db", std::process::id()));
    struct Cleanup(PathBuf);
    impl Drop for Cleanup {
        fn drop(&mut self) {
            let _ = fs::remove_file(&self.0);
        }
    }
    let _cleanup = Cleanup(path.clone());
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-source-particles.json")],
        &path,
        "source_particles",
    )
    .unwrap();
    let db = SqliteDictionary::open(&path).unwrap();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for (flag, policy) in [
        ("--dict-only", DictionaryFilter::Headword),
        ("--dict-compatible", DictionaryFilter::Compatible),
    ] {
        let report = validity::evaluate_with(&suite(), |word| {
            let mut analysis = engine.analyze_word(word).unwrap();
            let mut annotation = dictionary.annotate(&analysis).unwrap();
            annotation.filter(&mut analysis, policy);
            let cli = Command::new(env!("CARGO_BIN_EXE_klem"))
                .args(["word", word, "--dictionary"])
                .arg(&path)
                .arg(flag)
                .output()
                .unwrap();
            assert!(
                cli.status.success(),
                "{}",
                String::from_utf8_lossy(&cli.stderr)
            );
            let value: serde_json::Value = serde_json::from_slice(&cli.stdout).unwrap();
            assert_eq!(
                serde_json::from_value::<WordAnalysis>(value.clone()).unwrap(),
                analysis
            );
            assert_eq!(
                value["dictionary"],
                serde_json::to_value(&annotation).unwrap()
            );
            assert!(dictionary.cache_bytes() <= 4096);
            Ok(analysis)
        })
        .unwrap();
        assert!(report.passed(), "{:?}", report.violations);
    }
}

#[test]
fn source_compounds_preserve_both_boundaries_and_all_split_alternatives() {
    use klem::{Morpheme, MorphemeKind};
    let engine = Lemmatizer::new();
    let pairs = [
        ("로부터", "로"),
        ("으로부터", "으로"),
        ("에서부터", "에서"),
        ("서부터", "서"),
    ];
    let mut surfaces = Vec::new();
    for base in [
        "학교", "집", "교실", "입", "친구", "ABC", "2026", "쀍", "먹기",
    ] {
        for inner in ["", "만", "까지", "에게"] {
            for (bundle, _) in pairs {
                for outer in ["", "는", "도", "만", "의", "가"] {
                    surfaces.push(format!("{base}{inner}{bundle}{outer}"));
                }
            }
        }
    }
    surfaces.extend(
        [
            "학교로부터다",
            "학교로부터임으로부터",
            "먹고있음으로부터",
            "부모들로부터",
        ]
        .map(str::to_owned),
    );
    let mut compared = 0;
    for surface in surfaces {
        let word = engine.analyze_word(&surface).unwrap();
        for a in &word.analyses {
            for (i, m) in a.morphemes.iter().enumerate() {
                if m.kind != MorphemeKind::Particle {
                    continue;
                }
                for (bundle, prefix) in pairs {
                    let mut forms = a.morphemes.clone();
                    if m.form == bundle {
                        forms.splice(
                            i..=i,
                            [prefix, "부터"].map(|form| Morpheme {
                                form: form.into(),
                                kind: MorphemeKind::Particle,
                            }),
                        );
                    } else if m.form == prefix
                        && a.morphemes
                            .get(i + 1)
                            .is_some_and(|n| n.kind == MorphemeKind::Particle && n.form == "부터")
                    {
                        forms.splice(
                            i..i + 2,
                            [Morpheme {
                                form: bundle.into(),
                                kind: MorphemeKind::Particle,
                            }],
                        );
                    } else {
                        continue;
                    }
                    compared += 1;
                    assert!(
                        word.analyses
                            .iter()
                            .any(|b| b.lemmas == a.lemmas && b.morphemes == forms),
                        "{surface}: {:?} -> {forms:?}",
                        a.morphemes
                    );
                }
            }
        }
    }
    assert!(compared > 1000);
}

#[test]
fn source_particle_corpus_fixtures_preserve_split_and_bundled_annotations() {
    let kaist = include_str!("fixtures/kaist-source-particles.conllu");
    let gsd = include_str!("fixtures/gsd-source-particles.conllu");
    assert_eq!(kaist.matches("# sent_id =").count(), 2);
    assert_eq!(gsd.matches("# sent_id =").count(), 3);
    for (source, surface, gold, head, forms) in [
        (
            kaist,
            "토호로부터",
            "토호+로+부터",
            "토호",
            vec!["로", "부터"],
        ),
        (
            kaist,
            "아이디어에서부터",
            "아이디어+에서+부터",
            "아이디어",
            vec!["에서", "부터"],
        ),
        (
            gsd,
            "일본으로부터",
            "일본+으로부터",
            "일본",
            vec!["으로부터"],
        ),
        (
            gsd,
            "후원함으로써",
            "후원+하+ㅁ+으로써",
            "후원하다",
            vec!["음", "으로써"],
        ),
        (gsd, "드라마로서", "드라마+로서", "드라마", vec!["로서"]),
    ] {
        assert!(
            source
                .lines()
                .any(|l| l.contains(&format!("\t{surface}\t{gold}\t")))
        );
        let result = Lemmatizer::new().analyze_word(surface).unwrap();
        assert!(
            result.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == head
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())),
            "{surface}"
        );
    }
}
