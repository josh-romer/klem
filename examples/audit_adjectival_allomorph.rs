//! Development-only JSONL bridge for source-scoped, ordered-owner audits.
#[path = "../tools/adjectival_allomorph.rs"]
mod boundaries;

use klem::Analysis;
use std::io::{self, BufRead, BufWriter, Write};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut output = BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let analysis: Analysis = serde_json::from_str(&line?)?;
        serde_json::to_writer(
            &mut output,
            &serde_json::json!({
                "components": analysis.breakdown(),
                "reviewed_removal": boundaries::reviewed_removal(&analysis),
            }),
        )?;
        writeln!(output)?;
    }
    output.flush()?;
    Ok(())
}
