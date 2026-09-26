use klem::{Lemmatizer, Session, TokenKind};
use std::{
    io::{self, Read},
    sync::Arc,
};

struct Chunks<'a> {
    bytes: &'a [u8],
    chunk: usize,
}
impl Read for Chunks<'_> {
    fn read(&mut self, into: &mut [u8]) -> io::Result<usize> {
        let n = self.bytes.len().min(self.chunk).min(into.len());
        into[..n].copy_from_slice(&self.bytes[..n]);
        self.bytes = &self.bytes[n..];
        Ok(n)
    }
}

#[test]
fn streaming_matches_memory_at_every_small_chunk_size() {
    let e = Arc::new(Lemmatizer::new());
    let text = "“먹었어요.”\r\n학교에서는 café 😀 갔어요! English 42\t끝";
    let expected: Vec<_> = e.analyze_text(text).collect();
    assert_eq!(
        expected
            .iter()
            .map(|r| r.surface.as_str())
            .collect::<String>(),
        text
    );
    for record in &expected {
        assert_eq!(&text[record.span.clone()], record.surface);
    }
    for chunk in 1..=17 {
        let mut session = Session::new(e.clone(), 4096);
        let mut actual = Vec::new();
        klem::analyze_reader(
            Chunks {
                bytes: text.as_bytes(),
                chunk,
            },
            &mut session,
            |r| {
                actual.push(r);
                Ok(())
            },
        )
        .unwrap();
        assert_eq!(actual, expected);
        assert!(session.cached_bytes() <= 4096);
    }
    let nfd = expected
        .iter()
        .find(|r| r.surface.starts_with('ᄀ'))
        .unwrap();
    assert_eq!(nfd.analysis.as_ref().unwrap().normalized, "갔어요");
    assert!(
        nfd.analysis
            .as_ref()
            .unwrap()
            .lemma_strings()
            .contains(&"가다")
    );
    assert!(
        expected
            .iter()
            .any(|r| r.kind == TokenKind::Punctuation && r.surface == "😀")
    );
}

#[test]
fn invalid_utf8_and_io_errors_are_reported() {
    for bytes in [&b"word \xff"[..], &b"\xea\xb0"[..]] {
        let mut session = Session::new(Arc::new(Lemmatizer::new()), 0);
        let error = klem::analyze_reader(bytes, &mut session, |_| Ok(())).unwrap_err();
        assert_eq!(error.kind(), io::ErrorKind::InvalidData);
    }
    let mut session = Session::new(Arc::new(Lemmatizer::new()), 0);
    let error = klem::analyze_reader(&b"abc "[..], &mut session, |_| {
        Err(io::Error::other("sink failed"))
    })
    .unwrap_err();
    assert_eq!(error.to_string(), "sink failed");
}

#[test]
fn cache_eviction_and_shared_engine() {
    let engine = Arc::new(Lemmatizer::new());
    let mut cached = Session::new(engine.clone(), 16_384);
    let a = cached.analyze_word("먹다").unwrap();
    assert!(Arc::ptr_eq(&a, &cached.analyze_word("먹다").unwrap()));
    for i in 0..100 {
        cached.analyze_word(&format!("새단어{i}에서")).unwrap();
        assert!(cached.cached_bytes() <= 16_384);
    }
    assert_eq!(*a, engine.analyze_word("먹다").unwrap());
    let mut disabled = Session::new(engine.clone(), 0);
    disabled.analyze_word("먹다").unwrap();
    assert_eq!(disabled.cached_bytes(), 0);
    std::thread::spawn(move || engine.analyze_word("먹다").unwrap())
        .join()
        .unwrap();
}

#[test]
fn empty_and_pass_through() {
    let e = Lemmatizer::new();
    assert!(e.analyze_word("").is_err());
    assert!(e.analyze_word("두 단어").is_err());
    assert_eq!(e.analyze_text("").count(), 0);
    for word in ["English", "42", "ㄱ", "é"] {
        let r = e.analyze_word(word).unwrap();
        assert_eq!(r.analyses.len(), 1);
        assert!(r.analyses[0].unchanged);
    }
}
