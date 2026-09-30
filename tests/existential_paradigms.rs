//! COV-019h: native existential attestations, owner boundaries and lexical gold.
#[path = "../tools/validity.rs"]
mod validity;
use klem::dictionary::{
    Compatibility, DictionaryFilter, DictionarySession, SqliteDictionary, import_krdict,
};
use klem::{Analysis, Lemmatizer, WordAnalysis};
use std::{fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    let mut suite: validity::Suite =
        serde_json::from_str(include_str!("fixtures/validity.json")).unwrap();
    suite
        .cases
        .retain(|c| c.id.starts_with("existential-paradigm-"));
    suite
}

fn matches(a: &Analysis, j: &validity::Judgment) -> bool {
    a.lemmas.iter().map(|l| &l.text).eq(&j.lemmas)
        && a.lemmas
            .iter()
            .map(|l| l.kind)
            .eq(j.lemma_kinds.as_ref().unwrap().iter().copied())
        && a.morphemes
            .iter()
            .map(|m| &m.form)
            .eq(j.morphemes.as_ref().unwrap())
        && a.morphemes
            .iter()
            .map(|m| m.kind)
            .eq(j.morpheme_kinds.as_ref().unwrap().iter().copied())
}

#[test]
fn native_existential_paths_preserve_owner_boundaries_and_allomorphs() {
    let suite = suite();
    let report = validity::evaluate(&suite).unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!((report.required_total, report.forbidden_total), (17, 4));
    let engine = Lemmatizer::new();
    for c in suite.cases {
        let word = engine.analyze_word(&c.surface).unwrap();
        assert_eq!(
            word,
            engine
                .analyze_word(&c.surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(word.analyses.iter().any(|a| a.unchanged));
        for a in word.analyses {
            assert!(a.breakdown().is_some(), "{}", c.id);
            assert!(
                a.rules.iter().all(|r| klem::rule_explanation(r).is_some()),
                "{}",
                c.id
            );
        }
    }
}

struct Fixture(PathBuf);
impl Fixture {
    fn new() -> Self {
        let path = std::env::temp_dir().join(format!(
            "klem-existential-paradigms-{}.db",
            std::process::id()
        ));
        import_krdict(
            &[PathBuf::from(
                "tests/fixtures/krdict-existential-paradigms.json",
            )],
            &path,
            "existential-paradigms",
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

#[test]
fn native_existential_dictionary_roles_and_cli_parity_survive_both_filters() {
    let fixture = Fixture::new();
    let db = SqliteDictionary::open(&fixture.0).unwrap();
    let engine = Lemmatizer::new();
    for bytes in [0, 4096] {
        let mut dictionary = DictionarySession::new(&db, bytes);
        for case in suite()
            .cases
            .into_iter()
            .filter(|c| c.judgments[0].verdict == validity::Verdict::Required)
        {
            let word = engine.analyze_word(&case.surface).unwrap();
            let a = word
                .analyses
                .iter()
                .find(|a| matches(a, &case.judgments[0]))
                .unwrap();
            let annotation = dictionary.annotate(&word).unwrap();
            let reading = annotation.assess(a);
            for (lemma, assessed) in a.lemmas.iter().zip(&reading.lemmas) {
                assert!(
                    assessed
                        .entries
                        .iter()
                        .any(|e| e.status == Compatibility::Compatible),
                    "{}: {}",
                    case.id,
                    lemma.text
                );
                if lemma.kind == klem::LemmaKind::Auxiliary
                    && matches!(lemma.text.as_str(), "있다" | "계시다")
                {
                    let auxiliary_id = if lemma.text == "있다" {
                        "krdict:62595"
                    } else {
                        "krdict:61346"
                    };
                    for e in &assessed.entries {
                        assert_eq!(
                            e.status,
                            if e.id == auxiliary_id {
                                Compatibility::Compatible
                            } else {
                                Compatibility::Incompatible
                            },
                            "{}: {}",
                            case.id,
                            e.id
                        );
                    }
                }
            }
            for (flag, policy) in [
                ("--dict-only", DictionaryFilter::Headword),
                ("--dict-compatible", DictionaryFilter::Compatible),
            ] {
                let mut filtered = word.clone();
                let mut annotated = annotation.clone();
                annotated.filter(&mut filtered, policy);
                assert!(filtered.analyses.contains(a), "{}", case.id);
                let output = Command::new(env!("CARGO_BIN_EXE_klem"))
                    .args(["word", &case.surface, "--dictionary"])
                    .arg(&fixture.0)
                    .arg(flag)
                    .output()
                    .unwrap();
                assert!(
                    output.status.success(),
                    "{}",
                    String::from_utf8_lossy(&output.stderr)
                );
                let json: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
                assert_eq!(
                    serde_json::from_value::<WordAnalysis>(json.clone()).unwrap(),
                    filtered
                );
                assert_eq!(json["dictionary"], serde_json::to_value(annotated).unwrap());
            }
            assert!(dictionary.cache_bytes() <= bytes);
        }
    }
}
