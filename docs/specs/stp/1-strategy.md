## 1. 테스트 전략

구현은 TDD로 한다. 기능 하나는 실패하는 테스트로 시작하고, 그 테스트를 통과시키는 코드, 그다음 정리 순서로 간다. 브랜치 안의 커밋도 같은 순서다.

1. `test:` 실패하는 테스트. 이 커밋에서 새 테스트는 실패하고 나머지는 통과한다.
2. `feat:` 테스트를 통과시키는 코드.
3. `refactor:` 동작을 바꾸지 않는 정리(필요할 때만).

구현 커밋은 테스트 커밋 없이 들어가지 않는다. 브랜치 커밋은 스쿼시 머지로 하나가 되므로(CONTRIBUTING) 순서는 PR을 리뷰할 때 커밋 목록으로 확인한다.

테스트 이름은 다루는 요구사항 ID로 시작한다. ID가 없는 테스트, 테스트가 없는 FR·NFR은 빈칸으로 보고 PR 본문에 적는다.

- 백엔드: 메서드 이름 `test_<id>_<무엇을 확인하나>`, 소문자 ID. 여러 ID면 이어 쓴다. 예: `test_fr23_rejects_whole_cart_when_one_item_is_short`, `test_dr21_nfr15_restores_stock_once`.
- 프론트엔드: `it("FR-10 retries the original request once after refresh", ...)`처럼 대문자 ID를 문자열 앞에 쓴다.
- 파일은 앱 안 `tests/` 아래 영역별로 둔다(SDD 2절). 단위 테스트는 `test_<모듈>.py`, 통합 테스트는 `test_<영역>_api.py`, 프론트엔드는 대상 파일 옆 `<이름>.test.js(x)`.

### 1.1 계층

| 계층 | 도구 | 대상 | DB | 속도 |
| --- | --- | --- | --- | --- |
| 단위(백엔드) | Django 테스트 러너(`unittest`), `django.test.TestCase` | `services.py`, `order_number.py`, `couriers.py`, `payments.py`의 함수(2절) | 메모리 SQLite | 테스트 하나 수십 ms(목표, 안 쟀음) |
| 단위(프론트엔드) | Vitest | `src/lib/`, `src/auth/tokenStore.js`, `src/api/client.js` 인터셉터(2절) | 없음 | 테스트 하나 수 ms(목표) |
| API 통합 | DRF `APITestCase` + `APIClient` | `/api/` 경로마다 상태 코드, 응답 본문, 저장된 행(3절) | 메모리 SQLite, 테스트마다 롤백 | 백엔드 전체 1분 이내(목표) |
| 동시성 통합 | `TransactionTestCase` + 스레드 10개 | 마지막 재고 동시 주문(NFR-15) | 파일 SQLite(WAL, `IMMEDIATE`) | 테스트 하나 수 초(목표) |
| 화면 | Vitest + React Testing Library + jsdom | 화면 검증, 배너, 동의 칸(4절, 기능 단계에서 채움) | 없음. `src/api/`를 가짜로 바꿈 | 테스트 하나 수십 ms(목표) |
| 종단 | 사람이 Chrome으로 UC-1 ~ UC-14 수행 | 운영 환경 배포본(5절) | 운영 SQLite | 한 번 1시간 안팎(추정) |
| 정적 검사 | black, prettier, oxlint | 형식, 린트(NFR-29) | 없음 | 수 초 |
| 수동 | Chrome DevTools, `curl`, `openssl`, 외부 감시 | NFR-1, NFR-2, NFR-4, NFR-5, NFR-22 ~ NFR-25(9절) | 운영 | |

- 백엔드는 Django에 들어 있는 테스트 러너를 쓴다. pytest를 더하지 않는 이유: `requirements.txt`에 의존성이 늘지 않고, `APITestCase`·`TransactionTestCase`·`override_settings`가 그대로 있어서 필요한 기능이 모자라지 않는다.
- 프론트엔드는 Vitest를 쓴다. Vitest는 Vite 설정을 그대로 읽는 테스트 러너라 따로 변환 설정이 필요 없다(빌드 도구와 같은 설정, 유지보수성). 개발 의존성 `vitest`, `@testing-library/react`, `jsdom`을 더한다(정확한 버전으로 고정, NFR-19).
- 종단 테스트를 Playwright로 자동화하지 않는 이유: 마감(2026-11-30 24:00)까지 남은 기간에 브라우저 설치와 CI 실행 시간을 더할 여유가 없고, PG 결제창은 자동화 대상이 아니다. UC 수동 확인 결과는 9절 인수 체크리스트에 날짜와 함께 남긴다.

### 1.2 원칙

