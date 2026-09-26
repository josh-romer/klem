use std::{
    io::Write,
    process::{Command, Stdio},
};

#[test]
fn word_json_matches_library() {
    let out = Command::new(env!("CARGO_BIN_EXE_klem"))
        .args(["word", "먹었어요"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let actual: serde_json::Value = serde_json::from_slice(&out.stdout).unwrap();
    assert_eq!(
        actual,
        serde_json::to_value(klem::Lemmatizer::new().analyze_word("먹었어요").unwrap()).unwrap()
    );
}

#[test]
fn stdin_jsonl_matches_library() {
    let text = "학교에서는 먹었다.\n";
    let mut child = Command::new(env!("CARGO_BIN_EXE_klem"))
        .args(["text", "-", "--cache-bytes", "0"])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    child
        .stdin
        .take()
        .unwrap()
        .write_all(text.as_bytes())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(output.status.success());
    let actual: Vec<serde_json::Value> = String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|s| serde_json::from_str(s).unwrap())
        .collect();
    let expected: Vec<_> = klem::Lemmatizer::new()
        .analyze_text(text)
        .map(|r| serde_json::to_value(r).unwrap())
        .collect();
    assert_eq!(actual, expected);
}

#[test]
fn errors_go_to_stderr() {
    for args in [
        vec!["word"],
        vec!["word", "먹다", "--format", "xml"],
        vec!["unknown"],
        vec!["text", "/definitely/missing/klem.txt"],
    ] {
        let out = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(args)
            .output()
            .unwrap();
        assert!(!out.status.success());
        assert!(!out.stderr.is_empty());
        assert!(out.stdout.is_empty());
    }
}
