## 2. 단위 테스트

업무 규칙을 담은 함수를 API 없이 직접 부른다. 백엔드는 `django.test.TestCase`(메모리 SQLite, 테스트마다 롤백), 프론트엔드는 Vitest다. 함수 이름과 위치는 SDD 2절, 4절을 따른다.

### 2.1 원두와 재고 (`products/tests/test_services.py`, DR-4는 `test_models.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_dr4_option_price_is_base_plus_extra` | DR-4, DR-13 | 기본 가격 18,000원 + 추가 금액 4,000원 → 옵션 가격 22,000원(정수) |
| `test_dr5_decrease_stock_rejects_more_than_left` | DR-5, DR-10 | 재고 2에서 3 차감 → 409 `OUT_OF_STOCK` 예외, 재고 2 그대로 |
| `test_dr5_set_stock_rejects_negative` | DR-5, FR-41 | `set_stock(-1)` → 400 예외, 재고 그대로 |
| `test_dr5_decrease_stock_subtracts_in_db` | DR-5 | 재고 5에서 2 차감 → 재고 3 |
| `test_dr10_decrease_stock_rejects_non_positive_quantity` | DR-10 | 0개 차감 → 400 예외, 재고 그대로 |
| `test_dr10_increase_stock_rejects_non_positive_quantity` | DR-10 | -1개 복원 → 400 예외, 재고 그대로 |
| `test_fr41_set_stock_unknown_option_is_404` | FR-41 | 없는 옵션 ID → 404 예외 |
| `test_dr6_last_stock_sold_marks_product_sold_out` | DR-6 | 판매 중 원두의 마지막 재고 1 차감 → 원두 `SOLD_OUT` |
| `test_dr6_restock_returns_sold_out_to_on_sale` | DR-6 | 품절 원두 옵션 재고 0 → 3 → 원두 `ON_SALE` |
| `test_dr6_sold_out_only_when_all_options_empty` | DR-6 | 옵션 둘 중 하나만 0 → `ON_SALE` 유지 |
| `test_dr6_increase_stock_returns_sold_out_to_on_sale` | DR-6 | 품절 원두 옵션에 2개 복원(취소) → 재고 2, 원두 `ON_SALE` |
| `test_fr41_set_stock_zero_on_every_option_marks_sold_out` | FR-41, DR-6 | 옵션 둘 중 남은 하나를 0으로 → `SOLD_OUT` |
| `test_dr7_stopped_product_stays_stopped_on_stock_change` | DR-7, FR-42 | `STOPPED` 원두에 재고 증감 → `STOPPED` 유지 |
| `test_fr42_stop_sales_from_on_sale_and_sold_out` | FR-42 | `ON_SALE`, `SOLD_OUT` 원두 → `STOPPED` |
| `test_fr42_stop_sales_twice_is_409` | FR-42 | `STOPPED` 원두 다시 중지 → 409 `INVALID_STATE` |
| `test_fr42_stop_sales_unknown_product_is_404` | FR-42 | 없는 원두 ID → 404 예외 |
| `test_fr43_resume_picks_status_from_stock` | FR-43, DR-6 | 재고 있음 → `ON_SALE`, 모든 옵션 0 → `SOLD_OUT` |
| `test_fr43_resume_without_options_is_on_sale` | FR-43 | 옵션 없는 `STOPPED` 원두 재개 → `ON_SALE`(SDD 4.7.0 마지막 줄) |
| `test_fr43_resume_when_not_stopped_is_409` | FR-43 | `ON_SALE` 원두 재개 → 409 `INVALID_STATE`, 상태 그대로 |
| `test_fr1_customer_products_hide_stopped` | FR-1 | `customer_products()`에 `STOPPED` 없음, `SOLD_OUT` 포함 |

