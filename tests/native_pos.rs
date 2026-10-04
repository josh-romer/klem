//! Independently sourced class evidence must belong to the reviewed entry and
//! component. Native fields, raw hypotheses and unknown boundaries survive.
#[path = "../tools/adjectival_allomorph.rs"]
mod allomorph;
use klem::dictionary::{
    Annotation, AttachmentRule, Compatibility, Dictionary, DictionaryFilter, DictionaryMetadata,
    DictionarySession, Entry, EntrySummary, SqliteDictionary, import_krdict,
};
use klem::{Analysis, LemmaKind, Lemmatizer, WordAnalysis};
use serde_json::Value;
use std::{cell::Cell, fs, path::PathBuf, process::Command};
use unicode_normalization::UnicodeNormalization;

fn sources() -> Value {
    let mut source: Value =
        serde_json::from_str(include_str!("fixtures/native-pos-sources.json")).unwrap();
    let additional: Value =
        serde_json::from_str(include_str!("fixtures/native-pos-boundaries.json")).unwrap();
    for (surface, word) in additional["before_words"].as_object().unwrap() {
        if let Some(original) = source["before_words"].get(surface) {
            assert_eq!(original, word);
        }
        source["before_words"]
            .as_object_mut()
            .unwrap()
            .insert(surface.clone(), word.clone());
    }
    source
}
fn native() -> Entry {
    serde_json::from_value(sources()["source_entries"][0].clone()).unwrap()
}
struct Fixture(PathBuf);
impl Fixture {
    fn new(tag: &str) -> Self {
        let path =
            std::env::temp_dir().join(format!("klem-native-pos-{tag}-{}.db", std::process::id()));
        let copular: Value =
            serde_json::from_str(include_str!("fixtures/krdict-copular-class.json")).unwrap();
        let selected: Vec<_> = copular["LexicalResource"]["Lexicon"]["LexicalEntry"]
            .as_array()
            .unwrap()
            .iter()
            .filter(|e| ["86118", "86232", "92457"].contains(&e["val"].as_str().unwrap()))
            .cloned()
            .collect();
        let input = path.with_extension("json");
        fs::write(
            &input,
            serde_json::to_vec(
                &serde_json::json!({"LexicalResource": {"Lexicon": {"LexicalEntry": selected}}}),
            )
            .unwrap(),
        )
        .unwrap();
        import_krdict(
            &[
                PathBuf::from("tests/fixtures/krdict-source-head.json"),
                PathBuf::from("tests/fixtures/krdict-auxiliary-inventory.json"),
                input.clone(),
            ],
            &path,
            "native-pos-review",
        )
        .unwrap();
        fs::remove_file(input).unwrap();
        Self(path)
    }
    fn open(&self) -> SqliteDictionary {
        SqliteDictionary::open(&self.0).unwrap()
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.0);
    }
}

// Explicit adapter test controls, not alternative upstream exports. The full
// native entry stays separately frozen in the source fixture.
struct Provider {
    metadata: DictionaryMetadata,
    entries: Vec<Entry>,
    summaries: Vec<EntrySummary>,
    lookups: Cell<usize>,
    details: Cell<usize>,
}
impl Provider {
    fn new(dictionary: &SqliteDictionary, entries: Vec<Entry>) -> Self {
        let summaries = entries.iter().map(|e| e.summary.clone()).collect();
        Self {
            metadata: dictionary.metadata().clone(),
            entries,
            summaries,
            lookups: Cell::new(0),
            details: Cell::new(0),
        }
    }
}
impl Dictionary for Provider {
    fn metadata(&self) -> &DictionaryMetadata {
        &self.metadata
    }
    fn fingerprint(&self) -> &str {
        "authored-native-pos-adapter-control"
    }
    fn lookup(&self, head: &str) -> klem::dictionary::Result<Vec<EntrySummary>> {
        self.lookups.set(self.lookups.get() + 1);
        Ok(self
            .summaries
            .iter()
            .filter(|e| e.headword == head)
            .cloned()
            .collect())
    }
    fn entry(&self, id: &str) -> klem::dictionary::Result<Option<Entry>> {
        self.details.set(self.details.get() + 1);
        Ok(self.entries.iter().find(|e| e.summary.id == id).cloned())
    }
}
fn only_head(annotation: &Annotation) -> &klem::dictionary::EntryMatch {
    &annotation
        .lemmas
        .iter()
        .find(|m| m.lemma.text == "발그스레하다" && m.lemma.kind == LemmaKind::Predicate)
        .unwrap()
        .entries[0]
}
fn path<'a>(word: &'a WordAnalysis, heads: &[&str], forms: &[&str]) -> &'a Analysis {
    word.analyses
        .iter()
        .find(|a| {
            a.lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(heads.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
        })
        .unwrap_or_else(|| panic!("{}: {heads:?} {forms:?}", word.normalized))
}

