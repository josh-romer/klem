//! Each new whole connective preserves an exact older split-particle parent.
use klem::{Analysis, Morpheme, MorphemeKind, WordAnalysis};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::sync::OnceLock;

pub fn assert_addition(source: &str, surface: &str, candidate: &Analysis) -> Analysis {
    static HISTORY: OnceLock<Value> = OnceLock::new();
    let history = HISTORY.get_or_init(|| {
        serde_json::from_str(include_str!(
            "../fixtures/declarative-contrast-history.json"
        ))
        .unwrap()
    });
    assert_eq!(
        history["state"],
        "complete-legacy-candidate-preservation-passed"
    );
    assert_eq!(
        history["source_files_sha256"][source],
        format!("{:x}", Sha256::digest(std::fs::read(source).unwrap()))
    );
    let row = &history["changes"][surface];
    assert!(
        row["origins"]
            .as_array()
            .unwrap()
            .iter()
            .any(|o| o["source"] == source)
    );
    let before: WordAnalysis = serde_json::from_value(row["before"].clone()).unwrap();
    let after: WordAnalysis = serde_json::from_value(row["after"].clone()).unwrap();
    assert_eq!(
        after
            .analyses
            .iter()
            .filter(|a| before.analyses.contains(a))
            .cloned()
            .collect::<Vec<_>>(),
        before.analyses
    );
    assert!(after.analyses.contains(candidate));
    assert!(!before.analyses.contains(candidate));
    let addition = row["additions"]
        .as_array()
        .unwrap()
        .iter()
        .find(|a| serde_json::from_value::<Analysis>(a["analysis"].clone()).unwrap() == *candidate)
        .expect("missing exact contrast attribution");
    assert!(
        addition["id"]
            .as_str()
            .unwrap()
            .starts_with("declarative-contrast-legacy-")
    );
    assert_eq!(
        addition["structural_verdict"],
        "unjudged broader composition"
    );
    assert_eq!(addition["contextual_verdict"], "unjudged");
    assert_eq!(addition["independent_review"], "pending");
    assert!(
        candidate
            .rules
            .iter()
            .any(|r| r == "ending.declarative_contrast")
    );
    let mut inverse = candidate.clone();
    let mut positions = Vec::new();
    let mut morphemes = Vec::new();
    let mut sources = Vec::new();
    for (i, m) in candidate.morphemes.iter().enumerate() {
        let split = if m.kind == MorphemeKind::Ending {
            match m.form.as_str() {
                "다만" => Some(("다", "만", vec!["krdict:80322"])),
                "다마는" => Some(("다", "마는", vec!["krdict:80321"])),
                "는다만" => Some(("는다", "만", vec!["krdict:80324", "krdict:80326"])),
                "는다마는" => Some(("는다", "마는", vec!["krdict:80323", "krdict:80325"])),
                _ => None,
            }
        } else {
            None
        };
        if let Some((ending, particle, entries)) = split {
            positions.push(i);
            morphemes.push(Morpheme {
                form: ending.into(),
                kind: MorphemeKind::Ending,
            });
            morphemes.push(Morpheme {
                form: particle.into(),
                kind: MorphemeKind::Particle,
            });
            sources.extend(entries);
        } else {
            morphemes.push(m.clone());
        }
    }
    assert!(!positions.is_empty());
    inverse.morphemes = morphemes;
    inverse.rules.retain(|r| r != "ending.declarative_contrast");
    inverse
        .rules
        .extend(["particle".into(), "particle.concessive".into()]);
    inverse.rules.sort();
    inverse.rules.dedup();
    for p in &mut inverse.spelling_paths {
        for recovery in p {
            recovery.morpheme_index += positions
                .iter()
                .filter(|i| **i < recovery.morpheme_index)
                .count();
        }
    }
    sources.sort();
    sources.dedup();
    assert_eq!(
        addition["source_entries"],
        serde_json::to_value(sources).unwrap()
    );
    let captured: Analysis =
        serde_json::from_value(addition["exact_split_particle_parent"].clone()).unwrap();
    assert_eq!(inverse, captured);
    assert!(
        before.analyses.contains(&inverse),
        "{surface}: missing exact older split-particle parent"
    );
    assert!(candidate.breakdown().is_some());
    assert!(
        candidate
            .rules
            .iter()
            .all(|r| klem::rule_explanation(r).is_some())
    );
    inverse
}
