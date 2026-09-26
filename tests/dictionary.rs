use klem::dictionary::{
    Compatibility, Dictionary, DictionarySession, EntrySummary, SqliteDictionary, import_krdict,
    pos_compatibility,
};
use klem::{Lemma, LemmaKind, Lemmatizer};
use serde_json::{Value, json};
use std::{
    fs,
    path::PathBuf,
    process::Command,
    sync::atomic::{AtomicU64, Ordering},
};

struct Scratch(PathBuf);
impl Scratch {
    fn new() -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let dir = std::env::temp_dir().join(format!(
            "klem-dict-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&dir).unwrap();
        Self(dir)
    }
    fn db(&self) -> PathBuf {
        self.0.join("dictionary.db")
    }
    fn import(&self) -> SqliteDictionary {
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict.json")],
            self.db(),
            "test-subset",
        )
        .unwrap();
        SqliteDictionary::open(self.db()).unwrap()
    }
}
impl Drop for Scratch {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}
fn lemma(text: &str, kind: LemmaKind) -> Lemma {
    Lemma {
        text: text.into(),
        kind,
    }
}

#[test]
fn plural_nominal_survives_cli_dictionary_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-breakdown.json")],
        dir.db(),
        "plural-regression",
    )
    .unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_klem"))
        .args(["word", "지식인들을", "--dictionary"])
        .arg(dir.db())
        .arg("--dict-only")
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "{}",
        String::from_utf8_lossy(&output.stderr)
    );
    let result: Value = serde_json::from_slice(&output.stdout).unwrap();
    let a = result["analyses"]
        .as_array()
        .unwrap()
        .iter()
        .find(|a| a["lemmas"][0]["text"] == "지식인")
        .expect("dictionary-backed plural reading");
    assert_eq!(
        a["morphemes"],
        json!([{"form":"들", "kind":"suffix"}, {"form":"을", "kind":"particle"}])
    );
    let db = SqliteDictionary::open(dir.db()).unwrap();
    assert_eq!(db.lookup("-들").unwrap()[0].pos, "접사");
}

#[test]
fn comparative_endings_survive_dictionary_filtering_and_cli_export() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict.json"),
            PathBuf::from("tests/fixtures/krdict-comparative.json"),
        ],
        dir.db(),
        "comparative-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, ending) in [("보듯", "듯"), ("보듯이", "듯이"), ("보셨듯이", "듯이")] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(kept.analyses.iter().any(|a| {
            a.lemmas.len() == 1
                && a.lemmas[0].text == "보다"
                && annotation.has_match(&a.lemmas[0], true)
                && a.morphemes
                    .last()
                    .is_some_and(|m| m.form == ending && m.kind == klem::MorphemeKind::Ending)
        }));
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(["word", word, "--dictionary"])
            .arg(dir.db())
            .arg("--dict-only")
            .output()
            .unwrap();
        assert!(output.status.success());
        let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            actual["analyses"],
            serde_json::to_value(&kept.analyses).unwrap()
        );
    }
    for (headword, id) in [("-듯", "krdict:80280"), ("-듯이", "krdict:80282")] {
        assert!(
            db.lookup(headword)
                .unwrap()
                .iter()
                .any(|e| e.id == id && e.pos == "어미")
        );
    }
}

#[test]
fn adverb_derivation_keeps_lexical_readings_and_filters_on_predicate_bases() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-adverbs.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
        ],
        dir.db(),
        "adverb-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, base) in [
        ("같이", "같다"),
        ("없이", "없다"),
        ("달리", "다르다"),
        ("빨리", "빠르다"),
        ("똑같이", "똑같다"),
        ("끝없이", "끝없다"),
        ("높이", "높다"),
        ("없이도", "없다"),
        ("빨리들", "빠르다"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas[0].text == base
                && a.lemmas[0].kind == LemmaKind::Predicate
                && annotation.has_match(&a.lemmas[0], true)
                && a.morphemes[0].kind == klem::MorphemeKind::Suffix
                && a.morphemes[0].form == "이"),
            "{word}"
        );
        if !matches!(word, "없이도" | "빨리들") {
            assert!(
                kept.analyses.iter().any(|a| a.unchanged),
                "{word}: whole-word reading lost"
            );
        }
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(["word", word, "--dictionary"])
            .arg(dir.db())
            .arg("--dict-only")
            .output()
            .unwrap();
        assert!(output.status.success());
        let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            actual["analyses"],
            serde_json::to_value(&kept.analyses).unwrap()
        );
    }
    let suffixes = db.lookup("-이").unwrap();
    assert!(
        suffixes
            .iter()
            .any(|e| e.id == "krdict:88927" && e.pos == "접사")
    );
    // Collision fixture: the UI must open the adverb suffix, not the homonymous
    // noun suffix or ending, and preserve both whole-word POSs for 높이.
    assert!(suffixes.iter().any(|e| e.id == "krdict:88924"));
    assert!(suffixes.iter().any(|e| e.id == "krdict:80952"));
    let height = db.lookup("높이").unwrap();
    assert!(height.iter().any(|e| e.pos == "명사"));
    assert!(height.iter().any(|e| e.pos == "부사"));
}

