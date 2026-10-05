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
            "krdict-naikka.json",
            "krdict-rikka.json",
            "krdict-eumse.json",
            "krdict-ba.json",
            "krdict-neuni.json",
            "krdict-quoted-neuni.json",
            "krdict-neuni-comparison.json",
            "krdict-geol.json",
            "krdict-exclamation.json",
            "krdict-quoted-exclamation.json",
            "krdict-question-exclamation.json",
            "krdict-copular-command-exclamation.json",
            "krdict-proposal-exclamation.json",
            "krdict-conditional-question.json",
            "krdict-quote-followers.json",
            "krdict-proposal-audit.json",
            "krdict-complex-bieup.json",
            "krdict-source-head.json",
            "krdict-auxiliary-inventory.json",
            "krdict-continuation-left.json",
            "krdict-emphatic-ending.json",
            "krdict-doeda-complement.json",
            "krdict-doeda-suffix.json",
            "krdict-doeda-native.json",
        ] {
            let data: serde_json::Value = serde_json::from_slice(
                &fs::read(PathBuf::from("tests/fixtures").join(file)).unwrap(),
            )
            .unwrap();
            for entry in data["LexicalResource"]["Lexicon"]["LexicalEntry"]
                .as_array()
                .unwrap()
            {
                if file == "krdict-auxiliary-inventory.json"
                    && ![
                        "49988", "49985", "72226", "67248", "67249", "72227", "73991",
                    ]
                    .contains(&entry["val"].as_str().unwrap())
                {
                    continue;
                }
                if file == "krdict-source-head.json" && entry["val"] != "600930" {
                    continue;
                }
                if file == "krdict-complex-bieup.json"
                    && ![
                        "84853", "64511", "41140", "58034", "50935", "54086", "64728", "63307",
                        "89859", "14103", "77700", "71363",
                    ]
                    .contains(&entry["val"].as_str().unwrap())
                {
                    continue;
                }
                if matches!(
                    file,
                    "krdict-quote-followers.json" | "krdict-proposal-audit.json"
                ) {
                    let features = &entry["feat"];
                    let unit = features
                        .as_array()
                        .and_then(|fs| fs.iter().find(|f| f["att"] == "lexicalUnit"))
                        .or_else(|| (features["att"] == "lexicalUnit").then_some(features));
                    if !matches!(
                        unit.and_then(|u| u["val"].as_str()),
                        Some("단어" | "문법‧표현")
                    ) {
                        continue;
                    }
                }
                if matches!(
                    file,
                    "krdict-hieut-compatibility.json"
                        | "krdict-digeut-siot.json"
                        | "krdict-bieup.json"
                        | "krdict-reu.json"
                        | "krdict-short-stems.json"
                        | "krdict-jaop.json"
                        | "krdict-naikka.json"
                        | "krdict-rikka.json"
                        | "krdict-eumse.json"
                        | "krdict-ba.json"
                        | "krdict-neuni.json"
                        | "krdict-quoted-neuni.json"
                        | "krdict-neuni-comparison.json"
                        | "krdict-geol.json"
                        | "krdict-exclamation.json"
                        | "krdict-quoted-exclamation.json"
                        | "krdict-question-exclamation.json"
                        | "krdict-copular-command-exclamation.json"
                        | "krdict-proposal-exclamation.json"
                        | "krdict-conditional-question.json"
                        | "krdict-quote-followers.json"
                        | "krdict-proposal-audit.json"
                        | "krdict-complex-bieup.json"
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
    // COV-017bu explicitly corrects eight previously required aliases. The
    // already-forbidden 기다리냐느니 alias has the same sourced boundary.
    // These nine paths now fail generation. Later explicit structural controls
    // are identified below; all remaining lexical conflicts must still exist
    // before the optional dictionary filter is applied.
    let changes: serde_json::Value = serde_json::from_str(include_str!(
        "fixtures/adjectival-allomorph-policy-corrections.json"
    ))
    .unwrap();
    let mut structural_ids: Vec<_> = changes["superseded"]
        .as_array()
        .unwrap()
        .iter()
        .map(|r| r["replacement"]["id"].as_str().unwrap())
        .collect();
    structural_ids.push("quoted-neuni-policy-8");
    let emphatic: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/emphatic-ending-sources.json")).unwrap();
    let emphatic_boundaries: Vec<_> = emphatic["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["verdict"] == "forbidden")
        .map(|c| format!("{}-policy", c["id"].as_str().unwrap()))
        .collect();
    structural_ids.extend(emphatic_boundaries.iter().map(String::as_str));
    let doeda: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/doeda-role-sources.json")).unwrap();
    let doeda_boundaries: Vec<_> = doeda["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["scope"] == "connector_projection_boundary")
        .map(|c| format!("{}-policy", c["id"].as_str().unwrap()))
        .collect();
    // These three controls forbid only the new projection's provenance on
    // other connectors. They are absent in raw output as well as after filtering.
    assert_eq!(doeda_boundaries.len(), 3);
    structural_ids.extend(doeda_boundaries.iter().map(String::as_str));
    let complement: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/doeda-complement-sources.json")).unwrap();
    let corrections: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/doeda-complement-corrections.json")).unwrap();
    let mut complement_boundaries: Vec<_> = complement["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["verdict"] == "forbidden")
        .map(|c| format!("{}-policy", c["id"].as_str().unwrap()))
        .collect();
    complement_boundaries.extend(
        corrections["corrections"]
            .as_array()
            .unwrap()
            .iter()
            .map(|c| {
                format!(
                    "{}-policy",
                    c["replacement_control"]["id"].as_str().unwrap()
                )
            }),
    );
    let bridge: serde_json::Value = serde_json::from_str(include_str!(
        "fixtures/doeda-complement-bridge-boundaries.json"
    ))
    .unwrap();
    complement_boundaries.extend(
        bridge["cases"]
            .as_array()
            .unwrap()
            .iter()
            .map(|c| format!("{}-policy", c["id"].as_str().unwrap())),
    );
    assert_eq!(complement_boundaries.len(), 11);
    structural_ids.extend(complement_boundaries.iter().map(String::as_str));
    let suffix: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/doeda-suffix-sources.json")).unwrap();
    let suffix_corrections: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/doeda-suffix-corrections.json")).unwrap();
    let mut suffix_boundaries: Vec<_> = suffix["cases"]
        .as_array()
        .unwrap()
        .iter()
        .filter(|c| c["verdict"] == "forbidden")
        .map(|c| format!("{}-policy", c["id"].as_str().unwrap()))
        .collect();
    suffix_boundaries.extend(
        suffix_corrections["corrections"]
            .as_array()
            .unwrap()
            .iter()
            .map(|c| {
                format!(
                    "{}-policy",
                    c["replacement_control"]["id"].as_str().unwrap()
                )
            }),
    );
    assert_eq!(suffix_boundaries.len(), 20);
    structural_ids.extend(suffix_boundaries.iter().map(String::as_str));
    let mut structural = self::suite();
    structural
        .cases
        .retain(|c| structural_ids.contains(&c.id.as_str()));
    let boundaries = validity::evaluate(&structural).unwrap();
    assert!(boundaries.passed(), "{:?}", boundaries.violations);
    assert_eq!(
        (boundaries.required_total, boundaries.forbidden_total),
        (0, 66)
    );
    assert_eq!(
        raw.forbidden_present,
        raw.forbidden_total - boundaries.forbidden_total
    );
    assert_eq!(raw.required_present, raw.required_total);
    let headwords = validity::evaluate_with(&suite, |word| {
        let mut analysis = engine.analyze_word(word).unwrap();
        let mut annotation = dictionary.annotate(&analysis).unwrap();
        annotation.filter(&mut analysis, DictionaryFilter::Headword);
        Ok(analysis)
    })
    .unwrap();
    // A missing fixture headword must not masquerade as an attachment fix.
    assert_eq!(headwords.forbidden_present, raw.forbidden_present);
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
        (19728, 1994)
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
fn literary_naikka_keeps_compatible_homonyms_and_unknown_provider_classes() {
    let fixture = Fixture::new("naikka-homonyms");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let word = Lemmatizer::new().analyze_word("머나이까").unwrap();
    let a = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).eq(["멀다"])
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["나이까"])
        })
        .unwrap();
    let annotation = dictionary.annotate(&word).unwrap();
    let assessment = annotation.assess(a);
    assert_eq!(assessment.status, Compatibility::Compatible);
    let verb = assessment.lemmas[0]
        .entries
        .iter()
        .find(|e| e.id == "krdict:54855")
        .unwrap();
    assert_eq!(verb.status, Compatibility::Compatible);
    assert!(verb.conflicts.is_empty());
    let adjective = assessment.lemmas[0]
        .entries
        .iter()
        .find(|e| e.id == "krdict:26833")
        .unwrap();
    assert_eq!(adjective.status, Compatibility::Incompatible);
    assert!(
        adjective
            .conflicts
            .iter()
            .any(|c| c.rule == AttachmentRule::BareLiteraryQuestion && c.morpheme_index == Some(0))
    );
    let mut unknown = annotation.clone();
    let slot = unknown
        .lemmas
        .iter_mut()
        .find(|m| m.lemma == a.lemmas[0])
        .unwrap();
    slot.entries.retain(|e| e.entry.id == "krdict:26833");
    slot.entries[0].entry.pos = "unrecognized-provider-class".into();
    slot.entries[0].pos_compatibility = pos_compatibility(&slot.lemma, &slot.entries[0].entry);
    assert_eq!(unknown.assess(a).status, Compatibility::Unknown);
}

#[test]
fn literary_rikka_preserves_both_verbal_and_adjectival_homonyms() {
    let fixture = Fixture::new("rikka-homonyms");
    let db = fixture.open();
    let mut dictionary = DictionarySession::new(&db, 4096);
    let mut word = Lemmatizer::new().analyze_word("멀리까").unwrap();
    let analysis = word
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).eq(["멀다"])
                && a.morphemes.iter().map(|m| m.form.as_str()).eq(["으리까"])
        })
        .unwrap()
        .clone();
    let mut annotation = dictionary.annotate(&word).unwrap();
    let assessment = annotation.assess(&analysis);
    assert_eq!(assessment.status, Compatibility::Compatible);
    for id in ["krdict:54855", "krdict:26833"] {
        let evidence = assessment.lemmas[0]
            .entries
            .iter()
            .find(|e| e.id == id)
            .unwrap();
        assert_eq!(evidence.status, Compatibility::Compatible);
        assert!(evidence.conflicts.is_empty());
    }
    annotation.filter(&mut word, DictionaryFilter::Compatible);
    assert!(word.analyses.contains(&analysis));
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