#[test]
fn full_native_import_and_independent_evidence_keep_their_own_identities() {
    let fixture = Fixture::new("identity");
    let dictionary = fixture.open();
    let entry = dictionary.entry("krdict:600930").unwrap().unwrap();
    let mut expected = native();
    for sense in &mut expected.senses {
        sense.translations.retain(|t| t.language == "영어");
    }
    assert_eq!(entry, expected);
    let word = Lemmatizer::new().analyze_word("발그스레하냐").unwrap();
    let mut session = DictionarySession::new(&dictionary, 4096);
    let annotated = session.annotate(&word).unwrap();
    let matched = only_head(&annotated);
    assert_eq!(matched.entry, entry.summary);
    assert_eq!(matched.entry.pos, "동사");
    assert_eq!(matched.effective_pos(), "형용사");
    let evidence = matched.independent_pos.as_ref().unwrap();
    let source = sources();
    assert_eq!(evidence.source_id, "opendict:569243");
    assert_eq!(evidence.source_url, source["primary"]["url"]);
    assert_eq!(
        evidence.source_response_sha256,
        source["primary"]["html_sha256"]
    );
    assert_eq!(
        evidence.native_profile_sha256,
        source["native_profile_sha256"]
    );
    assert_eq!(dictionary.entry("krdict:600930").unwrap().unwrap(), entry);
    // All-language and English-only imports share Korean source evidence.
    let full = Provider::new(&dictionary, vec![native()]);
    assert_eq!(
        only_head(&DictionarySession::new(&full, 0).annotate(&word).unwrap()),
        matched
    );
}

#[test]
fn sparse_updated_or_mismatched_profiles_and_homonyms_do_not_borrow_evidence() {
    let fixture = Fixture::new("guards");
    let dictionary = fixture.open();
    let word = Lemmatizer::new().analyze_word("발그스레하느냐").unwrap();
    let original = native();
    let mut mutations = Vec::new();
    macro_rules! mutate {
        ($field:expr) => {{
            let mut e = original.clone();
            ($field)(&mut e);
            mutations.push(e);
        }};
    }
    mutate!(|e: &mut Entry| e.summary.id = "other:600930".into());
    mutate!(|e: &mut Entry| e.summary.homonym = "1".into());
    mutate!(|e: &mut Entry| e.summary.pos = "형용사".into());
    mutate!(|e: &mut Entry| e.url.push_str("&updated=1"));
    mutate!(|e: &mut Entry| e.level.clear());
    mutate!(|e: &mut Entry| e.lexical_unit.clear());
    mutate!(|e: &mut Entry| e.origins.push("別".into()));
    mutate!(|e: &mut Entry| e.notes.push("new source note".into()));
    mutate!(|e: &mut Entry| e.forms.clear());
    mutate!(|e: &mut Entry| e.forms[1].written = "발그스레하는".into());
    mutate!(|e: &mut Entry| e.forms[0].pronunciations.clear());
    mutate!(|e: &mut Entry| e.forms[4].written = "발그스레합니다".into());
    mutate!(|e: &mut Entry| e.senses.clear());
    mutate!(|e: &mut Entry| e.senses[0].id = "2".into());
    mutate!(|e: &mut Entry| e.senses[0].definition.clear());
    mutate!(|e: &mut Entry| e.senses[0].examples.pop());
    mutate!(|e: &mut Entry| e.senses[0].notes.push("new sense note".into()));
    mutate!(|e: &mut Entry| e.senses[0].patterns.clear());
    for entry in mutations {
        let provider = Provider::new(&dictionary, vec![entry.clone()]);
        let annotated = DictionarySession::new(&provider, 0)
            .annotate(&word)
            .unwrap();
        let matched = only_head(&annotated);
        assert!(matched.independent_pos.is_none(), "{entry:?}");
        assert_eq!(matched.effective_pos(), entry.summary.pos);
    }
    let mut mismatch = Provider::new(&dictionary, vec![original.clone()]);
    mismatch.entries[0].summary.pos = "형용사".into();
    assert!(
        only_head(
            &DictionarySession::new(&mismatch, 0)
                .annotate(&word)
                .unwrap()
        )
        .independent_pos
        .is_none()
    );
    let mut absent = Provider::new(&dictionary, vec![original.clone()]);
    absent.entries.clear();
    assert!(
        only_head(&DictionarySession::new(&absent, 0).annotate(&word).unwrap())
            .independent_pos
            .is_none()
    );

    let mut homonym = original.clone();
    homonym.summary.id = "test:homonym".into();
    homonym.summary.homonym = "1".into();
    let provider = Provider::new(&dictionary, vec![original, homonym]);
    let annotated = DictionarySession::new(&provider, 0)
        .annotate(&word)
        .unwrap();
    let a = path(&word, &["발그스레하다"], &["느냐"]);
    let assessed = annotated.assess(a);
    let entries = &assessed.lemmas[0].entries;
    assert_eq!(entries[0].status, Compatibility::Incompatible);
    assert_eq!(entries[1].status, Compatibility::Compatible);
    assert!(entries[1].conflicts.is_empty());
    assert_eq!(
        entries[0].conflicts[0].rule,
        AttachmentRule::BareVerbalQuestion
    );
    assert_eq!(entries[0].conflicts[0].morpheme_index, Some(0));
}

