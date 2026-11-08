# 6. 비기능 요구사항 설계

`requirements.md` 1.2절의 비기능 요구사항마다 이를 만족시키는 설계 수단과 적용 위치를 정리한다. 설계 수단은 기존 설계 문서에 정의된 것만 사용한다.

| 구분 | 요구사항 | 설계 수단 | 적용 위치 |
|---|---|---|---|
| 실행 환경 | 로컬 PC에서만 실행, 배포 안 함 | Vite 개발 서버(`:5173`)와 Django 서버(`:8000`) 두 프로세스를 로컬에서 실행 | `system-architecture.md`, `architecture.md` |
| 실행 환경 | React(Vite), Django + DRF, SQLite | 기술 스택 고정, DB는 `backend/db.sqlite3` 파일 하나 | `tech-stack.md`, `architecture.md` |
| 실행 환경 | Python 3.12, Node.js 24, Windows·macOS 같은 절차 | 버전 고정, OS별 명령만 다른 단일 설치 절차 | `tech-stack.md`, `README.md` Setup |
| 실행 환경 | 최신 Chrome에서 동작 | 시연·검증 브라우저를 Chrome으로 고정 | `external-interfaces.md` SW-06 |
| 실행 환경 | REST API·JSON으로만 통신 | 브라우저 → Vite `/api` 프록시 → DRF, 응답은 JSON | `architecture.md`, `vite.config.js` |
| 보안 | 비밀번호 8자 이상, 해시 저장 | `register`·`change_password`에서 8자 검증 후 PBKDF2-SHA256 해시(`make_password`) | `User` (ALG-06), `users.password_hash` |
| 보안 | JWT 인증, 로그인 필요 기능 보호 | DRF 기본 인증 `JWTAuthentication`, `IsAuthenticated` 권한 | `architecture.md` Back-end |
| 보안 | 액세스 토큰 자동 재발급 | 401 응답 시 `/api/token/refresh/` 호출 후 원 요청 1회 재시도, 실패 시 로그인 화면 | `client.js` 인터셉터, `sequence-algorithms.md` 1절 |
| 보안 | 본인 데이터만 조회·수정 | 장바구니·배송지·주문 쿼리를 요청 회원으로 필터링, 타인 객체는 404 | `architecture.md` Access control |
| 보안 | 관리 기능은 관리자만 | `role = ADMIN`만 허용하는 권한 클래스, 그 외 403 | `architecture.md` Access control, `Role` |
| 보안 | 결제 수단 정보 미저장 | `payments`에 카드 정보 컬럼 없이 PG 거래번호 `pg_tid`(UK)만 저장 | `Payment`, `table-specification.md` 3.8 |
| 보안 | 결제 금액 검증 | `process_payment`에서 결제 금액과 `final_payment_amt` 비교, 다르면 PG 환불(`CANCELLED`) | `Payment.process_payment` |
| 보안 | 민감 설정값 분리 | `SECRET_KEY`·`DEBUG`를 `.env`에서 python-dotenv로 읽고 `.env.example`만 커밋 | `architecture.md`, `CONTRIBUTING.md` |
| 데이터 정확성 | 주문 생성·재고 차감 원자성 | 단일 트랜잭션, 한 품목이라도 실패하면 전체 롤백 | `Order.create_order` (ALG-01) |
| 데이터 정확성 | 동시 주문에도 재고 음수 금지 | 조건부 UPDATE `WHERE stock_quantity >= quantity`, `CHECK(stock_quantity >= 0)` | `ProductOption.decrease_stock` (ALG-04) |
| 데이터 정확성 | 품절·판매 중지 서버 재확인 | 주문 생성 시 판매 상태와 재고를 서버에서 다시 검증 | `Order.create_order` (ALG-01) |
| 데이터 정확성 | 정해진 순서로만 상태 전환 | 상태 전이 매트릭스 외 전환 거부, 현재 상태를 조건으로 거는 조건부 UPDATE | `method-algorithms.md` 3절, ALG-02·03·05 |
| 데이터 정확성 | 주문 있는 회원 삭제 방지 | `orders.user_id` FK `RESTRICT` | `table-specification.md` 3.6 |
| 데이터 정확성 | 기존 주문 내역 불변 | 상품명·옵션·단가를 `OrderItem`에, 배송지를 `Order`에 스냅샷 저장 | `OrderItem`, `Order` |
| 성능 | 목록·검색·필터 2초 이내 | `idx_products_name`, `idx_products_filter` 인덱스 | `table-specification.md` 4절 |
| 성능 | 원두 목록 20개씩 | DRF `PageNumberPagination`, 페이지 크기 20 | `architecture.md` Access control and paging |
| 성능 | 원두 100종·회원 50명 규모 | 위 인덱스와 페이지 단위 조회로 조회량 제한 | `table-specification.md` 4절 |
| 사용성 | 한국어 문구, 원 단위 천 단위 쉼표 | 금액은 원 단위 정수(INT)로 저장·전달하고 화면에서 쉼표 형식으로 표시 | `table-specification.md`, SCR-01·02·05~08 |
| 사용성 | 품절 옵션 표시, 장바구니 담기 차단 | `is_available`·`sales_status`로 판별해 상세 화면에서 품절 표시 | `ProductOption.is_available`, SCR-02, SEQ-03 |
| 사용성 | 실패 사유 메시지 | 입력값 사전 검증, 요청 실패 시 오류 사유 안내와 재시도 제공 | `sequence-algorithms.md` 1절 |
| 유지보수성 | black·prettier·oxlint | 포매터·린터 설정 파일 커밋 | `tech-stack.md` |
| 유지보수성 | `useState`·props만 사용 | 상태 관리 라이브러리 금지 | `tech-stack.md` |
| 유지보수성 | 공통 axios 인스턴스 | `frontend/src/api/client.js` 하나만 사용 | `tech-stack.md`, `client.js` |
| 유지보수성 | 이슈·브랜치·PR로 변경 | GitHub Flow, 스쿼시 머지 | `CONTRIBUTING.md` |
| 유지보수성 | 코드 영어, 제출 문서 한국어 | 언어 규칙 명시 | `CONTRIBUTING.md` Language |
