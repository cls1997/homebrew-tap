"""Track verified public proxy releases using only this tap's GITHUB_TOKEN."""
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request

SOURCE = "cls1997/CodexBar"
ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"v(\d+)\.(\d+)\.(\d+)-proxy\.([1-9]\d*)")
MAX_ARCHIVE = 256 * 1024 * 1024


def version_key(tag):
    match = PATTERN.fullmatch(tag)
    if not match:
        raise ValueError("Not a proxy release tag")
    return tuple(map(int, match.groups()))


def select_release(releases):
    candidates = [item for item in releases if not item.get("draft") and not item.get("prerelease")
                  and PATTERN.fullmatch(item.get("tag_name", ""))]
    return max(candidates, key=lambda item: version_key(item["tag_name"]), default=None)


def canonical_url(tag, name):
    version_key(tag)
    return f"https://github.com/{SOURCE}/releases/download/{tag}/{name}"


def asset_url(release, name):
    matches = [asset for asset in release.get("assets", []) if asset.get("name") == name]
    if len(matches) != 1 or matches[0].get("browser_download_url") != canonical_url(release["tag_name"], name):
        raise ValueError(f"Missing, duplicate, or unexpected asset: {name}")
    return matches[0]["browser_download_url"]


def checksum(text, archive):
    matches = []
    for line in text.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9.-]+)", line)
        if match and match[2] == archive:
            matches.append(match[1])
    if len(matches) != 1:
        raise ValueError("Expected one SHA256 entry for the archive")
    return matches[0]


def download(url, limit):
    request = urllib.request.Request(url, headers={"User-Agent": "cls1997-homebrew-tap"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Release asset exceeds size limit")
    return data


def public_releases():
    request = urllib.request.Request(f"https://api.github.com/repos/{SOURCE}/releases?per_page=100",
                                     headers={"Accept": "application/vnd.github+json", "User-Agent": "cls1997-homebrew-tap"})
    if os.environ.get("GH_TOKEN"):
        request.add_header("Authorization", "Bearer " + os.environ["GH_TOKEN"])
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def cask(version, digest):
    version_key("v" + version)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid archive checksum")
    return f'''cask "codexbar-proxy" do
  version "{version}"
  sha256 "{digest}"

  url "https://github.com/{SOURCE}/releases/download/v#{{version}}/CodexBar-#{{version}}-macos-arm64.zip"
  name "CodexBar Proxy"
  desc "AI usage menu bar with application-wide proxy settings"
  homepage "https://github.com/{SOURCE}"

  conflicts_with cask: "codexbar"
  depends_on arch: :arm64
  depends_on macos: :sonoma

  app "CodexBar.app", target: "CodexBar Proxy.app"

  uninstall quit: "com.steipete.codexbar"

  caveats do
    <<~EOS
      This fork is locally signed (ad-hoc) and is not notarized by Apple.
      iCloud sync and built-in updates are disabled. Manage updates using Homebrew.
    EOS
  end
end
'''


def update(release, destination):
    tag = release["tag_name"]
    version = tag[1:]
    version_key(tag)
    if destination.exists():
        match = re.search(r'^  version "([^"]+)"$', destination.read_text(), re.M)
        if not match:
            raise ValueError("Existing Cask has no explicit version")
        if version_key("v" + match[1]) >= version_key(tag):
            print("Cask is already current; no assets downloaded.")
            return False
    archive = f"CodexBar-{version}-macos-arm64.zip"
    digest = checksum(download(asset_url(release, "SHA256SUMS"), 65536).decode(), archive)
    manifest = json.loads(download(asset_url(release, "release.json"), 65536))
    expected = {"repository": SOURCE, "version": version, "tag": tag, "archive": archive,
                "architecture": "arm64", "signing": "adhoc", "sha256": digest}
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise ValueError("Release manifest does not match checksum, platform or version")
    payload = download(asset_url(release, archive), MAX_ARCHIVE)
    if hashlib.sha256(payload).hexdigest() != digest:
        raise ValueError("Downloaded archive does not match SHA256SUMS")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(cask(version, digest))
    print(f"Updated codexbar-proxy to {version}; verified downloaded archive SHA256.")
    return True


def main():
    release = select_release(public_releases())
    if release is None:
        print("No public proxy release yet; keeping the tap unchanged.")
        return
    update(release, ROOT / "Casks/codexbar-proxy.rb")


if __name__ == "__main__":
    main()
