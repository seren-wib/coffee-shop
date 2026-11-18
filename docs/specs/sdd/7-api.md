## 7. API 설계 규칙

경로 목록은 SRS 6.2절이고, 경로마다의 입력·응답은 4절 각 소절이다. 이 절은 모든 경로에 똑같이 적용하는 규칙을 정한다.

### 7.1 공통

| 항목 | 규칙 | 요구사항 |
| --- | --- | --- |
| 형식 | 요청·응답 본문은 JSON(UTF-8). 응답 `Content-Type: application/json`. 상태 확인과 오류 응답도 JSON | NFR-28 |
| 경로 | 모두 `/api/` 아래, 끝에 `/`를 붙인다. 자원은 복수형 명사(`/orders/`), 상태 전환은 동사 하위 경로(`/orders/{id}/cancel/`) | SRS 6.2 |
| 메서드 | 조회 `GET`, 만들기와 상태 전환 `POST`, 일부 수정 `PATCH`, 삭제 `DELETE`. `PUT`은 쓰지 않는다 | |
| 필드 이름 | `snake_case`. 응답의 상태 필드는 `status`(DB 열 `order_status`, `payment_status`를 시리얼라이저가 바꿔 부른다). 토스페이먼츠에서 그대로 받는 `paymentKey`, `orderId`만 예외 | FR-23, FR-25 |
| 금액 | 원 단위 정수. 소수와 문자열 금액을 쓰지 않는다 | DR-13 |
| 시각 | ISO 8601, `+09:00` 오프셋(`TIME_ZONE="Asia/Seoul"`) | 11.1절 |
| 열거형 | 5.0.2절의 영어 대문자 코드. 한국어 이름은 화면이 바꾼다 | NFR-30 |
| ID | 주문은 주문번호 문자열(`ORD-...`), 나머지는 정수 | DR-11 |

### 7.2 검증과 오류 형식

입력 검증은 DRF 시리얼라이저가, 업무 규칙 검증은 서비스 함수가 한다. 어느 쪽에서 나든 응답은 아래 한 가지 모양이다. `common/exceptions.py`의 `api_exception_handler`가 DRF 예외와 `DomainError`를 이 모양으로 바꾼다.

```json
{
  "code": "VALIDATION_ERROR",
  "message": "입력값을 확인해 주세요.",
  "fields": {
    "password": ["비밀번호는 8자 이상이어야 합니다."]
  },
  "details": {}
}
```

- `code`: 영어 대문자 오류 코드. 화면이 분기에 쓴다.
- `message`: 화면에 그대로 보일 한국어 문장(NFR-30, NFR-34).
- `fields`: 400일 때만. 입력 필드 이름 → 한국어 메시지 배열. 화면은 칸 아래에 보인다(6.0.2절).
- `details`: 필요할 때만. 예: 재고 부족 항목 `{"cart_item_ids": [7, 9]}`.
- 응답에 스택 트레이스, SQL, 파일 경로, 설정값을 넣지 않는다. 처리하지 못한 예외는 500 `{"code": "SERVER_ERROR", "message": "일시적인 오류가 발생했습니다."}`이고 자세한 내용은 서버 로그에만 남는다(NFR-12).
- DRF 뷰에 닿지 않는 오류도 같은 모양이다. `config/urls.py`에 `handler404 = "common.views.json_404"`, `handler500 = "common.views.json_500"`을 두어 `/api/` 아래 없는 경로는 JSON 404, 뷰 밖 예외는 JSON 500이다(NFR-12, NFR-28). `/api/` 밖의 없는 경로는 nginx가 `index.html`(200)을 주고 화면의 `NotFoundPage`가 보인다(10.3절). 그래서 NFR-12의 "없는 경로 404" 측정은 `/api/` 경로로 한다.
- 예외 하나: 상태 확인(`GET /api/health/`)은 FR-52가 정한 `{"status": "ok"}` 모양을 지키려고 503도 `{"status": "unavailable"}`로 답한다(4.9.1).

| 상태 코드 | `code` | 언제 | 예 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 형식, 필수 값, 범위 | 7자 비밀번호(FR-7), 수량 0(FR-21), 음수 추가 금액(FR-39) |
| 400 | `EMPTY_CART` | 주문할 항목 없음 | FR-23 |
| 401 | `NOT_AUTHENTICATED` | 토큰 없음·만료 | NFR-9, FR-10 |
| 401 | `INVALID_CREDENTIALS` | 로그인 실패(이메일 없음, 비밀번호 틀림 같은 본문) | FR-8, NFR-7 |
| 401 | `INVALID_TOKEN` | 리프레시 토큰 만료·위조 | FR-9 |
| 402 | `PAYMENT_FAILED` | PG 승인 실패 | FR-28 |
| 403 | `PERMISSION_DENIED` | 회원 토큰으로 관리자 경로 | NFR-10 |
| 404 | `NOT_FOUND` | 없는 객체, 다른 회원의 객체, 판매 중지 원두 상세 | NFR-11, FR-6 |
| 409 | `OUT_OF_STOCK` | 재고 부족 | FR-19, FR-21, FR-23 |
| 409 | `NOT_AVAILABLE` | 품절·판매 중지 원두 | FR-19, NFR-16 |
| 409 | `INVALID_STATE` | 전환표에 없는 상태 전환 | DR-19, FR-32, FR-33, FR-47 |
| 409 | `ALREADY_PAID` | 성공 결제가 있는 주문의 재결제 | FR-29 |
| 409 | `PAYMENT_MISMATCH`, `ORDER_NOT_PENDING` | 승인됐지만 금액 불일치·주문 취소됨(PG 취소함) | FR-27 |
| 409 | `DUPLICATE_OPTION` | 같은 용량·분쇄도 옵션 | FR-39 |
| 409 | `DEFAULT_ADDRESS_DELETE` | 배송지 둘 이상일 때 기본 배송지 삭제 | FR-17 |
| 409 | `RETRY` | 주문번호 충돌 등 다시 하면 되는 경합 | 4.5.2 |
| 429 | `THROTTLED` | 요청 제한 초과 | 8.3절 |
| 502 | `PG_ERROR` | PG 호출 실패. 승인 시간 초과(결제는 `READY` 유지), 취소 실패 | FR-26, FR-50 |
| 503 | `ORDER_LIMIT` | 하루 주문 수 초과 | DR-11 |

