//! Finite compound evidence, distinct from productive predicate suffixes.
//!
//! NIKL, 한국어 교육 어휘 내용 개발(4단계), printed p. 54, lists
//! 잘-잘되다 under 부사+서술어 구성. Whole 잘되다 readings remain available.
use crate::{Analysis, LemmaKind};

pub(crate) const RULE: &str = "compound.predicate.well_doeda";

pub(crate) fn is_left(analysis: &Analysis, index: usize) -> bool {
    analysis.rules.iter().any(|r| r == RULE)
        && analysis
            .lemmas
            .get(index)
            .is_some_and(|l| l.kind == LemmaKind::Adverbial && l.text == "잘")
        && analysis
            .lemmas
            .get(index + 1)
            .is_some_and(|l| l.kind == LemmaKind::Predicate && l.text == "되다")
}

pub(crate) fn is_owner(analysis: &Analysis, index: usize) -> bool {
    index
        .checked_sub(1)
        .is_some_and(|left| is_left(analysis, left))
}