#[test]
fn legacy_serialization_cache_and_coarse_roles_preserve_their_original_scope() {
    let fixture = Fixture::new("legacy");
    let dictionary = fixture.open();
    let provider = Provider::new(&dictionary, vec![native()]);
    let word = Lemmatizer::new().analyze_word("발그스레하느냐").unwrap();
    let mut cached = DictionarySession::new(&provider, 8192);
    let annotated = cached.annotate(&word).unwrap();
    let detail_calls = provider.details.get();
    let lookup_calls = provider.lookups.get();
    assert!(cached.cache_bytes() > 0 && cached.cache_bytes() <= 8192);
    assert_eq!(annotated, cached.annotate(&word).unwrap());
    assert_eq!(provider.details.get(), detail_calls);
    assert_eq!(provider.lookups.get(), lookup_calls);
    assert_eq!(
        annotated,
        DictionarySession::new(&provider, 0)
            .annotate(&word)
            .unwrap()
    );
    assert_eq!(
        serde_json::from_value::<Annotation>(serde_json::to_value(&annotated).unwrap()).unwrap(),
        annotated
    );
    let mut legacy = serde_json::to_value(&annotated).unwrap();
    for slot in legacy["lemmas"].as_array_mut().unwrap() {
        for e in slot["entries"].as_array_mut().unwrap() {
            e.as_object_mut().unwrap().remove("independent_pos");
        }
    }
    let legacy: Annotation = serde_json::from_value(legacy).unwrap();
    assert_eq!(only_head(&legacy).effective_pos(), "동사");
    assert_eq!(
        legacy
            .assess(path(&word, &["발그스레하다"], &["느냐"]))
            .status,
        Compatibility::Compatible
    );
    assert_eq!(
        annotated
            .assess(path(&word, &["발그스레하다"], &["느냐"]))
            .status,
        Compatibility::Incompatible
    );
    let mut malformed = only_head(&annotated).clone();
    malformed.independent_pos.as_mut().unwrap().source_id = "other:569243".into();
    assert_eq!(malformed.effective_pos(), "동사");
    malformed = only_head(&annotated).clone();
    malformed.entry.homonym = "2".into();
    assert_eq!(malformed.effective_pos(), "동사");
    // Independent adjective evidence cannot turn a nominal role into unknown.
    let nominal = Lemmatizer::new().analyze_word("발그스레하다를").unwrap();
    let ann = cached.annotate(&nominal).unwrap();
    let a = nominal
        .analyses
        .iter()
        .find(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "발그스레하다"
                && a.lemmas[0].kind == LemmaKind::Nominal
        })
        .unwrap();
    assert_eq!(ann.assess(a).status, Compatibility::Incompatible);
    assert_eq!(
        ann.assess(a).lemmas[0].entries[0].conflicts[0].rule,
        AttachmentRule::LexicalRole
    );
}

