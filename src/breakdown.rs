//! Ordered, canonical components for reading tools. These are not surface spans.
use crate::{Analysis, LemmaKind, MorphemeKind};
use serde::Serialize;

/// An index into the original analysis, retaining identity without copying it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Component {
    Lemma(usize),
    Morpheme(usize),
}

impl Analysis {
    /// Interleave stems and grammatical components in reading order.
    ///
    /// The engine emits one ending per predicate (including each auxiliary and
    /// copula), with its prefinals before it and nominalization particles after
    /// it. Nominals consume an optional suffix followed by particles. This also handles nominalizations
    /// nested inside copulas. No source offsets or contextual interpretation are
    /// implied. Returns `None` for externally constructed, unsupported shapes.
    pub fn breakdown(&self) -> Option<Vec<Component>> {
        if self.lemmas.is_empty() {
            return None;
        }
        let mut parts = Vec::with_capacity(self.lemmas.len() + self.morphemes.len());
        let mut cursor = 0;
        for (index, lemma) in self.lemmas.iter().enumerate() {
            parts.push(Component::Lemma(index));
            if matches!(
                lemma.kind,
                LemmaKind::Predicate | LemmaKind::Auxiliary | LemmaKind::Copula
            ) {
                lemma
                    .text
                    .strip_suffix('다')
                    .filter(|stem| !stem.is_empty())?;
                while self
                    .morphemes
                    .get(cursor)
                    .is_some_and(|m| m.kind == MorphemeKind::Prefinal)
                {
                    parts.push(Component::Morpheme(cursor));
                    cursor += 1;
                }
                if self.morphemes.get(cursor)?.kind != MorphemeKind::Ending {
                    return None;
                }
                parts.push(Component::Morpheme(cursor));
                cursor += 1;
            }
            if lemma.kind == LemmaKind::Nominal
                && self
                    .morphemes
                    .get(cursor)
                    .is_some_and(|m| m.kind == MorphemeKind::Suffix)
            {
                parts.push(Component::Morpheme(cursor));
                cursor += 1;
            }
            while self
                .morphemes
                .get(cursor)
                .is_some_and(|m| m.kind == MorphemeKind::Particle)
            {
                parts.push(Component::Morpheme(cursor));
                cursor += 1;
            }
        }
        (cursor == self.morphemes.len()).then_some(parts)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::Lemmatizer;

    #[test]
    fn every_regression_candidate_preserves_component_order_and_identity() {
        let fixtures: serde_json::Value =
            serde_json::from_str(include_str!("../tests/fixtures/optimization.json")).unwrap();
        for fixture in fixtures.as_array().unwrap() {
            let word = fixture["word"].as_str().unwrap();
            for a in Lemmatizer::new().analyze_word(word).unwrap().analyses {
                let order = a.breakdown().expect(word);
                let lemmas: Vec<_> = order
                    .iter()
                    .filter_map(|c| match c {
                        Component::Lemma(i) => Some(*i),
                        _ => None,
                    })
                    .collect();
                let morphs: Vec<_> = order
                    .iter()
                    .filter_map(|c| match c {
                        Component::Morpheme(i) => Some(*i),
                        _ => None,
                    })
                    .collect();
                assert_eq!(lemmas, (0..a.lemmas.len()).collect::<Vec<_>>(), "{word}");
                assert_eq!(morphs, (0..a.morphemes.len()).collect::<Vec<_>>(), "{word}");
            }
        }
    }

    #[test]
    fn malformed_external_analyses_are_not_guessed() {
        let a = Analysis {
            lemmas: vec![],
            morphemes: vec![],
            rules: vec![],
            unchanged: false,
        };
        assert!(a.breakdown().is_none());
        let mut a = Lemmatizer::new()
            .analyze_word("먹어봤어요")
            .unwrap()
            .analyses
            .into_iter()
            .find(|a| a.lemmas.len() == 2)
            .unwrap();
        a.morphemes.pop();
        assert!(a.breakdown().is_none());
    }

    #[test]
    fn ordered_components_cover_auxiliaries_and_nested_nominalizations() {
        for (word, lemmas, ordered) in [
            ("저는", "저", "저 는"),
            ("지식인들을", "지식인", "지식인 들 을"),
            ("지식인들이다", "지식인 이다", "지식인 들 이다 다"),
            ("공부해요", "공부하다", "공부하다 어요"),
            ("먹어봤어요", "먹다 보다", "먹다 어 보다 었 어요"),
            ("학교에서만이다", "학교 이다", "학교 에서 만 이다 다"),
            ("먹어보기는", "먹다 보다", "먹다 어 보다 기 는"),
            (
                "먹어보기는이다",
                "먹다 보다 이다",
                "먹다 어 보다 기 는 이다 다",
            ),
            ("건", "것", "것 는"),
        ] {
            let result = Lemmatizer::new().analyze_word(word).unwrap();
            let mut found = false;
            for a in &result.analyses {
                let parts = a.breakdown().expect(word);
                assert_eq!(parts.len(), a.lemmas.len() + a.morphemes.len());
                let texts = parts
                    .iter()
                    .map(|part| match *part {
                        Component::Lemma(i) => a.lemmas[i].text.as_str(),
                        Component::Morpheme(i) => a.morphemes[i].form.as_str(),
                    })
                    .collect::<Vec<_>>()
                    .join(" ");
                if a.lemmas
                    .iter()
                    .map(|l| l.text.as_str())
                    .collect::<Vec<_>>()
                    .join(" ")
                    == lemmas
                    && texts == ordered
                {
                    found = true;
                }
            }
            assert!(found, "missing ordered reading for {word}: {ordered}");
        }
    }
}
