//! Exact surname/title possession, licensed by KRDict 것 62835 sense 3.
//! Corpus PROPN evidence supplies a separate lexical identity for 박.
use super::*;

const RULE: &str = "spacing.proper_name_title_possession";

pub(super) fn maybe(source: &str) -> bool {
    let source: String = source.nfc().collect();
    source.contains("박선생님") && source.contains('것')
}

pub(super) fn maybe_title(source: &str) -> bool {
    source.nfc().collect::<String>().contains("박선생님")
}

pub(super) fn inflected_title(a: &Analysis) -> bool {
    a.lemmas.len() == 1
        && a.lemmas[0].text == "선생님"
        && (unchanged_noun(a)
            || (a.lemmas[0].kind == LemmaKind::Nominal
                && a.morphemes.iter().all(|m| m.kind == MorphemeKind::Particle)
                && a.breakdown().is_some()))
}

pub(super) fn title(a: &Analysis) -> bool {
    a.lemmas.len() == 1
        && a.lemmas[0].text == "선생님"
        && (unchanged_noun(a)
            || (a.lemmas[0].kind == LemmaKind::Nominal
                && a.morphemes.len() == 1
                && a.morphemes[0].kind == MorphemeKind::Particle
                && a.morphemes[0].form == "의"
                && a.breakdown().is_some()))
}

pub(super) fn backed(annotation: &Annotation, a: &Analysis, role: Role) -> bool {
    let (id, head, pos) = match role {
        Role::ProperName => ("ud-ko-kaist:proper-name:park", "박", "PROPN"),
        Role::Title | Role::InflectedTitle => ("krdict:62818", "선생님", "명사"),
        Role::BoundNoun => ("krdict:62835", "것", "의존 명사"),
        _ => return false,
    };
    let assessment = annotation.assess(a);
    annotation
        .lemmas
        .iter()
        .find(|m| m.lemma == a.lemmas[0])
        .is_some_and(|m| {
            m.entries.iter().any(|e| {
                e.entry.id == id
                    && e.entry.headword == head
                    && e.entry.pos == pos
                    && assessment.lemmas[0]
                        .entries
                        .iter()
                        .any(|r| r.id == id && r.status != Compatibility::Incompatible)
            })
        })
}

impl<D: Dictionary + ?Sized> Search<'_, '_, D> {
    pub(super) fn walk_named_title(
        &mut self,
        start: usize,
        prefix: &mut Vec<SpacingSegment>,
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
        for cut in cuts.iter().copied() {
            if self.source[start..cut].nfc().collect::<String>() != "박" {
                continue;
            }
            if self.source[start..cut]
                .nfc()
                .chain(self.source[cut..].nfc())
                .collect::<String>()
                != self.source[start..].nfc().collect::<String>()
            {
                continue;
            }
            let Some(name) = self.segment(start, cut, Role::ProperName)? else {
                continue;
            };
            let Some(right) = self.segment(cut, self.source.len(), Role::InflectedTitle)? else {
                continue;
            };
            let mut records = prefix.clone();
            records.extend([name, right]);
            self.emit_joined(records, None, "spacing.proper_name_title")?;
            if !self.result.complete {
                return Ok(());
            }
        }
        for cut in cuts.into_iter().rev() {
            if let Some(left) = self.segment(start, cut, Role::Case)? {
                prefix.push(left);
                self.walk_named_title(cut, prefix)?;
                prefix.pop();
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
    pub(super) fn walk_proper_name(
        &mut self,
        start: usize,
        prefix: &mut Vec<SpacingSegment>,
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
        for name_end in cuts.iter().copied() {
            if self.source[start..name_end].nfc().collect::<String>() != "박" {
                continue;
            }
            for title_end in cuts.iter().copied().filter(|&cut| cut > name_end) {
                let title: String = self.source[name_end..title_end].nfc().collect();
                let right: String = self.source[title_end..].nfc().collect();
                if !matches!(title.as_str(), "선생님" | "선생님의") || !right.starts_with('것')
                {
                    continue;
                }
                if self.source[start..name_end]
                    .nfc()
                    .chain(title.chars())
                    .chain(right.chars())
                    .collect::<String>()
                    != self.source[start..].nfc().collect::<String>()
                {
                    continue;
                }
                let Some(name) = self.segment(start, name_end, Role::ProperName)? else {
                    continue;
                };
                let Some(title) = self.segment(name_end, title_end, Role::Title)? else {
                    continue;
                };
                let Some(right) = self.segment(title_end, self.source.len(), Role::BoundNoun)?
                else {
                    continue;
                };
                let paths = right
                    .record
                    .analysis
                    .as_ref()
                    .unwrap()
                    .analyses
                    .iter()
                    .filter(|a| backed(&right.dictionary, a, Role::BoundNoun))
                    .cloned()
                    .collect::<Vec<_>>();
                if paths.is_empty() {
                    continue;
                }
                let right = self.only_paths(&right, paths)?;
                let mut records = prefix.clone();
                records.extend([name, title, right]);
                self.emit_joined(records, None, RULE)?;
                if !self.result.complete {
                    return Ok(());
                }
            }
        }
        for cut in cuts.into_iter().rev() {
            if let Some(left) = self.segment(start, cut, Role::Case)? {
                prefix.push(left);
                self.walk_proper_name(cut, prefix)?;
                prefix.pop();
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
