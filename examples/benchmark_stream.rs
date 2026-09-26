//! One workload per process, so Linux peak RSS belongs to this file/mode only.
use klem::{Lemmatizer, Session};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    hint::black_box,
    io::{self, Read, Write},
    sync::Arc,
    time::Instant,
};

#[derive(Default)]
struct CountBytes(u64);
impl Write for CountBytes {
    fn write(&mut self, bytes: &[u8]) -> io::Result<usize> {
        self.0 += bytes.len() as u64;
        black_box(bytes);
        Ok(bytes.len())
    }
    fn flush(&mut self) -> io::Result<()> {
        Ok(())
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    if args.len() != 3 || !matches!(args[2].as_str(), "library" | "json") {
        return Err("usage: benchmark_stream FILE CACHE_BYTES library|json".into());
    }
    let budget: usize = args[1].parse()?;
    let mut input = File::open(&args[0])?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 8192];
    let mut input_bytes = 0u64;
    loop {
        let n = input.read(&mut buffer)?;
        if n == 0 {
            break;
        }
        digest.update(&buffer[..n]);
        input_bytes += n as u64;
    }
    let mut session = Session::new(Arc::new(Lemmatizer::new()), budget);
    let mut records = 0usize;
    let mut analyzed_tokens = 0usize;
    let mut analyses = 0usize;
    let mut max_analyses = 0usize;
    let mut max_token_bytes = 0usize;
    let mut output = CountBytes::default();
    let start = Instant::now();
    klem::analyze_reader(File::open(&args[0])?, &mut session, |record| {
        records += 1;
        if let Some(result) = &record.analysis {
            analyzed_tokens += 1;
            analyses += result.analyses.len();
            max_analyses = max_analyses.max(result.analyses.len());
            max_token_bytes = max_token_bytes.max(record.surface.len());
        }
        if args[2] == "json" {
            serde_json::to_writer(&mut output, &record)?;
            writeln!(output)?;
        } else {
            black_box(record);
        }
        Ok(())
    })?;
    let seconds = start.elapsed().as_secs_f64();
    let peak_rss = std::fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|s| {
            s.lines()
                .find(|l| l.starts_with("VmHWM:"))
                .and_then(|l| l.split_whitespace().nth(1))
                .and_then(|s| s.parse::<u64>().ok())
        });
    println!(
        "{}",
        json!({"input":args[0],"input_sha256":format!("{:x}",digest.finalize()),
        "mode":args[2],"cache_budget":budget,"charged_cache_bytes":session.cached_bytes(),
        "input_bytes":input_bytes,"records":records,"analyzed_tokens":analyzed_tokens,
        "analyses":analyses,"max_analyses_per_token":max_analyses,"max_token_bytes":max_token_bytes,
        "serialized_bytes":output.0,"seconds":seconds,"mib_per_second":input_bytes as f64 / 1_048_576.0 / seconds,
        "process_peak_rss_kib_linux":peak_rss})
    );
    Ok(())
}
