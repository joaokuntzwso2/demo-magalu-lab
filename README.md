# Magalu Login — Section 7 Identity Architecture Lab

**WSO2 Identity Server 7.3 · independent root tenants · OIDC · SCIM · OpenLDAP · application roles · consent · token exchange**

> **Scope:** local customer-evaluation laboratory, not a production installation or a certification report. This guide distinguishes **implemented test surfaces**, **live behavior confirmed during the November 2026 lab exercise**, and **tests that still need evidence**. No test is marked PASS merely because a page exists.
>
> **Currently deferred:** N2/N3 deployment, real MFA step-up acceptance for those levels, and the M2M 1,000-token/load scenario. Basic M2M and RFC 8693 exploration remain available where configured.

## 1. What this lab demonstrates

The lab models Magalu Commerce and MagaluPay as **two independent WSO2 root tenants**, not child organizations. Within Commerce, Magalu Retail and Netshoes are separate brands/pairwise sectors; MagaluPay uses its own tenant and sector. Six distinct OIDC applications (Web and Mobile for each brand) exercise independent authentication sessions and client configuration.

```text
                        WSO2 Identity Server 7.3
                             localhost:9543
                                    |
                   +----------------+------------------+
                   |                                   |
            magalu.demo                         magalupay.demo
           MAGALU COMMERCE                       MAGALUPAY
                   |                                   |
            +------+------+                         Pay sector
            |             |                             |
         Magalu       Netshoes                      Web + Mobile
       Web + Mobile  Web + Mobile
            |
     SELLERLDAP (OpenLDAP)
     SELLERLDAP/ldap.seller

  Magalu Architecture Lab: http://localhost:8180/lab
  Independent storefronts: localhost:8181 through localhost:8186
```

The portal is a **guide and evidence launcher**, not an additional OIDC client. Authentication occurs in the storefronts and existing workbenches. The Section 7 route catalog discovers existing GET pages at runtime, so later standalone workbenches can appear without replacing the established left-sidebar/right-workspace layout. Security-sensitive pages that deny framing open in their own tab; compatible same-origin pages can open in the workspace pane. The hub never issues a successful-test verdict from route availability.

### What is implemented versus what is verified

| Area | Present in source/lab | Live evidence currently known | Remaining gate |
|---|---|---|---|
| WSO2 7.3 and two root-tenant bootstrap | Yes | Console and `magalu.demo` API tested | Verify independent Pay admin and full tenant inventory |
| Six independent OIDC storefronts | Yes | Application login reported working | Execute six sign-ins with captured token evidence |
| Pairwise `sub` comparison | Yes (`/pairwise`) | UI and API in source | Capture six signed ID tokens for the same attested person |
| Per-client claims | App-specific client configuration and test surfaces | Not proven end-to-end here | Test ID token/UserInfo and negative release |
| N2/N3, actual adaptive MFA | Policy/event fixture exists | **Deferred** | Real WSO2 ACR/AMR and step-up after future deployment |
| Consent ledger | Yes (`/m3/consent`) | Flow implemented | Evidence for denial, grant, revocation and retention |
| Native WSO2 Consent Management v2 | Yes (`/m3/native-consent`) | Operator workbench exists | Live native readback and dual-gate enforcement |
| RFC 8693 token exchange | Yes (`/m3/exchange`) | Workbench exists | Validate `sub`, `act.sub`, audience, scopes and rejection |
| Secondary OpenLDAP user store | Yes (`SELLERLDAP`) | **Confirmed** LDAP bind, SCIM GET, Console visibility and login | Rebuild from bootstrap without manual changes |
| Application-specific roles | Yes | Seller role setup was used in the POC | Re-run membership/authorization negative checks |
| Third root tenant onboarding | Bootstrap script exists | Not verified in this conversation | Before/after inventory and real login |
| B2B seller application | Yes (`/seller`, completion workbench) | LDAP seller login worked | Validate real authorization boundaries and business policy |
| Basic M2M Client Credentials | Yes (`/m2m`) | Live outcomes not established here | Verify issuer, audience, scopes, failures |
| M2M 1,000-token/load target | Tools may exist | **Deferred** | Do not claim throughput/SLA without a real run |

For the original gate definitions, see `docs/RELEASE_GATES.md`. Those gates remain authoritative wherever this README describes an unverified live scenario.

## 2. Prerequisites and safety

