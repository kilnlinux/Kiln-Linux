//! Kiln's own state: which profiles are active, and which packages Kiln
//! itself installed for each. Nothing about versions or files; pacman owns
//! that. A package that was already installed before `kiln apply` is never
//! recorded, so `kiln remove --purge` can never take it away.
//!
//! Stored as TOML at /var/lib/kiln/state.toml (override: KILN_STATE_FILE).

use crate::error::{Error, Result, io_err};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

#[derive(Debug, Default, Deserialize, Serialize, PartialEq)]
pub struct State {
    /// Active profiles, by name.
    #[serde(default)]
    pub profiles: BTreeMap<String, ProfileState>,
}

#[derive(Debug, Default, Deserialize, Serialize, PartialEq)]
pub struct ProfileState {
    /// Packages Kiln installed because this profile asked for them.
    #[serde(default)]
    pub managed: BTreeSet<String>,
}

pub fn path() -> PathBuf {
    std::env::var_os("KILN_STATE_FILE")
        .map(PathBuf::from)
        .unwrap_or_else(|| PathBuf::from("/var/lib/kiln/state.toml"))
}

impl State {
    /// Missing file means a fresh system with nothing active.
    pub fn load() -> Result<State> {
        let p = path();
        match std::fs::read_to_string(&p) {
            Ok(text) => toml::from_str(&text).map_err(|e| {
                Error::Failed(format!("{}: corrupt state: {}", p.display(), e.message()))
            }),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(State::default()),
            Err(e) => Err(io_err("reading", &p)(e)),
        }
    }

    /// Write to a temp file in the same directory, fsync, then rename over the
    /// old file. rename() is atomic, so a crash leaves the old or the new
    /// state, never half of one.
    pub fn save(&self) -> Result<()> {
        use std::io::Write;
        let p = path();
        let dir = p.parent().unwrap_or(std::path::Path::new("."));
        std::fs::create_dir_all(dir).map_err(io_err("creating", dir))?;
        let tmp = p.with_extension("toml.tmp");
        let text = format!(
            "# Managed by kiln. Lists active profiles and the packages kiln installed for them.\n{}",
            toml::to_string(self).expect("state serializes")
        );
        let mut f = std::fs::File::create(&tmp).map_err(io_err("writing", &tmp))?;
        f.write_all(text.as_bytes())
            .and_then(|_| f.sync_all())
            .map_err(io_err("writing", &tmp))?;
        std::fs::rename(&tmp, &p).map_err(io_err("replacing", &p))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // Single test touching the env var, so parallel tests cannot race on it.
    #[test]
    fn round_trip_and_missing_file() {
        let dir = std::env::temp_dir().join(format!("kiln-state-test-{}", std::process::id()));
        let file = dir.join("sub/state.toml");
        unsafe { std::env::set_var("KILN_STATE_FILE", &file) };

        assert_eq!(State::load().unwrap(), State::default());

        let mut s = State::default();
        s.profiles
            .entry("dev".into())
            .or_default()
            .managed
            .insert("git".into());
        s.save().unwrap();
        assert_eq!(State::load().unwrap(), s);

        std::fs::remove_dir_all(&dir).unwrap();
    }
}
