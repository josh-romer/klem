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
        let mut entries = std::collections::BTreeMap::new();
        for file in [
            "krdict-report-ni.json",
            "krdict-attachments.json",
            "krdict-attachment-connectives.json",
            "krdict-expressive-hada.json",
            "krdict-copular-class.json",
            "krdict-danda.json",
            "krdict-daji.json",
            "krdict-dajiman.json",
            "krdict-danikka.json",
            "krdict-short-reports.json",
            "krdict-neura.json",
            "krdict-hieut-compatibility.json",
            "krdict-digeut-siot.json",
            "krdict-bieup.json",
            "krdict-reu.json",
            "krdict-short-stems.json",
            "krdict-jaop.json",
        ] {
            let data: serde_json::Value = serde_json::from_slice(
                &fs::read(PathBuf::from("tests/fixtures").join(file)).unwrap(),
            )
            .unwrap();
            for entry in data["LexicalResource"]["Lexicon"]["LexicalEntry"]
                .as_array()
                .unwrap()
            {
                if matches!(
                    file,
                    "krdict-hieut-compatibility.json"
                        | "krdict-digeut-siot.json"
                        | "krdict-bieup.json"
                        | "krdict-reu.json"
                        | "krdict-short-stems.json"
                        | "krdict-jaop.json"
                ) {
                    // Full native entries supply written forms absent from older
                    // POS-only fixtures; do not borrow evidence by headword.
                    entries.insert(entry["val"].to_string(), entry.clone());
                } else {
                    entries
                        .entry(entry["val"].to_string())
                        .or_insert(entry.clone());
                }
            }
        }
        let input = path.with_extension("json");
        fs::write(&input, serde_json::to_vec(&serde_json::json!({
            "LexicalResource": {"Lexicon": {"LexicalEntry": entries.into_values().collect::<Vec<_>>()}}
        })).unwrap()).unwrap();
        let imported = import_krdict(std::slice::from_ref(&input), &path, "attachment-fixture");
        fs::remove_file(input).unwrap();
        imported.unwrap();
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
        (report.required_total, report.forbidden_total),
        (1650, 1558)
    );
    assert_eq!(
        report.required_total + report.forbidden_total,
        suite.cases.len()
    );
    assert!(!report.review_queue.is_empty());
}

#[test]
fn literary_naida_preserves_verbal_homonyms_and_identifies_the_adjective_conflict() {
    let fixture = Fixture::new("naida-homonyms");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let word = Lemmatizer::new().analyze_word("머나이다").unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).eq(["멀다"])
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["나이다"])
        })
        .unwrap();
    let annotation = dictionary.annotate(&word).unwrap();
    let assessment = annotation.assess(a);
    assert_eq!(assessment.status, Compatibility::Compatible);
    for (id, status) in [
        ("krdict:54855", Compatibility::Compatible),
        ("krdict:26833", Compatibility::Incompatible),
    ] {
        let evidence = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == id)
            .unwrap();
        assert_eq!(evidence.status, status);
        if status == Compatibility::Incompatible {
            assert!(
                evidence
                    .conflicts
                    .iter()
                    .any(|c| c.rule == AttachmentRule::BareLiteraryDeclarative
                        && c.morpheme_index == Some(0))
            );
        } else {
            assert!(evidence.conflicts.is_empty());
        }
    }
    let mut filtered = word.clone();
    let mut annotation = annotation;
    annotation.filter(&mut filtered, DictionaryFilter::Compatible);
    assert!(filtered.analyses.contains(a));
}

