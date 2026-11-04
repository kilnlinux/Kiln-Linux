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
    def asset(self, payload=b"package"):
        return {
            "name": "kiln-0.2.0-1-x86_64.pkg.tar.zst",
            "browser_download_url": "https://github.com/kilnlinux/kiln-package-manager/releases/download/v0.2.0/kiln-0.2.0-1-x86_64.pkg.tar.zst",
            "size": len(payload), "digest": "sha256:" + hashlib.sha256(payload).hexdigest(),
        }

    def test_release_selection(self):
        asset = self.asset()
        self.assertEqual(update.candidate({"assets": [asset]})[0], "0.2.0-1")
        self.assertIsNone(update.candidate(None))
        self.assertIsNone(update.candidate({"assets": [asset], "prerelease": True}))
        self.assertIsNone(update.candidate({"assets": [asset], "draft": True}))
        with self.assertRaises(ValueError):
            update.candidate({"assets": [asset, asset]})

    def test_package_validation_and_pacman_install(self):
        def query(args, **kwargs):
            if args[1] == "-Qip":
                return "Name : kiln\nVersion : 0.2.0-1\nArchitecture : x86_64\n"
            return "kiln 0.1.0-1\n"
        with patch.object(update.urllib.request, "urlopen", return_value=io.BytesIO(b"package")), \
             patch.object(update.subprocess, "check_output", side_effect=query), \
             patch.object(update.subprocess, "run") as install, \
             patch.object(update, "newer", return_value=True):
            update.install_package("0.2.0-1", self.asset())
            self.assertEqual(install.call_args.args[0][:4], ["pacman", "-U", "--noconfirm", "--"])

    def test_corrupt_download_never_installs(self):
        with patch.object(update.urllib.request, "urlopen", return_value=io.BytesIO(b"corrupt")), \
             patch.object(update.subprocess, "run") as install:
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                update.install_package("0.2.0-1", self.asset())
            install.assert_not_called()

    def test_missing_digest_and_external_url_never_download(self):
        with patch.object(update.urllib.request, "urlopen") as download:
            for field, value in [("digest", ""), ("browser_download_url", "https://example.com/pkg")]:
                asset = self.asset()
                asset[field] = value
                with self.assertRaises(ValueError):
                    update.install_package("0.2.0-1", asset)
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
                        update.install_package("0.2.0-1", self.asset())
                else:
                    update.install_package("0.2.0-1", self.asset())
                install.assert_not_called()

    def test_distro_release_and_source_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory) / "build.json"
            build.write_text(json.dumps({"revision": "abc", "release": "v1", "built_at": "2026-01-01T00:00:00+00:00"}))
            release = {"tag_name": "v2", "published_at": "2026-02-01T00:00:00Z"}
            with patch.object(update, "BUILD", build), \
                 patch.object(update, "fetch_json", side_effect=[None, release, {"sha": "def"}]), \
                 patch.object(update.subprocess, "check_output", return_value="kiln 0.1.0-1\n"):
                data = update.collect()
            self.assertFalse(data["kiln_available"])
            self.assertEqual(data["distro_release"], release)
            self.assertTrue(data["source_update"])
            release["tag_name"] = "v1"
            with patch.object(update, "BUILD", build), \
                 patch.object(update, "fetch_json", side_effect=[None, release, {"sha": "abc"}]), \
                 patch.object(update.subprocess, "check_output", return_value="kiln 0.1.0-1\n"):
                data = update.collect()
            self.assertIsNone(data["distro_release"])
            self.assertFalse(data["source_update"])

    def test_check_does_not_install_or_write_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            with patch.object(update.sys, "argv", ["kiln-update", "--check"]), \
                 patch.object(update, "STATE", state), \
                 patch.object(update, "collect", return_value={"kiln_available": True}), \
                 patch.object(update, "install_package") as install, \
                 patch("sys.stdout", new_callable=io.StringIO):
                update.main()
            install.assert_not_called()
            self.assertFalse(state.exists())

    def test_apply_records_installed_version_in_readable_cache(self):
        import builtins
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            real_open = builtins.open
            def open_file(path, *args, **kwargs):
                if path == "/run/kiln-update.lock":
                    path = Path(directory) / "update.lock"
                return real_open(path, *args, **kwargs)
            data = {"installed": "0.1.0-1", "kiln_available": True,
                    "kiln_release": {"assets": [self.asset()]}}
            with patch.object(update.sys, "argv", ["kiln-update", "--apply"]), \
                 patch.object(update.os, "geteuid", return_value=0), \
                 patch.object(update, "STATE", state), \
                 patch.object(update, "collect", return_value=data), \
                 patch.object(update, "install_package") as install, \
                 patch.object(update.subprocess, "check_output", return_value="kiln 0.2.0-1\n"), \
                 patch("builtins.open", side_effect=open_file), \
                 patch("sys.stdout", new_callable=io.StringIO):
                update.main()
            install.assert_called_once()
            saved = json.loads(state.read_text())
            self.assertEqual(saved["installed"], "0.2.0-1")
            self.assertFalse(saved["kiln_available"])
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
