#!/usr/bin/env bash
# Deploy one release tag (SDD 11.4, SIP 2). Usage: sudo deploy/deploy.sh release-YYYYMMDD-N
# Run by .github/workflows/deploy.yml through SSM after CI passes on main, or by the operator with sudo.
# On a failed health check the previous release comes back.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "deploy: run with sudo" >&2; exit 1; }
tag=${1:-}
[[ "$tag" =~ ^release-[0-9]{8}-[0-9]+$ ]] || { echo "usage: deploy.sh release-YYYYMMDD-N" >&2; exit 2; }

repo=${REPO_URL:-https://github.com/seren-wib/coffee-shop.git}
app=/srv/coffee-shop
rel=$app/releases/$tag
env_file=$app/.env
[ -f "$env_file" ] || { echo "deploy: $env_file is missing (SIP 3.3)" >&2; exit 1; }
db=$(sed -n 's/^SQLITE_PATH=//p' "$env_file")
domain=$(sed -n 's/^ALLOWED_HOSTS=//p' "$env_file" | cut -d, -f1 | tr -d ' ')
builder=${DEPLOY_BUILDER:-${SUDO_USER:-root}}  # build as the operator, not as root or the app account (SSM runs as root)
previous=$(readlink -e $app/current || true)  # -e: empty on the first deploy, not the link path
started=$(date +%s)

step() { echo "== $(($(date +%s) - started))s $*"; }
as_app() { sudo -u coffee-shop env DOTENV_PATH="$env_file" "$@"; }
as_builder() { sudo -u "$builder" "$@"; }

step "checkout $tag"
[ -e "$rel" ] && { echo "deploy: $rel already exists" >&2; exit 1; }
install -d -o "$builder" "$rel"
as_builder git clone -q --branch "$tag" "$repo" "$rel"
as_builder git -C "$rel" merge-base --is-ancestor HEAD origin/main \
  || { echo "deploy: $tag is not on main" >&2; rm -rf "$rel"; exit 1; }
commit=$(git -C "$rel" rev-parse --short=7 HEAD)

step "backend venv"
as_builder python3 -m venv "$rel/.venv"
as_builder "$rel/.venv/bin/pip" install -q --disable-pip-version-check -r "$rel/backend/requirements.txt"

step "frontend build ($commit)"
toss_client_key=$(sed -n 's/^VITE_TOSS_CLIENT_KEY=//p' "$env_file")
(cd "$rel/frontend" && as_builder npm ci --no-audit --no-fund --loglevel=error \
  && as_builder env VITE_APP_VERSION="$commit" VITE_TOSS_CLIENT_KEY="$toss_client_key" npm run build)
echo "$commit" >"$rel/frontend/dist/version.txt"  # what nginx serves is checked below
chown -R root:root "$rel"

step "pre-deploy backup"
if [ -f "$db" ]; then
  as_app sqlite3 -cmd ".timeout 20000" "$db" ".backup '/var/backups/coffee-shop/pre-deploy/db-$tag.sqlite3'"
  ls -1t /var/backups/coffee-shop/pre-deploy/db-*.sqlite3 | tail -n +4 | xargs -r rm -f
fi

step "migrate"
(cd "$rel/backend" && as_app "$rel/.venv/bin/python" manage.py migrate --noinput \
  && as_app "$rel/.venv/bin/python" manage.py check --deploy --fail-level ERROR)

step "switch current"
ln -sfn "$rel" $app/current.new
mv -T $app/current.new $app/current
systemctl restart coffee-shop
nginx -t && systemctl reload nginx

step "health check"
ok=0
for _ in $(seq 1 15); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --unix-socket /run/coffee-shop/gunicorn.sock \
    -H "Host: $domain" -H "X-Forwarded-Proto: https" http://localhost/api/health/ || true)
  [ "$code" = 200 ] && { ok=1; break; }
  sleep 2
done
served=$(curl -sk --resolve "$domain:443:127.0.0.1" "https://$domain/version.txt" || true)
[ "$served" = "$commit" ] || ok=0

if [ "$ok" != 1 ]; then
  echo "deploy: health check failed (last code ${code:-none}) or nginx serves version ${served:-none}, not $commit" >&2
  if [ -n "$previous" ] && [ "$previous" != "$rel" ]; then
    ln -sfn "$previous" $app/current.new && mv -T $app/current.new $app/current
    systemctl restart coffee-shop
    echo "deploy: rolled back to $(basename "$previous"). If migrate changed data, restore" >&2
    echo "        /var/backups/coffee-shop/pre-deploy/db-$tag.sqlite3 (SIP 2.2)." >&2
  fi
  exit 1
fi

step "prune releases (keep 3)"
ls -1dt $app/releases/release-* | tail -n +4 | xargs -r rm -rf

step "done: $tag ($commit), health 200"