#[test]
fn shortened_hada_matches_full_lemmas_in_cli_and_pos_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-hada.json")],
        dir.db(),
        "hada-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemma, ending) in [
        ("생각지", "생각하다", "지"),
        ("생각건대", "생각하다", "건대"),
        ("비유컨대", "비유하다", "건대"),
        ("피케", "피하다", "게"),
        ("간편케", "간편하다", "게"),
        ("깨끗지", "깨끗하다", "지"),
        ("익숙지", "익숙하다", "지"),
        ("섭섭지", "섭섭하다", "지"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && annotation.has_match(&a.lemmas[0], true)
                && a.morphemes.len() == 1
                && a.morphemes[0].form == ending),
            "{word}"
        );
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(["word", word, "--dictionary"])
            .arg(dir.db())
            .arg("--dict-only")
            .output()
            .unwrap();
        assert!(output.status.success());
        let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            actual["analyses"],
            serde_json::to_value(&kept.analyses).unwrap()
        );
    }
    for word in ["생각컨대", "익숙치", "깨끗치", "섭섭치", "비유건대", "피게"] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(kept.analyses.is_empty(), "{word}: {kept:?}");
    }
    assert_eq!(db.lookup("-건대").unwrap()[0].id, "krdict:78410");
}

#[test]
fn derivational_suffixes_survive_dictionary_filtering_and_keep_lexical_readings() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-breakdown.json"),
        ],
        dir.db(),
        "suffix-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, base, suffix) in [
        ("학생답다", "학생", "답다"),
        ("학생다워요", "학생", "답다"),
        ("선생님께", "선생", "님"),
        ("선생님들을", "선생", "님"),
        ("과학적이다", "과학", "적"),
        ("과학적으로", "과학", "적"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas[0].text == base
                && a.morphemes[0].form == suffix
                && a.lemmas.iter().all(|l| annotation.has_match(l, true))),
            "{word}"
        );
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(["word", word, "--dictionary"])
            .arg(dir.db())
            .arg("--dict-only")
            .output()
            .unwrap();
        assert!(output.status.success());
        let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            actual["analyses"],
            serde_json::to_value(&kept.analyses).unwrap()
        );
        if word == "선생님께" || word == "과학적이다" {
            let whole = if word == "선생님께" {
                "선생님"
            } else {
                "과학적"
            };
            assert!(kept.analyses.iter().any(|a| a.lemmas[0].text == whole));
        }
    }
    for (headword, id) in [("-님", "88852"), ("-적", "88966"), ("-답다", "92145")] {
        let entry = &db.lookup(headword).unwrap()[0];
        assert_eq!(entry.pos, "접사");
        assert_eq!(entry.id, format!("krdict:{id}"));
    }
    // Actual source conjugations, alongside manually specified synthetic paths.
    let entry = db.entry("krdict:75947").unwrap().unwrap();
    let forms: Vec<_> = entry.forms.iter().filter(|f| f.kind == "활용").collect();
    assert_eq!(forms.len(), 4);
    for form in forms {
        assert!(
            Lemmatizer::new()
                .analyze_word(&form.written)
                .unwrap()
                .analyses
                .iter()
                .any(|a| a.lemmas[0].text == "정" && a.morphemes[0].form == "답다"),
            "{}",
            form.written
        );
    }
}

