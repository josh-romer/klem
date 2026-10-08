//! Reviewed modifier/nominalizer + bound-noun boundaries. No joined word is invented.
use super::*;

const RULE: &str = "spacing.modifier_bound_noun";
// Native entries and exact notes/examples are retained in the source fixture.
// These forms establish a structural boundary, not the intended noun sense.
const PROFILES: &[(&str, &str, &[&str])] = &[
    ("것", "krdict:62835", &["은", "는", "을", "던"]),
    ("수", "krdict:15615", &["은", "는", "을"]),
    ("줄", "krdict:91870", &["은", "는", "을"]),
    ("바", "krdict:56324", &["은", "는", "을"]),
    ("적", "krdict:71232", &["은", "을"]),
    ("지", "krdict:91881", &["은"]),
    ("듯", "krdict:49981", &["은", "는", "을"]),
    ("뿐", "krdict:66641", &["을"]),
    ("대로", "krdict:48415", &["은", "는", "을"]),
    ("만큼", "krdict:53008", &["은", "는", "을"]),
    ("때문", "krdict:64555", &["기"]),
    ("따름", "krdict:49675", &["을"]),
];

pub(super) fn maybe_bound_noun(source: &str) -> bool {
    let normalized: String = source.nfc().collect();
    PROFILES
        .iter()
        .any(|(head, _, _)| normalized.contains(head))
}

fn modifier_form(a: &Analysis) -> Option<&str> {
    let last = a.morphemes.last()?;
    if last.kind != MorphemeKind::Ending {
        return None;
    }
    let layout = a.breakdown()?;
    if layout.last()
        != Some(&crate::breakdown::Component::Morpheme(
            a.morphemes.len() - 1,
        ))
    {
        return None;
    }
    // 먹던 has both canonical 던 and 더 + 은 analyses. Licensing the latter
    // as plain 은 would incorrectly evade a noun's surface attachment class.
    if last.form == "은"
        && layout.iter().rev().nth(1).is_some_and(|c| {
            if let crate::breakdown::Component::Morpheme(i) = c {
                a.morphemes[*i].kind == MorphemeKind::Prefinal && a.morphemes[*i].form == "더"
            } else {
                false
            }
        })
    {
        return Some("던");
    }
    Some(&last.form)
}

pub(super) fn modifier(a: &Analysis) -> bool {
    modifier_form(a).is_some_and(|form| matches!(form, "은" | "는" | "을" | "던" | "기"))
}

pub(super) fn bound_noun(a: &Analysis) -> bool {
    a.lemmas.first().is_some_and(|l| {
        matches!(l.kind, LemmaKind::Nominal | LemmaKind::Unclassified)
            && PROFILES.iter().any(|(head, _, _)| l.text == *head)
    }) && a
        .morphemes
        .iter()
        .all(|m| m.kind != MorphemeKind::Suffix || m.form == "들")
        && a.breakdown().is_some()
}

