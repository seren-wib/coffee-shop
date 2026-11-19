#!/usr/bin/env bash
# First-time server setup on Ubuntu 24.04 (SIP 3.3). Safe to run again.
# Run from a clone of this repository: sudo deploy/install.sh
# Needs, before it runs: /srv/coffee-shop/.env (SDD 9.1) and the Cloudflare Origin CA
# certificate and key in /etc/nginx/ssl/. It does not deploy; run deploy.sh <tag> after it.
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "install: run with sudo" >&2; exit 1; }

here=$(cd "$(dirname "$0")" && pwd)
app=/srv/coffee-shop
env_file=$app/.env
cert=/etc/nginx/ssl/coffee-shop-origin.pem
key=/etc/nginx/ssl/coffee-shop-origin.key

echo "== packages"
apt-get update -q
DEBIAN_FRONTEND=noninteractive apt-get install -y -q nginx python3-venv sqlite3 git curl xz-utils

echo "== swap 1GiB (SDD 10.2)"
if ! swapon --show=NAME --noheadings | grep -qx /swapfile; then
  [ -f /swapfile ] || { fallocate -l 1G /swapfile; chmod 600 /swapfile; mkswap /swapfile; }
  swapon /swapfile
  grep -q '^/swapfile ' /etc/fstab || echo '/swapfile none swap sw 0 0' >>/etc/fstab
fi

echo "== Node.js 24 (build only, SDD 10.4)"
if ! node --version 2>/dev/null | grep -q '^v24\.'; then
  base=https://nodejs.org/dist/latest-v24.x
  sums=$(curl -fsS "$base/SHASUMS256.txt")
  file=$(echo "$sums" | awk '/linux-x64\.tar\.xz$/ {print $2}')
  tmp=$(mktemp -d)
  curl -fsS -o "$tmp/$file" "$base/$file"
  (cd "$tmp" && echo "$sums" | grep " $file\$" | sha256sum -c -)
  rm -rf /opt/node && mkdir -p /opt/node
  tar -xJf "$tmp/$file" -C /opt/node --strip-components=1
  rm -rf "$tmp"
  ln -sf /opt/node/bin/node /opt/node/bin/npm /opt/node/bin/npx /usr/local/bin/
fi
node --version

echo "== app account and folders (SDD 10.2)"
id coffee-shop >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin coffee-shop
usermod -aG coffee-shop www-data
install -d -m 755 $app $app/releases
install -d -m 750 -o coffee-shop -g coffee-shop $app/data /var/backups/coffee-shop /var/backups/coffee-shop/pre-deploy

echo "== .env"
if [ ! -f "$env_file" ]; then
  echo "install: $env_file is missing. Write it from .env.example (SIP 3.3) and run again." >&2
  exit 1
fi
chown coffee-shop:coffee-shop "$env_file"
chmod 600 "$env_file"
for name in SECRET_KEY ALLOWED_HOSTS SQLITE_PATH; do
  grep -Eq "^$name=.+" "$env_file" || { echo "install: $name is empty in $env_file" >&2; exit 1; }
done
grep -Eq '^DEBUG=False$' "$env_file" || { echo "install: set DEBUG=False in $env_file" >&2; exit 1; }
domain=$(sed -n 's/^ALLOWED_HOSTS=//p' "$env_file" | cut -d, -f1 | tr -d ' ')

echo "== journald"
install -D -m 644 "$here/journald/coffee-shop.conf" /etc/systemd/journald.conf.d/coffee-shop.conf
systemctl restart systemd-journald

echo "== nginx"
for f in "$cert" "$key"; do
  [ -f "$f" ] || { echo "install: $f is missing (Cloudflare Origin CA, SIP 3.2)" >&2; exit 1; }
done
chmod 600 "$key"
install -m 644 "$here/nginx/coffee-shop-log.conf" /etc/nginx/conf.d/coffee-shop-log.conf
install -m 644 "$here/nginx/coffee-shop-security-headers.conf" /etc/nginx/coffee-shop-security-headers.conf
"$here/cloudflare-real-ip.sh"
sed -e "s|__DOMAIN__|$domain|" -e "s|__ORIGIN_CERT__|$cert|" -e "s|__ORIGIN_KEY__|$key|" \
  "$here/nginx/coffee-shop.conf" >/etc/nginx/sites-available/coffee-shop
ln -sf /etc/nginx/sites-available/coffee-shop /etc/nginx/sites-enabled/coffee-shop
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "== systemd units"
install -m 644 "$here"/systemd/coffee-shop.service "$here"/systemd/coffee-shop-backup.service \
  "$here"/systemd/coffee-shop-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable nginx coffee-shop.service coffee-shop-backup.timer
systemctl reload nginx || systemctl start nginx

echo "install: done. Next: sudo deploy/deploy.sh <release tag> (SIP 2)"
