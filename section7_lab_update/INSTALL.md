# Install the Section 7 Lab UI and README update

This patch targets the repository `joaokuntzwso2/identity-rfp` checked out as `magalu-ciam-is73-poc`. It preserves the existing sidebar, overview and WSO2 routes. It adds a `/lab` guided catalog and supporting assets, and replaces `README.md` with an end-to-end guide (after creating a backup **outside** the repository).

**Do not paste configuration secrets into the patch**. This patch does not modify containers, LDAP, WSO2 configuration, databases, OAuth clients or live sessions.

## 1. In the repository root, unpack and preview

```bash
unzip section7_lab_update.zip
python3 section7_lab_update/install.py --check
```

Inspect the reported files. Existing `demo/main.py` and `demo/templates/base.html` are changed additively, not replaced. The README is replaced with a complete new edition, and the previous README is backed up outside the repo during apply.

## 2. Apply the patch

```bash
python3 section7_lab_update/install.py --apply
python3 -m compileall -q demo
python3 -m pytest -q tests/test_section7_lab.py
```

The installer is idempotent: if it has already added the route and navigation, it won't add them twice. Review `git diff` before committing.

## 3. Rebuild only the existing demo portal

```bash
docker compose -p magalu-ciam73-s7lab \
  -f compose.yaml -f compose.isolated.yaml -f compose.frontends.yaml \
  up -d --no-deps --build demo
```

If your project was launched with another Compose override, use the same set. `--no-deps` is intentional: WSO2 and PostgreSQL should not be restarted just to update the UI.

Visit **http://localhost:8180/lab**. Check:

```bash
curl -fsS http://localhost:8180/healthz
curl -fsS http://localhost:8180/api/lab/catalog | jq '{total:(.tests|length),active:([.tests[]|select(.available)]|length)}'
```

“Available” means registered route, not a passed test. Review missing cards and actual test results with WSO2 running.

## 4. Commit only reviewed changes

The original `README.md`, `demo/main.py`, and `demo/templates/base.html` are backed up in a sibling directory named `<repo>-section7-backup`, not inside the git checkout. The extracted installer folder `section7_lab_update/` is only a delivery artifact; you do not need to commit it after applying.

```bash
git status --short
git diff --check
git diff --stat
# Stage reviewed source files only (not generated secrets or installer ZIP)
git add README.md demo/main.py demo/lab_hub.py demo/templates/base.html \
  demo/templates/lab_hub.html demo/static/lab_hub.css demo/static/lab_hub.js \
  scripts/bootstrap_sellerldap_roles.sh tests/test_section7_lab.py
# Review the staged diff for unexpected config or secrets before committing
git diff --cached --check
git diff --cached --stat
```

## Notes

- Some existing workbenches use `X-Frame-Options: DENY` / restrictive CSP. The lab deliberately **opens them in new tabs**, instead of weakening those controls.
- Six storefronts are separate browser origins and are launched as separate applications. The hub cannot and should not merge their cookies into one simulated login.
- N2/N3 deployment and M2M 1,000-token/load tests remain explicitly **deferred**.
- This package has been syntax-checked and smoke-tested with a minimal FastAPI/Jinja app, but **has not been executed against your actual Mac Docker stack**. The `--check` review and local test run are required.
