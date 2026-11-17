#!/usr/bin/env bash
# Bootstrap the seven application-role assignments shown for ana.magalu
# onto SELLERLDAP/ldap.seller in WSO2 Identity Server 7.3.
# Dry run by default. Run with --apply to grant missing memberships.
set -euo pipefail

MODE="${1:---dry-run}"
case "$MODE" in
  --dry-run) APPLY=false ;;
  --apply) APPLY=true ;;
  *) echo "Usage: $0 [--dry-run|--apply]" >&2; exit 2 ;;
esac

for cmd in curl jq; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "Missing dependency: $cmd" >&2; exit 1; }
done

BASE_URL="${BASE_URL:-https://localhost:9543}"
BASE_URL="${BASE_URL%/}"
TENANT="${TENANT:-magalu.demo}"
ADMIN_USER="${ADMIN_USER:-tenantadmin@magalu.demo}"
SOURCE_USERNAME="${SOURCE_USERNAME:-ana.magalu}"
SOURCE_ID="${SOURCE_ID:-}"
TARGET_USERNAME="${TARGET_USERNAME:-SELLERLDAP/ldap.seller}"
TARGET_ID="${TARGET_ID:-}"
USERS_URL="$BASE_URL/t/$TENANT/scim2/Users"
ROLES_URL="$BASE_URL/t/$TENANT/scim2/v2/Roles"

if [[ -z "${WSO2_PASSWORD:-}" ]]; then
  read -r -s -p "WSO2 password for $ADMIN_USER: " WSO2_PASSWORD
  printf '\n'
fi
[[ -n "$WSO2_PASSWORD" ]] || { echo "Missing WSO2 password" >&2; exit 1; }

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { echo "ERROR: $*" >&2; exit 1; }

get_json() {
  local out="$1" url="$2" code
  shift 2
  code="$(curl -k -sS --user "$ADMIN_USER:$WSO2_PASSWORD" \
    -H 'Accept: application/scim+json' \
    -o "$out" -w '%{http_code}' "$@" "$url")" || fail "GET request failed: $url"
  if [[ "$code" != 200 ]]; then
    echo "Response ($code) from $url:" >&2
    head -c 1500 "$out" >&2 || true
    echo >&2
    fail "Unexpected HTTP $code"
  fi
  jq -e 'type == "object"' "$out" >/dev/null || fail "Not a JSON object from $url"
}

# Resolve Ana's SCIM ID unless provided explicitly.
if [[ -z "$SOURCE_ID" ]]; then
  for candidate in "$SOURCE_USERNAME" "PRIMARY/$SOURCE_USERNAME"; do
    printf 'Looking up source user: %s\n' "$candidate"
    get_json "$TMP_DIR/search.json" "$USERS_URL" \
      --get --data-urlencode "filter=userName eq \"$candidate\"" \
      --data-urlencode 'startIndex=1' --data-urlencode 'count=10'
    found="$(jq '[.Resources[]?] | length' "$TMP_DIR/search.json")"
    if [[ "$found" == 1 ]]; then
      SOURCE_ID="$(jq -r '.Resources[0].id // empty' "$TMP_DIR/search.json")"
      break
    elif [[ "$found" != 0 ]]; then
      fail "More than one source user matched $candidate; specify SOURCE_ID explicitly"
    fi
  done
fi
[[ -n "$SOURCE_ID" ]] || fail "Cannot find ana.magalu. Set SOURCE_ID to Ana's SCIM user ID and rerun."

# Resolve the target dynamically: entryUUID can change after a fresh LDAP seed.
if [[ -z "$TARGET_ID" ]]; then
  get_json "$TMP_DIR/target-search.json" "$USERS_URL" \
    --get --data-urlencode 'domain=SELLERLDAP' \
    --data-urlencode "filter=userName eq \"$TARGET_USERNAME\"" \
    --data-urlencode 'startIndex=1' --data-urlencode 'count=10'
  [[ "$(jq '[.Resources[]?] | length' "$TMP_DIR/target-search.json")" == 1 ]] ||
      fail "Cannot resolve one LDAP user: $TARGET_USERNAME; specify TARGET_ID explicitly"
  TARGET_ID="$(jq -r '.Resources[0].id // empty' "$TMP_DIR/target-search.json")"
fi
[[ -n "$TARGET_ID" ]] || fail "Target SCIM ID is empty"
get_json "$TMP_DIR/source.json" "$USERS_URL/$SOURCE_ID"
get_json "$TMP_DIR/target.json" "$USERS_URL/$TARGET_ID"
source_name="$(jq -r '.userName // empty' "$TMP_DIR/source.json")"
target_name="$(jq -r '.userName // empty' "$TMP_DIR/target.json")"
[[ "$target_name" == "$TARGET_USERNAME" ]] || fail "Target user mismatch: expected $TARGET_USERNAME, got $target_name"
[[ "$source_name" == *"$SOURCE_USERNAME" ]] || fail "Source user mismatch: expected $SOURCE_USERNAME, got $source_name"
jq -e '.roles | type == "array"' "$TMP_DIR/source.json" >/dev/null || fail "Source SCIM user did not include a roles array"

