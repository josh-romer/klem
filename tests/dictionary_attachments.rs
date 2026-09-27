//! Dictionary policy judgments are separate from unfiltered rule judgments.
#[path = "../tools/validity.rs"]
mod validity;

use klem::dictionary::{
    Annotation, AttachmentRule, Compatibility, DictionaryFilter, DictionarySession,
    SqliteDictionary, import_krdict, pos_compatibility,
};
use klem::{LemmaKind, Lemmatizer, Session, WordAnalysis};
use std::{fs, path::PathBuf, process::Command, sync::Arc};
use unicode_normalization::UnicodeNormalization;

fn suite() -> validity::Suite {
    serde_json::from_str(include_str!("fixtures/dictionary-attachments.json")).unwrap()
}

struct Fixture(PathBuf);
impl Fixture {
    fn new(name: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-attachments-{}-{name}.db", std::process::id()));
        import_krdict(
            &["krdict-report-ni.json", "krdict-attachments.json"]
                .map(|s| PathBuf::from("tests/fixtures").join(s)),
            &path,
            "attachment-fixture",
        )
        .unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        fs::remove_file(&self.0).unwrap();
    }
}

#[test]
fn source_backed_attachment_judgments_preserve_raw_rules_and_headword_policy() {
    let fixture = Fixture::new("judgments");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let suite = suite();
    let raw = validity::evaluate(&suite).unwrap();
    // Every forbidden dictionary reading really is generated before filtering.
    assert_eq!(raw.forbidden_present, raw.forbidden_total);
    assert_eq!(raw.required_present, raw.required_total);
    let headwords = validity::evaluate_with(&suite, |word| {
        let mut analysis = engine.analyze_word(word).unwrap();
        let mut annotation = dictionary.annotate(&analysis).unwrap();
        annotation.filter(&mut analysis, DictionaryFilter::Headword);
        Ok(analysis)
    })
    .unwrap();
    // A missing fixture headword must not masquerade as an attachment fix.
    assert_eq!(headwords.forbidden_present, raw.forbidden_total);
    assert_eq!(headwords.required_present, raw.required_total);
    let report = validity::evaluate_with(&suite, |word| {
        let mut analysis = engine.analyze_word(word).unwrap();
        let mut annotation = dictionary.annotate(&analysis).unwrap();
        let before = analysis.clone();
        let mut headwords = analysis.clone();
        let mut head_annotation = annotation.clone();
        head_annotation.filter(&mut headwords, DictionaryFilter::Headword);
        assert_eq!(
            headwords,
            before.filtered(|l| annotation.has_match(l, false))
        );
        annotation.filter(&mut analysis, DictionaryFilter::Compatible);
        assert_eq!(annotation.readings.len(), analysis.analyses.len());
        for (a, assessment) in analysis.analyses.iter().zip(&annotation.readings) {
            assert_eq!(*assessment, annotation.assess(a));
            assert_ne!(assessment.status, Compatibility::Incompatible);
            assert!(headwords.analyses.contains(a));
        }
        assert_eq!(before, engine.analyze_word(word).unwrap());
        assert!(dictionary.cache_bytes() <= 4096);
        Ok(analysis)
    })
    .unwrap();
    assert!(report.passed(), "{:?}", report.violations);
    assert_eq!(
        report.required_total + report.forbidden_total,
        suite.cases.len()
    );
    assert!(!report.review_queue.is_empty());
}

