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
fn adverb_root_roles_preserve_matches_homonyms_and_dictionary_gaps() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-adverb-roots.json")],
        dir.db(),
        "adverb-roots",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, base, kind, suffix, headword_match, pos_match) in [
        ("더욱이", "더욱", LemmaKind::Adverbial, "이", true, true),
        ("곰곰이", "곰곰", LemmaKind::Adverbial, "이", true, true),
        ("가만히", "가만", LemmaKind::Adverbial, "히", true, true),
        ("낱낱이", "낱낱", LemmaKind::Nominal, "이", true, true),
        ("집집이", "집집", LemmaKind::Nominal, "이", true, true),
        ("점점이", "점점", LemmaKind::Nominal, "이", true, false),
        ("틈틈이", "틈틈", LemmaKind::Nominal, "이", false, false),
        ("익히", "익숙하다", LemmaKind::Predicate, "히", true, true),
        ("특히", "특별하다", LemmaKind::Predicate, "히", true, true),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let filtered = result.filtered(|l| annotation.has_match(l, false));
        let compatible = result.filtered(|l| annotation.has_match(l, true));
        for (actual, expected) in [
            (&result, true),
            (&filtered, headword_match),
            (&compatible, pos_match),
        ] {
            assert_eq!(
                actual.analyses.iter().any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == base
                    && a.lemmas[0].kind == kind
                    && a.morphemes.len() == 1
                    && a.morphemes[0].form == suffix
                    && a.morphemes[0].kind == klem::MorphemeKind::Suffix),
                expected,
                "{word}"
            );
        }
        assert!(
            filtered.analyses.iter().any(|a| a.unchanged),
            "{word}: keep whole lexical adverb"
        );
        for (dict_only, expected) in [(false, &result), (true, &filtered)] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if dict_only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
        }
    }
}

#[test]
fn enumerative_yo_and_polite_particle_survive_dictionary_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-copula-yo.json"),
            PathBuf::from("tests/fixtures/krdict-colloquial-copulas.json"),
        ],
        dir.db(),
        "copula-yo",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, base) in [
        ("연장이요", "연장"),
        ("자화상이요", "자화상"),
        ("아비요", "아비"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(kept.analyses.iter().any(|a| {
            a.lemmas.iter().map(|l| l.text.as_str()).eq([base, "이다"])
                && a.lemmas.iter().all(|l| annotation.has_match(l, true))
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "요"
                && a.morphemes[0].kind == klem::MorphemeKind::Ending
        }));
        if word == "아비요" {
            assert!(kept.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == base
                && a.morphemes[0].kind == klem::MorphemeKind::Particle));
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
}

#[test]
fn omitted_copulas_keep_short_expanded_and_lexical_dictionary_readings() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-colloquial-copulas.json",
        )],
        dir.db(),
        "colloquial-copula-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms, present) in [
        ("겁니다", vec!["거", "이다"], vec!["습니다"], true),
        ("겁니다", vec!["것", "이다"], vec!["습니다"], true),
        ("건데", vec!["것", "이다"], vec!["은데"], true),
        ("거죠", vec!["것", "이다"], vec!["죠"], true),
        ("거면", vec!["거", "이다"], vec!["으면"], true),
        ("이겁니다", vec!["이것", "이다"], vec!["습니다"], true),
        ("그건데", vec!["그것", "이다"], vec!["은데"], true),
        ("저거죠", vec!["저것", "이다"], vec!["죠"], true),
        ("의삽니다", vec!["의사", "이다"], vec!["습니다"], true),
        ("학교죠", vec!["학교", "이다"], vec!["죠"], true),
        ("거예요", vec!["거", "이다"], vec!["에요"], true),
        ("거예요", vec!["것", "이다"], vec!["에요"], true),
        ("거지", vec!["거지"], vec![], true),
        ("거지", vec!["것", "이다"], vec!["지"], true),
        ("거니다", vec!["거", "이다"], vec!["습니다"], false),
        ("먹긴데", vec!["먹다", "이다"], vec!["기", "은데"], true),
        (
            "거지않다",
            vec!["것", "이다", "않다"],
            vec!["지", "다"],
            true,
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let filtered = result.filtered(|l| annotation.has_match(l, false));
        let compatible = result.filtered(|l| annotation.has_match(l, true));
        for (actual, pos_only) in [(&filtered, false), (&compatible, true)] {
            assert_eq!(
                actual.analyses.iter().any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())),
                // Identity has an unknown role: headword filtering keeps it,
                // while POS-only filtering does not certify that role.
                present && (!pos_only || !forms.is_empty()),
                "{word}"
            );
        }
        for (dict_only, expected) in [(false, &result), (true, &filtered)] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if dict_only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
        }
    }
}

