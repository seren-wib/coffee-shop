## 2. 배포 절차

`main`에 머지하면 `.github/workflows/deploy.yml`이 배포한다(FR-61, SDD 11.4절). 사람이 하는 일은 PR 머지뿐이다. 처음 한 번은 3절 설치(3.6절 자동 배포 설정 포함)와 2.3절 수동 배포 한 번이 먼저다. 시연 시간에는 배포하지 않는다(재시작 중 수십 초 502). 그동안은 저장소 변수 `DEPLOY_ENABLED`를 `false`로 바꿔 둔다. (2026-11-27 변경. 이전에는 "운영자가 SSH로 서버에 들어가 한다"였고, 그 절차는 2.3절로 옮겼다)

1. GitHub: PR이 `main`에 머지되면 `ci`가 그 커밋으로 `backend`·`frontend`를 돌린다.
2. GitHub: `ci`가 성공하면 `deploy` 워크플로가 시작한다. 배포는 한 번에 하나만 돈다.
3. 워크플로가 GitHub OIDC로 AWS 배포 역할을 받는다(NFR-43). 못 받으면 태그를 달기 전에 멈춘다.
4. 워크플로가 그 커밋에 다음 태그를 달고 올린다. 날짜는 서울 기준이고 같은 날 두 번째면 `-2`다(NFR-39).
5. 워크플로가 SSM Run Command로 서버에서 `DEPLOY_BUILDER=ubuntu /srv/coffee-shop/current/deploy/deploy.sh <태그>`를 root로 실행하고 10초마다 결과를 본다. 끝나면 스크립트 출력을 실행 로그에 남긴다.
6. 스크립트가 하는 일은 아래 2.3절 4번과 같다.
7. 워크플로가 밖에서 `https://<도메인>/version.txt`를 읽어 그 커밋 7자인지 본다.
8. SSM 상태가 `Success`가 아니거나 7번이 다르면 실행이 실패로 끝난다. 실패한 실행은 Actions 목록에 남고, 실행 화면의 Re-run으로 새 번호 태그를 달아 다시 배포할 수 있다.
9. 4절 "릴리스마다" 항목을 확인한다.

### 2.1 멈추는 조건

- `deploy` 워크플로가 배포하지 않고 끝나는 경우(2026-11-27 추가): `ci`가 실패하거나 취소됐을 때, `DEPLOY_ENABLED`가 `true`가 아닐 때, `ci`가 끝난 커밋이 `main` 최신이 아닐 때(더 새 커밋의 실행이 배포), 그 커밋에 이미 릴리스 태그가 있을 때(`ci`를 다시 돌린 경우), 직전 릴리스 태그 뒤로 `docs/`와 `*.md`만 바뀌었을 때. 실행 화면에 이유가 notice로 남는다.
- 태그 형식이 `release-YYYYMMDD-N`이 아니거나, 그 커밋이 `main`에 없거나, 같은 릴리스 폴더가 이미 있으면 아무것도 바꾸지 않고 멈춘다.
- `pip install`, `npm ci`, `npm run build`, 백업, `migrate`, `check --deploy`가 실패하면 `current`를 바꾸기 전에 멈춘다. 서비스는 이전 릴리스로 계속 돈다.
- 링크를 바꾼 뒤 상태 확인이 실패하면 2.2의 1번을 스크립트가 직접 하고 실패로 끝난다.
- SSM 명령은 30분이 지나면 끊긴다. 그때 워크플로는 실패로 끝나고, 운영자가 서버에서 `current` 링크와 `/api/health/`를 확인한다. (2026-11-27 추가)

### 2.2 롤백

1. 링크 되돌리기: `current`를 직전 릴리스로 돌리고 `sudo systemctl restart coffee-shop`. 상태 확인 실패 때는 `deploy.sh`가 한다. 손으로 할 때는 다음 두 줄이다. 22번이 막힌 곳에서는 AWS 콘솔 Session Manager로 서버 셸을 열어 같은 명령을 친다(3.6절 인스턴스 역할 덕분, 2026-11-27 추가).

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
4. 롤백 리허설 1회가 FR-62, 복원 리허설 1회가 FR-63의 측정이다(STP 8절). (2026-11-27 변경. 이전에는 "롤백 리허설 1회가 NFR-24의 측정")

### 2.3 수동 배포 (2026-11-27 2절 첫 순서를 옮김)

- 자동 배포가 건너뛴 커밋을 올리거나 `DEPLOY_ENABLED`를 다시 켠 뒤 바로 배포할 때: GitHub Actions `deploy` → Run workflow(`main`). `main` 최신 커밋에 새 번호 태그를 달고 2절 순서대로 배포한다. 문서만 바뀌었어도 배포한다.
- GitHub Actions나 SSM을 쓸 수 없을 때, 그리고 3.6절 설정 전 첫 배포: 운영자가 SSH로 서버에 들어가 아래 순서로 한다.

1. 개발 PC: `main`의 배포할 커밋이 CI `backend`·`frontend` 통과인지 본다.
2. 개발 PC: 태그를 달고 올린다. 같은 날 두 번째면 `-2`.

   ```bash
   git tag release-YYYYMMDD-1 origin/main
   ```

   ```bash
   git push origin release-YYYYMMDD-1
   ```

3. 서버: `sudo /srv/coffee-shop/current/deploy/deploy.sh release-YYYYMMDD-1`. 첫 배포는 `current`가 없으므로 3.3절에서 받은 클론의 `deploy/deploy.sh`를 쓴다.
4. 스크립트가 하는 일(SDD 11.4절, 자동 배포도 같다):
   1. `releases/<태그>`에 태그를 클론하고, 그 커밋이 `main`에 있는지 본다.
   2. `.venv`를 만들고 `backend/requirements.txt`를 설치한다.
   3. `npm ci`, `VITE_APP_VERSION=<커밋 7자>`로 `npm run build`, `dist/version.txt`에 커밋을 쓴다.
   4. DB가 있으면 `/var/backups/coffee-shop/pre-deploy/db-<태그>.sqlite3`로 백업한다(최근 3개).
   5. `migrate`, `check --deploy --fail-level ERROR`.
   6. `current` 링크를 새 릴리스로 바꾸고 gunicorn 재시작, nginx 다시 읽기.
   7. 소켓으로 `/api/health/` 200(최대 30초), nginx가 내주는 `version.txt`가 이번 커밋인지 본다.
   8. 릴리스 폴더는 최근 3개만 남긴다.
5. 4절 "릴리스마다" 항목을 확인한다.