- 404와 403의 구분: 회원 경로에서 남의 객체는 403이 아니라 404다. 객체가 있다는 사실도 알려주지 않으려는 것이다(NFR-11). 관리자 경로에 회원 토큰은 403이다(NFR-10).
- 400과 409의 구분: 요청만 보고 틀린 걸 알 수 있으면 400, 지금 서버 상태와 부딪치면 409다.

### 7.3 경로 묶음별 인증

| 묶음 | 경로 | 인증 | 권한 클래스 | 요구사항 |
| --- | --- | --- | --- | --- |
| 공개 | `GET /api/health/`, `POST /api/auth/register/`, `POST /api/auth/token/`, `POST /api/auth/token/refresh/`, `GET /api/products/`, `GET /api/products/{id}/` | 없음 | `AllowAny` | NFR-9 |
| 회원 | `/api/me/...`, `/api/cart/...`, `/api/orders/...`, `/api/payments/...` | Bearer 액세스 토큰 | `IsAuthenticated`(기본값) + 소유자 필터 | NFR-9, NFR-11 |
| 관리자 | `/api/admin/...` | Bearer 액세스 토큰 | `IsAuthenticated` + `IsAdminRole` | NFR-10 |

- 기본 권한이 `IsAuthenticated`라서 새 뷰가 권한 설정을 빠뜨려도 공개되지 않는다. 공개 경로만 명시적으로 연다.
- 테스트: 공개 목록 밖의 모든 경로에 토큰 없이 요청하면 401인지 URL 설정을 돌며 확인하는 테스트 하나를 둔다(NFR-9, STP 3절).
- 개인정보 처리방침(`/privacy`, FR-59)과 고지 배너(NFR-36)는 화면에만 있고 API 경로가 없다(2026-11-19 추가).
- 세션 인증과 CSRF는 쓰지 않는다. 브라우저가 쿠키를 자동으로 붙이는 인증이 없으므로 CSRF 공격 대상이 없다. 개발 환경 `/admin/`만 Django 세션을 쓴다.

### 7.4 페이지네이션

```python
class StandardPagination(PageNumberPagination):
    page_size = 20               # FR-1
    page_size_query_param = None # 크기는 바꾸지 못한다
    max_page_size = 20
```

```json
{
  "count": 137,
  "next": "/api/products/?page=3&roast_level=LIGHT",
  "previous": "/api/products/?page=1&roast_level=LIGHT",
  "results": []
}
```

- 쓰는 곳: 원두 목록(FR-1), 내 주문 목록(FR-30), 관리자 원두 목록(FR-36), 관리자 주문 목록(FR-44).
- 안 쓰는 곳: 배송지 목록, 장바구니(회원 한 명 분이라 적다).
- `next`, `previous`는 도메인을 뺀 경로로 준다. 프록시 뒤에서 내부 주소가 새지 않게 한다.
- 범위 밖 페이지는 404 `NOT_FOUND`. 화면은 1페이지로 돌아간다.

### 7.5 정렬과 필터 매개변수

| 경로 | 매개변수 | 정렬 |
| --- | --- | --- |
| `GET /api/products/` | `search`, `origin`, `min_price`, `max_price`, `roast_level`, `page` | 최근 등록 순 |
| `GET /api/orders/` | `status`, `page` | `created_at` 내림차순(FR-30) |
| `GET /api/admin/products/` | `search`, `sales_status`, `page` | 최근 등록 순 |
| `GET /api/admin/orders/` | `search`, `status`, `page` | `created_at` 내림차순(FR-44) |

- 모르는 매개변수는 무시한다. 아는 매개변수의 값이 틀리면 400이다.
- 정렬을 바꾸는 매개변수(`ordering`)는 두지 않는다.

### 7.6 버전

- 경로에 버전(`/api/v1/`)을 넣지 않는다. 화면과 API를 한 레포에서 같은 커밋으로 함께 배포하므로 옛 클라이언트가 남지 않는다(10절).
- 응답 필드를 지우거나 이름을 바꿀 땐 같은 PR에서 화면과 이 문서(4절)를 함께 고친다.

### 7.7 SRS 6.2에 없는 경로

설계하면서 필요해진 경로다. 결정은 11.1절에 적었다. 2026-11-19에 SRS 6.2에도 더했다.

| 경로 | 왜 | 4절 |
| --- | --- | --- |
| `POST /api/payments/fail/` | 결제창 실패를 결제 기록 `FAILED`로 남긴다(FR-28) | 4.6.4 |
| `GET /api/admin/products/{id}/` | 관리자 수정 화면에 판매 중지 원두와 재고를 채운다(FR-38 ~ FR-41) | 6.13 |