#[test]
fn p1_particles_match_dictionary_roles_without_changing_headword_filter_semantics() {
    use klem::MorphemeKind;
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-breakdown.json"),
        ],
        dir.db(),
        "p1-particles",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, headword, kind) in [
        ("학교에선", "학교", LemmaKind::Nominal),
        ("선생님께선", "선생님", LemmaKind::Nominal),
        ("저도요", "저", LemmaKind::Nominal),
        ("친구는요", "친구", LemmaKind::Nominal),
        ("이건", "이것", LemmaKind::Nominal),
        ("뭘", "무엇", LemmaKind::Nominal),
        ("빨리들", "빨리", LemmaKind::Adverbial),
        ("먹어들", "먹다", LemmaKind::Predicate),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, true));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .any(|l| l.text == headword && l.kind == kind)),
            "{word}"
        );
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(["word", word, "--dictionary"])
            .arg(dir.db())
            .arg("--dict-only")
            .output()
            .unwrap();
        assert!(output.status.success());
        let cli: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            cli["analyses"],
            serde_json::to_value(result.filtered(|l| annotation.has_match(l, false)).analyses)
                .unwrap()
        );
    }
    let result = Lemmatizer::new().analyze_word("빨리들").unwrap();
    let annotation = session.annotate(&result).unwrap();
    assert!(annotation.has_match(&lemma("빨리", LemmaKind::Nominal), false));
    assert!(!annotation.has_match(&lemma("빨리", LemmaKind::Nominal), true));
    let strict = result.filtered(|l| annotation.has_match(l, true));
    assert!(
        strict
            .analyses
            .iter()
            .all(|a| a.lemmas[0].kind == LemmaKind::Adverbial
                && a.morphemes[0].kind == MorphemeKind::Particle)
    );
    assert_eq!(db.lookup("들").unwrap()[0].id, "krdict:86264");
}

#[test]
fn official_lmf_preserves_homonyms_senses_and_forms() {
    let dir = Scratch::new();
    let db = dir.import();
    let entries = db.lookup("가다").unwrap();
    assert_eq!(
        entries.iter().map(|e| e.id.as_str()).collect::<Vec<_>>(),
        ["krdict:27500", "krdict:28764"]
    );
    let verb = db.entry("krdict:27500").unwrap().unwrap();
    assert_eq!(verb.level, "초급");
    assert!(
        verb.forms
            .iter()
            .any(|f| f.kind == "활용" && f.written == "갑니다")
    );
    assert_eq!(verb.senses[0].id, "1");
    assert!(!verb.senses[0].examples.is_empty());
    assert!(
        verb.senses[0]
            .translations
            .iter()
            .any(|t| t.language == "영어" && !t.definition.is_empty())
    );
    assert!(!serde_json::to_string(&verb).unwrap().contains(".wav"));
    let aux = db.entry("krdict:28764").unwrap().unwrap();
    assert!(aux.senses[0].notes.iter().any(|n| n.contains("'-어 가다'")));
    assert_eq!(db.lookup("가다").unwrap(), entries);
    assert!(db.lookup("없는표제어xyz").unwrap().is_empty());
    assert!(db.entry("krdict:00000000").unwrap().is_none());
    assert_eq!(db.lookup("-가").unwrap()[0].id, "krdict:72337");
    assert!(
        !db.lookup("가")
            .unwrap()
            .iter()
            .any(|e| e.id == "krdict:72337")
    );
}

#[test]
fn pos_mapping_does_not_confuse_predicates_auxiliaries_or_copulas() {
    use Compatibility::*;
    use LemmaKind::*;
    for (word, pos, kind, expected) in [
        ("가다", "동사", Predicate, Compatible),
        ("가다", "동사", Auxiliary, Incompatible),
        ("가다", "보조 동사", Auxiliary, Compatible),
        ("가다", "보조 동사", Predicate, Incompatible),
        ("이다", "조사", Copula, Compatible),
        ("아니다", "형용사", Copula, Compatible),
        ("가깝다", "형용사", Copula, Incompatible),
        ("가", "조사", Copula, Incompatible),
        ("나", "대명사", Nominal, Compatible),
        ("것", "의존 명사", Nominal, Compatible),
        ("가", "명사", Unclassified, Unknown),
        ("가-", "품사 없음", Predicate, Unknown),
        ("word", "future-pos-label", Nominal, Unknown),
    ] {
        let entry = EntrySummary {
            id: "test:1".into(),
            headword: word.into(),
            homonym: "0".into(),
            pos: pos.into(),
        };
        assert_eq!(
            pos_compatibility(&lemma(word, kind), &entry),
            expected,
            "{word} {pos} {kind:?}"
        );
    }
}