#[test]
fn prefinal_licenses_keep_exact_dictionary_paths_and_cli_parity() {
    let dir = Scratch::new();
    let mut fixture: Value =
        serde_json::from_str(include_str!("fixtures/krdict-emphatic-particles.json")).unwrap();
    let copulas: Value =
        serde_json::from_str(include_str!("fixtures/krdict-derivation.json")).unwrap();
    let copula = copulas["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["Lemma"]["feat"]["val"] == "이다")
        .unwrap();
    fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array_mut()
        .unwrap()
        .push(copula.clone());
    let input = dir.0.join("prefinal-licenses.json");
    fs::write(&input, serde_json::to_vec(&fixture).unwrap()).unwrap();
    import_krdict(&[input], dir.db(), "prefinal-license-regression").unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms, present) in [
        ("먹었더라", vec!["먹다"], vec!["었", "더라"], true),
        ("먹었더라", vec!["먹다"], vec!["었", "더", "라"], true),
        ("먹었더라", vec!["먹다"], vec!["었", "더", "어라"], false),
        ("먹었더라", vec!["먹다"], vec!["었", "더", "으라"], false),
        ("먹으리라", vec!["먹다"], vec!["으리", "라"], true),
        ("먹으리라", vec!["먹다"], vec!["으리라"], true),
        ("먹더라는", vec!["먹다"], vec!["더라는"], true),
        ("먹더라는", vec!["먹다"], vec!["더", "으라는"], false),
        ("학생이라고", vec!["학생", "이다"], vec!["라고"], true),
        ("학생이라고", vec!["학생", "이다"], vec!["으라고"], false),
        ("먹으세요", vec!["먹다"], vec!["으세요"], true),
        ("학생이세요", vec!["학생", "이다"], vec!["으세요"], true),
        ("먹었으세요", vec!["먹다"], vec!["었", "으세요"], false),
        (
            "먹어봤더라는",
            vec!["먹다", "보다"],
            vec!["어", "었", "더라는"],
            true,
        ),
        ("학생답더라는", vec!["학생"], vec!["답다", "더라는"], true),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let filtered = result.filtered(|l| annotation.has_match(l, false));
        let compatible = result.filtered(|l| annotation.has_match(l, true));
        for actual in [&filtered, &compatible] {
            assert_eq!(
                actual.analyses.iter().any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())),
                present,
                "{word}"
            );
        }
        for (dict_only, expected) in [(false, &result), (true, &filtered)] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if dict_only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
        }
    }
}

#[test]
fn obligation_bundles_keep_dictionary_groups_and_cli_parity() {
    let dir = Scratch::new();
    let mut fixture: Value =
        serde_json::from_str(include_str!("fixtures/krdict-emphatic-particles.json")).unwrap();
    let copulas: Value =
        serde_json::from_str(include_str!("fixtures/krdict-derivation.json")).unwrap();
    let copula = copulas["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["Lemma"]["feat"]["val"] == "이다")
        .unwrap();
    fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array_mut()
        .unwrap()
        .push(copula.clone());
    let input = dir.0.join("obligation.json");
    fs::write(&input, serde_json::to_vec(&fixture).unwrap()).unwrap();
    import_krdict(&[input], dir.db(), "obligation-regression").unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, present) in [
        ("먹어야겠네요", vec!["먹다"], true),
        ("먹으셔야겠다", vec!["먹다"], true),
        ("먹어봐야겠다", vec!["먹다", "보다"], true),
        ("학생이어야겠다", vec!["학생", "이다"], true),
        ("학생다워야겠다", vec!["학생"], true),
        ("먹아야겠다", vec!["먹다"], false),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let filtered = result.filtered(|l| annotation.has_match(l, false));
        let compatible = result.filtered(|l| annotation.has_match(l, true));
        for actual in [&filtered, &compatible] {
            assert_eq!(
                actual.analyses.iter().any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.rules.iter().any(|r| r == "prefinal.obligation")),
                present,
                "{word}"
            );
        }
        for (dict_only, expected) in [(false, &result), (true, &filtered)] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if dict_only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
        }
    }
}

#[test]
fn definition_and_quotation_readings_keep_dictionary_groups_and_roles() {
    let dir = Scratch::new();
    let mut fixture: Value =
        serde_json::from_str(include_str!("fixtures/krdict-emphatic-particles.json")).unwrap();
    let copulas: Value =
        serde_json::from_str(include_str!("fixtures/krdict-derivation.json")).unwrap();
    let copula = copulas["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array()
        .unwrap()
        .iter()
        .find(|e| e["Lemma"]["feat"]["val"] == "이다")
        .unwrap();
    // The attributed fixtures overlap on 학생; add only the missing copula.
    fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
        .as_array_mut()
        .unwrap()
        .push(copula.clone());
    let input = dir.0.join("definitions.json");
    fs::write(&input, serde_json::to_vec(&fixture).unwrap()).unwrap();
    import_krdict(&[input], dir.db(), "definition-quotation-regression").unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        ("학생이란", vec!["학생"], vec!["이란"]),
        ("학생이란", vec!["학생", "이다"], vec!["란"]),
        ("학교란", vec!["학교", "이다"], vec!["란"]),
        ("이란", vec!["이다"], vec!["란"]),
        ("이라는", vec!["이다"], vec!["라는"]),
        ("라는", vec!["이다"], vec!["라는"]),
        ("먹으란", vec!["먹다"], vec!["으란"]),
        ("작으리란", vec!["작다"], vec!["으리", "란"]),
        ("먹어보란", vec!["먹다", "보다"], vec!["어", "으란"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let filtered = result.filtered(|lemma| annotation.has_match(lemma, false));
        let compatible = result.filtered(|lemma| annotation.has_match(lemma, true));
        for actual in [&filtered, &compatible] {
            assert!(
                actual.analyses.iter().any(|a| a
                    .lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())),
                "{word}: {lemmas:?}"
            );
        }
        if matches!(word, "이란" | "이라는" | "라는") {
            assert!(compatible.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "이다"
                && a.lemmas[0].kind == LemmaKind::Copula));
        }
        for (dict_only, expected) in [(false, &result), (true, &filtered)] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if dict_only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
        }
    }
}

