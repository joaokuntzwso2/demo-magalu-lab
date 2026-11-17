#!/usr/bin/env bash
# Non-destructive release gate. Executes from the project repository root.
# Requires git and Gitleaks; prints paths, never secret values.
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || { echo 'Not a git repository' >&2; exit 2; })"
command -v gitleaks >/dev/null || { echo 'Missing gitleaks: on macOS, brew install gitleaks' >&2; exit 2; }
[[ -f .gitignore ]] || { echo 'Missing .gitignore' >&2; exit 2; }

for path in .env generated/tenant-secrets.json generated/user-secrets.json generated/manifest.json generated/wso2/deployment.toml backups/test.sql test.pem; do
  if ! git check-ignore -q "$path"; then
    echo "FAIL: .gitignore does not protect $path" >&2
    exit 1
  fi
done

# Note: ignore rules do NOT untrack files that have already been committed!
tracked_ignored="$(git ls-files --cached --ignored --exclude-standard)"
if [[ -n "$tracked_ignored" ]]; then
  echo 'FAIL: Already tracked files are matched by .gitignore; review them:' >&2
  printf '%s\n' "$tracked_ignored" >&2
  echo 'For any private file, use git rm --cached <path> and check the entire repository history.' >&2
  exit 1
fi

# Verify staged paths do not include obvious secrets, including nested files.
if git diff --cached --name-only --diff-filter=ACMRT | grep -E '(^|/)(\.env($|\.)|generated/|backups/|secrets/|private/|.*-secrets\.json$|.*\.(pem|key|p12|pfx|jks|kdbx|tfstate)$)' > /dev/null; then
  echo 'FAIL: suspicious secret/generated file staged for commit.' >&2
  git diff --cached --name-only --diff-filter=ACMRT | grep -E '(^|/)(\.env($|\.)|generated/|backups/|secrets/|private/|.*-secrets\.json$|.*\.(pem|key|p12|pfx|jks|kdbx|tfstate)$)' >&2
  exit 1
fi

# Work on a temporary, permissions-locked export of the Git *index* only.
# This avoids scanning unrelated private .env / generated/ files on disk.
tmp="$(mktemp -d)"
chmod 700 "$tmp"
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/staged"
git checkout-index -a --prefix="$tmp/staged/"
echo 'Scanning staged repository snapshot with Gitleaks ...'
if ! gitleaks dir "$tmp/staged" --redact --no-banner >/dev/null; then
  echo 'FAIL: Gitleaks found potential secrets in staged snapshot. Review locally.' >&2
  exit 1
fi
if git rev-parse -q --verify HEAD >/dev/null; then
  echo 'Scanning existing Git history with Gitleaks ...'
  if ! gitleaks git . --redact --no-banner >/dev/null; then
    echo 'FAIL: Gitleaks found potential secrets in Git history. Rotate any exposed credentials; do not push.' >&2
    exit 1
  fi
fi

git diff --cached --check
printf '%s\n' 'PASS: tracked/ignored-file and Gitleaks checks completed.' \
  'WARNING: secret scanning is not a mathematical guarantee; review the staged diff and Git history yourself.'