#[test]
fn annotation_preserves_alternatives_and_cache_budget() {
    let dir = Scratch::new();
    let db = dir.import();
    let engine = Lemmatizer::new();
    let original = engine.analyze_word("가까워").unwrap();
    let before = serde_json::to_vec(&original).unwrap();
    let mut cached = DictionarySession::new(&db, 1024);
    let mut uncached = DictionarySession::new(&db, 0);
    for word in ["가까워", "가다", "가고가", "xyz", "가", "가까워"] {
        let analysis = engine.analyze_word(word).unwrap();
        assert_eq!(
            cached.annotate(&analysis).unwrap(),
            uncached.annotate(&analysis).unwrap()
        );
        assert!(cached.cache_bytes() <= 1024);
    }
    let annotation = cached.annotate(&original).unwrap();
    assert!(annotation.has_match(&lemma("가깝다", LemmaKind::Predicate), true));
    assert_eq!(before, serde_json::to_vec(&original).unwrap());
    assert_eq!(uncached.cache_bytes(), 0);
    // Filtering, if the caller requests it, applies to every component of an
    // existing analysis. Annotating never constructs a new combination.
    let filtered = original.filtered(|l| annotation.has_match(l, true));
    assert!(
        filtered
            .analyses
            .iter()
            .all(|a| original.analyses.contains(a))
    );
}

#[test]
fn imported_conjugations_recover_their_dictionary_headwords() {
    let dir = Scratch::new();
    let db = dir.import();
    let engine = Lemmatizer::new();
    for id in ["krdict:65200", "krdict:27500", "krdict:28764"] {
        let entry = db.entry(id).unwrap().unwrap();
        for form in entry
            .forms
            .iter()
            .filter(|f| f.kind == "활용" && !f.written.is_empty())
        {
            let analysis = engine.analyze_word(&form.written).unwrap();
            assert!(
                analysis
                    .lemma_strings()
                    .contains(&entry.summary.headword.as_str()),
                "{id}: {}",
                form.written
            );
        }
    }
}

