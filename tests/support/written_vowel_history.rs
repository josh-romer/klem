//! Only COV-021k's vowel and COV-021o's owned ㄼ obligations are projected.
//! Frozen linguistic judgments, lexical candidates, order and older spelling
//! obligations remain exact. The new obligations have independent owner tests.
use klem::{Analysis, SpellingClass, WordAnalysis};
#[path = "complex_bieup_history.rs"]
pub mod complex_bieup;
pub fn project_analysis(a: &Analysis) -> Analysis {
    let mut a = complex_bieup::project_analysis(a);
    for path in &mut a.spelling_paths {
        path.retain(|r| {
            !matches!(
                r.class,
                SpellingClass::WrittenVowelA
                    | SpellingClass::WrittenVowelEo
                    | SpellingClass::EuUncontracted
            )
        });
    }
    if a.spelling_paths.iter().any(Vec::is_empty) {
        a.spelling_paths.clear();
    }
    a.spelling_paths.sort();
    a.spelling_paths.dedup();
    a
}
#[allow(dead_code)]
pub fn project_word(w: &WordAnalysis) -> WordAnalysis {
    let mut w = w.clone();
    w.analyses = w.analyses.iter().map(project_analysis).collect();
    w
}
