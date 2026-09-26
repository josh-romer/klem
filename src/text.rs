use crate::{Lemmatizer, WordAnalysis};
use serde::Serialize;
use std::{ops::Range, sync::Arc};
use unicode_general_category::{GeneralCategory::*, get_general_category};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum TokenKind {
    Word,
    Punctuation,
    Whitespace,
}

pub(crate) fn kind(c: char) -> TokenKind {
    if c.is_whitespace() {
        TokenKind::Whitespace
    } else if matches!(
        get_general_category(c),
        ClosePunctuation
            | ConnectorPunctuation
            | DashPunctuation
            | FinalPunctuation
            | InitialPunctuation
            | OpenPunctuation
            | OtherPunctuation
            | MathSymbol
            | CurrencySymbol
            | ModifierSymbol
            | OtherSymbol
            | Control
            | Format
    ) {
        TokenKind::Punctuation
    } else {
        TokenKind::Word
    }
}

/// Lossless tokens. Offsets always refer to the original UTF-8 input.
pub struct Tokenizer<'a> {
    source: &'a str,
    offset: usize,
}
impl<'a> Tokenizer<'a> {
    pub fn new(source: &'a str) -> Self {
        Self { source, offset: 0 }
    }
}
impl<'a> Iterator for Tokenizer<'a> {
    type Item = (Range<usize>, TokenKind, &'a str);
    fn next(&mut self) -> Option<Self::Item> {
        let rest = &self.source[self.offset..];
        let first = rest.chars().next()?;
        let token_kind = kind(first);
        let len = if token_kind == TokenKind::Punctuation {
            first.len_utf8()
        } else {
            rest.char_indices()
                .find(|(_, c)| kind(*c) != token_kind)
                .map_or(rest.len(), |(i, _)| i)
        };
        let start = self.offset;
        self.offset += len;
        Some((
            start..self.offset,
            token_kind,
            &self.source[start..self.offset],
        ))
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct TokenAnalysis {
    pub surface: String,
    pub span: Range<usize>,
    pub kind: TokenKind,
    /// Whitespace/punctuation pass through with no linguistic claims.
    pub analysis: Option<Arc<WordAnalysis>>,
}

pub struct TextIter<'a> {
    engine: &'a Lemmatizer,
    tokens: Tokenizer<'a>,
}
impl<'a> TextIter<'a> {
    pub(crate) fn new(engine: &'a Lemmatizer, source: &'a str) -> Self {
        Self {
            engine,
            tokens: Tokenizer::new(source),
        }
    }
}
impl Iterator for TextIter<'_> {
    type Item = TokenAnalysis;
    fn next(&mut self) -> Option<Self::Item> {
        let (span, kind, surface) = self.tokens.next()?;
        let analysis = (kind == TokenKind::Word).then(|| {
            Arc::new(
                self.engine
                    .analyze_word(surface)
                    .expect("nonempty token without whitespace"),
            )
        });
        Some(TokenAnalysis {
            surface: surface.into(),
            span,
            kind,
            analysis,
        })
    }
}

/// Stream lossless records without buffering a whole line or book. UTF-8 is
/// validated before analysis; an error can follow records already emitted.
pub fn stream<R: std::io::Read>(
    mut reader: R,
    session: &mut crate::Session,
    mut emit: impl FnMut(TokenAnalysis) -> std::io::Result<()>,
) -> std::io::Result<()> {
    use std::io::{Error, ErrorKind};
    let mut pending = Vec::new();
    let mut token = String::new();
    let mut token_kind = TokenKind::Whitespace;
    let mut start = 0;
    let mut offset = 0;
    let mut block = [0u8; 8192];
    let flush = |token: &mut String,
                 kind,
                 start,
                 end,
                 session: &mut crate::Session,
                 emit: &mut dyn FnMut(TokenAnalysis) -> std::io::Result<()>| {
        if token.is_empty() {
            return Ok(());
        }
        let surface = std::mem::take(token);
        let analysis = if kind == TokenKind::Word {
            Some(
                session
                    .analyze_word(&surface)
                    .map_err(|e| Error::new(ErrorKind::InvalidData, e))?,
            )
        } else {
            None
        };
        emit(TokenAnalysis {
            surface,
            span: start..end,
            kind,
            analysis,
        })
    };
    loop {
        let n = match reader.read(&mut block) {
            Err(e) if e.kind() == ErrorKind::Interrupted => continue,
            result => result?,
        };
        pending.extend_from_slice(&block[..n]);
        let (valid_len, invalid) = match std::str::from_utf8(&pending) {
            Ok(s) => (s.len(), false),
            Err(e) => (e.valid_up_to(), e.error_len().is_some() || n == 0),
        };
        let valid = std::str::from_utf8(&pending[..valid_len]).expect("validated prefix");
        for c in valid.chars() {
            let next_kind = kind(c);
            if !token.is_empty()
                && (next_kind != token_kind || token_kind == TokenKind::Punctuation)
            {
                flush(&mut token, token_kind, start, offset, session, &mut emit)?;
            }
            if token.is_empty() {
                start = offset;
                token_kind = next_kind;
            }
            token.push(c);
            offset += c.len_utf8();
        }
        pending.drain(..valid_len);
        if invalid {
            return Err(Error::new(
                ErrorKind::InvalidData,
                format!("invalid UTF-8 at byte {offset}"),
            ));
        }
        if n == 0 {
            flush(&mut token, token_kind, start, offset, session, &mut emit)?;
            return Ok(());
        }
    }
}
