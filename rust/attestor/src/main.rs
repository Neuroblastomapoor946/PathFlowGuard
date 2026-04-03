use serde::Serialize;
use std::env;
use std::error::Error;
use std::fs;
use std::fs::File;
use std::io::Read;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

#[derive(Debug, Serialize, PartialEq, Eq)]
struct ManifestEntry {
    path: String,
    bytes: u64,
    blake3: String,
}
fn collect_entries(root: &Path) -> Result<Vec<ManifestEntry>, Box<dyn Error>> {
    let mut entries = Vec::new();

    for entry_result in WalkDir::new(root) {
        let entry = entry_result?;
        if !entry.file_type().is_file() {
            continue;
        }

        let full_path = entry.into_path();
        let relative = normalized_relative_path(root, &full_path)?;
        let metadata = fs::metadata(&full_path)?;
        entries.push(ManifestEntry {
            path: relative,
            bytes: metadata.len(),
            blake3: hash_file(&full_path)?,
        });
    }

    entries.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(entries)
}

fn normalized_relative_path(root: &Path, full_path: &Path) -> Result<String, Box<dyn Error>> {
    let relative = full_path.strip_prefix(root)?;
    let text = relative
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join("/");
    Ok(text)
}

fn hash_file(path: &Path) -> Result<String, Box<dyn Error>> {
    let mut hasher = blake3::Hasher::new();
    let mut file = File::open(path)?;
    let mut buffer = [0_u8; 8192];

    loop {
        let bytes_read = file.read(&mut buffer)?;
        if bytes_read == 0 {
            break;
        }
        hasher.update(&buffer[..bytes_read]);
    }

    Ok(hasher.finalize().to_hex().to_string())
}

fn run(root: PathBuf) -> Result<(), Box<dyn Error>> {
    let entries = collect_entries(&root)?;
    println!("{}", serde_json::to_string_pretty(&entries)?);
    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let mut args = env::args_os();
    let executable = args
        .next()
        .and_then(|value| value.into_string().ok())
        .unwrap_or_else(|| "pathflow-attestor".to_string());

    let Some(path) = args.next() else {
        eprintln!("Usage: {executable} <directory>");
        return Ok(());
    };

    run(PathBuf::from(path))
}

#[cfg(test)]
mod tests {
    use super::collect_entries;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn collect_entries_is_deterministic() {
        let temp = tempdir().expect("temp dir");
        let root = temp.path();
        fs::write(root.join("b.txt"), "beta").expect("write b");
        fs::create_dir(root.join("nested")).expect("create dir");
        fs::write(root.join("nested").join("a.txt"), "alpha").expect("write a");

        let first = collect_entries(root).expect("first collect");
        let second = collect_entries(root).expect("second collect");

        assert_eq!(first, second);
        assert_eq!(first[0].path, "b.txt");
        assert_eq!(first[1].path, "nested/a.txt");
    }
}