#[test]
fn emphatic_particles_and_concessive_endings_keep_dictionary_roles_and_cli_parity() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-emphatic-particles.json",
        )],
        dir.db(),
        "emphatic-particle-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemma, forms, present) in [
        ("학교야말로", "학교", vec!["야말로"], true),
        ("학생이야말로", "학생", vec!["이야말로"], true),
        ("잠시나마", "잠시", vec!["나마"], true),
        ("학교에서나마", "학교", vec!["에서", "나마"], true),
        ("사과는커녕", "사과", vec!["는커녕"], true),
        ("먹긴커녕", "먹다", vec!["기", "는커녕"], true),
        ("밥커녕", "밥", vec!["커녕"], true),
        ("서울서", "서울", vec!["서"], true),
        ("작으나마", "작다", vec!["으나마"], true),
        ("학교이야말로", "학교", vec!["이야말로"], false),
        ("학생나마", "학생", vec!["나마"], false),
        ("먹나마", "먹다", vec!["으나마"], false),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let filtered = result.filtered(|lemma| annotation.has_match(lemma, false));
        let compatible = result.filtered(|lemma| annotation.has_match(lemma, true));
        for actual in [&filtered, &compatible] {
            assert_eq!(
                actual.analyses.iter().any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == lemma
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())),
                present,
                "{word}"
            );
        }
        if word == "잠시나마" {
            assert!(compatible.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && a.lemmas[0].kind == LemmaKind::Adverbial));
        }
        for (dict_only, expected) in [(false, &result), (true, &filtered)] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if dict_only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
        }
    }
}

#[test]
fn intention_endings_preserve_dictionary_filtering_and_cli_groups() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-particles.json")],
        dir.db(),
        "intention-ending-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, form, present) in [
        ("먹으리라고", "으리라고", true),
        ("먹을지라도", "을지라도", true),
        ("먹자면", "자면", true),
        ("먹리라고", "으리라고", false),
        ("먹었자면", "자면", false),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let filtered = result.filtered(|lemma| annotation.has_match(lemma, false));
        let compatible = result.filtered(|lemma| annotation.has_match(lemma, true));
        for actual in [&filtered, &compatible] {
            assert_eq!(
                actual.analyses.iter().any(|a| a.lemmas.len() == 1
                    && a.lemmas[0].text == "먹다"
                    && a.morphemes.last().is_some_and(|m| m.form == form)),
                present,
                "{word}"
            );
        }
        for (dict_only, expected) in [(false, &result), (true, &filtered)] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if dict_only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(
                output.status.success(),
                "{}",
                String::from_utf8_lossy(&output.stderr)
            );
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
        }
    }
}

#[test]
fn standard_propositive_is_preserved_by_cli_dictionary_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-particles.json")],
        dir.db(),
        "propositive-label-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for word in ["먹읍시다", "먹습시다"] {
        let analysis = Lemmatizer::new().analyze_word(word).unwrap();
        let annotated = session.annotate(&analysis).unwrap();
        let expected = analysis.filtered(|lemma| annotated.has_match(lemma, false));
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(["word", word, "--dictionary"])
            .arg(dir.db())
            .arg("--dict-only")
            .output()
            .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
        assert_eq!(
            actual["analyses"],
            serde_json::to_value(&expected.analyses).unwrap()
        );
        assert_eq!(
            expected.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == "먹다"
                && a.morphemes.len() == 1
                && a.morphemes[0].form == "읍시다"),
            word == "먹읍시다"
        );
    }
}

