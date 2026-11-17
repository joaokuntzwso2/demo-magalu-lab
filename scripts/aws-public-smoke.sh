#!/usr/bin/env bash
# Usage: ./scripts/aws-public-smoke.sh demo.example.com
# Test public pages + TLS + redirect locations. Does not use credentials.
set -euo pipefail
[[ $# -eq 1 ]] || { echo "Usage: $0 your-demo-domain.example" >&2; exit 2; }
domain="$1"
[[ "$domain" =~ ^[a-zA-Z0-9.-]+$ ]] || { echo 'Invalid domain' >&2; exit 2; }
command -v curl >/dev/null || { echo 'curl required' >&2; exit 2; }
failed=0
while IFS='|' read -r host path; do
  [[ -n "$host" ]] || continue
  url="https://${host}.${domain}${path}"
  # HTTP code, redirect target, TLS verify result, measured time, without body or cookies.
  result="$(curl --silent --show-error --max-time 18 --output /dev/null \
    --location --max-redirs 12 --proto-redir =https \
    --write-out '%{http_code}|%{url_effective}|%{ssl_verify_result}|%{time_total}' "$url")" || {
    echo "FAIL: cannot reach $url"; failed=1; continue;
  }
  IFS='|' read -r status final_url tls seconds <<< "$result"
  if [[ "$status" =~ ^(2|3)[0-9][0-9]$ && "$tls" == 0 && "$final_url" != *localhost* && "$final_url" != *127.0.0.1* ]]; then
    printf 'PASS %-75s HTTP %s / %ss\n' "$url" "$status" "$seconds"
  else
    printf 'FAIL %-75s HTTP %s / final_url=%s / tls=%s\n' "$url" "$status" "$final_url" "$tls"
    failed=1
  fi
done <<'ROUTES'
auth|/console
auth|/t/magalu.demo/console
auth|/t/magalupay.demo/console
lab|/lab
magalu-web|/
magalu-mobile|/
netshoes-web|/
netshoes-mobile|/
pay-web|/
pay-mobile|/
ROUTES
if (( failed )); then
  echo 'FAIL: investigate DNS, Caddy, backend health, HTTPS or localhost redirects.' >&2
  exit 1
fi
echo 'Public HTTP/TLS checks pass. Real interactive OIDC logins still require browser verification.'
