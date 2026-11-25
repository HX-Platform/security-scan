# security-scan

Reusable GitHub Actions security gate for HX-Platform / IGC projects.

Runs three scanners on the **caller's** checkout, renders findings as markdown
tables in the job summary, uploads JSON reports as artifacts, and alerts
Google Chat when blocking findings exist.

| Scanner  | Scope                                   | Blocks on (when `enforce: true`) |
|----------|-----------------------------------------|----------------------------------|
| Trivy    | deps vulns, secrets, IaC misconfig (fs) | any CRITICAL (unfixed ignored)   |
| Gitleaks | secrets in the commits of this push     | any leak                         |
| Semgrep  | SAST                                    | any ERROR                        |

Default mode is **report-only**: findings never fail the run.

## Usage

```yaml
# .github/workflows/deploy.yml in the calling repo
jobs:
  security-scan:
    uses: HX-Platform/security-scan/.github/workflows/security-scan.yml@v1
    with:
      caller: deploy-api-dev                 # label in summary + alert
      scan_paths: apps/api docker/apps       # Semgrep targets / Gitleaks pathspec
      trivy_skip_dirs: docs,ui-testing
      semgrep_config: p/typescript p/nodejs
      enforce: false
    secrets: inherit                         # passes GOOGLE_CHAT_WEBHOOK

  deploy:
    needs: security-scan
    # ...
```

### Inputs

| Input              | Type    | Default     | Meaning                                                    |
|--------------------|---------|-------------|------------------------------------------------------------|
| `caller`           | string  | `manual`    | Label used in the summary and alert title                  |
| `scan_paths`       | string  | `.`         | Space-separated paths for Semgrep and the Gitleaks pathspec |
| `trivy_skip_dirs`  | string  | `""`        | Comma-separated dirs Trivy skips                           |
| `trivy_skip_files` | string  | `""`        | Comma-separated files Trivy skips                          |
| `semgrep_config`   | string  | `p/default` | Space-separated Semgrep rulesets                           |
| `enforce`          | boolean | `false`     | Fail the run on blocking findings                          |

### Secrets

- `GOOGLE_CHAT_WEBHOOK` (optional) — incoming webhook for alerts. Missing → alert skipped with a warning.

### Per-project tuning

Put these in the **calling** repo root; the scanners pick them up automatically:
`.trivyignore`, `.semgrepignore`, `.gitleaks.toml`.

## Access

Callers live in other orgs (e.g. `igc-developer`), so this repo must be
**public** — GitHub does not allow calling a reusable workflow from a private
repo in another organization. Nothing secret lives here; the webhook is passed
by the caller as a secret.

## Versioning

Callers pin a major tag (`@v1`). The workflow also references its own
composite action at `@v1`, so the tag must exist before first use:

```sh
git tag -a v1.0.0 -m "v1.0.0" && git push origin v1.0.0
git tag -f v1 && git push -f origin v1     # move the major tag on each release
```

Breaking input/behavior changes → new major tag (`v2`) and update the
`notify-google-chat@v1` ref inside `security-scan.yml` to match.