#[test]
fn conditional_foreign_readings_do_not_bypass_dictionary_only_filtering() {
    let dir = Scratch::new();
    let dictionary = dir.import();
    let engine = Lemmatizer::new();
    let mut session = DictionarySession::new(&dictionary, 4096);
    for (word, base) in [("ABC는", "ABC"), ("3은", "3"), ("김민수는", "김민수")] {
        let result = engine.analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        assert!(
            result
                .analyses
                .iter()
                .any(|a| a.lemmas.len() == 1 && a.lemmas[0].text == base)
        );
        assert!(
            annotation
                .lemmas
                .iter()
                .find(|m| m.lemma.text == base)
                .unwrap()
                .entries
                .is_empty()
        );
        for only in [false, true] {
            let mut command = Command::new(env!("CARGO_BIN_EXE_klem"));
            command.args(["word", word, "--dictionary"]).arg(dir.db());
            if only {
                command.arg("--dict-only");
            }
            let output = command.output().unwrap();
            assert!(output.status.success());
            let actual: Value = serde_json::from_slice(&output.stdout).unwrap();
            let expected = if only {
                result.filtered(|l| annotation.has_match(l, false))
            } else {
                result.clone()
            };
            assert_eq!(
                actual["analyses"],
                serde_json::to_value(&expected.analyses).unwrap()
            );
            if only {
                assert!(expected.analyses.is_empty());
            }
        }
    }
    let output = Command::new(env!("CARGO_BIN_EXE_klem"))
        .args(["text", "-", "--dict-only", "--dictionary"])
        .arg(dir.db())
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .spawn()
        .unwrap();
    let mut child = output;
    use std::io::Write;
    child
        .stdin
        .take()
        .unwrap()
        .write_all("ABC는 3은!".as_bytes())
        .unwrap();
    let output = child.wait_with_output().unwrap();
    assert!(output.status.success());
    let records: Vec<Value> = String::from_utf8(output.stdout)
        .unwrap()
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect();
    assert_eq!(
        records
            .iter()
            .map(|r| r["surface"].as_str().unwrap())
            .collect::<String>(),
        "ABC는 3은!"
    );
    for record in records.iter().filter(|r| r["kind"] == "word") {
        assert_eq!(record["analysis"]["analyses"], json!([]));
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
fn quoted_questions_preserve_dictionary_groups_and_cli_parity() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-quoted-questions.json"),
            PathBuf::from("tests/fixtures/krdict-conditional.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-adnominal.json"),
        ],
        dir.db(),
        "quoted-question-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        ("아니냐는", vec!["아니다"], vec!["냐는"]),
        ("좋으냐는", vec!["좋다"], vec!["으냐는"]),
        ("추우냐는", vec!["춥다"], vec!["으냐는"]),
        ("파라냐는", vec!["파랗다"], vec!["으냐는"]),
        ("먹더냐는", vec!["먹다"], vec!["더", "냐는"]),
        ("했느냐는", vec!["하다"], vec!["었", "느냐는"]),
        ("먹으시겠냐는", vec!["먹다"], vec!["시", "겠", "냐는"]),
        (
            "먹어봤느냐는",
            vec!["먹다", "보다"],
            vec!["어", "었", "느냐는"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
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
    }
    for (word, id) in [
        ("-냐는", "krdict:86030"),
        ("-느냐는", "krdict:86031"),
        ("-으냐는", "krdict:86032"),
    ] {
        assert!(
            db.lookup(word)
                .unwrap()
                .iter()
                .any(|e| e.id == id && e.pos == "품사 없음")
        );
    }
}

#[test]
fn post_ending_particles_preserve_dictionary_and_cli_groups() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-post-ending-particles.json"),
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-conditional.json"),
            PathBuf::from("tests/fixtures/krdict-breakdown.json"),
        ],
        dir.db(),
        "post-ending-particles",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        ("있습니다만", vec!["있다"], vec!["습니다", "만"]),
        ("먹는다마는", vec!["먹다"], vec!["는다", "마는"]),
        ("하면서도", vec!["하다"], vec!["으면서", "도"]),
        ("먹고는", vec!["먹다"], vec!["고", "는"]),
        ("학생입니다만", vec!["학생", "이다"], vec!["습니다", "만"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
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
    }
    let ids: std::collections::BTreeSet<_> =
        db.lookup("만").unwrap().into_iter().map(|e| e.id).collect();
    assert!(ids.contains("krdict:86554") && ids.contains("krdict:86555"));
}

#[test]
fn particle_chains_and_quotation_survive_dictionary_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-particle-chains.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
        ],
        dir.db(),
        "particle-chains",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemma, forms) in [
        ("어디까지나", "어디", vec!["까지", "나"]),
        ("이제부터라도", "이제", vec!["부터", "라도"]),
        ("학생만이라도", "학생", vec!["만", "이라도"]),
        ("학교에서든지", "학교", vec!["에서", "든지"]),
        ("학생이라고", "학생", vec!["이라고"]),
        ("사회주의라고", "사회주의", vec!["라고"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
                && annotation.has_match(&a.lemmas[0], true)),
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
        if word == "학생이라고" {
            assert!(kept.analyses.iter().any(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(["학생", "이다"])
            }));
        }
    }
    for (form, ids) in [
        ("라고", ["krdict:70074", "krdict:86366"]),
        ("이라고", ["krdict:70075", "krdict:86353"]),
    ] {
        let entries = db.lookup(form).unwrap();
        assert!(
            ids.iter()
                .all(|id| entries.iter().any(|e| &e.id == id && e.pos == "조사"))
        );
    }
}

