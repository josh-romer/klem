//! Finite, independently reviewed POS evidence. Never infer a class from a
//! definition, translation, headword alone, or another dictionary's homonym.
use super::{Entry, EntrySummary};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

const PROFILE: &str = "93f7b45bd7ac9eaa460402b6cbab5e84c7519764714351133754e9eb5d66ffbe";

/// Separate source evidence used for attachment checks. The native `pos` and
/// entry remain unchanged. This is a lexical class, not a selected sense or
/// an assertion about the intended meaning of a sentence.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct IndependentPosEvidence {
    pub reviewed_pos: String,
    pub source_id: String,
    pub source_url: String,
    pub source_response_sha256: String,
    /// SHA-256 of serde's compact native Entry JSON with translations emptied.
    /// All Korean fields, forms, pronunciations, senses and identities remain.
    pub native_profile_sha256: String,
}

fn reviewed() -> IndependentPosEvidence {
    IndependentPosEvidence {
        reviewed_pos: "형용사".into(),
        source_id: "opendict:569243".into(),
        source_url:
            "https://opendict.korean.go.kr/dictionary/view?sense_no=569243&viewType=confirm".into(),
        source_response_sha256: "2061cc240475b872cf76d10ee73f8e84d3a7b0e7f64380ed08106e5466e8cb33"
            .into(),
        native_profile_sha256: PROFILE.into(),
    }
}

pub(super) fn consult(summary: &EntrySummary) -> bool {
    summary.id == "krdict:600930"
        && summary.headword == "발그스레하다"
        && summary.homonym == "0"
        && summary.pos == "동사"
}

impl IndependentPosEvidence {
    pub(super) fn from_entry(entry: &Entry) -> Option<Self> {
        if !consult(&entry.summary) {
            return None;
        }
        // Different translation selections are projections of the same native
        // entry. Do not strip any Korean evidence, including the conflicting
        // written form 발그르세합니다. Updated/sparse profiles require review.
        let mut native = entry.clone();
        for sense in &mut native.senses {
            sense.translations.clear();
        }
        let bytes = serde_json::to_vec(&native).ok()?;
        (format!("{:x}", Sha256::digest(bytes)) == PROFILE).then(reviewed)
    }

    pub(super) fn applies_to(&self, summary: &EntrySummary) -> bool {
        // Older annotations omit this evidence. Reject malformed or moved
        // sidecars as well; they cannot upgrade another entry's class.
        consult(summary)
            && self.reviewed_pos == "형용사"
            && self.source_id == "opendict:569243"
            && self.source_url
                == "https://opendict.korean.go.kr/dictionary/view?sense_no=569243&viewType=confirm"
            && self.source_response_sha256
                == "2061cc240475b872cf76d10ee73f8e84d3a7b0e7f64380ed08106e5466e8cb33"
            && self.native_profile_sha256 == PROFILE
    }

    pub(super) fn retained_bytes(&self) -> usize {
        self.reviewed_pos.capacity()
            + self.source_id.capacity()
            + self.source_url.capacity()
            + self.source_response_sha256.capacity()
            + self.native_profile_sha256.capacity()
    }
}
