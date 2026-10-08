//! Nominal causes and possessions, separate from adnominal predicate profiles.
use super::*;

const RULE: &str = "spacing.nominal_bound_noun";
const BARE_POSSESSORS: &[(&str, &str, &str)] = &[
    ("우리", "krdict:17182", "대명사"),
    ("누구", "krdict:62078", "대명사"),
    ("언니", "krdict:31971", "명사"),
    ("친구", "krdict:29742", "명사"),
    ("동생", "krdict:70748", "명사"),
    ("할머니", "krdict:27375", "명사"),
    ("선생님", "krdict:62818", "명사"),
];

pub(super) fn maybe_nominal_bound_noun(source: &str) -> bool {
    let normalized: String = source.nfc().collect();
    normalized.contains("것") || normalized.contains("때문")
}

fn genitive(a: &Analysis) -> bool {
    nominal_case(a)
        && a.morphemes
            .last()
            .is_some_and(|m| m.kind == MorphemeKind::Particle && m.form == "의")
        && a.breakdown().is_some()
}

pub(super) fn owner(a: &Analysis) -> bool {
    genitive(a)
        || unchanged_noun(a)
        || (a.lemmas.len() == 1
            && a.lemmas[0].kind == LemmaKind::Nominal
            && a.morphemes
                .iter()
                .all(|m| m.kind == MorphemeKind::Suffix && m.form == "들")
            && a.breakdown().is_some())
}

fn backed(annotation: &Annotation, a: &Analysis, id: Option<&str>, pos: &[&str]) -> bool {
    let lemma = &a.lemmas[0];
    let assessment = annotation.assess(a);
    annotation
        .lemmas
        .iter()
        .find(|m| m.lemma == *lemma)
        .is_some_and(|m| {
            m.entries.iter().any(|e| {
                e.entry.headword == lemma.text
                    && pos.contains(&e.entry.pos.as_str())
                    && id.is_none_or(|id| id == e.entry.id)
                    && assessment.lemmas[0]
                        .entries
                        .iter()
                        .any(|r| r.id == e.entry.id && r.status != Compatibility::Incompatible)
            })
        })
}

pub(super) fn known_owner(annotation: &Annotation, a: &Analysis) -> bool {
    let pos = if genitive(a) {
        // Independent nominalized predicates can themselves take 의.
        &["명사", "대명사", "동사", "형용사"][..]
    } else {
        &["명사", "대명사"][..]
    };
    backed(annotation, a, None, pos)
}

fn possession_paths(segment: &SpacingSegment) -> Vec<Analysis> {
    segment
        .record
        .analysis
        .as_ref()
        .unwrap()
        .analyses
        .iter()
        .filter(|a| {
            genitive(a)
                || BARE_POSSESSORS.iter().any(|(head, id, pos)| {
                    a.lemmas[0].text == *head && backed(&segment.dictionary, a, Some(id), &[*pos])
                })
        })
        .cloned()
        .collect()
}

struct NominalTarget<'a> {
    end: usize,
    right: &'a SpacingSegment,
    possession: bool,
    prefix: &'a [SpacingSegment],
}

impl<D: Dictionary + ?Sized> Search<'_, '_, D> {
    fn nominal_owners(
        &mut self,
        start: usize,
        target: &NominalTarget<'_>,
        owners: &mut Vec<SpacingSegment>,
        dead: &mut HashSet<usize>,
    ) -> Result<bool> {
        let NominalTarget {
            end,
            right,
            possession,
            prefix,
        } = *target;
        if !possession && dead.contains(&start) {
            return Ok(false);
        }
        let mut found = false;
        if let Some(segment) = self.segment(start, end, Role::NominalOwner)? {
            owners.push(segment);
            let selected = if !possession {
                Some(owners.clone())
            } else if owners.len() == 1 {
                let paths = possession_paths(&owners[0]);
                if paths.is_empty() {
                    None
                } else {
                    Some(vec![self.only_paths(&owners[0], paths)?])
                }
            } else {
                None
            };
            if let Some(selected) = selected {
                found = true;
                let mut records = prefix.to_vec();
                records.extend(selected);
                records.push(right.clone());
                self.emit_joined(records, None, RULE)?;
            }
            owners.pop();
        }
        if !self.result.complete || possession {
            return Ok(found);
        }
        let cuts: Vec<_> = self.source[start..end]
            .char_indices()
            .skip(1)
            .map(|(i, _)| start + i)
            .collect();
        for cut in cuts.into_iter().rev() {
            // Never introduce a boundary inside a decomposed Hangul syllable.
            if self.source[start..cut]
                .nfc()
                .chain(self.source[cut..end].nfc())
                .collect::<String>()
                != self.source[start..end].nfc().collect::<String>()
            {
                continue;
            }
            if let Some(left) = self.segment(start, cut, Role::NominalOwner)? {
                owners.push(left);
                found |= self.nominal_owners(cut, target, owners, dead)?;
                owners.pop();
            }
            if !self.result.complete {
                break;
            }
        }
        if !found && !possession && self.result.complete {
            dead.insert(start);
        }
        Ok(found)
    }

    pub(super) fn walk_nominal_bound_noun(
        &mut self,
        start: usize,
        path: &mut Vec<SpacingSegment>,
    ) -> Result<()> {
        if self.dead_starts.contains(&start) {
            return Ok(());
        }
        let before = self.result.alternatives.len();
        let cuts: Vec<_> = self.source[start..]
            .char_indices()
            .skip(1)
            .map(|(i, _)| start + i)
            .collect();
        for end in cuts.iter().rev().copied() {
            let tail: String = self.source[end..].nfc().collect();
            let (head, id) = if tail.starts_with("것") {
                ("것", "krdict:62835")
            } else if tail.starts_with("때문") {
                ("때문", "krdict:64555")
            } else {
                continue;
            };
            if self.source[start..end]
                .nfc()
                .chain(tail.chars())
                .collect::<String>()
                != self.source[start..].nfc().collect::<String>()
            {
                continue;
            }
            if let Some(right) = self.segment(end, self.source.len(), Role::BoundNoun)? {
                let paths = right
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .iter()
                    .filter(|a| {
                        a.lemmas[0].text == head
                            && backed(&right.dictionary, a, Some(id), &["의존 명사"])
                    })
                    .cloned()
                    .collect::<Vec<_>>();
                if !paths.is_empty() {
                    let right = self.only_paths(&right, paths)?;
                    self.nominal_owners(
                        start,
                        &NominalTarget {
                            end,
                            right: &right,
                            possession: head == "것",
                            prefix: path,
                        },
                        &mut Vec::new(),
                        &mut HashSet::new(),
                    )?;
                }
            }
            if !self.result.complete {
                return Ok(());
            }
        }
        for end in cuts.into_iter().rev() {
            if let Some(left) = self.segment(start, end, Role::Case)? {
                path.push(left);
                self.walk_nominal_bound_noun(end, path)?;
                path.pop();
            }
            if !self.result.complete {
                break;
            }
        }
        if self.result.complete && before == self.result.alternatives.len() {
            self.dead_starts.insert(start);
        }
        Ok(())
    }
}
