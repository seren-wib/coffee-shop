## 2. 디렉터리 구조

구현이 끝났을 때의 레포 구조다. `(예정)`은 2026-11-17 현재 레포에 없고 구현(텀프로젝트 마감 2026-11-30 24:00)에서 만드는 것이다. (2026-11-19 변경. 이전에는 출처 없는 날짜 2026-11-22) 2026-11-19에 스파이크(#73)와 CI(#77)로 생긴 파일을 반영했다. 테이블 정의의 원본은 모델과 마이그레이션이고 `backend/schema.sql`은 지운다(11.1절).

```
coffee-shop/
├── backend/
│   ├── manage.py
│   ├── requirements.txt          # 고정 버전 의존성 (NFR-19)
│   ├── requirements-dev.txt      # 개발·CI 전용(black). 운영 서버에는 설치하지 않음 (STP 1.3절)
│   ├── config/
│   │   ├── settings.py           # 환경 변수로 운영·개발을 가른다 (9절)
│   │   ├── test_settings.py      # 테스트 설정: 메모리 SQLite, 가짜 시크릿 (STP 1.2절)
│   │   ├── test_settings_file.py # 동시 주문 테스트용 파일 SQLite (NFR-15, STP 1.2절)
│   │   ├── urls.py               # /api/ 경로 묶음. /admin/은 DEBUG일 때만 (11.1절)
│   │   └── wsgi.py               # gunicorn 진입점
│   ├── common/                   # (예정) 앱 공통
│   │   ├── permissions.py        # IsAdminRole (NFR-10)
│   │   ├── pagination.py         # PageNumberPagination 20 (FR-1, 7.4절)
│   │   ├── exceptions.py         # 오류 응답 형식, 업무 예외 → 상태 코드 (7.2절)
│   │   └── views.py              # GET /api/health/ (FR-52)
│   ├── users/
│   │   ├── models.py             # User(커스텀 사용자 모델), UserAddress
│   │   ├── migrations/           # (예정) 테이블 정의 원본
│   │   ├── serializers.py        # (예정) 가입, 내 정보, 비밀번호, 배송지
│   │   ├── services.py           # (예정) 기본 배송지 규칙 (DR-16, DR-17)
│   │   ├── views.py              # (예정)
│   │   ├── urls.py               # (예정) /api/auth/, /api/me/
│   │   ├── management/commands/
│   │   │   └── create_admin.py   # (예정) 관리자 계정 생성 (FR-53)
│   │   └── tests/                # (예정) 테스트 이름 앞에 FR·NFR ID
│   ├── products/
│   │   ├── models.py             # Product, ProductOption, 열거형
│   │   ├── migrations/           # (예정)
│   │   ├── serializers.py        # (예정)
│   │   ├── services.py           # (예정) 재고 증감, 판매 상태 전환 (DR-5 ~ DR-7)
│   │   ├── queries.py            # (예정) customer_products(), 검색·필터 함수 (FR-1 ~ FR-5, FR-56)
│   │   ├── origins.py            # 원산지 고정 목록 (4.3.7)
│   │   ├── views.py              # 고객용 (4.3)
│   │   ├── admin_views.py        # 관리자용 (4.7)
│   │   ├── urls.py               # (예정) /api/products/, /api/admin/products/
│   │   ├── management/commands/
│   │   │   └── seed_demo.py      # 시연 데이터 100·50·500 (NFR-3)
│   │   └── tests/                # (예정)
│   └── orders/
│       ├── models.py             # CartItem, Order, OrderItem, Payment, 열거형
│       ├── migrations/           # (예정)
│       ├── serializers.py        # (예정)
│       ├── services.py           # (예정) 장바구니, 주문 생성, 상태 전환 (DR-9 ~ DR-21)
│       ├── order_number.py       # (예정) ORD-YYYYMMDD-NNN 생성 (DR-11)
│       ├── payments.py           # (예정) 결제 시작·확인·취소 (DR-22 ~ DR-24)
│       ├── pg.py                 # (예정) TossPaymentsClient, 테스트용 FakePaymentsClient
│       ├── couriers.py           # (예정) 택배사 목록과 조회 주소 (FR-35, 5.10절)
│       ├── views.py              # (예정) 회원용 + 관리자용
│       ├── urls.py               # (예정) /api/cart/, /api/orders/, /api/payments/, /api/admin/orders/
│       └── tests/                # (예정)
├── frontend/
│   ├── index.html
│   ├── package.json              # npm 스크립트: dev, build, lint(oxlint), test(vitest)
│   ├── .oxlintrc.json            # oxlint 설정 (NFR-29)
│   ├── .env.example              # (예정) VITE_ 변수 이름만 (9.2절)
│   ├── vite.config.js            # 개발 서버의 /api 프록시
│   └── src/
│       ├── main.jsx              # 라우터 장착
│       ├── App.jsx               # 라우트 표 (6.0절)
│       ├── api/
│       │   ├── client.js         # 하나뿐인 axios 인스턴스, 토큰 인터셉터 (NFR-31, FR-10)
│       │   ├── auth.js           # 경로 영역별 호출 함수. client.js만 쓴다
│       │   ├── products.js       # 4.3 원두 조회
│       │   ├── cart.js           # 4.4 장바구니
│       │   ├── orders.js         # (예정)
│       │   └── admin.js          # (예정)
│       ├── auth/                 # 토큰 저장소, RequireAuth·RequireAdmin 경로 보호
│       ├── components/           # 헤더, 가격 표시, 상태 배지, 페이지 버튼, 필드 오류
│       ├── pages/                # 화면 하나에 파일 하나, SCR ID 순서 (6절)
│       │   └── admin/            # (예정) SCR-11 ~ SCR-14
│       ├── lib/                  # 금액 형식(NFR-33), 상태 한국어 이름(NFR-30), 오류 문구
│       ├── test/                 # Vitest 설정(jsdom)과 테스트 도우미
│       └── index.css             # Tailwind 진입점, 디자인 토큰(@theme)
├── deploy/                       # 운영 설정 틀. 주소·키 값은 넣지 않는다 (SIP 3절)
│   ├── nginx/                    # 사이트 틀(coffee-shop.conf), 보안 헤더, 쿼리 뺀 로그 형식
│   ├── systemd/                  # gunicorn 서비스, 백업 서비스와 timer
│   ├── journald/                 # 로그 200MB 제한
│   ├── gunicorn.conf.py          # 소켓, 워커 3, 30초
│   ├── install.sh                # 처음 한 번: 패키지, 스왑, Node.js, 계정, 폴더, nginx, 단위 (SIP 3.3)
│   ├── cloudflare-real-ip.sh     # Cloudflare 대역 → set_real_ip_from
│   ├── deploy.sh                 # 릴리스 폴더, 의존성, 빌드, 백업, migrate, 링크 전환, 상태 확인 (10.4절)
│   └── backup.sh                 # sqlite3 .backup, 7개 남기기 (NFR-25)
├── spikes/                       # 설계 전 확인 코드, 스파이크 하나에 폴더 하나 (3절)
├── docs/
│   ├── images/                   # 문서 그림 (아키텍처, 와이어프레임)
│   └── specs/                    # 단계 문서 원본 (spmp, srs, sdd, stp, sip, smp)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                # backend, frontend 검사 (STP 7절)
│   │   └── docs-sync.yml         # main의 docs/specs → Google Docs
│   └── pull_request_template.md
├── .env.example                  # 환경 변수 이름만 (NFR-13, 9절)
├── .editorconfig, .gitattributes, .prettierrc, pyproject.toml   # 형식 규칙 (NFR-29)
├── CONTRIBUTING.md
└── README.md
```

### 2.1 폴더 규칙

| 규칙 | 이유 | 요구사항 |
| --- | --- | --- |
| 업무 규칙과 트랜잭션은 각 앱의 `services.py`에만 둔다. 뷰와 시리얼라이저는 서비스를 부른다 | 조건부 UPDATE와 트랜잭션 경계를 한 곳에서 검토하고 단위 테스트한다 | NFR-14, NFR-15 |
| 재고를 바꾸는 코드는 `products/services.py`의 `decrease_stock`, `increase_stock`, `set_stock` 셋뿐이다 | 판매 상태 자동 전환(DR-6, DR-7)이 빠지는 경로를 없앤다 | DR-5 ~ DR-7 |
| 외부 결제 호출은 `orders/pg.py`에만 둔다 | 테스트에서 가짜 클라이언트로 바꾼다 | FR-25 ~ FR-29 |
| 프론트엔드의 HTTP 요청은 `src/api/`의 함수만 보낸다. 그 함수들은 `client.js`만 쓴다 | 토큰 첨부와 재발급을 한 곳에서 한다 | NFR-31, FR-10 |
| 화면 컴포넌트는 `useState`와 props만 쓴다 | 상태 관리 라이브러리를 넣지 않는다 | NFR-32 |
| 테스트는 앱 안 `tests/`에 두고, 이름 앞에 요구사항 ID를 붙인다(`test_fr23_...`) | STP와 추적 | STP 1절 |
| `deploy/`의 파일에는 도메인, 서버 주소, 키 값을 쓰지 않고 환경 변수나 자리표시자로 둔다 | 레포가 공개다 | NFR-13 |
