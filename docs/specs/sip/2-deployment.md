## 2. 배포 절차

운영자가 SSH로 서버에 들어가 한다. 처음 한 번은 3절 설치가 먼저다. 시연 시간에는 배포하지 않는다(재시작 중 수십 초 502).

1. 개발 PC: `main`의 배포할 커밋이 CI `backend`·`frontend` 통과인지 본다.
2. 개발 PC: 태그를 달고 올린다. 같은 날 두 번째면 `-2`.

   ```bash
   git tag release-YYYYMMDD-1 origin/main
   ```

   ```bash
   git push origin release-YYYYMMDD-1
   ```

3. 서버: `sudo /srv/coffee-shop/current/deploy/deploy.sh release-YYYYMMDD-1`. 첫 배포는 `current`가 없으므로 3.3절에서 받은 클론의 `deploy/deploy.sh`를 쓴다.
4. 스크립트가 하는 일(SDD 10.4절):
   1. `releases/<태그>`에 태그를 클론하고, 그 커밋이 `main`에 있는지 본다.
   2. `.venv`를 만들고 `backend/requirements.txt`를 설치한다.
   3. `npm ci`, `VITE_APP_VERSION=<커밋 7자>`로 `npm run build`, `dist/version.txt`에 커밋을 쓴다.
   4. DB가 있으면 `/var/backups/coffee-shop/pre-deploy/db-<태그>.sqlite3`로 백업한다(최근 3개).
   5. `migrate`, `check --deploy --fail-level ERROR`.
   6. `current` 링크를 새 릴리스로 바꾸고 gunicorn 재시작, nginx 다시 읽기.
   7. 소켓으로 `/api/health/` 200(최대 30초), nginx가 내주는 `version.txt`가 이번 커밋인지 본다.
   8. 릴리스 폴더는 최근 3개만 남긴다.
5. 4절 "릴리스마다" 항목을 확인한다.

### 2.1 멈추는 조건

- 태그 형식이 `release-YYYYMMDD-N`이 아니거나, 그 커밋이 `main`에 없거나, 같은 릴리스 폴더가 이미 있으면 아무것도 바꾸지 않고 멈춘다.
- `pip install`, `npm ci`, `npm run build`, 백업, `migrate`, `check --deploy`가 실패하면 `current`를 바꾸기 전에 멈춘다. 서비스는 이전 릴리스로 계속 돈다.
- 링크를 바꾼 뒤 상태 확인이 실패하면 2.2의 1번을 스크립트가 직접 하고 실패로 끝난다.

### 2.2 롤백

1. 링크 되돌리기: `current`를 직전 릴리스로 돌리고 `sudo systemctl restart coffee-shop`. 상태 확인 실패 때는 `deploy.sh`가 한다. 손으로 할 때는 다음 두 줄이다.

   ```bash
   sudo ln -sfn /srv/coffee-shop/releases/<직전 태그> /srv/coffee-shop/current
   ```

   ```bash
   sudo systemctl restart coffee-shop
   ```

2. DB 복원(이번 배포에 데이터를 바꾸는 마이그레이션이 있었을 때만): 서비스를 멈추고 배포 직전 백업을 덮어쓴 뒤 다시 켠다.

   ```bash
   sudo systemctl stop coffee-shop
   ```

   ```bash
   sudo -u coffee-shop sqlite3 /srv/coffee-shop/data/db.sqlite3 ".restore '/var/backups/coffee-shop/pre-deploy/db-<태그>.sqlite3'"
   ```

   ```bash
   sudo systemctl start coffee-shop
   ```

3. 4절 "릴리스마다" 항목을 다시 확인하고, 실패한 태그와 원인을 WORK 기록에 남긴다.
4. 롤백 리허설 1회가 NFR-24의 측정이다(STP 8절).