impl<D: Dictionary + ?Sized> Search<'_, '_, D> {
    fn licensed_bound_forms(&self, right: &SpacingSegment) -> HashSet<&'static str> {
        let mut forms = HashSet::new();
        for a in &right.record.analysis.as_ref().unwrap().analyses {
            let lemma = &a.lemmas[0];
            let assessment = right.dictionary.assess(a);
            for (head, id, allowed) in PROFILES {
                if lemma.text != *head {
                    continue;
                }
                let backed = right
                    .dictionary
                    .lemmas
                    .iter()
                    .find(|m| m.lemma == *lemma)
                    .is_some_and(|m| {
                        m.entries.iter().any(|e| {
                            e.entry.id == *id
                                && e.entry.pos == "의존 명사"
                                && assessment.lemmas[0]
                                    .entries
                                    .iter()
                                    .any(|r| r.id == *id && r.status != Compatibility::Incompatible)
                        })
                    });
                if backed {
                    forms.extend(allowed.iter().copied());
                }
            }
        }
        forms
    }

    fn modifier_pair(&mut self, start: usize, path: &[SpacingSegment]) -> Result<()> {
        let cuts: Vec<_> = self.source[start..]
            .char_indices()
            .skip(1)
            .map(|(i, _)| start + i)
            .collect();
        for end in cuts.into_iter().rev() {
            // Avoid spending the shared budget on every arbitrary suffix.
            let normalized: String = self.source[end..].nfc().collect();
            if !PROFILES
                .iter()
                .any(|(head, _, _)| normalized.starts_with(head))
            {
                continue;
            }
            let left_text: String = self.source[start..end].nfc().collect();
            let whole: String = self.source[start..].nfc().collect();
            if left_text + &normalized != whole {
                continue;
            }
            let Some(right) = self.segment(end, self.source.len(), Role::BoundNoun)? else {
                if !self.result.complete {
                    break;
                }
                continue;
            };
            let forms = self.licensed_bound_forms(&right);
            if forms.is_empty() {
                continue;
            }
            let Some(left) = self.segment(start, end, Role::Modifier)? else {
                if !self.result.complete {
                    break;
                }
                continue;
            };
            let analyses: Vec<_> = left
                .record
                .analysis
                .as_ref()
                .unwrap()
                .analyses
                .iter()
                .filter(|a| modifier_form(a).is_some_and(|f| forms.contains(f)))
                .cloned()
                .collect();
            if analyses.is_empty() {
                continue;
            }
            let has_auxiliary = analyses
                .iter()
                .any(|a| a.lemmas.iter().any(|l| l.kind == LemmaKind::Auxiliary));
            let left = self.only_paths(&left, analyses)?;
            let mut records = path.to_vec();
            records.extend([left, right.clone()]);
            self.emit_joined(records, None, RULE)?;
            if !self.result.complete {
                break;
            }
            if has_auxiliary {
                // The auxiliary chain ends before the noun. Its subsearch has
                // only the parent's remaining work/output capacity; account all
                // probes and propagate every reached bound to the outer result.
                let mut child = Search {
                    source: &self.source[start..end],
                    offset: self.offset + start,
                    session: self.session,
                    dictionary: self.dictionary,
                    cache: HashMap::new(),
                    dead_starts: HashSet::new(),
                    result: SpacingSuggestions {
                        rule: "spacing.nominal_case_predicate",
                        alternatives: Vec::new(),
                        complete: true,
                        limited_by: Vec::new(),
                        segment_probes: 0,
                        limits: SpacingLimits {
                            token_chars: self.result.limits.token_chars,
                            segment_probes: self
                                .result
                                .limits
                                .segment_probes
                                .saturating_sub(self.result.segment_probes),
                            alternatives: self
                                .result
                                .limits
                                .alternatives
                                .saturating_sub(self.result.alternatives.len()),
                        },
                    },
                };
                child.walk_auxiliary(0, &mut Vec::new())?;
                let result = child.result;
                self.result.segment_probes += result.segment_probes;
                for alternative in result.alternatives {
                    let contexts: Vec<_> = alternative
                        .joined_contexts
                        .into_iter()
                        .filter(|c| {
                            c.record
                                .analysis
                                .as_ref()
                                .unwrap()
                                .analyses
                                .iter()
                                .all(|a| {
                                    modifier(a)
                                        && modifier_form(a).is_some_and(|f| forms.contains(f))
                                })
                        })
                        .collect();
                    if contexts.is_empty() {
                        continue;
                    }
                    let mut records = path.to_vec();
                    records.extend(alternative.records);
                    records.push(right.clone());
                    for context in contexts {
                        self.emit_joined(records.clone(), Some(context), RULE)?;
                    }
                }
                for limit in result.limited_by {
                    self.limit(limit);
                }
                if !self.result.complete {
                    break;
                }
            }
        }
        Ok(())
    }

    pub(super) fn walk_bound_noun(
        &mut self,
        start: usize,
        path: &mut Vec<SpacingSegment>,
    ) -> Result<()> {
        if self.dead_starts.contains(&start) {
            return Ok(());
        }
        let before = self.result.alternatives.len();
        self.modifier_pair(start, path)?;
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
                self.walk_bound_noun(end, path)?;
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
