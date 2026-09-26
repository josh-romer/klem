//! Quotation fragments preserve token boundaries and state omitted context.
use klem::{LemmaKind, Lemmatizer, MorphemeKind, Session};
use std::sync::Arc;
use unicode_normalization::UnicodeNormalization;

#[test]
fn explicit_and_omitted_fragments_keep_copula_role_and_conditions() {
    let engine = Lemmatizer::new();
    for (word, rule) in [
        ("이라는", "copula.fragment"),
        ("라는", "copula.omitted_fragment"),
    ] {
        let result = engine.analyze_word(word).unwrap();
        let a = result
            .analyses
            .iter()
            .find(|a| a.rules.iter().any(|r| r == rule))
            .unwrap();
        assert_eq!(a.lemmas.len(), 1);
        assert_eq!(a.lemmas[0].text, "이다");
        assert_eq!(a.lemmas[0].kind, LemmaKind::Copula);
        assert_eq!(a.morphemes.len(), 1);
        assert_eq!(a.morphemes[0].form, "라는");
        assert_eq!(a.morphemes[0].kind, MorphemeKind::Ending);
        assert!(result.analyses.iter().all(|a| a.breakdown().is_some()));
        assert!(result.analyses.iter().any(|a| a.unchanged));
        assert!(a.rules.iter().all(|r| klem::rule_explanation(r).is_some()));
        assert_eq!(
            result,
            engine
                .analyze_word(&word.nfd().collect::<String>())
                .unwrap()
        );
    }
    for word in [
        "라",
        "라면",
        "라서",
        "라는요",
        "먹는다는",
        "먹라는",
        "학생라는",
        "사회주의라는",
    ] {
        let result = engine.analyze_word(word).unwrap();
        assert!(
            !result
                .analyses
                .iter()
                .any(|a| a.rules.iter().any(|r| r == "copula.omitted_fragment")),
            "{word}"
        );
        assert!(
            result
                .analyses
                .iter()
                .all(|a| a.lemmas.iter().all(|l| !l.text.is_empty()))
        );
    }
    let noun = engine.analyze_word("사회주의라는").unwrap();
    assert!(noun.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["사회주의", "이다"])
    }));
    let bad = engine.analyze_word("학생라는").unwrap();
    assert!(!bad.analyses.iter().any(|a| {
        a.lemmas
            .iter()
            .map(|l| l.text.as_str())
            .eq(["학생", "이다"])
    }));
}

#[test]
fn quotation_punctuation_and_streaming_offsets_are_preserved() {
    let engine = Arc::new(Lemmatizer::new());
    let text = "“사랑”이라는 말과 ‘왜?’라는 물음. 라는";
    let records: Vec<_> = engine.analyze_text(text).collect();
    assert_eq!(
        records
            .iter()
            .map(|r| r.surface.as_str())
            .collect::<String>(),
        text
    );
    for record in &records {
        assert_eq!(&text[record.span.clone()], record.surface);
    }
    let fragments: Vec<_> = records
        .iter()
        .filter(|r| matches!(r.surface.as_str(), "이라는" | "라는"))
        .collect();
    assert_eq!(fragments.len(), 3);
    for record in fragments {
        assert_eq!(
            record.analysis.as_deref(),
            Some(&engine.analyze_word(&record.surface).unwrap())
        );
    }
    // The cache stores conditional word candidates, not an inferred sentence
    // interpretation; a preceding quote does not alter the standalone result.
    let mut session = Session::new(engine, 4096);
    let mut streamed = vec![];
    klem::analyze_reader(text.as_bytes(), &mut session, |r| {
        streamed.push(r);
        Ok(())
    })
    .unwrap();
    assert_eq!(streamed, records);
}