- macOS or a Docker-capable host, Docker Desktop/Compose v2, Python 3, `curl`, `jq`, `openssl`, `zip`, `unzip`.
- The customer-approved **WSO2 IS 7.3.18** Docker image or distribution. `7.3.18` is the repository's intended update level; verify what image your local environment actually runs.
- Ports `9543`, `8180` and `8181–8186` free on `localhost`.
- Access to generated local bootstrap secrets and an operator account for any protected workbench.
- Browser: use **`localhost` consistently** rather than mixing `127.0.0.1` and `localhost` because browser cookie behavior matters.

**Never commit** `.env`, `generated/`, `generated/wso2/deployment.toml`, tenant secrets, LDAP admin passwords, identity manifests, browser tokens, JWT capture files or generated backups. These can contain reusable credentials. The repository's `.gitignore` should exclude them; verify with `git status` before pushing. Self-signed TLS and development defaults are not suitable for production.

## 3. Start the local lab

From the repository root:

```bash
chmod +x scripts/*.sh
./scripts/setup-isolated.sh
./scripts/run-isolated.sh
```

The setup script creates a dedicated Docker Compose project and generated tenant/DB configuration. If using another updated WSO2 image, set `WSO2_IMAGE` in `.env`; if using a distribution ZIP, set `WSO2_DIST_PATH` and follow `scripts/prepare-updated-image.sh` / setup instructions. **Do not run a legacy `run-local.sh` from another architecture revision.**

Validate container and service availability:

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}'
curl -fsS http://localhost:8180/healthz | jq .
curl -fsS http://localhost:8180/api/lab/catalog | jq '{tests: (.tests|length), deferred: (.deferred|length)}'
```

Expected central URLs:

| Service | URL |
|---|---|
| Section 7 guided lab | `http://localhost:8180/lab` |
| Original overview | `http://localhost:8180/` |
| WSO2 Console (super tenant) | `https://localhost:9543/console` |
| Magalu Commerce tenant Console | `https://localhost:9543/t/magalu.demo/console` |
| MagaluPay tenant Console | `https://localhost:9543/t/magalupay.demo/console` |
| Magalu Web / Mobile | `http://localhost:8181` / `http://localhost:8182` |
| Netshoes Web / Mobile | `http://localhost:8183` / `http://localhost:8184` |
| MagaluPay Web / Mobile | `http://localhost:8185` / `http://localhost:8186` |

A certificate warning on local WSO2 HTTPS can be expected with self-signed development certificates. Do not bypass TLS verification in an internet-exposed deployment.

To rerun the existing bootstrap after the initial setup:

```bash
docker compose -p magalu-ciam73-s7lab -f compose.yaml -f compose.isolated.yaml \
  --profile tools run --rm bootstrap
```

For bootstrap failures, inspect `generated/bootstrap-report.json`; never interpret a failed management API call as successful provisioning.

## 4. Credentials: which username, and how to obtain passwords

**Passwords are not supplied in this README.** Exact tenant and user passwords may differ per bootstrap. Below is how an authorized local operator obtains or resets each one.