#[test]
fn expressive_hada_checks_each_lexical_homonym_and_negative_dependency() {
    let fixture = Fixture::new("expressive");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 0);
    let engine = Lemmatizer::new();
    for (surface, head, _connector, status) in [
        ("커한다", "크다", 0, Compatibility::Compatible),
        ("읽지않아한다", "읽다", 1, Compatibility::Unknown),
        ("읽지는않아한다", "읽다", 2, Compatibility::Unknown),
        ("잘해서", "자다", 0, Compatibility::Unknown),
        ("꺼려한다", "꺼리다", 0, Compatibility::Unknown),
        ("내키지않아한다", "내키다", 1, Compatibility::Unknown),
        ("먹어한다", "먹다", 0, Compatibility::Unknown),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas[0].text == head
                    && a.lemmas.last().unwrap().kind == LemmaKind::Auxiliary
                    && a.lemmas.last().unwrap().text == "하다"
            })
            .unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let assessment = annotation.assess(a);
        assert_eq!(assessment.status, status, "{surface}");
        let matched = annotation
            .lemmas
            .iter()
            .find(|m| m.lemma == a.lemmas[0])
            .unwrap();
        let mut verbs = 0;
        for entry in &matched.entries {
            let evidence = assessment.lemmas[0]
                .entries
                .iter()
                .find(|e| e.id == entry.entry.id)
                .unwrap();
            if entry.entry.pos == "동사" {
                verbs += 1;
                assert_eq!(evidence.status, Compatibility::Unknown);
                assert!(evidence.conflicts.is_empty());
            } else if entry.entry.pos == "형용사" {
                assert_eq!(evidence.status, Compatibility::Compatible);
            } else if entry.entry.pos == "보조 동사" {
                assert_eq!(evidence.status, Compatibility::Unknown);
            }
        }
        assert!(verbs > 0);
        // An unrelated nominal homonym conflicts with the lexical role; an
        // unrecognized provider POS must remain unknown instead of guessed.
        let mut changed = annotation.clone();
        let entries = &mut changed
            .lemmas
            .iter_mut()
            .find(|m| m.lemma == a.lemmas[0])
            .unwrap()
            .entries;
        entries.retain(|e| e.entry.pos == "동사");
        assert_eq!(changed.assess(a).status, Compatibility::Unknown);
        let slot = changed
            .lemmas
            .iter_mut()
            .find(|m| m.lemma == a.lemmas[0])
            .unwrap();
        for entry in &mut slot.entries {
            entry.entry.pos = "명사".into();
            entry.pos_compatibility = pos_compatibility(&slot.lemma, &entry.entry);
        }
        assert_eq!(changed.assess(a).status, Compatibility::Incompatible);
        let slot = changed
            .lemmas
            .iter_mut()
            .find(|m| m.lemma == a.lemmas[0])
            .unwrap();
        slot.entries[0].entry.pos = "unmapped provider class".into();
        slot.entries[0].pos_compatibility = pos_compatibility(&slot.lemma, &slot.entries[0].entry);
        assert_eq!(changed.assess(a).status, Compatibility::Unknown);
        let mut retained = word.clone();
        changed.filter(&mut retained, DictionaryFilter::Compatible);
        assert!(retained.analyses.contains(a));
    }
    // The uncertainty belongs to this attachment, not every earlier verb or
    // every use of 하다. A new auxiliary class owns its following connector.
    for surface in ["읽고싶어한다", "읽게한다", "읽어야한다", "읽어보려한다"] {
        let word = engine.analyze_word(surface).unwrap();
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas[0].text == "읽다"
                    && a.lemmas.last().unwrap().kind == LemmaKind::Auxiliary
                    && a.lemmas.last().unwrap().text == "하다"
            })
            .unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let assessment = annotation.assess(a);
        assert_eq!(
            assessment.lemmas[0].status,
            Compatibility::Compatible,
            "{surface}"
        );
        assert!(
            assessment.lemmas[0]
                .entries
                .iter()
                .all(|e| e.status == Compatibility::Compatible)
        );
    }
}

#[test]
fn connective_attachment_checks_preserve_homonyms_and_unknown_classes() {
    let fixture = Fixture::new("connective-evidence");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    let cases: Vec<_> = suite()
        .cases
        .into_iter()
        .filter(|c| c.id.starts_with("attachment-connectives-") && c.id.ends_with("-homonym"))
        .collect();
    assert_eq!(cases.len(), 13);
    for case in cases {
        let word = engine.analyze_word(&case.surface).unwrap();
        let form = &case.judgments[0].morphemes.as_ref().unwrap()[0];
        let a = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].text == "크다"
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == *form
            })
            .unwrap();
        let mut annotation = dictionary.annotate(&word).unwrap();
        let assessed = annotation.assess(a);
        assert_eq!(assessed.status, Compatibility::Compatible);
        let entries = &assessed.lemmas[0].entries;
        let verb = entries.iter().find(|e| e.id == "krdict:66584").unwrap();
        assert_eq!(verb.status, Compatibility::Compatible);
        let adjective = entries.iter().find(|e| e.id == "krdict:66586").unwrap();
        assert_eq!(adjective.status, Compatibility::Incompatible);
        assert_eq!(adjective.conflicts.len(), 1);
        assert_eq!(adjective.conflicts[0].morpheme_index, Some(0));
        assert_eq!(
            adjective.conflicts[0].rule,
            if matches!(form.as_str(), "어다" | "어다가") {
                AttachmentRule::ResultTransferVerb
            } else {
                AttachmentRule::IntentionVerb
            }
        );

        // Unknown provider classes cannot be replaced by another homonym's
        // known adjective class; each entry supplies its own evidence.
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
        let mut filtered = word.clone();
        annotation.filter(&mut filtered, DictionaryFilter::Compatible);
        assert!(filtered.analyses.contains(a));

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
    }
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

