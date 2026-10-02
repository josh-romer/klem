//! Project only newly recorded ㄼ obligations for pre-COV-021o comparisons.
//! Simple ㅂ evidence and every earlier spelling class remain exact.
use klem::{Analysis, SpellingClass};
pub fn project_analysis(analysis: &Analysis) -> Analysis {
    use klem::breakdown::Component;
    let mut projected = analysis.clone();
    let mut owners = vec![None; analysis.morphemes.len()];
    if let Some(components) = analysis.breakdown() {
        let mut owner = None;
        for component in components {
            match component {
                Component::Lemma(index) => owner = Some(index),
                Component::Morpheme(index) => owners[index] = owner,
            }
        }
    }
    for path in &mut projected.spelling_paths {
        path.retain(|requirement| {
            let complex = owners[requirement.morpheme_index].is_some_and(|index| {
                analysis.lemmas[index]
                    .text
                    .strip_suffix('다')
                    .and_then(|stem| stem.chars().last())
                    .is_some_and(|last| {
                        ('가'..='힣').contains(&last) && (last as u32 - '가' as u32) % 28 == 11
                    })
            });
            !(complex
                && matches!(
                    requirement.class,
                    SpellingClass::BieupRegular | SpellingClass::BieupIrregular
                ))
        });
    }
    if projected.spelling_paths.iter().any(Vec::is_empty) {
        projected.spelling_paths.clear();
    }
    projected.spelling_paths.sort();
    projected.spelling_paths.dedup();
    projected
}