#[test]
fn auxiliary_class_constraints_keep_dictionary_and_cli_results_in_sync() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-auxiliary-inventory.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
            PathBuf::from("tests/fixtures/krdict-auxiliary-classes.json"),
        ],
        dir.db(),
        "auxiliary-classes",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        (
            "먹고싶어해요",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "어", "어요"],
        ),
        (
            "학생다워해요",
            vec!["학생", "하다"],
            vec!["답다", "어", "어요"],
        ),
        (
            "먹고싶지않아해요",
            vec!["먹다", "싶다", "않다", "하다"],
            vec!["고", "지", "어", "어요"],
        ),
        ("먹고싶은", vec!["먹다", "싶다"], vec!["고", "은"]),
        (
            "먹고싶지는않은",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "는", "은"],
        ),
        (
            "먹고싶어하는",
            vec!["먹다", "싶다", "하다"],
            vec!["고", "어", "는"],
        ),
        (
            "먹고싶었는데",
            vec!["먹다", "싶다"],
            vec!["고", "었", "는데"],
        ),
        ("먹을만한", vec!["먹다", "만하다"], vec!["을", "은"]),
        ("없어요", vec!["없다"], vec!["어요"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
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
    }
    assert!(db.lookup("없다").unwrap().iter().all(|e| e.pos == "형용사"));
    let hada = db.entry("krdict:62888").unwrap().unwrap();
    assert!(hada.senses.iter().any(|s| {
        s.id == "9"
            && s.notes
                .iter()
                .any(|n| n == "형용사 뒤에서 '-어하다'로 쓴다.")
    }));
    for (word, forbidden) in [
        ("먹어봐해요", vec!["먹다", "보다", "하다"]),
        ("먹고있어해요", vec!["먹다", "있다", "하다"]),
        ("학생이어해요", vec!["학생", "이다", "하다"]),
        ("먹기이어해요", vec!["먹다", "이다", "하다"]),
        ("먹어보지않아해요", vec!["먹다", "보다", "않다", "하다"]),
        ("먹어없다", vec!["먹다", "없다"]),
        ("먹고싶는다", vec!["먹다", "싶다"]),
        ("먹을만하는", vec!["먹다", "만하다"]),
        ("먹고싶지않는", vec!["먹다", "싶다", "않다"]),
        ("먹고싶잖는", vec!["먹다", "싶다", "않다"]),
        ("학생인듯하는", vec!["학생", "이다", "듯하다"]),
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_klem"))
            .args(["word", word, "--dictionary"])
            .arg(dir.db())
            .arg("--dict-only")
            .output()
            .unwrap();
        assert!(output.status.success());
        let actual: klem::WordAnalysis = serde_json::from_slice(&output.stdout).unwrap();
        assert!(
            !actual.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(forbidden.iter().copied())),
            "{word}"
        );
    }
}

#[test]
fn negative_auxiliaries_preserve_dictionary_groups_and_cli_parity() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-auxiliary-inventory.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
            PathBuf::from("tests/fixtures/krdict-negative-auxiliaries.json"),
        ],
        dir.db(),
        "negative-auxiliaries",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        ("마", vec!["말다"], vec!["어"]),
        ("먹지마라", vec!["먹다", "말다"], vec!["지", "어라"]),
        ("먹지마요", vec!["먹다", "말다"], vec!["지", "어요"]),
        (
            "먹지는않았다",
            vec!["먹다", "않다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹진못했다",
            vec!["먹다", "못하다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹진아니했다",
            vec!["먹다", "아니하다"],
            vec!["지", "는", "었", "다"],
        ),
        (
            "먹어보진마요",
            vec!["먹다", "보다", "말다"],
            vec!["어", "지", "는", "어요"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
                && a.lemmas.iter().all(|l| annotation.has_match(l, true))),
            "{word}"
        );
        if word == "마" {
            assert!(
                kept.analyses
                    .iter()
                    .any(|a| a.unchanged && a.lemmas[0].text == "마")
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
}

#[test]
fn auxiliary_inventory_and_internal_particles_survive_dictionary_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-auxiliary-inventory.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
        ],
        dir.db(),
        "auxiliary-inventory",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        ("먹을만하다", vec!["먹다", "만하다"], vec!["을", "다"]),
        ("먹는듯하다", vec!["먹다", "듯하다"], vec!["는", "다"]),
        ("먹고계셨다", vec!["먹다", "계시다"], vec!["고", "었", "다"]),
        (
            "학생인듯하다",
            vec!["학생", "이다", "듯하다"],
            vec!["은", "다"],
        ),
        ("먹어들봐요", vec!["먹다", "보다"], vec!["어", "들", "어요"]),
        (
            "먹곤했다",
            vec!["먹다", "하다"],
            vec!["고", "는", "었", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
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
    }
}

#[test]
fn expanded_adverbs_keep_lexical_words_and_related_adjective_lookups() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict.json"),
            PathBuf::from("tests/fixtures/krdict-adverb-expansion.json"),
            PathBuf::from("tests/fixtures/krdict-negative-contractions.json"),
        ],
        dir.db(),
        "adverb-expansion",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, root, suffix) in [
        ("가까이", "가깝다", "이"),
        ("가벼이", "가볍다", "이"),
        ("적잖이", "적잖다", "이"),
        ("깨끗이", "깨끗하다", "이"),
        ("조용히", "조용하다", "히"),
        ("다분히", "다분하다", "히"),
        ("상당히", "상당하다", "히"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == root
                && annotation.has_match(&a.lemmas[0], true)
                && a.morphemes.len() == 1
                && a.morphemes[0].form == suffix
                && a.morphemes[0].kind == klem::MorphemeKind::Suffix),
            "{word}"
        );
        assert!(
            kept.analyses
                .iter()
                .any(|a| a.unchanged && a.lemmas[0].text == word),
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
}

