//! Conditional nominal boundaries when spelling does not supply a Hangul coda.
//!
//! We do not guess a transliteration, numeral reading, or letter-name language.
//! These rule IDs state necessary pronunciation assumptions for a candidate.
use crate::{TokenKind, hangul, text};
use unicode_general_category::{GeneralCategory::*, get_general_category};

pub(crate) fn unknown_coda(base: &str) -> bool {
    // Text analysis never joins punctuation. Apply the same restriction to new
    // hypotheses in word analysis, including symbols and standalone marks.
    let Some(last) = base.chars().rev().find(|c| {
        !matches!(
            get_general_category(*c),
            NonspacingMark | SpacingMark | EnclosingMark
        )
    }) else {
        return false;
    };
    hangul::split(last).is_none()
        && last.is_alphanumeric()
        && base.chars().all(|c| text::kind(c) == TokenKind::Word)
}

pub(crate) fn assumption(base: &str, condition: u8) -> Option<&'static str> {
    if condition == 0 || !unknown_coda(base) {
        return None;
    }
    match condition {
        1 => Some("pronunciation.assumed_consonant"),
        2 => Some("pronunciation.assumed_vowel"),
        3 => Some("pronunciation.assumed_non_rieul_consonant"),
        4 => Some("pronunciation.assumed_vowel_or_rieul"),
        _ => None,
    }
}
