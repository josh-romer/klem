//! Bounded splits witnessed by a recovered, dictionary-backed auxiliary chain.
use super::*;
use crate::breakdown::Component;

const RULE: &str = "spacing.predicate_auxiliary";

fn matches_piece(
    raw: &Analysis,
    joined: &Analysis,
    from: (usize, usize),
    to: (usize, usize),
) -> bool {
    let (li, mi) = from;
    let (le, me) = to;
    raw.lemmas.len() == le - li
        && raw
            .lemmas
            .iter()
            .zip(&joined.lemmas[li..le])
            .enumerate()
            .all(|(i, (actual, expected))| {
                actual.text == expected.text
                    && actual.kind
                        == if i == 0 && expected.kind == LemmaKind::Auxiliary {
                            LemmaKind::Predicate
                        } else {
                            expected.kind
                        }
            })
        && raw.morphemes == joined.morphemes[mi..me]
        && raw.breakdown().is_some()
}

struct Witness<'a> {
    analysis: &'a Analysis,
    points: &'a [(usize, usize)],
    context: &'a SpacingSegment,
    prefix_len: usize,
}

impl<D: Dictionary + ?Sized> Search<'_, '_, D> {
    pub(super) fn only_paths(
        &mut self,
        segment: &SpacingSegment,
        analyses: Vec<Analysis>,
    ) -> Result<SpacingSegment> {
        let analysis = WordAnalysis {
            normalized: segment.record.analysis.as_ref().unwrap().normalized.clone(),
            analyses,
        };
        Ok(SpacingSegment {
            record: TokenAnalysis {
                analysis: Some(Arc::new(analysis.clone())),
                ..segment.record.clone()
            },
            breakdowns: analysis.analyses.iter().map(Analysis::breakdown).collect(),
            dictionary: self.dictionary.annotate(&analysis)?,
        })
    }

    pub(super) fn emit_joined(
        &mut self,
        records: Vec<SpacingSegment>,
        context: Option<SpacingSegment>,
        rule: &'static str,
    ) -> Result<()> {
        let inserted: Vec<_> = records
            .iter()
            .skip(1)
            .map(|s| s.record.span.start)
            .collect();
        if let Some(index) = self
            .result
            .alternatives
            .iter()
            .position(|h| h.rule == Some(rule) && h.inserted_at == inserted)
        {
            // Equal spaces are one option with all witnessed analyses. A complete
            // joined reading remains available, so independent alternatives do
            // not imply that every cross-product of segment readings is licensed.
            let old = self.result.alternatives[index].clone();
            let mut merged = Vec::new();
            for (left, right) in old.records.iter().zip(records) {
                let mut analyses = left.record.analysis.as_ref().unwrap().analyses.clone();
                analyses.extend(right.record.analysis.as_ref().unwrap().analyses.clone());
                analyses.sort();
                analyses.dedup();
                merged.push(self.only_paths(left, analyses)?);
            }
            let mut contexts = old.joined_contexts;
            if let Some(context) = context {
                if let Some(index) = contexts
                    .iter()
                    .position(|old| old.record.span == context.record.span)
                {
                    let mut analyses = contexts[index]
                        .record
                        .analysis
                        .as_ref()
                        .unwrap()
                        .analyses
                        .clone();
                    analyses.extend(context.record.analysis.as_ref().unwrap().analyses.clone());
                    analyses.sort();
                    analyses.dedup();
                    contexts[index] = self.only_paths(&contexts[index], analyses)?;
                } else {
                    contexts.push(context);
                }
            }
            self.result.alternatives[index].records = merged;
            self.result.alternatives[index].joined_contexts = contexts;
        } else {
            let count = self.result.alternatives.len();
            self.emit(records, Some(rule));
            if self.result.alternatives.len() > count {
                self.result.alternatives[count].joined_contexts = context.into_iter().collect();
            }
        }
        Ok(())
    }

