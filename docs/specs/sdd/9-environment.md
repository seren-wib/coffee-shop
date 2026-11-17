## 9. 환경과 시크릿

이름과 설정 위치만 적는다. 값은 적지 않는다(NFR-13). 백엔드는 레포 루트의 `.env`를 python-dotenv로 읽는다(`backend/config/settings.py`). 새 변수를 더하면 `.env.example`에 이름을 같이 더한다(CONTRIBUTING).

### 9.1 백엔드 (Django, 실행 때)

| 이름 | 종류 | 설정 위치 | 환경 | 쓰임 |
| --- | --- | --- | --- | --- |
| `SECRET_KEY` | 시크릿 | 개발: 각자 `.env` / 운영: EC2 `.env` | 개발, 운영 | JWT 서명, Django 서명. 없으면 서버가 뜨지 않는다 |
| `DEBUG` | 설정 | `.env` | 개발 `True`, 운영 `False` | NFR-12. `True`일 때만 `/admin/` URL을 붙인다(11.1절) |
| `ALLOWED_HOSTS` | 설정 | `.env`, 쉼표로 여러 개 | 개발 `localhost,127.0.0.1`, 운영 도메인(SRS 7.2 미결) | Host 헤더 검사 |
| `SQLITE_PATH` | 설정 | `.env` | 개발 기본 `backend/db.sqlite3`, 운영은 릴리스 폴더 밖의 데이터 폴더 | DB 파일 위치. 배포로 릴리스 폴더가 바뀌어도 DB는 그대로 |
| `TOSS_SECRET_KEY` | 시크릿 | `.env` | 개발, 운영(둘 다 테스트 키) | 토스페이먼츠 승인·취소 API Basic 인증(4.6.5) |
| `PAYMENTS_CLIENT` | 설정 | `.env`(없으면 `orders.pg.TossPaymentsClient`) | 테스트 설정은 `orders.pg.FakePaymentsClient` | 4.6.5 |
| `LOG_LEVEL` | 설정 | `.env`(없으면 `INFO`) | 개발, 운영 | 4.9.4 |

- 설정 파일 안에서 정하는 값(환경 변수 아님): `TIME_ZONE="Asia/Seoul"`, `USE_TZ=True`, `LANGUAGE_CODE="ko-kr"`, `AUTH_USER_MODEL`, `SIMPLE_JWT`, `REST_FRAMEWORK`(4.1.0), DB 옵션은 아래와 같다.

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("SQLITE_PATH", BASE_DIR / "db.sqlite3"),
        "OPTIONS": {
            "transaction_mode": "IMMEDIATE",   # 4.0절, 3.1절
            "timeout": 20,                     # 잠금 대기 초
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",  # 11.1절 WAL
        },
    }
}
```

- `ATOMIC_REQUESTS`는 켜지 않는다. IMMEDIATE 모드에서 켜면 읽기 요청까지 쓰기 잠금을 잡는다. 트랜잭션은 서비스 함수의 `transaction.atomic()`으로만 연다(4.0절).

### 9.2 프론트엔드 (Vite, 빌드 때)

Vite는 `VITE_`로 시작하는 변수만 빌드 결과에 넣는다. 빌드 결과는 브라우저에 그대로 보이므로 시크릿을 넣지 않는다.

| 이름 | 종류 | 설정 위치 | 환경 | 쓰임 |
| --- | --- | --- | --- | --- |
| `VITE_TOSS_CLIENT_KEY` | 공개 키 | 개발: `frontend/.env.local` / 운영: 배포 스크립트가 서버 `.env`에서 읽어 빌드에 넘김 | 개발, 운영(테스트 키) | 결제창 SDK 초기화(4.6.2) |
| `VITE_APP_VERSION` | 설정 | 배포 스크립트가 `git rev-parse --short HEAD`로 넣음 | 운영(개발은 `dev`) | 푸터 버전 표시(NFR-24, 6.0.1절) |

- `frontend/.env.local`은 `.gitignore` 대상이다. 레포에는 `frontend/.env.example`에 이름만 둔다.

### 9.3 서버 파일 (환경 변수가 아닌 시크릿·설정)

| 이름 | 종류 | 설정 위치 | 환경 |
| --- | --- | --- | --- |
| Cloudflare Origin CA 인증서·개인 키 | 시크릿 파일 | EC2 nginx 인증서 폴더, 권한 600 | 운영 |
| nginx 사이트 설정 | 설정 | 레포 `deploy/nginx/` 틀에서 도메인을 넣어 EC2에 둔다 | 운영 |
| systemd 단위(gunicorn, 백업 서비스·timer) | 설정 | 레포 `deploy/systemd/`를 EC2에 복사 | 운영 |
| SSH 개인 키 | 시크릿 파일 | 운영자 PC | 운영 |

### 9.4 외부 서비스 계정 (레포 밖)

| 서비스 | 쓰는 것 | 누가 관리 |
| --- | --- | --- |
| AWS | EC2 인스턴스, Elastic IP, 보안 그룹, EBS | 운영자 |
| Cloudflare | DNS 영역, 프록시, SSL/TLS 설정, Origin CA 인증서 발급 | 운영자 |
| 토스페이먼츠 개발자 센터 | 테스트 클라이언트 키, 테스트 시크릿 키 | 운영자 |
| GitHub | 레포. 지금은 Actions 시크릿 없음(CI 미도입, STP 7절) | 팀 |

계정 이름과 로그인 정보는 이 문서에 쓰지 않는다. 처음 한 번 하는 설정 절차는 SIP 3절이다.

### 9.5 환경 비교

| 항목 | 개발 | 테스트(자동) | 운영 |
| --- | --- | --- | --- |
| 실행 | `python manage.py runserver` + `npm run dev` | `python manage.py test` | gunicorn + nginx |
| DB | `backend/db.sqlite3` | 메모리 SQLite(테스트마다 새로) | `SQLITE_PATH`, WAL |
| PG | 토스 테스트 키 | `FakePaymentsClient` | 토스 테스트 키 |
| `DEBUG` | `True` | `False` | `False` |
| `/admin/` | 열림 | 없음 | 없음 |
| HTTPS | 없음(localhost) | 없음 | Cloudflare + Origin CA |