#[test]
fn attachment_entry_evidence_preserves_homonyms_unknowns_and_component_ownership() {
    let fixture = Fixture::new("evidence");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    let word = engine.analyze_word("큰다니").unwrap();
    let mut annotation = dictionary.annotate(&word).unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| a.lemmas.len() == 1 && a.lemmas[0].text == "크다")
        .unwrap();
    let assessed = annotation.assess(a);
    assert_eq!(assessed.status, Compatibility::Compatible);
    let entries = &assessed.lemmas[0].entries;
    assert_eq!(
        entries
            .iter()
            .find(|e| e.id == "krdict:66584")
            .unwrap()
            .status,
        Compatibility::Compatible
    );
    let adjective = entries.iter().find(|e| e.id == "krdict:66586").unwrap();
    assert_eq!(adjective.status, Compatibility::Incompatible);
    assert_eq!(
        adjective.conflicts[0].rule,
        AttachmentRule::PresentDeclarativeVerb
    );
    assert_eq!(adjective.conflicts[0].morpheme_index, Some(0));

    // Synthetic adapter evidence: a nominal-only entry cannot lend its
    // class to an incompatible lexical adjective entry. Unknown is not false.
    let matches = annotation
        .lemmas
        .iter_mut()
        .find(|m| m.lemma == a.lemmas[0])
        .unwrap();
    let verb = matches
        .entries
        .iter_mut()
        .find(|e| e.entry.id == "krdict:66584")
        .unwrap();
    verb.entry.pos = "명사".into();
    verb.pos_compatibility = pos_compatibility(&matches.lemma, &verb.entry);
    assert_eq!(annotation.assess(a).status, Compatibility::Incompatible);
    let matches = annotation
        .lemmas
        .iter_mut()
        .find(|m| m.lemma == a.lemmas[0])
        .unwrap();
    let verb = matches
        .entries
        .iter_mut()
        .find(|e| e.entry.id == "krdict:66584")
        .unwrap();
    verb.entry.pos = "unmapped provider class".into();
    verb.pos_compatibility = pos_compatibility(&matches.lemma, &verb.entry);
    assert_eq!(annotation.assess(a).status, Compatibility::Unknown);
    let mut kept = word.clone();
    annotation.filter(&mut kept, DictionaryFilter::Compatible);
    assert!(kept.analyses.contains(a));

    let word = engine.analyze_word("가늘어한다니").unwrap();
    let annotation = dictionary.annotate(&word).unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(["가늘다", "하다"])
        })
        .unwrap();
    assert_eq!(annotation.assess(a).status, Compatibility::Compatible);
    let mut swapped = a.clone();
    swapped.morphemes.swap(0, 1);
    let assessment = annotation.assess(&swapped);
    assert_eq!(assessment.status, Compatibility::Incompatible);
    assert_eq!(
        assessment.lemmas[0].entries[0].conflicts[0].morpheme_index,
        Some(0)
    );
    assert_eq!(assessment.lemmas[1].lemma_index, 1);

    let separate = engine.analyze_word("싶었다").unwrap();
    let annotation = dictionary.annotate(&separate).unwrap();
    let auxiliary = separate
        .analyses
        .iter()
        .find(|a| a.lemmas.len() == 1 && a.lemmas[0].text == "싶다")
        .unwrap();
    assert_eq!(annotation.assess(auxiliary).status, Compatibility::Unknown);
    assert!(
        annotation
            .lemmas
            .iter()
            .find(|m| m.lemma == auxiliary.lemmas[0])
            .unwrap()
            .entries
            .iter()
            .all(|e| e.pos_compatibility == Compatibility::Incompatible)
    );

    let unknown = engine.analyze_word("뛻는다니").unwrap();
    let mut annotation = dictionary.annotate(&unknown).unwrap();
    assert!(
        annotation
            .readings
            .iter()
            .all(|r| r.status == Compatibility::Unknown)
    );
    let mut filtered = unknown;
    annotation.filter(&mut filtered, DictionaryFilter::Compatible);
    assert!(filtered.analyses.is_empty());
    let mut malformed = a.clone();
    malformed.morphemes.clear();
    assert_eq!(annotation.assess(&malformed).status, Compatibility::Unknown);
    assert_eq!(dictionary.cache_bytes(), 0);
}

#[test]
fn dictionary_attachment_cli_library_unicode_and_cache_parity() {
    let fixture = Fixture::new("cli");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 1024 * 1024);
    let engine = Arc::new(Lemmatizer::new());
    let mut session = Session::new(Arc::clone(&engine), 1024 * 1024);
    for case in suite().cases {
        let raw = engine.analyze_word(&case.surface).unwrap();
        let annotation = dictionary.annotate(&raw).unwrap();
        for (flag, policy) in [
            ("--dict-only", DictionaryFilter::Headword),
            ("--dict-compatible", DictionaryFilter::Compatible),
        ] {
            let mut expected = raw.clone();
            let mut evidence = annotation.clone();
            evidence.filter(&mut expected, policy);
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
                expected,
                "{} {flag}",
                case.id
            );
            assert_eq!(
                serde_json::from_value::<Annotation>(json["dictionary"].clone()).unwrap(),
                evidence
            );
        }
        let nfd: String = case.surface.nfd().collect();
        assert_eq!(engine.analyze_word(&nfd).unwrap(), raw);
        // Filtering one text consumer must not modify shared Session candidates.
        let records = klem::analyze_reader(case.surface.as_bytes(), &mut session, |mut record| {
            if let Some(a) = record.analysis.as_mut() {
                let mut annotation = dictionary.annotate(a).unwrap();
                annotation.filter(Arc::make_mut(a), DictionaryFilter::Compatible);
            }
            Ok(())
        });
        records.unwrap();
        klem::analyze_reader(case.surface.as_bytes(), &mut session, |record| {
            assert_eq!(record.analysis.as_deref().unwrap(), &raw);
            Ok(())
        })
        .unwrap();
    }
    // Legacy annotations and caller-reordered candidates get freshly indexed checks.
    let mut raw = engine.analyze_word("가늘다니").unwrap();
    let annotation = dictionary.annotate(&raw).unwrap();
    let mut json = serde_json::to_value(annotation).unwrap();
    json.as_object_mut().unwrap().remove("readings");
    let mut older: Annotation = serde_json::from_value(json).unwrap();
    raw.analyses.reverse();
    older.filter(&mut raw, DictionaryFilter::Compatible);
    assert_eq!(older.readings.len(), raw.analyses.len());
    assert!(
        raw.analyses
            .iter()
            .all(|a| a.lemmas[0].kind != LemmaKind::Nominal)
    );
    for (a, assessment) in raw.analyses.iter().zip(&older.readings) {
        assert_eq!(older.assess(a), *assessment);
    }
    for args in [
        vec!["word", "먹다", "--dict-compatible"],
        vec!["word", "먹다", "--dict-compatible", "--format", "text"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(args)
            .output()
            .unwrap();
        assert!(!output.status.success());
        assert!(
            String::from_utf8_lossy(&output.stderr)
                .contains("--dict-compatible requires --dictionary")
        );
    }
}
