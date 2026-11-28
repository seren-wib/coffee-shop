## 4. 설치 테스트

### 4.1 첫 배포 직후

- ☐ `curl -I http://<도메인>/` → 301 또는 308, `Location`이 `https://`(NFR-4)
- ☐ `curl https://<도메인>/api/health/` → 200 `{"status": "ok"}`(FR-52)
- ☐ 없는 경로 `https://<도메인>/api/nope/` → 404 JSON, 본문에 파일 경로·`Traceback` 없음(NFR-12)
- ☐ `https://<도메인>/admin/` → 화면(SPA `index.html`)이고 Django 관리 화면이 아님. nginx는 `/api/`만 gunicorn으로 넘기고, Django 관리 경로는 `DEBUG=False`라 없다(SDD 12.1)
- ☐ 응답 헤더에 CSP, `X-Content-Type-Options: nosniff`, `Referrer-Policy`(SDD 9.6)
- ☐ 서버에서 `ss -ltn`: 443과 22만 바깥에 열림. gunicorn은 유닉스 소켓뿐
- ☐ `sudo -u coffee-shop sqlite3 /srv/coffee-shop/data/db.sqlite3 "PRAGMA journal_mode;"` → `wal`
- ☐ `seed_demo` 뒤 NFR-1: 원두 목록·검색·필터 경로 각각 20회, 서버 응답 시간 p95 500 ms 이하(NFR-3 데이터). 잰 명령과 값은 5절
- ☐ 결제 끈 상태: `POST /api/orders/{id}/payments/` → 503 `PAYMENTS_DISABLED`
- ☐ `sudo reboot` 뒤 5분 안에 `/api/health/` 200, 손으로 친 명령 0회(NFR-22)
- ☐ `sudo systemctl start coffee-shop-backup` 뒤 `/var/backups/coffee-shop/`에 오늘 파일 하나, 복원 리허설 1회(NFR-25, STP 8절)
- ☐ `journalctl -u coffee-shop`과 nginx 접근 로그에 쿼리 문자열, 토큰, 연락처 0건(NFR-35)

### 4.2 릴리스마다

- ☐ `deploy` 워크플로 실행 성공, 실행 요약에 태그와 커밋(자동 배포, 2026-11-27 추가)
- ☐ `deploy.sh`가 "done: <태그> (<커밋>), health 200"으로 끝남
- ☐ `https://<도메인>/version.txt`와 화면 푸터 버전이 태그 커밋과 같음(NFR-24)
- ☐ `/api/health/` 200, 원두 목록 화면이 열림

### 4.3 결제를 켠 뒤 (3.4절)

- ☐ 토스 테스트 카드로 결제 → 결제 완료 화면, 주문 `PAID`
- ☐ 관리자 취소 승인 → 주문 `CANCELLED`, 토스 개발자 센터 결제 내역 취소