#[test]
fn negative_contractions_keep_expanded_and_lexical_dictionary_readings() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-negative-contractions.json"),
            PathBuf::from("tests/fixtures/krdict-auxiliary-inventory.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
        ],
        dir.db(),
        "negative-contractions",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        ("적잖은", vec!["적다", "않다"], vec!["지", "은"]),
        ("적잖은", vec!["적잖다"], vec!["은"]),
        (
            "만만찮았다",
            vec!["만만하다", "않다"],
            vec!["지", "었", "다"],
        ),
        ("만만찮았다", vec!["만만찮다"], vec!["었", "다"]),
        (
            "먹고싶잖다",
            vec!["먹다", "싶다", "않다"],
            vec!["고", "지", "다"],
        ),
        ("먹잖아요", vec!["먹다"], vec!["잖아요"]),
        ("먹잖아요", vec!["먹다", "않다"], vec!["지", "어요"]),
        ("학생이잖아요", vec!["학생", "이다"], vec!["잖아요"]),
        ("괜찮아요", vec!["괜찮다"], vec!["어요"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
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
    }
}

#[test]
fn direct_nominalized_copulas_survive_dictionary_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-auxiliary-inventory.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-derivation.json"),
        ],
        dir.db(),
        "nominalized-copulas",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        (
            "학생다움이다",
            vec!["학생", "이다"],
            vec!["답다", "음", "다"],
        ),
        (
            "학생다움이에요",
            vec!["학생", "이다"],
            vec!["답다", "음", "에요"],
        ),
        ("먹기다", vec!["먹다", "이다"], vec!["기", "다"]),
        ("먹기예요", vec!["먹다", "이다"], vec!["기", "에요"]),
        (
            "먹어보기였다",
            vec!["먹다", "보다", "이다"],
            vec!["어", "기", "었", "다"],
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
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
    }
}

#[test]
fn daga_and_eodaga_remain_distinct_through_dictionary_and_cli_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-daga.json"),
            PathBuf::from("tests/fixtures/krdict.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
        ],
        dir.db(),
        "daga-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemma, forms) in [
        ("먹다가", "먹다", vec!["다가"]),
        ("갔다가", "가다", vec!["었", "다가"]),
        ("불렀다가", "부르다", vec!["었", "다가"]),
        ("먹으셨다가", "먹다", vec!["시", "었", "다가"]),
        ("가다가", "가다", vec!["다가"]),
        ("가다가", "가다", vec!["어다가"]),
        ("먹어다가", "먹다", vec!["어다가"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && annotation.has_match(&a.lemmas[0], true)
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())),
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
    for (word, id) in [("-다가", "krdict:85740"), ("-어다가", "krdict:86099")] {
        assert!(
            db.lookup(word)
                .unwrap()
                .iter()
                .any(|e| e.id == id && e.pos == "어미")
        );
    }
}

#[test]
fn shortened_adnominals_survive_dictionary_filtering_and_cli_export() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-adnominal.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
            PathBuf::from("tests/fixtures/krdict-conditional.json"),
            PathBuf::from("tests/fixtures/krdict-comparative.json"),
        ],
        dir.db(),
        "adnominal-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms) in [
        ("먹으려는", vec!["먹다"], vec!["으려는"]),
        ("살려는", vec!["살다"], vec!["으려는"]),
        ("먹으시려는", vec!["먹다"], vec!["시", "으려는"]),
        ("먹자는", vec!["먹다"], vec!["자는"]),
        ("먹어보자는", vec!["먹다", "보다"], vec!["어", "자는"]),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
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
    }
    for (word, id) in [
        ("-으려는", "krdict:86717"),
        ("-려는", "krdict:86688"),
        ("-자는", "krdict:83896"),
    ] {
        assert!(
            db.lookup(word)
                .unwrap()
                .iter()
                .any(|e| e.id == id && e.pos == "품사 없음")
        );
    }
}