#[test]
fn frozen_raw_paths_and_all_forty_six_class_controls_agree_without_rewriting_pos() {
    let fixture = Fixture::new("frozen");
    let dictionary = fixture.open();
    let provider = Provider::new(&dictionary, vec![native()]);
    let mut session = DictionarySession::new(&provider, 4096);
    let engine = Lemmatizer::new();
    let source = sources();
    let policy: Value =
        serde_json::from_str(include_str!("fixtures/native-pos-policy.json")).unwrap();
    let ledger: Value =
        serde_json::from_str(include_str!("fixtures/dictionary-attachments.json")).unwrap();
    assert_eq!(policy["primary"], source["primary"]);
    assert_eq!(
        policy["native_profile_sha256"],
        source["native_profile_sha256"]
    );
    let corrections: Value = serde_json::from_str(include_str!(
        "fixtures/adjectival-allomorph-policy-corrections.json"
    ))
    .unwrap();
    let role_additions: Value =
        serde_json::from_str(include_str!("fixtures/doeda-role-historical.json")).unwrap();
    for case in policy["cases"].as_array().unwrap() {
        let corrected = corrections["superseded"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["original"]["id"] == case["id"]);
        let expected = if let Some(change) = corrected {
            assert_eq!(change["original"], *case);
            &change["replacement"]
        } else {
            case
        };
        assert_eq!(
            ledger["cases"]
                .as_array()
                .unwrap()
                .iter()
                .find(|c| c["id"] == case["id"])
                .unwrap(),
            expected
        );
    }
    for (surface, frozen) in source["before_words"].as_object().unwrap() {
        let word = engine.analyze_word(surface).unwrap();
        let mut expected: WordAnalysis = serde_json::from_value(frozen.clone()).unwrap();
        expected
            .analyses
            .retain(|a| !allomorph::reviewed_removal(a));
        if let Some(change) = role_additions["changes"]
            .as_array()
            .unwrap()
            .iter()
            .find(|r| r["surface"] == surface.as_str())
        {
            // Keep the original snapshot and the earlier spelling correction
            // separate. Only this explicit source-backed role overlay advances
            // the expected output; the old class judgments below stay intact.
            assert_eq!(change["original"], *frozen);
            assert_eq!(serde_json::to_value(&expected).unwrap(), change["before"]);
            assert_eq!(serde_json::to_value(&word).unwrap(), change["after"]);
            let retained: Vec<_> = word
                .analyses
                .iter()
                .filter(|a| expected.analyses.contains(a))
                .cloned()
                .collect();
            assert_eq!(retained, expected.analyses);
            assert!(
                word.analyses
                    .iter()
                    .filter(|a| !expected.analyses.contains(a))
                    .all(|a| a.rules.iter().any(|r| r == "lexical.doeda.complement"))
            );
        } else {
            assert_eq!(word, expected, "{surface}");
        }
        assert_eq!(
            word,
            engine
                .analyze_word(&surface.nfd().collect::<String>())
                .unwrap()
        );
        assert!(
            word.analyses.iter().all(|a| a.breakdown().is_some()),
            "{surface}"
        );
        if let Some(expected) = source["isolated_adjective_controls"].get(surface) {
            let mut filtered = word.clone();
            let mut annotation = session.annotate(&word).unwrap();
            for entry in annotation.lemmas.iter().flat_map(|m| &m.entries) {
                assert_eq!(entry.entry.pos, "동사");
                assert_eq!(entry.effective_pos(), "형용사");
            }
            annotation.filter(&mut filtered, DictionaryFilter::Compatible);
            assert_eq!(
                filtered.analyses,
                serde_json::from_value::<Vec<Analysis>>(expected.clone())
                    .unwrap()
                    .into_iter()
                    .filter(|a| !allomorph::reviewed_removal(a))
                    .collect::<Vec<_>>(),
                "{surface}"
            );
        }
    }
}

