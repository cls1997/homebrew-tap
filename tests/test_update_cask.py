import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("update_cask", Path(__file__).parents[1] / "scripts/update_cask.py")
tap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tap)


class CaskUpdateTests(unittest.TestCase):
    def test_numeric_release_order_and_filtering(self):
        items = [{"tag_name": tag} for tag in ["v0.82.0", "v0.82.0-proxy.2", "v0.82.0-proxy.10"]]
        items += [{"tag_name": "v0.83.0-proxy.1", "draft": True}]
        self.assertEqual(tap.select_release(items)["tag_name"], "v0.82.0-proxy.10")
        self.assertIsNone(tap.select_release([]))

    def test_cask_only_accepts_strict_version_and_checksum(self):
        with self.assertRaises(ValueError):
            tap.cask('0.82.0";system("bad")', "a" * 64)
        with self.assertRaises(ValueError):
            tap.cask("0.82.0-proxy.1", "invalid")

    def test_rejects_foreign_asset_urls_and_duplicate_checksums(self):
        release = {"tag_name": "v0.82.0-proxy.1", "assets": [
            {"name": "SHA256SUMS", "browser_download_url": "https://example.com/SHA256SUMS"}]}
        with self.assertRaises(ValueError):
            tap.asset_url(release, "SHA256SUMS")
        with self.assertRaises(ValueError):
            tap.checksum(("a" * 64 + "  file.zip\n") * 2, "file.zip")

    def test_archive_is_verified_before_cask_is_written(self):
        tag = "v0.82.0-proxy.1"
        archive = "CodexBar-0.82.0-proxy.1-macos-arm64.zip"
        payload = b"test archive"
        digest = hashlib.sha256(payload).hexdigest()
        manifest = {"repository": tap.SOURCE, "version": tag[1:], "tag": tag, "archive": archive,
                    "architecture": "arm64", "signing": "adhoc", "sha256": digest}
        release = {"tag_name": tag, "assets": [{"name": name, "browser_download_url": tap.canonical_url(tag, name)}
                                                for name in [archive, "SHA256SUMS", "release.json"]]}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "codexbar-proxy.rb"
            data = [f"{digest}  {archive}\n".encode(), json.dumps(manifest).encode(), b"tampered"]
            with patch.object(tap, "download", side_effect=data), self.assertRaises(ValueError):
                tap.update(release, target)
            self.assertFalse(target.exists())
            with patch.object(tap, "download", side_effect=data[:2] + [payload]):
                self.assertTrue(tap.update(release, target))
            self.assertIn(f'  sha256 "{digest}"', target.read_text())
            self.assertNotIn("auto_updates true", target.read_text())
            with patch.object(tap, "download") as download:
                self.assertFalse(tap.update(release, target))
                download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