#[test]
fn present_conditionals_survive_dictionary_filtering_and_cli_export() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-conditional.json"),
            PathBuf::from("tests/fixtures/krdict-particles.json"),
        ],
        dir.db(),
        "conditional-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemma) in [
        ("한다면", "하다"),
        ("산다면", "살다"),
        ("먹는다면", "먹다"),
        ("먹으신다면", "먹다"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && annotation.has_match(&a.lemmas[0], true)
                && a.morphemes
                    .last()
                    .is_some_and(|m| m.form == "는다면" && m.kind == klem::MorphemeKind::Ending)),
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
    let entries = db.lookup("-는다면").unwrap();
    assert!(
        entries
            .iter()
            .any(|e| e.id == "krdict:68738" && e.pos == "어미")
    );
    assert!(
        entries
            .iter()
            .any(|e| e.id == "krdict:68841" && e.pos == "품사 없음")
    );
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
fn reporting_endings_preserve_dictionary_filtered_cli_paths() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-reporting.json")],
        dir.db(),
        "reporting-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemma, ending) in [
        ("넘었답니다", "넘다", "답니다"),
        ("묻었답니다", "묻다", "답니다"),
        ("좋았답니다", "좋다", "답니다"),
        ("산답니다", "살다", "는답니다"),
        ("먹는답니다", "먹다", "는답니다"),
        ("물어본답니다", "물어보다", "는답니다"),
        ("도우랍니다", "돕다", "으랍니다"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a.lemmas.len() == 1
                && a.lemmas[0].text == lemma
                && annotation.has_match(&a.lemmas[0], true)
                && a.morphemes.last().is_some_and(|m| m.form == ending)),
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
}

#[test]
fn causal_endings_keep_dictionary_filtered_cli_paths_and_nominal_alternatives() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-causal.json")],
        dir.db(),
        "causal-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, ending) in [
        ("추천하길래", vec!["추천하다"], "길래"),
        ("뽑길래", vec!["뽑다"], "길래"),
        ("살길래", vec!["살다"], "길래"),
        ("먹기에", vec!["먹다"], "기에"),
        ("학생이기에", vec!["학생", "이다"], "기에"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.lemmas.iter().all(|l| annotation.has_match(l, true))
                    && a.morphemes.last().is_some_and(|m| m.form == ending)
            }),
            "{word}"
        );
        if ending == "기에" {
            assert!(
                kept.analyses.iter().any(|a| a
                    .morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(["기", "에"])),
                "{word}"
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
}

#[test]
fn destination_particles_keep_filtered_bundled_and_component_paths() {
    use klem::MorphemeKind;
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-destination-particles.json",
        )],
        dir.db(),
        "destination-particles-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms, kind) in [
        ("강에다", vec!["강"], vec!["에다"], MorphemeKind::Particle),
        (
            "강에다",
            vec!["강"],
            vec!["에", "다"],
            MorphemeKind::Particle,
        ),
        (
            "거기에다",
            vec!["거기"],
            vec!["에다"],
            MorphemeKind::Particle,
        ),
        (
            "학교에다가",
            vec!["학교"],
            vec!["에다가"],
            MorphemeKind::Particle,
        ),
        (
            "친구에게다",
            vec!["친구"],
            vec!["에게다"],
            MorphemeKind::Particle,
        ),
        (
            "친구에게다가",
            vec!["친구"],
            vec!["에게다가"],
            MorphemeKind::Particle,
        ),
        (
            "친구한테다",
            vec!["친구"],
            vec!["한테다"],
            MorphemeKind::Particle,
        ),
        (
            "친구한테다가",
            vec!["친구"],
            vec!["한테다가"],
            MorphemeKind::Particle,
        ),
        (
            "서울로다가",
            vec!["서울"],
            vec!["로다가"],
            MorphemeKind::Particle,
        ),
        (
            "손으로다가",
            vec!["손"],
            vec!["으로다가"],
            MorphemeKind::Particle,
        ),
        (
            "노동자보고",
            vec!["노동자"],
            vec!["보고"],
            MorphemeKind::Particle,
        ),
        ("나더러", vec!["나"], vec!["더러"], MorphemeKind::Particle),
        ("저기다", vec!["저기"], vec!["다"], MorphemeKind::Particle),
        (
            "어디다가",
            vec!["어디"],
            vec!["다가"],
            MorphemeKind::Particle,
        ),
        ("돌보고", vec!["돌보다"], vec!["고"], MorphemeKind::Ending),
        ("먹다가", vec!["먹다"], vec!["다가"], MorphemeKind::Ending),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
                && a.morphemes.last().unwrap().kind == kind
                && a.lemmas.iter().all(|l| annotation.has_match(l, true))),
            "{word}: {forms:?}"
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
}

