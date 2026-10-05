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
    /// it. Nominals consume licensed suffixes, then particles. A final 답다
    /// suffix consumes its own prefinals and ending. Source-listed -되다 also
    /// consumes its own inflections after its noun/adverb/root lookup base.
    /// This also handles nominalizations
    /// nested inside copulas. Reviewed noun/adverb bases before suffix 이/히
    /// have no inflectional ending. `derivation.nominal.compound` marks the first
    /// two lemmas as one noun-forming base; the suffix follows both components.
    /// No source offsets or contextual interpretation are
    /// implied. Returns `None` for externally constructed, unsupported shapes.
    pub fn breakdown(&self) -> Option<Vec<Component>> {
        if self.lemmas.is_empty() {
            return None;
        }
        if self
            .morphemes
            .iter()
            .any(|m| m.kind == MorphemeKind::Suffix && m.form == "씩")
            && !self.rules.iter().any(|r| r == "suffix.distributive.ssik")
        {
            return None;
        }
        if self
            .rules
            .iter()
            .any(|r| r == crate::predicate_compound::RULE)
            && !(0..self.lemmas.len()).any(|i| crate::predicate_compound::is_left(self, i))
        {
            return None;
        }
        let verbal_compound = self
            .rules
            .iter()
            .any(|r| r == "derivation.nominal.compound");
        let root_compound = self
            .rules
            .iter()
            .any(|r| r == "derivation.nominal.root_compound");
        let compound = verbal_compound || root_compound;
        if root_compound
            && (verbal_compound
                || !self.rules.iter().any(|r| r == "suffix.nominal.i")
                || self.lemmas.len() < 2
                || self.lemmas[0].kind != LemmaKind::Nominal
                || self.lemmas[1].kind != LemmaKind::Root
                || !crate::grammar::NOUN_I_ROOT_COMPOUNDS
                    .iter()
                    .any(|&(_, left, right, _)| {
                        left == self.lemmas[0].text && right == self.lemmas[1].text
                    }))
        {
            return None;
        }
        let mut prefixes = crate::grammar::NOUN_I_PREFIX_FORMS
            .iter()
            .filter(|&&(_, _, _, rule)| self.rules.iter().any(|r| r == rule));
        let prefix = prefixes.next();
        if prefixes.next().is_some() {
            return None;
        }
        let prefixed = prefix.is_some();
        let bagi = self.rules.iter().any(|r| r == "suffix.nominal.bagi");
        let adnominal = self
            .rules
            .iter()
            .any(|r| r == "derivation.nominal.adnominal");
        let bound_i = self.rules.iter().any(|r| r == "derivation.nominal.bound_i");
        let dungi = self.rules.iter().any(|r| r == "suffix.nominal.dungi");
        let noun_i_rule = self.rules.iter().any(|r| r == "suffix.nominal.i");
        if dungi && !adnominal {
            return None;
        }
        if adnominal || bound_i {
            if compound
                || prefixed
                || bagi
                || (adnominal && bound_i)
                || self
                    .rules
                    .iter()
                    .any(|r| r == "derivation.nominal.related_root")
                || self.lemmas[0].kind != LemmaKind::Predicate
                || !self
                    .morphemes
                    .first()
                    .is_some_and(|m| m.kind == MorphemeKind::Ending && m.form == "ㄴ")
            {
                return None;
            }
            if adnominal {
                let suffix = if dungi { "둥이" } else { "이" };
                if noun_i_rule == dungi
                    || !crate::grammar::NOUN_ADNOMINAL_FORMS
                        .iter()
                        .any(|&(_, head, _, form)| head == self.lemmas[0].text && form == suffix)
                    || !self
                        .morphemes
                        .get(1)
                        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == suffix)
                {
                    return None;
                }
            } else if noun_i_rule
                || dungi
                || self.lemmas[0].text != "못나다"
                || !self
                    .lemmas
                    .get(1)
                    .is_some_and(|l| l.kind == LemmaKind::Nominal && l.text == "이")
            {
                return None;
            }
        }
        if let Some(&(_, form, base, _)) = prefix
            && (compound
                || bagi
                || !self.rules.iter().any(|r| r == "suffix.nominal.i")
                || self.lemmas[0].text != base
                || self.lemmas[0].kind != LemmaKind::Nominal
                || !self
                    .morphemes
                    .first()
                    .is_some_and(|m| m.kind == MorphemeKind::Prefix && m.form == form))
        {
            return None;
        }
        if self
            .morphemes
            .iter()
            .filter(|m| m.kind == MorphemeKind::Prefix)
            .count()
            != usize::from(prefixed)
            || (bagi
                && (compound
                    || self.rules.iter().any(|r| r == "suffix.nominal.i")
                    || self.lemmas[0].text != "점"
                    || self.lemmas[0].kind != LemmaKind::Nominal))
        {
            return None;
        }
        if self
            .rules
            .iter()
            .any(|r| r == "derivation.nominal.related_root")
            && (compound
                || !self.rules.iter().any(|r| r == "suffix.nominal.i")
                || self.lemmas[0].kind != LemmaKind::Predicate
                || !crate::grammar::NOUN_I_ROOTS
                    .iter()
                    .any(|&(_, _, heads)| heads.contains(&self.lemmas[0].text.as_str())))
        {
            return None;
        }
        if verbal_compound
            && (!self.rules.iter().any(|r| r == "suffix.nominal.i")
                || self.lemmas.len() < 2
                || !matches!(
                    self.lemmas[0].kind,
                    LemmaKind::Nominal | LemmaKind::Predicate
                )
                || self.lemmas[1].kind != LemmaKind::Predicate)
        {
            return None;
        }
        let mut parts = Vec::with_capacity(self.lemmas.len() + self.morphemes.len());
        let mut cursor = 0;
        if prefixed {
            parts.push(Component::Morpheme(0));
            cursor = 1;
        }
        for (index, lemma) in self.lemmas.iter().enumerate() {
            parts.push(Component::Lemma(index));
            if crate::predicate_compound::is_left(self, index) {
                continue;
            }
            let predicate = matches!(
                lemma.kind,
                LemmaKind::Predicate | LemmaKind::Auxiliary | LemmaKind::Copula
            );
            if bound_i && index == 0 {
                // The adnominal ending belongs to 못나다. Outer particles and
                // suffixes belong to the following bound noun, even when no
                // plural intervenes to distinguish their serialized positions.
                parts.push(Component::Morpheme(cursor));
                cursor += 1;
                continue;
            }
            if compound && index == 0 {
                if predicate {
                    lemma
                        .text
                        .strip_suffix('다')
                        .filter(|stem| !stem.is_empty())?;
                }
                continue;
            }
            let noun_i = index == usize::from(compound)
                && matches!(
                    lemma.kind,
                    LemmaKind::Nominal
                        | LemmaKind::Predicate
                        | LemmaKind::Adverbial
                        | LemmaKind::Root
                )
                && self.rules.iter().any(|r| r == "suffix.nominal.i");
            let noun_suffix = noun_i || ((bagi || dungi) && index == 0);
            let doeda_suffix =
                crate::engine::derivational_class(lemma, &self.rules, &self.morphemes[cursor..])
                    .is_some();
            let mut derived_predicate = false;
            if lemma.kind == LemmaKind::Nominal && !noun_suffix {
                let start = cursor;
                while self
                    .morphemes
                    .get(cursor)
                    .is_some_and(|m| m.kind == MorphemeKind::Suffix)
                {
                    parts.push(Component::Morpheme(cursor));
                    cursor += 1;
                }
                let mut suffixes = self.morphemes[start..cursor]
                    .iter()
                    .map(|m| m.form.as_str())
                    .collect::<Vec<_>>();
                if suffixes.last() == Some(&"답다") {
                    derived_predicate = true;
                    suffixes.pop();
                }
                if suffixes.last() == Some(&"하다") {
                    if crate::hada_suffix::owner_class(lemma, &self.rules, &self.morphemes[start..])
                        .is_none()
                        || !matches!(
                            suffixes.as_slice(),
                            ["하다"] | ["화", "하다"] | ["시", "하다"]
                        )
                    {
                        return None;
                    }
                    derived_predicate = true;
                    suffixes.pop();
                }
                if suffixes.last() == Some(&"되다") {
                    if !doeda_suffix
                        || (suffixes.len() != 1
                            && !(crate::nominal_si::passive_owner(
                                lemma,
                                &self.rules,
                                &self.morphemes[start..],
                            ) || crate::nominal_hwa::passive_owner(
                                lemma,
                                &self.rules,
                                &self.morphemes[start..],
                            )))
                    {
                        return None;
                    }
                    derived_predicate = true;
                    suffixes.pop();
                }
                if !matches!(
                    suffixes.as_slice(),
                    [] | ["님"]
                        | ["적"]
                        | ["들"]
                        | ["님", "들"]
                        | ["이"]
                        | ["히"]
                        | ["시"]
                        | ["시", "들"]
                        | ["시", "쯤"]
                        | ["시", "들", "쯤"]
                        | ["화"]
                        | ["화", "들"]
                        | ["화", "쯤"]
                        | ["화", "들", "쯤"]
                        | ["쯤"]
                        | ["님", "쯤"]
                        | ["적", "쯤"]
                        | ["들", "쯤"]
                        | ["님", "들", "쯤"]
                        | ["씩"]
                        | ["님", "씩"]
                        | ["적", "씩"]
                        | ["들", "씩"]
                        | ["님", "들", "씩"]
                        | ["시", "씩"]
                        | ["시", "들", "씩"]
                        | ["화", "씩"]
                        | ["화", "들", "씩"]
                ) || (derived_predicate
                    && suffixes.iter().any(|s| matches!(*s, "적" | "쯤" | "씩")))
                {
                    return None;
                }
                if suffixes.first() == Some(&"시")
                    && !crate::nominal_si::owner(lemma, &self.rules, &self.morphemes[start..])
                {
                    return None;
                }
                if suffixes.first() == Some(&"화")
                    && !crate::nominal_hwa::owner(lemma, &self.rules, &self.morphemes[start..])
                {
                    return None;
                }
            }
            if doeda_suffix && lemma.kind != LemmaKind::Nominal {
                parts.push(Component::Morpheme(cursor));
                cursor += 1;
                derived_predicate = true;
            }
            if predicate {
                lemma
                    .text
                    .strip_suffix('다')
                    .filter(|stem| !stem.is_empty())?;
            }
            if noun_suffix {
                if adnominal {
                    parts.push(Component::Morpheme(cursor));
                    cursor += 1;
                }
                let first = self.morphemes.get(cursor)?;
                if first.kind != MorphemeKind::Suffix
                    || first.form
                        != if noun_i {
                            "이"
                        } else if dungi {
                            "둥이"
                        } else {
                            "박이"
                        }
                {
                    return None;
                }
                parts.push(Component::Morpheme(cursor));
                cursor += 1;
                for form in ["들", "쯤"] {
                    if self
                        .morphemes
                        .get(cursor)
                        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == form)
                    {
                        parts.push(Component::Morpheme(cursor));
                        cursor += 1;
                    }
                }
                if self
                    .morphemes
                    .get(cursor)
                    .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "씩")
                {
                    if self
                        .morphemes
                        .get(cursor.saturating_sub(1))
                        .is_some_and(|m| m.kind == MorphemeKind::Suffix && m.form == "쯤")
                    {
                        return None;
                    }
                    parts.push(Component::Morpheme(cursor));
                    cursor += 1;
                }
            }
            let adverbial = !noun_suffix
                && matches!(
                    lemma.kind,
                    LemmaKind::Predicate | LemmaKind::Adverbial | LemmaKind::Root
                )
                && self.morphemes.get(cursor).is_some_and(|m| {
                    m.kind == MorphemeKind::Suffix && matches!(m.form.as_str(), "이" | "히")
                });
            if lemma.kind == LemmaKind::Root && !adverbial && !noun_i && !derived_predicate {
                return None;
            }
            if adverbial {
                parts.push(Component::Morpheme(cursor));
                cursor += 1;
            } else if !noun_suffix && (predicate || derived_predicate) {
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
            spelling_paths: Vec::new(),
        };
        assert!(a.breakdown().is_none());
        let mut a = Lemmatizer::new()
            .analyze_word("먹어봤어요")
            .unwrap()
            .analyses
            .into_iter()
            .find(|a| {
                a.lemmas.len() == 2
                    && a.morphemes
                        .last()
                        .is_some_and(|m| m.kind == MorphemeKind::Ending)
            })
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