#[test]
fn failed_imports_are_atomic_and_existing_databases_are_preserved() {
    let dir = Scratch::new();
    let original: Value = serde_json::from_str(include_str!("fixtures/krdict.json")).unwrap();
    let mut duplicated = original.clone();
    let entries = duplicated["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array_mut()
        .unwrap();
    entries.push(entries[0].clone());
    let mut missing_definition = original.clone();
    missing_definition["LexicalResource"]["Lexicon"]["LexicalEntry"][0]["Sense"] = json!([]);
    for contents in [
        "{}".into(),
        "{\"LexicalResource\":".into(),
        serde_json::to_string(&duplicated).unwrap(),
        serde_json::to_string(&missing_definition).unwrap(),
        format!("{} trailing", original),
    ] {
        let input = dir.0.join("bad.json");
        fs::write(&input, contents).unwrap();
        assert!(import_krdict(&[input], dir.db(), "test").is_err());
        assert!(!dir.db().exists());
        assert!(!fs::read_dir(&dir.0).unwrap().any(|p| {
            p.unwrap()
                .file_name()
                .to_string_lossy()
                .contains(".import-")
        }));
    }
    let db = dir.import();
    let fingerprint = db.fingerprint().to_owned();
    drop(db);
    assert!(
        import_krdict(
            &[PathBuf::from("tests/fixtures/krdict.json")],
            dir.db(),
            "replacement"
        )
        .is_err()
    );
    assert_eq!(
        SqliteDictionary::open(dir.db()).unwrap().fingerprint(),
        fingerprint
    );
    let other = dir.0.join("empty.db");
    fs::write(&other, []).unwrap();
    assert!(SqliteDictionary::open(&other).is_err());
    assert!(SqliteDictionary::open(dir.0.join("missing.db")).is_err());
    assert!(!dir.0.join("missing.db").exists());
}

#[test]
fn idioms_with_shared_upstream_ids_remain_separate() {
    let dir = Scratch::new();
    let mut raw: Value = serde_json::from_str(include_str!("fixtures/krdict.json")).unwrap();
    let entries = raw["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array_mut()
        .unwrap();
    let mut idiom = entries[0].clone();
    idiom["Lemma"] = json!({"feat":{"att":"writtenForm","val":"테스트 관용구"}});
    idiom["feat"] = json!({"att":"lexicalUnit","val":"관용구"});
    entries.push(idiom);
    let input = dir.0.join("idiom.json");
    fs::write(&input, serde_json::to_vec(&raw).unwrap()).unwrap();
    import_krdict(&[input], dir.db(), "test").unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let sub = db.lookup("테스트 관용구").unwrap();
    assert_eq!(sub.len(), 1);
    assert!(sub[0].id.starts_with("krdict:27733:"));
    assert!(db.entry("krdict:27733").unwrap().is_some());
}

#[test]
fn cli_import_lookup_and_annotations_work_without_changing_candidates() {
    let dir = Scratch::new();
    let bin = env!("CARGO_BIN_EXE_klem");
    let imported = Command::new(bin)
        .args(["dict", "import-krdict", "tests/fixtures/krdict.json"])
        .arg(dir.db())
        .args(["--snapshot", "test"])
        .output()
        .unwrap();
    assert!(
        imported.status.success(),
        "{}",
        String::from_utf8_lossy(&imported.stderr)
    );
    for command in ["lookup", "entry"] {
        let key = if command == "lookup" {
            "가다"
        } else {
            "krdict:27500"
        };
        let out = Command::new(bin)
            .args(["dict", command])
            .arg(dir.db())
            .arg(key)
            .output()
            .unwrap();
        assert!(out.status.success());
        assert!(serde_json::from_slice::<Value>(&out.stdout).is_ok());
    }
    let out = Command::new(bin)
        .args(["word", "가까워", "--dictionary"])
        .arg(dir.db())
        .output()
        .unwrap();
    assert!(out.status.success());
    let mut value: Value = serde_json::from_slice(&out.stdout).unwrap();
    let annotation = value.as_object_mut().unwrap().remove("dictionary").unwrap();
    assert!(!annotation["lemmas"].as_array().unwrap().is_empty());
    assert_eq!(
        value,
        serde_json::to_value(Lemmatizer::new().analyze_word("가까워").unwrap()).unwrap()
    );
    let text = "가까워.\n가다";
    let input = dir.0.join("book.txt");
    fs::write(&input, text).unwrap();
    let out = Command::new(bin)
        .arg("text")
        .arg(&input)
        .arg("--dictionary")
        .arg(dir.db())
        .output()
        .unwrap();
    assert!(out.status.success());
    for (line, expected) in String::from_utf8(out.stdout)
        .unwrap()
        .lines()
        .zip(Lemmatizer::new().analyze_text(text))
    {
        let mut value: Value = serde_json::from_str(line).unwrap();
        let annotation = value.as_object_mut().unwrap().remove("dictionary").unwrap();
        assert_eq!(annotation.is_null(), expected.analysis.is_none());
        assert_eq!(value, serde_json::to_value(expected).unwrap());
    }
    let out = Command::new(bin)
        .args(["word", "가다", "--format", "text", "--dictionary"])
        .arg(dir.db())
        .output()
        .unwrap();
    assert!(!out.status.success());
    assert!(out.stdout.is_empty());
}

#[test]
fn input_hashes_and_fingerprints_are_reproducible_and_sensitive_to_source_bytes() {
    use sha2::{Digest, Sha256};
    let dir = Scratch::new();
    let db = dir.import();
    let bytes = fs::read("tests/fixtures/krdict.json").unwrap();
    assert_eq!(
        db.metadata().files[0].sha256,
        format!("{:x}", Sha256::digest(&bytes))
    );
    let second = dir.0.join("second.db");
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict.json")],
        &second,
        "test-subset",
    )
    .unwrap();
    assert_eq!(
        db.fingerprint(),
        SqliteDictionary::open(second).unwrap().fingerprint()
    );
    let copy = dir.0.join("krdict.json");
    let mut changed = bytes;
    changed.push(b'\n');
    fs::write(&copy, changed).unwrap();
    let third = dir.0.join("third.db");
    import_krdict(&[copy], &third, "test-subset").unwrap();
    assert_ne!(
        db.fingerprint(),
        SqliteDictionary::open(third).unwrap().fingerprint()
    );
}

#[test]
fn cli_dict_only_filters_complete_groups_and_keeps_lossless_text_records() {
    let dir = Scratch::new();
    let db = dir.import();
    let engine = Lemmatizer::new();
    let bin = env!("CARGO_BIN_EXE_klem");
    let expected = |word: &str| {
        engine
            .analyze_word(word)
            .unwrap()
            .filtered(|lemma| !db.lookup(&lemma.text).unwrap().is_empty())
    };
    // Both components are attested; partial matches must not survive as fragments.
    assert!(
        expected("가가")
            .analyses
            .iter()
            .any(|a| a.lemmas.len() == 2)
    );
    let partial = engine.analyze_word("먹어가").unwrap();
    assert!(partial.analyses.iter().any(|a| {
        a.lemmas.iter().any(|l| l.text == "먹다") && a.lemmas.iter().any(|l| l.text == "가다")
    }));
    assert!(expected("먹어가").analyses.is_empty());
    for word in ["가까워", "가다", "가가", "먹어가", "xyz"] {
        let output = Command::new(bin)
            .args(["word", word, "--dict-only", "--dictionary"])
            .arg(dir.db())
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let mut value: Value = serde_json::from_slice(&output.stdout).unwrap();
        let annotation: klem::dictionary::Annotation =
            serde_json::from_value(value.as_object_mut().unwrap().remove("dictionary").unwrap())
                .unwrap();
        let wanted = expected(word);
        assert_eq!(value, serde_json::to_value(&wanted).unwrap());
        let keys: std::collections::BTreeSet<_> = wanted
            .analyses
            .iter()
            .flat_map(|a| a.lemmas.iter())
            .collect();
        assert_eq!(
            annotation
                .lemmas
                .iter()
                .map(|m| &m.lemma)
                .collect::<std::collections::BTreeSet<_>>(),
            keys
        );
        assert!(annotation.lemmas.iter().all(|m| !m.entries.is_empty()));
        if word == "가다" {
            // Headword matching deliberately includes unclassified/unknown POS.
            assert!(wanted.analyses.iter().any(|a| a.unchanged));
        }
    }
    let text = "가가 xyz.\n먹어가 가까워 가가";
    let input = dir.0.join("filter.txt");
    fs::write(&input, text).unwrap();
    let expected_records: Vec<_> = engine.analyze_text(text).collect();
    for budget in ["0", "8388608"] {
        let output = Command::new(bin)
            .arg("text")
            .arg(&input)
            .args(["--dictionary"])
            .arg(dir.db())
            .args(["--dict-only", "--cache-bytes", budget])
            .output()
            .unwrap();
        assert!(output.status.success());
        let records: Vec<Value> = String::from_utf8(output.stdout)
            .unwrap()
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert_eq!(records.len(), expected_records.len());
        let reconstructed: String = records
            .iter()
            .map(|r| r["surface"].as_str().unwrap())
            .collect();
        assert_eq!(reconstructed, text);
        for (mut actual, original) in records.into_iter().zip(&expected_records) {
            let annotation = actual
                .as_object_mut()
                .unwrap()
                .remove("dictionary")
                .unwrap();
            let mut wanted = serde_json::to_value(original).unwrap();
            if original.analysis.is_some() {
                wanted["analysis"] = serde_json::to_value(expected(&original.surface)).unwrap();
            } else {
                assert!(annotation.is_null());
            }
            assert_eq!(actual, wanted);
        }
    }
}

#[test]
fn cli_dict_only_requires_a_dictionary_and_supported_output() {
    let dir = Scratch::new();
    let _db = dir.import();
    let bin = env!("CARGO_BIN_EXE_klem");
    for args in [
        vec!["word", "가다", "--dict-only"],
        vec!["text", "--dict-only"],
        vec!["explain", "irregular.digeut", "--dict-only"],
    ] {
        let output = Command::new(bin).args(args).output().unwrap();
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
        assert!(
            String::from_utf8_lossy(&output.stderr).contains("--dict-only requires --dictionary")
        );
    }
    let output = Command::new(bin)
        .args([
            "word",
            "가다",
            "--dict-only",
            "--format",
            "text",
            "--dictionary",
        ])
        .arg(dir.db())
        .output()
        .unwrap();
    assert!(!output.status.success());
    assert!(output.stdout.is_empty());
}
