//! Every removed full-stream path has a source-reviewed ordered owner.
#[path = "../tools/adjectival_allomorph.rs"]
mod boundaries;

use klem::{Analysis, Lemmatizer, Session};
use serde_json::Value;
use std::{collections::HashSet, sync::Arc};

#[test]
fn every_tracked_full_stream_removal_is_rejected_for_its_actual_owner() {
    let fixture: Value = serde_json::from_str(include_str!(
        "fixtures/adjectival-allomorph-stream-removals.json"
    ))
    .unwrap();
    let cases = fixture["cases"].as_array().unwrap();
    assert_eq!(cases.len(), 3806);
    let mut session = Session::new(Arc::new(Lemmatizer::new()), 4096);
    let mut ids = HashSet::new();
    let mut surfaces = HashSet::new();
    for case in cases {
        let surface = case["surface"].as_str().unwrap();
        let analysis: Analysis = serde_json::from_value(case["analysis"].clone()).unwrap();
        assert!(ids.insert(case["id"].as_str().unwrap()));
        surfaces.insert(surface);
        assert!(
            boundaries::reviewed_removal(&analysis),
            "{surface}: {analysis:?}"
        );
        let actual = session.analyze_word(surface).unwrap();
        assert!(
            !actual.analyses.contains(&analysis),
            "{surface}: {analysis:?}"
        );
        assert!(actual.analyses.iter().any(|a| a.unchanged));
        assert!(
            actual
                .analyses
                .iter()
                .all(|a| !boundaries::reviewed_removal(a))
        );
    }
    assert_eq!(surfaces.len(), 1642);
}
