use klem::{LemmaKind, Lemmatizer, MorphemeKind};
use sha2::{Digest, Sha256};

#[test]
fn output_matches_reviewed_snapshots() {
    // Full JSON fingerprints, including alternate groups, morphemes, ordering
    // and provenance. Initially captured before chart optimization; reviewed
    // particle/하다 changes retain prior hashes in the fixture for review.
    // These are compatibility snapshots, not linguistic accuracy judgments.
    #[derive(serde::Deserialize)]
    struct Snapshot {
        word: String,
        sha256: String,
        before_spelling_sha256: Option<String>,
        before_digeut_siot_sha256: Option<String>,
        before_bieup_sha256: Option<String>,
    }
    let snapshots: Vec<Snapshot> =
        serde_json::from_str(include_str!("fixtures/optimization.json")).unwrap();
    let engine = Lemmatizer::new();
    for snapshot in snapshots {
        let result = engine.analyze_word(&snapshot.word).unwrap();
        if let Some(expected) = snapshot.before_bieup_sha256 {
            let mut previous = result.clone();
            for a in &mut previous.analyses {
                for path in &mut a.spelling_paths {
                    path.retain(|r| {
                        !matches!(
                            r.class,
                            klem::SpellingClass::BieupRegular | klem::SpellingClass::BieupIrregular
                        )
                    });
                }
                if a.spelling_paths.iter().any(Vec::is_empty) {
                    a.spelling_paths.clear();
                }
                a.spelling_paths.sort();
                a.spelling_paths.dedup();
            }
            let mut json = serde_json::to_vec(&previous).unwrap();
            json.push(b'\n');
            assert_eq!(
                format!("{:x}", Sha256::digest(json)),
                expected,
                "{}: pre-ㅂ output changed",
                snapshot.word
            );
        }
        if let Some(expected) = snapshot.before_digeut_siot_sha256 {
            let mut previous = result.clone();
            for a in &mut previous.analyses {
                for path in &mut a.spelling_paths {
                    path.retain(|r| {
                        matches!(
                            r.class,
                            klem::SpellingClass::HieutRegular | klem::SpellingClass::HieutIrregular
                        )
                    });
                }
                if a.spelling_paths.iter().any(Vec::is_empty) {
                    a.spelling_paths.clear();
                }
                a.spelling_paths.sort();
                a.spelling_paths.dedup();
            }
            let mut json = serde_json::to_vec(&previous).unwrap();
            json.push(b'\n');
            assert_eq!(
                format!("{:x}", Sha256::digest(json)),
                expected,
                "{}: pre-ㄷ/ㅅ output changed",
                snapshot.word
            );
        }
        if let Some(expected) = snapshot.before_spelling_sha256 {
            let mut legacy = result.clone();
            for a in &mut legacy.analyses {
                a.spelling_paths.clear();
            }
            let mut json = serde_json::to_vec(&legacy).unwrap();
            json.push(b'\n');
            assert_eq!(
                format!("{:x}", Sha256::digest(json)),
                expected,
                "{}: pre-spelling output changed",
                snapshot.word
            );
        }
        let mut json = serde_json::to_vec(&result).unwrap();
        json.push(b'\n');
        assert_eq!(
            format!("{:x}", Sha256::digest(json)),
            snapshot.sha256,
            "{}",
            snapshot.word
        );
    }
    let mut json = serde_json::to_vec(&engine.analyze_word(&"가".repeat(64)).unwrap()).unwrap();
    json.push(b'\n');
    assert_eq!(
        format!("{:x}", Sha256::digest(json)),
        "ddd77ed67c939112e4496ac1807be4bf932d54be32d0fea102302912f5318eea"
    );
}

#[test]
fn repeated_tokens_keep_every_auxiliary_chain() {
    let engine = Lemmatizer::new();
    for n in [2, 8, 64, 256] {
        let result = engine.analyze_word(&"가".repeat(n)).unwrap();
        // Identity, nominal + 가, regular head lengths 1..=n, and ㅡ-deletion
        // head lengths 2..=n. No search-depth or output cutoff.
        assert_eq!(result.analyses.len(), 2 * n + 1);
        for head_len in 1..=n {
            let mut expected = vec![format!("{}다", "가".repeat(head_len))];
            expected.extend((head_len..n).map(|_| "가다".into()));
            assert!(
                result.analyses.iter().any(|a| {
                    a.lemmas.iter().map(|l| &l.text).eq(expected.iter())
                        && a.lemmas[0].kind == LemmaKind::Predicate
                        && a.lemmas[1..].iter().all(|l| l.kind == LemmaKind::Auxiliary)
                        && a.morphemes.len() == n - head_len + 1
                        && a.morphemes
                            .iter()
                            .all(|m| m.form == "어" && m.kind == MorphemeKind::Ending)
                }),
                "missing head length {head_len} for {n} syllables"
            );
        }
    }
}

#[cfg(target_os = "linux")]
#[test]
fn thousand_syllables_fit_in_a_memory_limited_process() {
    use std::{
        process::{Command, Stdio},
        time::{Duration, Instant},
    };
    // This is a test-only virtual-memory limit. The production analyzer has
    // no token/candidate cap. The previous chart exhausted this allowance.
    let mut child = Command::new("sh")
        .args([
            "-c",
            "ulimit -c 0; ulimit -v 262144 || exit 90; exec \"$1\" word \"$2\"",
            "klem-stress",
            env!("CARGO_BIN_EXE_klem"),
            &"가".repeat(1024),
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let start = Instant::now();
    loop {
        if child.try_wait().unwrap().is_some() {
            break;
        }
        if start.elapsed() > Duration::from_secs(30) {
            child.kill().unwrap();
            child.wait().unwrap();
            panic!("1024-syllable analysis exceeded the 30-second test deadline");
        }
        std::thread::sleep(Duration::from_millis(25));
    }
    let output = child.wait_with_output().unwrap();
    assert!(
        output.status.success(),
        "stress subprocess failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );
}
