use klem::dictionary::{Dictionary, Result, SqliteDictionary, import_krdict};
use std::{
    fs,
    io::{self, Write},
    path::PathBuf,
};

pub fn run(args: Vec<String>) -> Result<()> {
    let result = match args.as_slice() {
        [command, input, destination, option, snapshot] if command == "import-krdict" && option == "--snapshot" => {
            let path = PathBuf::from(input);
            let mut files = if path.is_dir() {
                fs::read_dir(&path)?.map(|e| e.map(|e| e.path()))
                    .collect::<std::result::Result<Vec<_>, _>>()?
                    .into_iter().filter(|p| p.extension().is_some_and(|e| e == "json")).collect()
            } else { vec![path] };
            files.sort();
            serde_json::to_value(import_krdict(&files, destination, snapshot)?)?
        }
        [command, path] if command == "info" => {
            let db = SqliteDictionary::open(path)?;
            serde_json::json!({"fingerprint":db.fingerprint(), "metadata":db.metadata()})
        }
        [command, path, word] if command == "lookup" => {
            let db = SqliteDictionary::open(path)?;
            serde_json::json!({"source":db.metadata().source, "fingerprint":db.fingerprint(), "entries":db.lookup(word)?})
        }
        [command, path, id] if command == "entry" => {
            let db = SqliteDictionary::open(path)?;
            let entry = db.entry(id)?.ok_or("dictionary entry not found")?;
            serde_json::json!({"source":db.metadata().source, "fingerprint":db.fingerprint(), "entry":entry})
        }
        _ => return Err("usage: klem dict import-krdict <json-directory|file> <new.db> --snapshot <label>\n       klem dict info <db>\n       klem dict lookup <db> <headword>\n       klem dict entry <db> <entry-id>".into()),
    };
    let mut out = io::BufWriter::new(io::stdout().lock());
    serde_json::to_writer(&mut out, &result)?;
    writeln!(out)?;
    out.flush()?;
    Ok(())
}