#[test]
fn cli_and_library_agree_on_every_diagnostic_in_all_three_modes() {
    let fixture = Fixture::new("cli");
    let dictionary = fixture.open();
    let mut session = DictionarySession::new(&dictionary, 4096);
    let engine = Lemmatizer::new();
    for surface in sources()["before_words"].as_object().unwrap().keys() {
        for (flag, filter) in [
            (None, None),
            (Some("--dict-only"), Some(DictionaryFilter::Headword)),
            (
                Some("--dict-compatible"),
                Some(DictionaryFilter::Compatible),
            ),
        ] {
            let mut word = engine.analyze_word(surface).unwrap();
            let mut annotation = session.annotate(&word).unwrap();
            if let Some(filter) = filter {
                annotation.filter(&mut word, filter);
            }
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command
                .args(["word", surface, "--dictionary"])
                .arg(&fixture.0);
            if let Some(flag) = flag {
                command.arg(flag);
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let mut actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual
                    .as_object_mut()
                    .unwrap()
                    .remove("dictionary")
                    .unwrap(),
                serde_json::to_value(&annotation).unwrap(),
                "{surface} {flag:?}"
            );
            assert_eq!(
                actual,
                serde_json::to_value(&word).unwrap(),
                "{surface} {flag:?}"
            );
        }
    }
}