- 테스트에서 외부 호출 없음. 토스페이먼츠는 설정 `PAYMENTS_CLIENT`를 `orders.pg.FakePaymentsClient`로 바꿔 부르지 않는다(SDD 4.6.5). 가짜 클라이언트는 테스트가 정한 결과(승인 성공, 실패 코드, 다른 금액, 시간 초과, 이미 취소됨)를 돌려주고, 받은 호출(`confirm`, `cancel`의 인수)을 기록해서 테스트가 확인한다. 택배사는 링크만 만들므로(FR-35) 호출할 것이 없다. 메일은 보내지 않는다.
- 실제 토스 테스트 서버로 확인할 것(승인·취소 응답 형식, 중복 취소, 다른 금액 승인)은 테스트가 아니라 스파이크(SDD 3.2절)와 리허설(8절)에서 한다.
- 테스트 DB는 운영과 같은 SQLite 엔진이다. Django 테스트 러너가 메모리 SQLite에 마이그레이션을 전부 적용해 만들고, 테스트마다 트랜잭션을 롤백한다(SDD 9.5). 운영과 같은 제약(`Meta.constraints`, CHECK, 부분 유니크 인덱스)이 마이그레이션으로 들어가므로 제약 위반도 테스트에서 똑같이 난다.
- 메모리 DB에는 WAL과 파일 잠금이 없다. 그래서 동시 주문(NFR-15)만 파일 SQLite에 운영과 같은 옵션(`transaction_mode="IMMEDIATE"`, WAL, `timeout=20`, SDD 9.1)으로 따로 돌린다. 이 테스트는 `@tag("concurrency")`를 달고, 테스트 DB 이름(`DATABASES["default"]["TEST"]["NAME"]`)을 임시 파일로 바꾼 설정 `config/test_settings_file.py`에서만 돈다. 이 테스트의 기대값(성공 1, 재고 0, 잠금 오류 0)은 스파이크 `sqlite-concurrent-order`(SDD 3.1절) 결과와 같아야 한다.
- 시간은 고정한다. 백엔드는 `unittest.mock.patch("django.utils.timezone.now")`로 시각을 정한다(주문번호 날짜 DR-11, 자정 전후 Asia/Seoul). 프론트엔드는 `vi.useFakeTimers()`와 `vi.setSystemTime()`을 쓴다. 토큰 만료(NFR-8)는 기다리지 않고 만료 시각이 지난 토큰을 만들어 보낸다.
- 시크릿은 가짜 값만. 테스트 설정 `backend/config/test_settings.py`가 `SECRET_KEY`, `TOSS_SECRET_KEY`에 테스트 전용 문자열을 넣는다. CI에는 Actions 시크릿이 없다(7절).
- 테스트 설정은 `config/settings.py`를 가져온 뒤 다음만 바꾼다: `PAYMENTS_CLIENT = "orders.pg.FakePaymentsClient"`, `DEFAULT_THROTTLE_RATES`를 크게(로그인·가입 테스트가 429에 걸리지 않게, SDD 4.1.2), `PASSWORD_HASHERS`를 `MD5PasswordHasher`로(속도). 해시 형식을 보는 NFR-6 테스트만 `override_settings`로 운영 해셔(`PBKDF2PasswordHasher`)를 다시 쓴다.
- 테스트 데이터는 앱마다 `tests/factories.py`의 함수(`make_member()`, `make_product(options=...)`, `make_paid_order()`)로 만든다. factory_boy 같은 의존성은 더하지 않는다. 시연 데이터 명령(`seed_demo`)은 테스트에서 쓰지 않는다.
- 프론트엔드 테스트는 서버를 띄우지 않는다. `src/api/client.js` 테스트는 axios 인스턴스의 `adapter`를 가짜 함수로 바꿔 응답을 정한다. 화면 테스트는 `src/api/<영역>.js` 함수를 `vi.mock`으로 바꾼다.
- 테스트는 실행 순서와 상관없이 통과한다. 다른 테스트가 만든 행이나 전역 상태(`localStorage`)를 기대하지 않고, 프론트엔드는 `afterEach`에서 `localStorage.clear()`를 부른다.

### 1.3 명령

| 명령 | 내용 |
| --- | --- |
| `cd backend` 후 `python manage.py test --settings=config.test_settings --exclude-tag=concurrency` | 백엔드 단위·통합 테스트 전부(메모리 SQLite) |
| `python manage.py test users --settings=config.test_settings` | 앱 하나만. `orders.tests.test_orders_api` 같은 점 경로로 파일 하나만 |
| `python manage.py test --settings=config.test_settings_file --tag=concurrency` | 동시 주문 테스트만, 파일 SQLite(NFR-15) |
| `black --check backend` | 파이썬 형식(NFR-29) |
| `python manage.py makemigrations --check --dry-run --settings=config.test_settings` | 마이그레이션 빠짐 확인(7.1절) |
| `cd frontend` 후 `npm test` | 프론트엔드 단위·화면 테스트 한 번 실행(`vitest run`) |
| `npm run lint` | oxlint(NFR-29) |
| `npx prettier --check .` | 프론트엔드 형식(NFR-29) |
| `npm run build` | 운영 빌드가 되는지 |

- 백엔드 명령은 `backend/.venv`를 켠 뒤 실행한다. `black`은 개발 전용 `backend/requirements-dev.txt`에 둔다(운영 서버에는 설치하지 않음).
- `frontend/package.json`에 `"test": "vitest run"` 스크립트를 더한다. (2026-11-19 #77로 더했다)
