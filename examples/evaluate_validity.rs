#[path = "../tools/validity.rs"]
mod validity;

fn main() {
    if let Err(error) = run() {
        eprintln!("klem validity: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    use std::io::Write;
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 1 {
        return Err("usage: cargo run --example evaluate_validity -- FIXTURE.json".into());
    }
    let suite = serde_json::from_reader(std::io::BufReader::new(std::fs::File::open(&args[0])?))?;
    let report = validity::evaluate(&suite)?;
    let mut output = std::io::BufWriter::new(std::io::stdout().lock());
    serde_json::to_writer_pretty(&mut output, &report)?;
    writeln!(output)?;
    output.flush()?;
    if !report.passed() {
        return Err(report.violations.join("\n").into());
    }
    Ok(())
}