#[test]
fn reviewed_class_checks_every_boundary_and_negative_owner_without_crossing_later_owners() {
    let fixture = Fixture::new("owners");
    let dictionary = fixture.open();
    let mut session = DictionarySession::new(&dictionary, 8192);
    let engine = Lemmatizer::new();
    // Existing finite attachment policies already have independent sources.
    // Here their class premise comes from the reviewed adjective, not the
    // contradictory native label. No new register/grammar restriction.
    for (surface, forms, status, rule) in [
        ("발그스레하냐", vec!["냐"], Compatibility::Compatible, None),
        (
            "발그스레하구나",
            vec!["구나"],
            Compatibility::Compatible,
            None,
        ),
        (
            "발그스레하는",
            vec!["는"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BarePresentAdnominalClass),
        ),
        (
            "발그스레하느냐",
            vec!["느냐"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BareVerbalQuestion),
        ),
        (
            "발그스레한다",
            vec!["는다"],
            Compatibility::Incompatible,
            Some(AttachmentRule::PresentDeclarativeVerb),
        ),
        (
            "발그스레하단다",
            vec!["단다"],
            Compatibility::Compatible,
            None,
        ),
        (
            "발그스레하느니라",
            vec!["느니라"],
            Compatibility::Incompatible,
            Some(AttachmentRule::LiteraryAssertionClass),
        ),
        (
            "발그스레하나이다",
            vec!["나이다"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BareLiteraryDeclarative),
        ),
        (
            "발그스레하나이까",
            vec!["나이까"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BareLiteraryQuestion),
        ),
        (
            "발그스레하느냐면",
            vec!["느냐면"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BareVerbalQuestion),
        ),
        (
            "발그스레하는구나",
            vec!["는구나"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BareExclamationVerb),
        ),
        (
            "발그스레하는걸",
            vec!["는걸"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BareGeolVerb),
        ),
        (
            "발그스레하느니",
            vec!["느니"],
            Compatibility::Incompatible,
            Some(AttachmentRule::BareNeuniVerb),
        ),
        (
            "발그스레하니만",
            vec!["니만"],
            Compatibility::Compatible,
            None,
        ),
        (
            "발그스레하려다가",
            vec!["으려다가"],
            Compatibility::Incompatible,
            Some(AttachmentRule::IntentionVerb),
        ),
        (
            "발그스레하느라",
            vec!["느라"],
            Compatibility::Incompatible,
            Some(AttachmentRule::NeuraVerb),
        ),
        (
            "발그스레할라치면",
            vec!["을라치면"],
            Compatibility::Incompatible,
            Some(AttachmentRule::HabitualConditionVerb),
        ),
        ("발그스레하거라", vec!["거라"], Compatibility::Unknown, None),
        (
            "발그스레합시다",
            vec!["읍시다"],
            Compatibility::Unknown,
            None,
        ),
        (
            "발그스레하자는구나",
            vec!["자는구나"],
            Compatibility::Unknown,
            None,
        ),
        (
            "발그스레하라는구나",
            vec!["으라는구나"],
            Compatibility::Unknown,
            None,
        ),
        (
            "발그스레하시느냐면",
            vec!["시", "느냐면"],
            Compatibility::Unknown,
            None,
        ),
        (
            "발그스레하였느냐",
            vec!["었", "느냐"],
            Compatibility::Compatible,
            None,
        ),
        (
            "발그스레하였구나",
            vec!["었", "구나"],
            Compatibility::Compatible,
            None,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let annotation = session.annotate(&word).unwrap();
        let a = path(&word, &["발그스레하다"], &forms);
        let assessed = annotation.assess(a);
        let entry = &assessed.lemmas[0].entries[0];
        assert_eq!(entry.id, "krdict:600930");
        assert_eq!(entry.status, status, "{surface}");
        assert_eq!(entry.conflicts.first().map(|c| c.rule), rule, "{surface}");
        if rule.is_some() {
            assert_eq!(entry.conflicts[0].morpheme_index, Some(0), "{surface}");
        }
        let mut filtered = word.clone();
        let mut ann = annotation.clone();
        ann.filter(&mut filtered, DictionaryFilter::Compatible);
        assert_eq!(
            filtered.analyses.contains(a),
            status != Compatibility::Incompatible,
            "{surface}"
        );
    }
    for (surface, ending, status, rule) in [
        (
            "발그스레하지않는",
            "는",
            Compatibility::Incompatible,
            Some(AttachmentRule::AuxiliaryAdjectiveAdnominalClass),
        ),
        (
            "발그스레하지않느냐",
            "느냐",
            Compatibility::Incompatible,
            Some(AttachmentRule::BareVerbalQuestion),
        ),
        (
            "발그스레하지않으냐",
            "으냐",
            Compatibility::Compatible,
            None,
        ),
        (
            "발그스레하지않느냐면",
            "느냐면",
            Compatibility::Unknown,
            None,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let annotation = session.annotate(&word).unwrap();
        let a = path(&word, &["발그스레하다", "않다"], &["지", ending]);
        let assessed = annotation.assess(a);
        assert_eq!(
            assessed.lemmas[0].entries[0].status,
            Compatibility::Compatible
        );
        let adjective = assessed.lemmas[1]
            .entries
            .iter()
            .find(|e| e.id == "krdict:71583")
            .unwrap();
        assert_eq!(adjective.status, status, "{surface}");
        assert_eq!(
            adjective.conflicts.first().map(|c| c.rule),
            rule,
            "{surface}"
        );
        if rule.is_some() {
            assert_eq!(adjective.conflicts[0].morpheme_index, Some(1));
        }
        let verb = assessed.lemmas[1]
            .entries
            .iter()
            .find(|e| e.id == "krdict:71581")
            .unwrap();
        assert_eq!(verb.conflicts[0].rule, AttachmentRule::NegativeLexicalClass);
        assert_eq!(verb.conflicts[0].morpheme_index, Some(0));
        assert!(
            annotation
                .lemmas
                .iter()
                .filter(|m| m.lemma.text != "발그스레하다")
                .flat_map(|m| &m.entries)
                .all(|e| e.independent_pos.is_none())
        );
    }
    // Later verbal 하다 owns 는. It must not be pruned by the left adjective.
    let word = engine.analyze_word("발그스레해하는").unwrap();
    let annotation = session.annotate(&word).unwrap();
    let a = path(&word, &["발그스레하다", "하다"], &["어", "는"]);
    assert_eq!(
        annotation.assess(a).lemmas[0].entries[0].status,
        Compatibility::Compatible
    );
    let right = annotation.assess(a);
    assert_eq!(
        right.lemmas[1]
            .entries
            .iter()
            .find(|e| e.id == "krdict:62888")
            .unwrap()
            .status,
        Compatibility::Compatible
    );

    // Compare every diagnostic to an explicitly authored adjective adapter.
    // This also catches any class gate still consulting the native label.
    let mut entries = vec![native()];
    for head in ["않다", "못하다", "아니하다", "하다"] {
        entries.extend(
            dictionary
                .lookup(head)
                .unwrap()
                .into_iter()
                .map(|e| dictionary.entry(&e.id).unwrap().unwrap()),
        );
    }
    let evidence = Provider::new(&dictionary, entries.clone());
    entries[0].summary.pos = "형용사".into();
    let control = Provider::new(&dictionary, entries);
    let mut evidenced = DictionarySession::new(&evidence, 8192);
    let mut controlled = DictionarySession::new(&control, 8192);
    for surface in sources()["before_words"].as_object().unwrap().keys() {
        let word = engine.analyze_word(surface).unwrap();
        assert_eq!(
            evidenced.annotate(&word).unwrap().readings,
            controlled.annotate(&word).unwrap().readings,
            "{surface}"
        );
    }
}

#[test]
fn additional_class_sensitive_boundaries_keep_prefinals_and_later_owners_separate() {
    let fixture = Fixture::new("additional");
    let dictionary = fixture.open();
    let mut session = DictionarySession::new(&dictionary, 8192);
    let engine = Lemmatizer::new();
    for (surface, heads, forms, rule, boundary) in [
        (
            "발그스레해다",
            vec!["발그스레하다"],
            vec!["어다"],
            AttachmentRule::ResultTransferVerb,
            0,
        ),
        (
            "발그스레해다가",
            vec!["발그스레하다"],
            vec!["어다가"],
            AttachmentRule::ResultTransferVerb,
            0,
        ),
        (
            "발그스레하는듯하다",
            vec!["발그스레하다", "듯하다"],
            vec!["는", "다"],
            AttachmentRule::ConjecturalAdnominalClass,
            0,
        ),
        (
            "발그스레하는듯싶다",
            vec!["발그스레하다", "듯싶다"],
            vec!["는", "다"],
            AttachmentRule::ConjecturalAdnominalClass,
            0,
        ),
        (
            "발그스레하는척하다",
            vec!["발그스레하다", "척하다"],
            vec!["는", "다"],
            AttachmentRule::PretenceAdnominalClass,
            0,
        ),
        (
            "발그스레하는양하다",
            vec!["발그스레하다", "양하다"],
            vec!["는", "다"],
            AttachmentRule::PretenceAdnominalClass,
            0,
        ),
        (
            "발그스레하는체하다",
            vec!["발그스레하다", "체하다"],
            vec!["는", "다"],
            AttachmentRule::PretenceAdnominalClass,
            0,
        ),
        (
            "발그스레해대는",
            vec!["발그스레하다", "대다"],
            vec!["어", "는"],
            AttachmentRule::RepetitiveVerb,
            0,
        ),
        (
            "발그스레하지않아대는",
            vec!["발그스레하다", "않다", "대다"],
            vec!["지", "어", "는"],
            AttachmentRule::RepetitiveVerb,
            1,
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let ann = session.annotate(&word).unwrap();
        let a = path(&word, &heads, &forms);
        let assessed = ann.assess(a);
        let left = &assessed.lemmas[0].entries[0];
        assert_eq!(left.id, "krdict:600930");
        assert_eq!(left.status, Compatibility::Incompatible, "{surface}");
        assert_eq!(left.conflicts[0].rule, rule);
        assert_eq!(left.conflicts[0].morpheme_index, Some(boundary));
        assert!(
            a.lemmas.iter().all(|l| ann.has_match(l, false)),
            "{surface}: dictionary gap cannot establish a class conflict"
        );
    }
    for (surface, heads, forms) in [
        ("발그스레하였느니", vec!["발그스레하다"], vec!["었", "느니"]),
        ("발그스레하시느니", vec!["발그스레하다"], vec!["시", "느니"]),
        (
            "발그스레하시다더군요",
            vec!["발그스레하다"],
            vec!["시", "다더군요"],
        ),
        (
            "발그스레하였다는구나",
            vec!["발그스레하다"],
            vec!["었", "다는구나"],
        ),
        (
            "발그스레하시는척하다",
            vec!["발그스레하다", "척하다"],
            vec!["시", "는", "다"],
        ),
        (
            "발그스레함이로구나",
            vec!["발그스레하다", "이다"],
            vec!["음", "로구나"],
        ),
    ] {
        let word = engine.analyze_word(surface).unwrap();
        let ann = session.annotate(&word).unwrap();
        let a = path(&word, &heads, &forms);
        assert_eq!(
            ann.assess(a).lemmas[0].entries[0].status,
            Compatibility::Compatible,
            "{surface}"
        );
        assert!(ann.assess(a).lemmas[0].entries[0].conflicts.is_empty());
    }
    let word = engine.analyze_word("발그스레하지않으려고하는").unwrap();
    let ann = session.annotate(&word).unwrap();
    let a = path(
        &word,
        &["발그스레하다", "않다", "하다"],
        &["지", "으려고", "는"],
    );
    assert_eq!(
        ann.assess(a).lemmas[0].entries[0].status,
        Compatibility::Unknown
    );
    assert!(ann.assess(a).lemmas[0].entries[0].conflicts.is_empty());
}
