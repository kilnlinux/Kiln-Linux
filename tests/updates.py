#!/usr/bin/env python3
"""Test GitHub update decisions without network calls or package installation."""
import hashlib
import importlib.machinery
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader("kiln_update", "packages/kiln-updates/kiln-update")
spec = importlib.util.spec_from_loader(loader.name, loader)
update = importlib.util.module_from_spec(spec)
loader.exec_module(update)


class UpdateTests(unittest.TestCase):
    def asset(self, payload=b"package", name="kiln-0.2.0-1-x86_64.pkg.tar.zst"):
        return {
            "name": name,
            "browser_download_url": "https://github.com/kilnlinux/kiln-package-manager/releases/download/v0.2.0/" + name,
            "size": len(payload), "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
        }

    def update(self, asset=None):
        return {"name": "kiln", "installed": "0.1.0-1", "version": "0.2.0-1",
                "repo": "kilnlinux/kiln-package-manager", "asset": asset or self.asset()}

    def test_release_selection(self):
        asset = self.asset()
        self.assertEqual(update.candidate({"assets": [asset]}, "kiln")[0], "0.2.0-1")
        self.assertIsNone(update.candidate(None, "kiln"))
        self.assertIsNone(update.candidate({"assets": [asset], "prerelease": True}, "kiln"))
        self.assertIsNone(update.candidate({"assets": [asset], "draft": True}, "kiln"))
        with self.assertRaises(ValueError):
            update.candidate({"assets": [asset, asset]}, "kiln")
        # Other packages in the same release never match, including name prefixes.
        other = self.asset(name="kiln-updates-0.2.0-1-any.pkg.tar.zst")
        self.assertEqual(update.candidate({"assets": [asset, other]}, "kiln")[1], asset)
        self.assertEqual(update.candidate({"assets": [asset, other]}, "kiln-updates")[0], "0.2.0-1")

    def test_installed_kiln_packages_and_repositories(self):
        info = {
            "kiln": "Name : kiln\nVersion : 0.1.0-1\nURL : https://github.com/kilnlinux/kiln-package-manager\n",
            "twmx": "Name : twmx\nVersion : 2.1-3\nURL : https://example.com/twmx\n",
        }
        def query(args, **kwargs):
            name = args[-1]
            return update.subprocess.CompletedProcess(args, 0 if name in info else 1, info.get(name, ""), "")
        with patch.object(update.subprocess, "check_output", return_value="kiln twmx kiln-updates\n"), \
             patch.object(update.subprocess, "run", side_effect=query):
            self.assertEqual(update.installed_packages(), {
                "kiln": ("0.1.0-1", "kilnlinux/kiln-package-manager"), "twmx": ("2.1-3", None)})

    def test_package_validation_and_single_pacman_transaction(self):
        def query(args, **kwargs):
            if args[1] == "-Qip":
                name = Path(args[2]).name.split("-0.2.0")[0]
                return f"Name : {name}\nVersion : 0.2.0-1\nArchitecture : x86_64\n"
            return "kiln 0.1.0-1\n"
        second = self.update(self.asset(name="kiln-updates-0.2.0-1-any.pkg.tar.zst"))
        second["name"] = "kiln-updates"
        with patch.object(update.urllib.request, "urlopen", side_effect=lambda *a, **k: io.BytesIO(b"package")), \
             patch.object(update.subprocess, "check_output", side_effect=query), \
             patch.object(update.subprocess, "run") as install, \
             patch.object(update, "newer", return_value=True):
            update.install([self.update(), second])
            install.assert_called_once()
            self.assertEqual(install.call_args.args[0][:4], ["pacman", "-U", "--noconfirm", "--"])
            self.assertEqual(len(install.call_args.args[0]), 6)

    def test_corrupt_download_never_installs(self):
        with patch.object(update.urllib.request, "urlopen", return_value=io.BytesIO(b"corrupt")), \
             patch.object(update.subprocess, "run") as install:
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                update.install([self.update()])
            install.assert_not_called()

    def test_missing_digest_and_external_url_never_download(self):
        with patch.object(update.urllib.request, "urlopen") as download:
            for field, value in [("digest", ""), ("browser_download_url", "https://example.com/pkg"),
                                 ("browser_download_url", "https://github.com/other/repo/releases/download/v1/pkg")]:
                asset = self.asset()
                asset[field] = value
                with self.assertRaises(ValueError):
                    update.install([self.update(asset)])
            download.assert_not_called()

    def test_wrong_package_and_concurrent_upgrade(self):
        for metadata, newer, error in [
            ("Name : other\nVersion : 0.2.0-1\nArchitecture : x86_64\n", True, True),
            ("Name : kiln\nVersion : 0.2.0-1\nArchitecture : x86_64\n", False, False),
        ]:
            with patch.object(update.urllib.request, "urlopen", return_value=io.BytesIO(b"package")), \
                 patch.object(update.subprocess, "check_output", side_effect=[metadata, "kiln 0.3.0-1\n"]), \
                 patch.object(update.subprocess, "run") as install, \
                 patch.object(update, "newer", return_value=newer):
                if error:
                    with self.assertRaises(ValueError):
                        update.install([self.update()])
                else:
                    update.install([self.update()])
                install.assert_not_called()

    def test_distro_release_and_source_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory) / "build.json"
            build.write_text(json.dumps({"revision": "abc", "release": "v1", "built_at": "2026-01-01T00:00:00+00:00"}))
            release = {"tag_name": "v2", "published_at": "2026-02-01T00:00:00Z"}
            with patch.object(update, "BUILD", build), \
                 patch.object(update, "fetch_json", side_effect=[None, release, {"sha": "def"}]), \
                 patch.object(update, "installed_packages", return_value={
                     "kiln": ("0.1.0-1", "kilnlinux/kiln-package-manager"), "twmx": ("2.1-3", None)}):
                data = update.collect()
            self.assertEqual(data["updates"], [])
            self.assertEqual(data["distro_release"], release)
            self.assertTrue(data["source_update"])
            release["tag_name"] = "v1"
            with patch.object(update, "BUILD", build), \
                 patch.object(update, "fetch_json", side_effect=[None, release, {"sha": "abc"}]), \
                 patch.object(update, "installed_packages", return_value={
                     "kiln": ("0.1.0-1", "kilnlinux/kiln-package-manager")}):
                data = update.collect()
            self.assertIsNone(data["distro_release"])
            self.assertFalse(data["source_update"])

    def test_check_does_not_install_or_write_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            with patch.object(update.sys, "argv", ["kiln-update", "--check"]), \
                 patch.object(update, "STATE", state), \
                 patch.object(update, "collect", return_value={"updates": [self.update()]}), \
                 patch.object(update, "install") as install, \
                 patch("sys.stdout", new_callable=io.StringIO):
                update.main()
            install.assert_not_called()
            self.assertFalse(state.exists())

    def test_apply_clears_installed_updates_in_readable_cache(self):
        import builtins
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            real_open = builtins.open
            def open_file(path, *args, **kwargs):
                if path == "/run/kiln-update.lock":
                    path = Path(directory) / "update.lock"
                return real_open(path, *args, **kwargs)
            data = {"updates": [self.update()]}
            with patch.object(update.sys, "argv", ["kiln-update", "--apply"]), \
                 patch.object(update.os, "geteuid", return_value=0), \
                 patch.object(update, "STATE", state), \
                 patch.object(update, "collect", return_value=data), \
                 patch.object(update, "install") as install, \
                 patch("builtins.open", side_effect=open_file), \
                 patch("sys.stdout", new_callable=io.StringIO):
                update.main()
            install.assert_called_once()
            saved = json.loads(state.read_text())
            self.assertEqual(saved["updates"], [])
            self.assertEqual(state.stat().st_mode & 0o777, 0o644)

    def test_cached_status_never_uses_network(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text("{}")
            with patch.object(update.sys, "argv", ["kiln-update", "--status"]), \
                 patch.object(update, "STATE", state), \
                 patch.object(update, "fetch_json") as fetch:
                update.main()
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
