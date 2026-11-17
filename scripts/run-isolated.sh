#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./scripts/setup-isolated.sh
set -a; source .env; set +a
export HOST_UID="${HOST_UID:-$(id -u)}" HOST_GID="${HOST_GID:-$(id -g)}"
command -v docker >/dev/null || { echo 'Docker CLI is required' >&2; exit 1; }
docker info >/dev/null || { echo 'Docker daemon is not reachable' >&2; exit 1; }
# Isolate every resource under a project name unique to this PoC.
files=(-f compose.yaml -f compose.isolated.yaml)
name=magalu-ciam73-s7lab
[[ "${1:-}" != '--skip-bootstrap' && "${1:-}" != '--with-storefronts' && "${1:-}" != '' ]] && { echo 'Usage: ./scripts/run-isolated.sh [--skip-bootstrap|--with-storefronts]'; exit 2; }
./scripts/prepare-updated-image.sh
./scripts/prepare-identity-sql.sh
./scripts/generate-local-tls.sh
python3 scripts/prepare-wso2-config.py
docker compose -p "$name" "${files[@]}" up -d --build identity-db db sector demo is
printf "WSO2 public endpoint: %s\nDemo portal: %s\n" "$IS_PUBLIC_URL" "$DEMO_PUBLIC_URL"
if [[ "${1:-}" == '--skip-bootstrap' ]]; then
  exit 0
fi
printf 'Waiting for the independent WSO2 root server on port 9543...\n'
ready=0
for attempt in {1..90}; do
  if curl -ksf https://localhost:9543/oauth2/token/.well-known/openid-configuration >/dev/null; then
    ready=1; break
  fi
  sleep 5
done
if (( ready == 0 )); then
  echo 'WSO2 did not become ready. View logs:' >&2
  echo "docker compose -p $name -f compose.yaml -f compose.isolated.yaml logs --tail=150 is identity-db" >&2
  exit 1
fi
docker compose -p "$name" "${files[@]}" --profile tools run --rm bootstrap
# Smoke test is fail closed; a bootstrap alone is not a Section 7 PASS.
docker compose -p "$name" "${files[@]}" --profile tools run --rm bootstrap python -m scripts.smoke

if [[ "${1:-}" == '--with-storefronts' ]]; then
  echo "Provisioning six independent storefront clients..."

  docker compose -p "$name" "${files[@]}" \
    --profile tools run --rm bootstrap \
    python -m bootstrap.storefront_provision

  if [[ ! -s generated/storefront-manifest.json ]]; then
    echo "Storefront manifest missing; refusing to start storefronts." >&2
    exit 1
  fi

  echo "Starting six storefront containers..."

  docker compose -p "$name" "${files[@]}" \
    -f compose.frontends.yaml up -d --build \
    store-magalu-web \
    store-magalu-app \
    store-netshoes-web \
    store-netshoes-app \
    store-magalupay-web \
    store-magalupay-app

  docker compose -p "$name" "${files[@]}" \
    -f compose.frontends.yaml ps
fi