#[test]
fn copular_endings_distinguish_lexical_ida_and_keep_unknown_entry_classes() {
    let fixture = Fixture::new("copular-class");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let engine = Lemmatizer::new();
    for surface in ["이라고", "누이라고밖에"] {
        let word = engine.analyze_word(surface).unwrap();
        let annotation = dictionary.annotate(&word).unwrap();
        let factual = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 1
                    && a.lemmas[0].kind == LemmaKind::Predicate
                    && a.morphemes[0].form == "라고"
            })
            .unwrap();
        let evidence = annotation.assess(factual);
        assert_eq!(evidence.status, Compatibility::Incompatible);
        for entry in &evidence.lemmas[0].entries {
            assert_eq!(entry.status, Compatibility::Incompatible);
            let expected = if matches!(
                entry.id.as_str(),
                "krdict:92457" | "krdict:45654" | "krdict:45655"
            ) {
                (AttachmentRule::BareCopularEnding, Some(0))
            } else {
                (AttachmentRule::LexicalRole, None)
            };
            assert!(
                entry
                    .conflicts
                    .iter()
                    .any(|c| (c.rule, c.morpheme_index) == expected),
                "{entry:?}"
            );
        }
        let copula = word
            .analyses
            .iter()
            .find(|a| {
                a.lemmas.len() == 2
                    && a.lemmas[1].kind == LemmaKind::Copula
                    && a.morphemes[0].form == "라고"
            })
            .unwrap();
        let copula_evidence = annotation.assess(copula);
        let entries = &copula_evidence.lemmas[1].entries;
        assert_eq!(
            entries
                .iter()
                .find(|e| e.id == "krdict:86232")
                .unwrap()
                .status,
            Compatibility::Compatible
        );
        assert_eq!(
            entries
                .iter()
                .find(|e| e.id == "krdict:92457")
                .unwrap()
                .status,
            Compatibility::Incompatible
        );

        // Synthetic provider boundaries: no known entry may lend its POS to
        // another homonym. Standalone auxiliary and unmapped POS stay unknown.
        for (pos, expected) in [
            ("형용사", Compatibility::Incompatible),
            ("보조 동사", Compatibility::Unknown),
            ("보조 형용사", Compatibility::Unknown),
            ("provider-specific", Compatibility::Unknown),
        ] {
            let mut changed = annotation.clone();
            let slot = changed
                .lemmas
                .iter_mut()
                .find(|m| m.lemma == factual.lemmas[0])
                .unwrap();
            let entry = slot
                .entries
                .iter_mut()
                .find(|e| e.entry.pos == "동사")
                .unwrap();
            entry.entry.pos = pos.into();
            entry.pos_compatibility = pos_compatibility(&slot.lemma, &entry.entry);
            let assessment = changed.assess(factual);
            assert_eq!(assessment.status, expected, "{surface}: {pos}");
            let mut filtered = word.clone();
            changed.filter(&mut filtered, DictionaryFilter::Compatible);
            assert_eq!(
                filtered.analyses.contains(factual),
                expected != Compatibility::Incompatible
            );
        }
        let mut missing = annotation.clone();
        missing.lemmas.retain(|m| m.lemma != factual.lemmas[0]);
        assert_eq!(missing.assess(factual).status, Compatibility::Unknown);
        let mut filtered = word.clone();
        missing.filter(&mut filtered, DictionaryFilter::Compatible);
        assert!(!filtered.analyses.contains(factual));
    }
}
