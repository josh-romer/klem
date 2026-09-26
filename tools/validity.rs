//! Development-only candidate judgments. Unjudged outputs remain unknown.
use klem::{Analysis, LemmaKind, Lemmatizer, MorphemeKind};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Suite {
    pub schema_version: u32,
    pub review_status: String,
    pub sources: BTreeMap<String, String>,
    pub cases: Vec<Case>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Case {
    pub id: String,
    pub surface: String,
    pub judgments: Vec<Judgment>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Judgment {
    pub id: String,
    pub lemmas: Vec<String>,
    /// Optional role constraints; omitted fields preserve existing broad scopes.
    pub lemma_kinds: Option<Vec<LemmaKind>>,
    /// None selects all morpheme paths for this ordered lemma group.
    pub morphemes: Option<Vec<String>>,
    pub morpheme_kinds: Option<Vec<MorphemeKind>>,
    pub verdict: Verdict,
    pub reason: String,
    pub source: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Verdict {
    Required,
    Forbidden,
}

#[derive(Debug, Serialize)]
pub struct ReviewItem {
    pub case_id: String,
    pub surface: String,
    pub analysis: Analysis,
}

#[derive(Debug, Serialize)]
pub struct Report {
    pub schema_version: u32,
    pub review_status: String,
    pub cases: usize,
    pub required_total: usize,
    pub required_present: usize,
    pub forbidden_total: usize,
    pub forbidden_present: usize,
    pub emitted_nonidentity: usize,
    pub judged_nonidentity: usize,
    pub violations: Vec<String>,
    pub review_queue: Vec<ReviewItem>,
}

impl Report {
    pub fn passed(&self) -> bool {
        self.violations.is_empty()
    }
}

impl Judgment {
    fn matches(&self, a: &Analysis) -> bool {
        a.lemmas.iter().map(|l| &l.text).eq(self.lemmas.iter())
            && self
                .lemma_kinds
                .as_ref()
                .is_none_or(|kinds| a.lemmas.iter().map(|l| &l.kind).eq(kinds.iter()))
            && self
                .morphemes
                .as_ref()
                .is_none_or(|forms| a.morphemes.iter().map(|m| &m.form).eq(forms.iter()))
            && self
                .morpheme_kinds
                .as_ref()
                .is_none_or(|kinds| a.morphemes.iter().map(|m| &m.kind).eq(kinds.iter()))
    }
}

pub fn evaluate(suite: &Suite) -> Result<Report, String> {
    if suite.schema_version != 1 || suite.review_status.trim().is_empty() || suite.cases.is_empty()
    {
        return Err("expected a nonempty version-1 judgment suite with review status".into());
    }
    let engine = Lemmatizer::new();
    let mut ids = BTreeSet::new();
    let mut report = Report {
        schema_version: 1,
        review_status: suite.review_status.clone(),
        cases: suite.cases.len(),
        required_total: 0,
        required_present: 0,
        forbidden_total: 0,
        forbidden_present: 0,
        emitted_nonidentity: 0,
        judged_nonidentity: 0,
        violations: vec![],
        review_queue: vec![],
    };
    for case in &suite.cases {
        if case.id.is_empty() || !ids.insert(case.id.clone()) || case.judgments.is_empty() {
            return Err(format!(
                "invalid/duplicate case ID or empty judgments: {}",
                case.id
            ));
        }
        let mut judgment_ids = BTreeSet::new();
        for (i, j) in case.judgments.iter().enumerate() {
            if j.id.is_empty()
                || !judgment_ids.insert(&j.id)
                || j.lemmas.is_empty()
                || j.lemmas.iter().any(String::is_empty)
                || j.lemma_kinds
                    .as_ref()
                    .is_some_and(|k| k.len() != j.lemmas.len())
                || j.morphemes
                    .as_ref()
                    .zip(j.morpheme_kinds.as_ref())
                    .is_some_and(|(forms, kinds)| forms.len() != kinds.len())
                || j.reason.trim().is_empty()
                || !suite
                    .sources
                    .get(&j.source)
                    .is_some_and(|s| s.starts_with("https://"))
            {
                return Err(format!("invalid judgment {}/{}", case.id, j.id));
            }
            for other in &case.judgments[..i] {
                fn compatible<T: PartialEq>(a: &Option<T>, b: &Option<T>) -> bool {
                    a.is_none() || b.is_none() || a == b
                }
                let count = |j: &Judgment| {
                    j.morphemes
                        .as_ref()
                        .map(Vec::len)
                        .or_else(|| j.morpheme_kinds.as_ref().map(Vec::len))
                };
                let overlap = j.lemmas == other.lemmas
                    && compatible(&j.lemma_kinds, &other.lemma_kinds)
                    && compatible(&j.morphemes, &other.morphemes)
                    && compatible(&j.morpheme_kinds, &other.morpheme_kinds)
                    && compatible(&count(j), &count(other));
                let identical = j.lemma_kinds == other.lemma_kinds
                    && j.morphemes == other.morphemes
                    && j.morpheme_kinds == other.morpheme_kinds;
                if overlap && (j.verdict != other.verdict || identical) {
                    return Err(format!(
                        "conflicting or duplicate scopes: {}/{} and {}",
                        case.id, j.id, other.id
                    ));
                }
            }
        }
        let result = engine
            .analyze_word(&case.surface)
            .map_err(|e| e.to_string())?;
        for j in &case.judgments {
            let present = result.analyses.iter().any(|a| j.matches(a));
            match j.verdict {
                Verdict::Required => {
                    report.required_total += 1;
                    report.required_present += usize::from(present);
                    if !present {
                        report.violations.push(format!(
                            "{}/{}: missing required {:?} ({})",
                            case.id, j.id, j.lemmas, j.reason
                        ));
                    }
                }
                Verdict::Forbidden => {
                    report.forbidden_total += 1;
                    report.forbidden_present += usize::from(present);
                    if present {
                        report.violations.push(format!(
                            "{}/{}: emitted forbidden {:?} ({})",
                            case.id, j.id, j.lemmas, j.reason
                        ));
                    }
                }
            }
        }
        for analysis in result.analyses.into_iter().filter(|a| !a.unchanged) {
            report.emitted_nonidentity += 1;
            if case.judgments.iter().any(|j| j.matches(&analysis)) {
                report.judged_nonidentity += 1;
            } else {
                report.review_queue.push(ReviewItem {
                    case_id: case.id.clone(),
                    surface: case.surface.clone(),
                    analysis,
                });
            }
        }
    }
    Ok(report)
}