    fn auxiliary_partitions(
        &mut self,
        start: usize,
        point: usize,
        witness: &Witness<'_>,
        path: &mut Vec<SpacingSegment>,
    ) -> Result<()> {
        for next in point + 1..witness.points.len() {
            let final_piece = next == witness.points.len() - 1;
            if point == 0 && final_piece {
                continue;
            }
            let ends: Vec<_> = if final_piece {
                vec![self.source.len()]
            } else {
                self.source[start..]
                    .char_indices()
                    .skip(1)
                    .map(|(i, _)| start + i)
                    .collect()
            };
            for end in ends {
                // Do not cut inside a composed Hangul syllable in NFD input.
                let left: String = self.source[start..end].nfc().collect();
                let right: String = self.source[end..].nfc().collect();
                let whole: String = self.source[start..].nfc().collect();
                if left + &right != whole {
                    continue;
                }
                if let Some(segment) = self.segment(start, end, Role::AuxiliaryPiece)? {
                    let analyses: Vec<_> = segment
                        .record
                        .analysis
                        .as_ref()
                        .unwrap()
                        .analyses
                        .iter()
                        .filter(|a| {
                            matches_piece(
                                a,
                                witness.analysis,
                                witness.points[point],
                                witness.points[next],
                            )
                        })
                        .cloned()
                        .collect();
                    if !analyses.is_empty() {
                        let segment = self.only_paths(&segment, analyses)?;
                        path.push(segment);
                        if final_piece && path.len() > witness.prefix_len + 1 {
                            self.emit_joined(path.clone(), Some(witness.context.clone()), RULE)?;
                        } else if !final_piece {
                            self.auxiliary_partitions(end, next, witness, path)?;
                        }
                        path.pop();
                    }
                }
                if !self.result.complete {
                    return Ok(());
                }
            }
        }
        Ok(())
    }

    fn auxiliary_at(&mut self, start: usize, path: &mut Vec<SpacingSegment>) -> Result<()> {
        let Some(whole) = self.segment(start, self.source.len(), Role::AuxiliaryChain)? else {
            return Ok(());
        };
        for joined in &whole.record.analysis.as_ref().unwrap().analyses {
            if !joined.lemmas.iter().any(|l| l.kind == LemmaKind::Auxiliary) {
                continue;
            }
            let assessment = whole.dictionary.assess(joined);
            // An unknown provider or lexical-only homonym cannot establish the
            // relationship. A known auxiliary may still have unknown policy.
            let backed = joined
                .lemmas
                .iter()
                .enumerate()
                .filter(|(_, l)| l.kind == LemmaKind::Auxiliary)
                .all(|(i, l)| {
                    whole
                        .dictionary
                        .lemmas
                        .iter()
                        .find(|m| m.lemma == *l)
                        .is_some_and(|m| {
                            m.entries.iter().any(|e| {
                                matches!(e.effective_pos(), "보조 동사" | "보조 형용사")
                                    && assessment.lemmas[i].entries.iter().any(|a| {
                                        a.id == e.entry.id
                                            && a.status != Compatibility::Incompatible
                                    })
                            })
                        })
                });
            if !backed {
                continue;
            }
            let Some(order) = joined.breakdown() else {
                continue;
            };
            let mut points = vec![(0, 0)];
            let mut morph = 0;
            for component in order {
                match component {
                    Component::Lemma(i) if joined.lemmas[i].kind == LemmaKind::Auxiliary => {
                        points.push((i, morph))
                    }
                    Component::Morpheme(i) => morph = i + 1,
                    _ => (),
                }
            }
            points.push((joined.lemmas.len(), joined.morphemes.len()));
            let context = self.only_paths(&whole, vec![joined.clone()])?;
            let witness = Witness {
                analysis: joined,
                points: &points,
                context: &context,
                prefix_len: path.len(),
            };
            self.auxiliary_partitions(start, 0, &witness, path)?;
            if !self.result.complete {
                break;
            }
        }
        Ok(())
    }

    pub(super) fn walk_auxiliary(
        &mut self,
        start: usize,
        path: &mut Vec<SpacingSegment>,
    ) -> Result<()> {
        if self.dead_starts.contains(&start) {
            return Ok(());
        }
        let before = self.result.alternatives.len();
        self.auxiliary_at(start, path)?;
        if !self.result.complete {
            return Ok(());
        }
        let cuts: Vec<_> = self.source[start..]
            .char_indices()
            .skip(1)
            .map(|(i, _)| start + i)
            .collect();
        for end in cuts.into_iter().rev() {
            if let Some(left) = self.segment(start, end, Role::Case)? {
                path.push(left);
                self.walk_auxiliary(end, path)?;
                path.pop();
            }
            if !self.result.complete {
                break;
            }
        }
        if self.result.complete && self.result.alternatives.len() == before {
            self.dead_starts.insert(start);
        }
        Ok(())
    }
}
