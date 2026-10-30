# cls1997 Homebrew tap

Casks for personal forks. CodexBar Proxy targets Apple Silicon and macOS 14 or later.

```sh
brew install --cask cls1997/tap/codexbar-proxy
brew update
brew upgrade --cask cls1997/tap/codexbar-proxy
```

The `codexbar-proxy` cask is generated after the first public `vX.Y.Z-proxy.N`
release in [cls1997/CodexBar](https://github.com/cls1997/CodexBar). It installs
`CodexBar Proxy.app` and conflicts with the official `codexbar` Cask. Do not run
both variants together; they share the application's preferences and identity.
Local preferences are preserved on uninstall; no `zap` data deletion is configured.

The fork is ad-hoc signed, not Apple-notarized. iCloud and built-in updates are
disabled; use Homebrew for upgrades. Gatekeeper is not disabled by this tap.

## Automatic synchronization

The Update casks workflow polls the public source releases every 30 minutes
(at minutes 17 and 47) and can be run manually. It selects numeric proxy versions,
rejects drafts/prereleases, checks the platform manifest and verifies the full
archive against SHA256SUMS before writing a Cask. Existing or older versions are
not re-downloaded and never downgrade an installed Cask definition.

Only this repository's GITHUB_TOKEN is needed. No cross-repository PAT or source
repository write permission is used. Scheduled GitHub Actions can be delayed and
may be disabled after extended repository inactivity; re-enable/run the workflow
from Actions if necessary.

Before the first source release, synchronization exits successfully without
publishing a Cask containing a placeholder URL or checksum.
