#!/usr/bin/env bash
# Daily SQLite backup (SDD 11.5, NFR-25). Keeps the newest 7 files.
# `.backup` copies a consistent DB even in WAL mode; plain cp is not used.
set -euo pipefail

db=${SQLITE_PATH:-/srv/coffee-shop/data/db.sqlite3}
dir=${BACKUP_DIR:-/var/backups/coffee-shop}
keep=${BACKUP_KEEP:-7}
name="db-$(TZ=Asia/Seoul date +%Y%m%d).sqlite3"

sqlite3 -cmd ".timeout 20000" "$db" ".backup '$dir/$name'"
sqlite3 "$dir/$name" "PRAGMA quick_check;" | grep -qx ok

ls -1 "$dir"/db-*.sqlite3 | sort -r | tail -n +"$((keep + 1))" | xargs -r rm -f
echo "backup: $dir/$name ($(stat -c %s "$dir/$name") bytes), $(ls -1 "$dir"/db-*.sqlite3 | wc -l) kept"