#[test]
fn enumerative_particles_and_choice_endings_keep_filtered_cli_alternatives() {
    use klem::MorphemeKind;
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-enumerative-particles.json",
        )],
        dir.db(),
        "enumerative-particles-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms, last_kind) in [
        (
            "학생이라든가",
            vec!["학생"],
            vec!["이라든가"],
            MorphemeKind::Particle,
        ),
        (
            "학생이라든가",
            vec!["학생", "이다"],
            vec!["라든가"],
            MorphemeKind::Ending,
        ),
        (
            "학교라든가",
            vec!["학교"],
            vec!["라든가"],
            MorphemeKind::Particle,
        ),
        (
            "밥이라든지",
            vec!["밥"],
            vec!["이라든지"],
            MorphemeKind::Particle,
        ),
        (
            "학교에서라든지",
            vec!["학교"],
            vec!["에서", "라든지"],
            MorphemeKind::Particle,
        ),
        (
            "학생이든가",
            vec!["학생"],
            vec!["이든가"],
            MorphemeKind::Particle,
        ),
        (
            "학생이든가",
            vec!["학생", "이다"],
            vec!["든가"],
            MorphemeKind::Ending,
        ),
        (
            "학교든가",
            vec!["학교"],
            vec!["든가"],
            MorphemeKind::Particle,
        ),
        ("먹든가", vec!["먹다"], vec!["든가"], MorphemeKind::Ending),
        (
            "먹는다든가",
            vec!["먹다"],
            vec!["는다", "든가"],
            MorphemeKind::Particle,
        ),
        (
            "먹는다든가",
            vec!["먹다"],
            vec!["는다든가"],
            MorphemeKind::Ending,
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.morphemes
                        .iter()
                        .map(|m| m.form.as_str())
                        .eq(forms.iter().copied())
                    && a.morphemes.last().unwrap().kind == last_kind
                    && a.lemmas.iter().all(|l| annotation.has_match(l, true))
            }),
            "{word}: {forms:?}"
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
}

#[test]
fn quoted_alternatives_preserve_dictionary_filtered_cli_groups() {
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from(
            "tests/fixtures/krdict-quoted-alternatives.json",
        )],
        dir.db(),
        "quoted-alternatives-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, ending) in [
        ("된다거나", vec!["되다"], "는다거나"),
        ("경시한다든가", vec!["경시하다"], "는다든가"),
        ("세련되었다든가", vec!["세련되다"], "다든가"),
        ("먹었다거나", vec!["먹다"], "다거나"),
        ("학생이라거나", vec!["학생", "이다"], "라거나"),
        ("교사라든가", vec!["교사", "이다"], "라든가"),
        ("도우라거나", vec!["돕다"], "으라거나"),
        ("먹자거나", vec!["먹다"], "자거나"),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| {
                a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .eq(lemmas.iter().copied())
                    && a.lemmas.iter().all(|l| annotation.has_match(l, true))
                    && a.morphemes.last().is_some_and(|m| m.form == ending)
            }),
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
}

#[test]
fn shortened_hada_matches_full_lemmas_in_cli_and_pos_filtering() {
    let dir = Scratch::new();
    import_krdict(
        &[
            PathBuf::from("tests/fixtures/krdict-hada.json"),
            PathBuf::from("tests/fixtures/krdict-hada-ki.json"),
        ],
        dir.db(),
        "hada-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemma, ending) in [
        ("강구키", "강구하다", "기"),
        ("조성키로", "조성하다", "기로"),
        ("돌변키도", "돌변하다", "기도"),
        ("생각기", "생각하다", "기"),
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

#[test]
fn enumerative_da_keeps_particle_and_copula_paths_in_dictionary_cli() {
    use klem::MorphemeKind;
    let dir = Scratch::new();
    import_krdict(
        &[PathBuf::from("tests/fixtures/krdict-enumerative-da.json")],
        dir.db(),
        "enumerative-da-regression",
    )
    .unwrap();
    let db = SqliteDictionary::open(dir.db()).unwrap();
    let mut session = DictionarySession::new(&db, 1024 * 1024);
    for (word, lemmas, forms, kind) in [
        ("구두다", vec!["구두"], vec!["다"], MorphemeKind::Particle),
        ("옷이다", vec!["옷"], vec!["이다"], MorphemeKind::Particle),
        ("노래다", vec!["노래"], vec!["다"], MorphemeKind::Particle),
        ("춤이다", vec!["춤"], vec!["이다"], MorphemeKind::Particle),
        (
            "학생들이다",
            vec!["학생"],
            vec!["들", "이다"],
            MorphemeKind::Particle,
        ),
        (
            "먹기다",
            vec!["먹다"],
            vec!["기", "다"],
            MorphemeKind::Particle,
        ),
        (
            "먹음이다",
            vec!["먹다"],
            vec!["음", "이다"],
            MorphemeKind::Particle,
        ),
        ("저기다", vec!["저기"], vec!["다"], MorphemeKind::Particle),
        (
            "손으로다",
            vec!["손"],
            vec!["으로", "다"],
            MorphemeKind::Particle,
        ),
        (
            "구두다",
            vec!["구두", "이다"],
            vec!["다"],
            MorphemeKind::Ending,
        ),
        (
            "옷이다",
            vec!["옷", "이다"],
            vec!["다"],
            MorphemeKind::Ending,
        ),
    ] {
        let result = Lemmatizer::new().analyze_word(word).unwrap();
        let annotation = session.annotate(&result).unwrap();
        let kept = result.filtered(|l| annotation.has_match(l, false));
        assert!(
            kept.analyses.iter().any(|a| a
                .lemmas
                .iter()
                .map(|l| l.text.as_str())
                .eq(lemmas.iter().copied())
                && a.morphemes
                    .iter()
                    .map(|m| m.form.as_str())
                    .eq(forms.iter().copied())
                && a.morphemes.last().unwrap().kind == kind
                && a.lemmas.iter().all(|l| annotation.has_match(l, true))),
            "{word}: {forms:?}"
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
}
