#[path = "../tools/corpus.rs"]
mod corpus;
use std::{
    env,
    fs::File,
    io::{self, BufReader, BufWriter},
};
fn main() {
    if let Err(error) = run() {
        eprintln!("klem evaluate: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().skip(1).collect();
    if args.len() < 2 || args.len() > 3 {
        return Err(
            "usage: cargo run --release --example evaluate -- kaist|gsd FILE [BASELINE.jsonl]"
                .into(),
        );
    }
    let report = corpus::evaluate(
        BufReader::new(File::open(&args[1])?),
        corpus::Corpus::parse(&args[0])?,
        &args[1],
    )?;
    if let Some(path) = args.get(2) {
        let old = corpus::read_report(BufReader::new(File::open(path)?))?;
        // Always emit the candidate report, even on regression, for inspection.
        corpus::write_report(BufWriter::new(io::stdout().lock()), &report)?;
        corpus::check_baseline(&report, &old)?;
    } else {
        corpus::write_report(BufWriter::new(io::stdout().lock()), &report)?;
    }
    Ok(())
}