printf 'Source: %s (%s)\n' "$source_name" "$SOURCE_ID"
printf 'Target: %s (%s)\n' "$target_name" "$TARGET_ID"
printf 'Mode: %s\n\n' "$MODE"

# Pin the bootstrap to the exact seven app/audience combinations from Ana's screenshot.
# Do NOT blindly copy any new roles Ana might receive later.
cat > "$TMP_DIR/expected.tsv" <<'ROLES'
poc_customer	MAGALU CIAM POC - MAGALU - WEB
poc_request_creator	MAGALU CIAM POC - MAGALU - APP
poc_request_creator	MAGALU CIAM POC - MAGALU - WEB
poc_request_creator	MAGALU CIAM POC - NETSHOES - APP
poc_request_creator	MAGALU CIAM POC - NETSHOES - WEB
poc_m3_ana_token_evidence	MAGALU CIAM POC - M3 - TOKEN EVIDENCE
poc_m3_ana_exchange_read	MAGALU CIAM POC - COMMERCE - M2M - EXCHANGE
ROLES

# Prevalidate ALL role references before making changes, so incorrect tenant,
# audience, or source role data doesn't result in partial unexpected grants.
: > "$TMP_DIR/assignment.tsv"
while IFS=$'\t' read -r role_name audience; do
  [[ -n "$role_name" ]] || continue
  role_ids="$(jq -r --arg name "$role_name" --arg audience "$audience" \
    '.roles[]? | select(.display == $name and .audienceDisplay == $audience and .audienceType == "application") | .value' \
    "$TMP_DIR/source.json")"
  role_count="$(printf '%s\n' "$role_ids" | sed '/^$/d' | wc -l | tr -d ' ')"
  [[ "$role_count" == 1 ]] || fail "Expected one match for [$role_name] [$audience] on Ana, found $role_count"
  role_id="$role_ids"
  get_json "$TMP_DIR/role.json" "$ROLES_URL/$role_id"
  jq -e --arg id "$role_id" --arg name "$role_name" --arg audience "$audience" \
    '.id == $id and .displayName == $name and .audience.type == "application" and (.audience.display == $audience)' \
    "$TMP_DIR/role.json" >/dev/null || fail "Role API returned a different role/audience for $role_name ($audience)"
  printf '%s\t%s\t%s\n' "$role_id" "$role_name" "$audience" >> "$TMP_DIR/assignment.tsv"
done < "$TMP_DIR/expected.tsv"

printf 'Validated seven role IDs and their audiences.\n\n'
while IFS=$'\t' read -r role_id role_name audience; do
  if jq -e --arg id "$role_id" '[.roles[]? | select(.value == $id)] | length > 0' \
      "$TMP_DIR/target.json" >/dev/null; then
    printf 'SKIP  %-28s %s (already assigned)\n' "$role_name" "$audience"
    continue
  fi

  if [[ "$APPLY" != true ]]; then
    printf 'PLAN  %-28s %s\n' "$role_name" "$audience"
    continue
  fi

  payload="$(jq -nc --arg id "$TARGET_ID" \
    '{schemas:["urn:ietf:params:scim:api:messages:2.0:PatchOp"],Operations:[{op:"add",path:"users",value:[{value:$id}]}]}')"
  code="$(curl -k -sS --user "$ADMIN_USER:$WSO2_PASSWORD" \
    -X PATCH -H 'Content-Type: application/scim+json' -H 'Accept: application/scim+json' \
    --data "$payload" -o "$TMP_DIR/patch-response" -w '%{http_code}' "$ROLES_URL/$role_id")" \
    || fail "Role PATCH failed: $role_name ($audience)"
  case "$code" in
    200|204) printf 'ADDED %-28s %s\n' "$role_name" "$audience" ;;
    *) echo "Role update response ($code):" >&2; head -c 1500 "$TMP_DIR/patch-response" >&2; echo >&2;
       fail "Could not assign $role_name ($audience)" ;;
  esac
done < "$TMP_DIR/assignment.tsv"

if [[ "$APPLY" == true ]]; then
  printf '\nVerifying target user roles...\n'
  get_json "$TMP_DIR/verified.json" "$USERS_URL/$TARGET_ID"
  missing=0
  while IFS=$'\t' read -r role_id role_name audience; do
    if jq -e --arg id "$role_id" '[.roles[]? | select(.value == $id)] | length > 0' \
        "$TMP_DIR/verified.json" >/dev/null; then
      printf 'OK    %-28s %s\n' "$role_name" "$audience"
    else
      printf 'CHECK %-28s %s (not yet shown by SCIM GET)\n' "$role_name" "$audience"
      missing=$((missing + 1))
    fi
  done < "$TMP_DIR/assignment.tsv"
  [[ "$missing" == 0 ]] || fail "$missing role(s) not visible in final target-user response"
  printf '\nAll seven application-role assignments verified.\n'
else
  printf '\nDry run only. Run with --apply to grant missing memberships.\n'
fi