| Persona | Username / identifier | Password source / method |
|---|---|---|
| Super tenant administrator | `admin` | Isolated setup documents `admin/admin` as a localhost development default; verify `.env`/your environment; change outside localhost |
| Commerce tenant administrator | `tenantadmin@magalu.demo` | `generated/tenant-secrets.json` (locally generated) |
| Pay tenant administrator | tenant admin for `magalupay.demo` | `generated/tenant-secrets.json`; inspect the exact username |
| Seeded consumer | `ana.magalu` (use app's expected qualifier when needed) | `generated/manifest.json` or generated private bootstrap credentials |
| OpenLDAP seller | `SELLERLDAP/ldap.seller` at WSO2; `uid=ldap.seller,ou=people,dc=example,dc=test` in LDAP | Cannot recover plaintext from a password hash. Reset via LDAP administrator (below) |
| M2M applications | Per-client ID | Generated private client credentials in manifest/secret files. **Never paste client secrets into the browser or README** |

To inspect the local tenant secret structure **on your machine only**:

```bash
jq 'keys' generated/tenant-secrets.json
jq . generated/tenant-secrets.json
```

The second command prints credentials to your terminal; **do not copy its output into tickets, logs, pull requests or chats**. To inspect synthetic seeded user keys:

```bash
jq '.users | keys' generated/manifest.json
jq '.users["commerce:ana.magalu"] | {username, password, id}' generated/manifest.json
```

The sample key follows the POC's `commerce:ana.magalu` naming. If fields differ, inspect the local manifest structure and only use data that belongs to your lab.

### Reset and verify the LDAP seller password

The LDAP `userPassword` is a hash; there is no supported plaintext “fetch” operation. On the **existing** lab, set a known password interactively (no password on the shell command line):

```bash
docker exec -it magalu-ciam73-s7lab-ldap-1 ldappasswd \
  -x -H ldap://127.0.0.1:389 \
  -D 'cn=admin,dc=example,dc=test' -W -S \
  'uid=ldap.seller,ou=people,dc=example,dc=test'
```

`-S` prompts for the new seller password; `-W` prompts for the LDAP administrator bind password. If you do not know the admin password, obtain it from the approved local bootstrap secret source or responsible administrator; do not guess. For standard `osixia/openldap`, check the container's configured `LDAP_ADMIN_PASSWORD` environment only if you are authorized; displaying it writes it to your terminal history/output context. After resetting:

```bash
docker exec -it magalu-ciam73-s7lab-ldap-1 ldapwhoami \
  -x -H ldap://127.0.0.1:389 \
  -D 'uid=ldap.seller,ou=people,dc=example,dc=test' -W
```

Expected identity response: `dn:uid=ldap.seller,ou=people,dc=example,dc=test`.

**Important distinction:** `tenantadmin@magalu.demo` is the WSO2 tenant administrator for SCIM/management APIs; `cn=admin,dc=example,dc=test` is the LDAP administrator; `SELLERLDAP/ldap.seller` is the user who authenticates to OIDC apps.

## 5. End-to-end demonstration: use the lab as your presenter script

Open `http://localhost:8180/lab`. The left navigation remains the existing Magalu lab. The right workspace shows the requirement chapters and the integrated test catalog. The search box finds a requirement; “Abrir na área de trabalho” opens frame-safe pages in the right work pane; “Executar teste” opens the original workbench in a new tab when that is safer. Operator workbenches may require a configured operator key. Missing routes are listed as unavailable, not hidden success.

### Chapter 01 — Architecture and readiness (7.1)

1. Open **Visão geral**. Show root tenants `magalu.demo` and `magalupay.demo`.
2. Open the tenant Consoles and compare applications, user stores and administrators.
3. Check the **Section 7 acceptance cockpit** (`/s7/acceptance`, if registered).
4. Collect `generated/bootstrap-report.json` and the live inventory. Never claim tenant isolation solely from labels on a page.

**Pass evidence:** separate issuers/admin contexts, real tenant-bound API access and app inventory.

### Chapter 02 — Six application logins (7.2 #1, PF)

1. Use a private browser window or log out first; launch Magalu Web from the lab (8181).
2. Authenticate `ana.magalu` with the password from your local bootstrap manifest.
3. Repeat in Magalu Mobile (8182) and both Netshoes channels (8183/8184).
4. Authenticate an appropriate Pay tenant user on 8185/8186. **A matching human across root tenants must be explicitly attested**; the lab's identity vault does not prove production cross-root federation.
5. Each client should have its own signed session and logout behavior; do not presume one app's cookie authenticates another.

**Pass evidence:** actual ID tokens with verified issuer, `aud`, `exp`, `sub`; independent browser sessions. All six must be tested, not merely provisioned.

### Chapter 03 — Pairwise identity and claims (7.2 #1, #2)

1. After six sign-ins, open `/pairwise`.
2. Compare signed `sub` values: consistent within each brand's Web/Mobile sector; different across brands for the same attested identity.
3. Export `/api/pairwise-evidence` and record any `INCOMPLETE` or `MISMATCH` honestly.
4. Compare per-client scope requests and actual claim release. A requested scope alone does not prove its claim was issued or withheld; check the signed ID token and UserInfo, if supported.

**Pass evidence:** six signed token observations, known sector identifiers and negative claim release checks.

### Chapter 04 — Consent and root isolation (7.2 #4)

1. Open `/m3/consent` after authenticating the origin and recipient apps in the same browser.
2. Create an explicit directional link (not automatic identity correlation). Attempt resource access before consent: expect a denial.
3. Grant consent, verify the recipient can read the permitted synthetic resource, then revoke and expect denial again.
4. Open `/m3/native-consent` for WSO2 CM v2; inspect preflight, native consent record, business ledger and double-check decision. If native integration is not configured, record `BLOCKED` rather than a PASS.
5. Open `/m3/isolation` to test denied cross-root grants or exchanges without the intended configuration.

**Pass evidence:** authorization and revocation behavior with both stores checked, audit record and negative path.

### Chapter 05 — Delegation and M2M (7.2 #5, 7.3)

1. Open `/m3/exchange`: execute subject-only control, delegated request and attempted scope escalation.
2. Check `issued_token_type`, verified signature, audience, scopes, `sub` and `act.sub` (where actual actor preservation is required).
3. The negative case is not sufficient by itself; the legitimate delegated request must also succeed.
4. Open `/m2m` for a basic `client_credentials` issuance check. The UI must not display reusable raw JWTs or client secrets.

**Pass evidence:** real response codes and validated claims. **Do not run or claim** the deferred 1,000-token/load case from this chapter.

### Chapter 06 — LDAP seller, roles and third tenant (7.2 #6/#7, 7.3 PJ)

1. In WSO2 Console select `User Attributes & Stores → User Stores → SELLERLDAP` and verify the store is active.
2. Under Users, locate `SELLERLDAP/ldap.seller`. The existing lab validated this with SCIM ID `c7a24ec0-7232-1041-8f50-6ff5a9b38f9c`; after a fresh rebuild, **do not assume the same ID**.
3. Verify it through SCIM using the tenant admin (see commands below).
4. Launch the seller/B2B login (`/m3/completion?tab=b2b`) or a relevant Magalu storefront, authenticate `SELLERLDAP/ldap.seller` with the reset LDAP password, and verify authorization.
5. Compare application-specific role **names plus application audience** to Ana; identical role names may refer to distinct applications. Check denial without the required role.
6. Third-tenant onboarding is separate from LDAP: execute the operator bootstrap command only in an intended test environment, inspect before/after inventory and log into the third tenant.

SCIM retrieval of the LDAP seller:

```bash
curl -k -i --user 'tenantadmin@magalu.demo' \
  -G 'https://localhost:9543/t/magalu.demo/scim2/Users' \
  --data-urlencode 'domain=SELLERLDAP' \
  --data-urlencode 'filter=userName eq "SELLERLDAP/ldap.seller"' \
  --data-urlencode 'startIndex=1' \
  --data-urlencode 'count=10'
```

The expected successful response contains a **`Resources` array** with the seller, not `totalResults: 1` plus `itemsPerPage: 0`, and not HTTP 200 with an empty body. For a known ID, use `GET /t/magalu.demo/scim2/Users/{id}`. This was confirmed working during the interactive lab exercise.

To compare and assign the seven known application roles shown for Ana, use the included **optional** script:

```bash
chmod +x scripts/bootstrap_sellerldap_roles.sh
./scripts/bootstrap_sellerldap_roles.sh --dry-run
./scripts/bootstrap_sellerldap_roles.sh --apply
```

It prompts for the tenant-admin password, resolves seller ID dynamically, checks audience and does not remove existing role memberships. This script is a separate operator step; **it has not been proven integrated into `bootstrap.main`**. Running bootstrap after a complete environment recreation still requires a dedicated repeatability test.

The third root tenant, when deliberately in scope for live acceptance, can be created with:

```bash
docker compose -p magalu-ciam73-s7lab -f compose.yaml -f compose.isolated.yaml \
  --profile tools run --rm bootstrap python -m scripts.onboard_brand
```

This provisions `magalufresh.demo` as a new **root tenant**, not a child organization; verify a before/after inventory and actual login.

### Chapter 07 — Evidence handover

Use the lab's read-only `/api/evidence` and `/api/storefront-status` results and the specialized workbench reports. Label every artifact with date, environment, tenant, client, expected result, actual result and trace ID. Retain sensitive JWTs, manifests and operator data only in appropriately protected local storage.

Suggested acceptance line per test: `NOT RUN`, `BLOCKED`, `FAIL`, `PARTIAL`, `PASS`. Never infer PASS from a configured route, a green-looking UI, a successful LDAP bind, or an HTTP 200 with empty body.

## 6. Why the SELLERLDAP integration needed special care

The validated OpenLDAP seller entry has:

```text
DN: uid=ldap.seller,ou=people,dc=example,dc=test
uid: ldap.seller
objectClass: inetOrgPerson
User ID attribute: entryUUID
```

The tenant's secondary store file was deployed at:

```text
/home/wso2carbon/wso2is-7.3.0/repository/tenants/1/userstores/SELLERLDAP.xml
```

The working search configuration is:

```text
UserNameAttribute = uid
UserSearchBase = ou=people,dc=example,dc=test
UserNameSearchFilter = (&(objectClass=inetOrgPerson)(uid=?))
UserNameListFilter = (objectClass=inetOrgPerson)
UserIDAttribute = entryUUID
UserIdSearchFilter = (&(objectClass=inetOrgPerson)(entryUUID=?))
SCIMEnabled = true
```

**Claims:** tenant local User ID maps `SELLERLDAP → entryUUID`. Username should map `SELLERLDAP → uid` if required by the configured claims. LDAP operational dates `createTimestamp` / `modifyTimestamp` are LDAP GeneralizedTime values (such as `20261111154618Z`), not ISO 8601. Directly mapping them into SCIM Created/Modified caused `java.time.format.DateTimeParseException` in `SCIMCommonUtils.convertToMicroTimestamp`. The live fix was to avoid passing these incompatible raw timestamps into SCIM conversion. Do not silently recreate that mapping during bootstrap; use an explicitly validated conversion if time metadata is needed later.

**File permissions:** copying `SELLERLDAP.xml` from the host changed ownership on one occasion; WSO2 runs as `wso2carbon` (UID 802 in the observed container). Confirm the file is writable by WSO2 before updating in Console:

```bash
docker exec magalu-ciam73-s7lab-is-1 sh -c '
  FILE=/home/wso2carbon/wso2is-7.3.0/repository/tenants/1/userstores/SELLERLDAP.xml
  id; ls -l "$FILE"; test -w "$FILE" && echo WRITABLE || echo NOT_WRITABLE
'
```

Fix ownership only if it is wrong, with an authorized container admin. Do not broadly change permissions on the entire WSO2 repository.

**AgentIdentity:** the lab's generated `/generated/wso2/deployment.toml` originally omitted `[datasource.AgentIdentity]`, causing a secondary user-store startup error. The local development configuration was repaired, but generated files may be overwritten when setup is rerun. Make the datasource change in the **source that generates the file**, not by committing generated secrets. The H2 agent datasource was a local-only workaround; PostgreSQL-backed persistence requires WSO2's agent database schema and appropriate datasource. Do not treat the workaround as a production design.

## 7. Debug commands

```bash
# WSO2 container/network/ports
docker ps --format 'table {{.Names}}\t{{.Ports}}'
docker port magalu-ciam73-s7lab-is-1
docker inspect magalu-ciam73-s7lab-is-1 \
  --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'

# Recent WSO2 errors after a failed request
docker exec magalu-ciam73-s7lab-is-1 sh -c \
  'tail -n 400 /home/wso2carbon/wso2is-7.3.0/repository/logs/wso2carbon.log' \
  | grep -Ei -C 5 'ERROR|UserStoreException|DateTimeParseException|SCIM|SELLERLDAP'

# Lab route discovery, not execution success
curl -fsS http://localhost:8180/api/lab/catalog | jq '.tests[] | {id,available,path}'
```

The real application route table is discovered at runtime. If a generated page is missing, confirm its router is included in `demo/main.py` and that the demo container was rebuilt with the new Python/templates/static files. Some existing workbenches intentionally send `X-Frame-Options: DENY` or CSP `frame-ancestors 'none'`; open these via the lab's **Executar teste** action rather than weakening those protections.

## 8. Development, testing and release criteria

Run local lint/test commands available in the repo, then rebuild **only the demo service** for UI-only modifications:

```bash
python3 -m compileall -q demo
python3 -m pytest -q tests  # if pytest and the test dependencies are installed

docker compose -p magalu-ciam73-s7lab \
  -f compose.yaml -f compose.isolated.yaml \
  -f compose.frontends.yaml up -d --no-deps --build demo
```

The Compose invocation depends on the same file/profile selection used by your environment; if the project was started with additional override files, include those in the rebuild. Do not reset PostgreSQL or WSO2 just to update the portal.

**UI acceptance:** sidebar preserved, `/lab` returns 200, search and filters work, existing workbenches can be launched, framing-sensitive tests open separately, unavailable routes are not treated as passing, six storefronts remain independent. Review narrow-screen behavior and keyboard navigation. **Functional acceptance:** use the actual WSO2 server and complete the full Section 7 evidence matrix; keep deferred scope explicit.

### Planned next work

1. Integrate the verified `SELLERLDAP` configuration, claim mappings, AgentIdentity datasource and the optional role script into the **persistent bootstrap source**, rather than relying on repaired container state.
2. Automate positive and negative authorization checks for each application audience.
3. Capture a reproducible, sanitized evidence bundle for each Section 7 scenario.
4. Enhance UX/observability without claiming unimplemented MFA levels or throughput.

**Final rule:** this lab explains how Section 7 can be demonstrated. It does **not** assert that every original Section 7 gate has passed until actual evidence exists for that gate.