### 2.2 장바구니와 주문 (`orders/tests/test_services.py`(장바구니), `test_order_services.py`(주문·택배사), `test_order_number.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_dr9_adding_same_option_merges_quantity` | DR-9 | 같은 옵션 2개 + 3개 → 항목 1행, 수량 5 |
| `test_dr8_cannot_add_unavailable_option` | DR-8 | 품절·판매 중지 원두, 재고 0 옵션 담기 → 409 예외 |
| `test_dr10_merged_quantity_cannot_exceed_stock` | DR-10, DR-9 | 재고 3에 2개 담은 뒤 2개 더 → 409 `OUT_OF_STOCK`, 수량 2 그대로 |
| `test_dr14_shipping_fee_boundary` | DR-14, DR-13 | 상품 금액 29,999원 → 배송비 3,000원, 30,000원 → 0원, 0원(빈 장바구니) → 0원 |
| `test_dr15_final_amount_is_items_plus_fee` | DR-15 | 상품 금액 29,000원 → 최종 32,000원 |
| `test_dr12_dr18_order_copies_product_and_address` | DR-12, DR-18 | 주문 뒤 원두 이름·가격, 배송지 주소를 바꿔도 주문 항목 단가·주문 주소 그대로 |
| `test_fr23_nfr14_short_item_rolls_back_whole_order` | FR-23, NFR-14 | 두 항목 중 하나 재고 부족 → 409, 주문 0행, 두 옵션 재고와 장바구니 그대로 |
| `test_dr11_order_number_format` | DR-11 | 2026-11-30 10:00(KST) 첫 주문 → `ORD-20261130-001` |
| `test_dr11_order_number_resets_daily_in_seoul_time` | DR-11 | 2026-11-30 23:59(KST) 주문 `...-005` 다음 2026-12-01 00:01(KST, UTC로는 11-30) 주문 → `ORD-20261201-001` |
| `test_dr11_order_limit_after_999` | DR-11 | 같은 날 1000번째 → 503 `ORDER_LIMIT` 예외 |
| `test_dr19_disallowed_transitions_raise_invalid_state` | DR-19 | SRS 2절 전환 표에 없는 (현재, 다음) 쌍 전부 → 409 `INVALID_STATE`, 상태 그대로 |
| `test_dr20_no_cancel_request_from_shipped` | DR-20 | `PENDING`, `SHIPPED`, `DELIVERED`, `CANCEL_REQUESTED`, `CANCELLED`에서 취소 요청 → 409, 상태 그대로 |
| `test_dr21_cancel_pending_twice_restores_stock_once` | DR-21, FR-32 | 결제 대기 주문 즉시 취소를 두 번 → 두 번째 409, 재고는 한 번만 복구 |
| `test_dr21_cancel_restores_stock_once` | DR-21 | 같은 주문 취소 승인 서비스를 두 번 부름 → 재고는 주문 수량만큼 한 번만 늘어남, 두 번째는 409 |
| `test_fr35_tracking_url_strips_dash_and_encodes` | FR-35 | `CJ`, `1234-5678-9012` → 조회 주소에 `123456789012`, 택배사 5곳 모두 주소 생성 |

### 2.3 결제 (`orders/tests/test_payments.py`, 가짜 PG)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_dr24_each_attempt_gets_new_pg_order_id` | DR-24, FR-29 | 같은 주문 두 번째 결제 시작 → 결제 2행, `pg_order_id` `<주문번호>-P1`, `-P2` |
| `test_dr22_confirm_success_marks_order_paid` | DR-22, FR-26 | 가짜 PG 승인 성공, 금액 같음 → 결제 `SUCCESS`, 주문 `PAID` |
| `test_dr23_amount_mismatch_cancels_payment` | DR-23, FR-27 | 가짜 PG가 다른 금액 승인 → 가짜 PG `cancel` 1회 호출, 결제 `CANCELLED`, 주문 `PENDING` |
| `test_dr23_success_on_cancelled_order_is_cancelled` | DR-22, DR-23, FR-27 | 이미 `CANCELLED`인 주문의 승인 성공 → PG `cancel` 1회, 주문 `CANCELLED` 유지 |
| `test_dr24_failure_keeps_order_pending` | DR-24, FR-28 | 가짜 PG 실패 코드 → 결제 `FAILED` + 실패 사유, 주문 `PENDING` |
| `test_fr26_timeout_keeps_payment_ready` | FR-26 | 가짜 PG 시간 초과 → 502 `PG_ERROR` 예외, 결제 `READY` 유지 |
| `test_dr21_cancel_treats_already_cancelled_as_success` | DR-21, FR-50 | 가짜 PG가 `ALREADY_CANCELED_PAYMENT` → 결제 `CANCELLED`, 예외 없음 |
| `test_fr50_cancel_sends_idempotency_key` | FR-50 | `cancel` 호출 기록에 `cancel-<payment_id>` 키 |

### 2.4 배송지 (`users/tests/test_services.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_dr16_first_address_becomes_default` | DR-16, FR-15 | 첫 배송지 `is_default=true`, 두 번째 `false` |
| `test_dr16_set_default_leaves_exactly_one` | DR-16, FR-18 | 다른 배송지를 기본으로 → 그 회원 `is_default=true` 1행 |
| `test_dr17_default_delete_blocked_while_others_exist` | DR-17, FR-17 | 배송지 둘, 기본 삭제 → 409, 하나뿐이면 삭제 가능 |

### 2.5 프론트엔드 (Vitest)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `NFR-33 formats won with thousands separator` (`src/lib/format.test.js`) | NFR-33 | `formatWon(29000)` → `29,000원`, `formatWon(0)` → `0원` |
| `NFR-30 labels every status in Korean` (`src/lib/labels.test.js`) | NFR-30 | SDD 5.0.2 열거형 값마다 한국어 이름이 있음(빈 값 0개) |
| `FR-10 retries the original request once after refresh` (`src/api/client.test.js`) | FR-10 | 가짜 어댑터: 401 → 재발급 200 → 원 요청 다시 200. 원 요청 2회, 재발급 1회 |
| `FR-10 shares one refresh across concurrent 401s` | FR-10 | 동시 요청 3개가 401 → 재발급 요청 1회 |
| `FR-10 does not refresh on login 401` | FR-10, NFR-7 | `/auth/token/` 401 → 재발급 0회, 오류 그대로 |
| `FR-10 clears tokens and goes to login when refresh fails` | FR-10 | 재발급 401 → `localStorage` 토큰 둘 없음, `/login?next=<경로>`로 이동 |
| `FR-10 rejects off-site next paths` | FR-10 | `next=https://evil.example` → `/`로 이동 |
| `FR-54 clearTokens removes both tokens` (`src/auth/tokenStore.test.js`) | FR-54 | `coffee.access`, `coffee.refresh` 둘 다 없음 |
