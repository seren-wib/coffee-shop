## 3. 통합 테스트

`/api/` 경로를 HTTP 요청 그대로 부르고 상태 코드, 응답 본문, 저장된 행을 확인한다. 기대 열의 상태 코드와 오류 코드는 SDD 7.2절을 따른다.

- 앱과 DB: 파일마다 DRF `APITestCase`를 상속한다. 테스트 러너가 실행 시작 때 메모리 SQLite에 마이그레이션을 한 번 적용하고, 테스트마다 트랜잭션을 열었다가 롤백한다. 공통 데이터는 `setUpTestData`에서 `tests/factories.py` 함수로 만든다.
- 인증: `APIClient`에 `force_authenticate`를 쓰지 않고, 로그인 API(`/api/auth/token/`)에서 받은 실제 액세스 토큰을 `Authorization: Bearer`로 붙인다. 권한 클래스와 JWT 설정까지 함께 확인하기 위해서다. 헬퍼 `auth_client(user)`가 이 일을 한다.
- PG: 테스트 설정의 `FakePaymentsClient`를 쓰고, 테스트마다 다음 결과를 정한다(1.2절).
- 동시 주문(NFR-15)은 `TransactionTestCase`, 파일 SQLite(1.2절)에서 돈다.

### 3.1 회원과 인증 (`users/tests/test_auth_api.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr7_register_creates_member` | FR-7 | `POST /api/auth/register/` 201, `role=MEMBER`, 응답에 `password` 없음 |
| `test_fr7_register_ignores_role_admin` | FR-7, NFR-10 | 요청에 `role=ADMIN` → 201, 저장된 `role=MEMBER` |
| `test_fr7_register_rejects_duplicate_email` | FR-7 | 대소문자만 다른 같은 이메일 → 400, `fields.email` |
| `test_fr7_register_rejects_short_password` | FR-7, NFR-6 | 7자 비밀번호 → 400, `fields.password` |
| `test_fr58_register_requires_privacy_agreement` | FR-58 | `privacy_agreed` 빠짐, `false` → 400, `fields.privacy_agreed`, 회원 0행 |
| `test_fr58_register_stores_agreement_time` | FR-58 | `privacy_agreed=true` → 201, `users.privacy_agreed_at`이 고정 시각과 같음 |
| `test_nfr6_password_stored_as_pbkdf2_hash` | NFR-6 | 운영 해셔로 가입 → `users.password`가 `pbkdf2_sha256$`로 시작, 원문과 다름 |
| `test_fr8_login_returns_tokens` | FR-8 | `POST /api/auth/token/` 200, `access`, `refresh`, `user.role` |
| `test_fr8_nfr7_unknown_email_and_wrong_password_look_same` | FR-8, NFR-7 | 둘 다 401, 본문 완전히 같음(`INVALID_CREDENTIALS`) |
| `test_nfr8_token_lifetimes` | NFR-8 | 액세스 `exp - iat` 1,800초, 리프레시 604,800초 |
| `test_fr9_refresh_issues_access` | FR-9 | `POST /api/auth/token/refresh/` 200, `access` |
| `test_fr9_expired_or_forged_refresh_is_401` | FR-9 | 만료 시각이 지난 토큰, 서명 바꾼 토큰 → 401 `INVALID_TOKEN` |
| `test_fr11_me_returns_own_profile` | FR-11, NFR-11 | `GET /api/me/` 200, 자기 `email`만 |
| `test_fr12_me_update_keeps_email` | FR-12 | `PATCH /api/me/`에 `user_name`, `email` → 200, 이름만 바뀜 |
| `test_fr13_password_change` | FR-13 | 맞는 현재 비밀번호 → 204, 옛 비밀번호 로그인 401, 새 비밀번호 200 |
| `test_fr13_wrong_current_password_is_400` | FR-13 | 400, `fields.current_password` |
| `test_nfr9_every_private_route_needs_token` | NFR-9 | URL 설정의 모든 `/api/` 경로 중 공개 6개(SDD 7.3) 밖은 토큰 없이 401 |
| `test_nfr10_member_token_on_admin_routes_is_403` | NFR-10 | `/api/admin/` 아래 모든 경로에 회원 토큰 → 403 |
| `test_login_throttle_returns_429` | NFR-7(SDD 8.3절) | 한도를 낮춘 `override_settings`에서 11번째 로그인 → 429 `THROTTLED` |

### 3.2 배송지 (`users/tests/test_addresses_api.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr14_list_puts_default_first` | FR-14 | `GET /api/me/addresses/` 200, 첫 항목 `is_default=true`, 자기 배송지만 |
| `test_fr15_create_first_address_is_default` | FR-15, DR-16 | 201, `is_default=true`. 필수 항목 빠짐 400 |
| `test_fr16_update_address` | FR-16 | `PATCH` 200, 바뀐 값 |
| `test_fr16_nfr11_other_members_address_is_404` | FR-16, NFR-11 | 다른 회원 배송지 `PATCH`, `DELETE` → 404 |
| `test_fr17_delete_address` | FR-17 | 기본 아닌 배송지 `DELETE` 204 |
| `test_fr17_delete_default_with_others_is_409` | FR-17, DR-17 | 409 `DEFAULT_ADDRESS_DELETE` |
| `test_fr18_set_default` | FR-18, DR-16 | `POST .../default/` 200, 그 회원 `is_default=true` 1행 |

### 3.3 원두 조회 (`products/tests/test_catalog_api.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr1_list_pages_by_20_without_stopped` | FR-1 | 원두 25개(판매 중지 2개) → 1페이지 20개, `count=23`, `STOPPED` 없음, `SOLD_OUT` 포함 |
| `test_fr1_list_is_public` | FR-1, NFR-9 | 토큰 없이 200 |
| `test_fr1_list_item_fields_and_newest_first` | FR-1 | 최근 등록 순, 항목 필드 8개, `lowest_price` = 기본 가격 + 가장 낮은 추가 금액 |
| `test_fr1_lowest_price_without_options_is_base_price` | FR-1 | 옵션 없는 원두 → `lowest_price` = `base_price` |
| `test_fr1_page_out_of_range_is_404` | FR-1 | 범위 밖 `?page=5` → 404 `NOT_FOUND`(SDD 7.4) |
| `test_fr2_search_by_name_part` | FR-2 | `?search=에티` → 이름에 "에티"가 든 원두만 |
| `test_fr3_filter_by_origin` | FR-3 | `?origin=에티오피아` → 그 원산지만 |
| `test_fr4_filter_by_price_range` | FR-4 | `?min_price=10000&max_price=20000` → 기본 가격이 범위 안인 것만(경계 포함) |
| `test_fr4_bad_price_param_is_400` | FR-4 | `?min_price=abc`, `?max_price=-1`, `min_price > max_price` → 400 `VALIDATION_ERROR` |
| `test_fr5_filter_by_roast_level` | FR-5 | `?roast_level=LIGHT` → 라이트만. 모르는 값 400 |
| `test_fr5_filters_combine_with_and` | FR-3 ~ FR-5 | 원산지·로스팅·최고 가격을 함께 → 셋 다 맞는 원두만(SRS 3.1 AND) |
| `test_fr6_detail_has_option_prices_and_availability` | FR-6, DR-4 | `GET /api/products/{id}/` 200, 옵션마다 `price`, `is_available`, 용량·분쇄도 순서 |
| `test_fr6_stopped_product_detail_is_404` | FR-6 | 판매 중지 원두 → 404 |
| `test_fr6_unknown_product_is_404` | FR-6 | 없는 원두 ID → 404 |
| `test_dr8_sold_out_product_options_are_unavailable` | DR-8, FR-6 | 품절 원두 상세 200, 옵션 `is_available=false` |

### 3.4 장바구니 (`orders/tests/test_cart_api.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr19_add_item` | FR-19 | `POST /api/cart/items/` 새 옵션 201, 같은 옵션 다시 200, 수량 합침 |
| `test_fr19_unavailable_option_is_409` | FR-19, DR-8 | 품절 옵션 409 `OUT_OF_STOCK`, 판매 중지 원두 409 `NOT_AVAILABLE` |
| `test_fr19_rejects_missing_option_and_bad_quantity` | FR-19 | 없는 옵션 404, 수량 0 → 400 `fields.quantity` |
| `test_fr19_needs_token` | FR-19, NFR-9 | 토큰 없이 401 |
| `test_fr20_cart_totals` | FR-20, DR-14, DR-15 | `GET /api/cart/` 200, 항목 `price`·`is_available`, 상품 금액 29,000원 → 배송비 3,000원, 30,000원 → 0원 |
| `test_fr20_item_fields_and_unavailable_items` | FR-20, DR-10 | 항목 필드 12개(SDD 4.4.2), 담은 뒤 재고가 수량보다 줄면 `is_available=false`, `can_order=false` |
| `test_fr20_empty_cart` | FR-20, DR-14 | 빈 장바구니 `items` 빈 배열, 배송비 0, `can_order=false` |
| `test_fr20_lists_items_in_added_order_and_only_mine` | FR-20, NFR-11 | 담은 순서, 다른 회원 항목 없음 |
| `test_fr21_change_quantity` | FR-21, DR-10 | `PATCH` 200. 0개 400, 재고 초과 409 |
| `test_fr22_remove_item` | FR-22 | `DELETE` 204, 다시 조회하면 없음 |
| `test_nfr11_other_members_cart_item_is_404` | NFR-11 | 다른 회원 항목 `PATCH`, `DELETE` → 404 |

### 3.5 주문 (`orders/tests/test_orders_api.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr23_create_order_from_whole_cart` | FR-23, DR-11 | `POST /api/orders/` 201, `status=PENDING`, 주문번호 `ORD-YYYYMMDD-NNN`, 재고 차감, 장바구니 비움 |
| `test_fr23_nfr14_one_short_item_rejects_all` | FR-23, NFR-14 | 한 항목 재고 부족 → 409, 모든 옵션 재고·장바구니·주문 수 그대로 |
| `test_fr23_empty_cart_is_400` | FR-23 | 400 `EMPTY_CART` |
| `test_fr23_new_address_is_copied` | FR-23, DR-18 | 저장 안 한 새 주소로 주문 → 주문에 주소 복사, 배송지 행은 늘지 않음 |
| `test_fr23_address_is_required_and_must_be_mine` | FR-23, NFR-11 | 배송지 없음 400, 다른 회원 배송지 404, 장바구니 그대로 |
| `test_nfr16_stopped_product_in_cart_is_409` | NFR-16, DR-8 | 담은 뒤 판매 중지된 원두 → 409 `NOT_AVAILABLE` |
| `test_fr30_list_own_orders_newest_first` | FR-30, NFR-11 | `GET /api/orders/` 200, 자기 주문만, `created_at` 내림차순 |
| `test_fr55_filter_own_orders_by_status` | FR-55 | `?status=PAID` → 그 상태만, 빈 값은 전체, 모르는 값 400 |
| `test_fr30_needs_token` | FR-30, NFR-9 | 토큰 없이 401 |
| `test_fr31_order_detail` | FR-31 | 200, 항목·결제·배송지·상태 |
| `test_fr31_nfr11_other_members_order_is_404` | FR-31, NFR-11 | 404 |
| `test_fr32_cancel_pending_order` | FR-32 | `POST .../cancel/` 200, `CANCELLED`, 재고 복구 |
| `test_fr32_cancel_paid_order_is_409` | FR-32 | 결제 완료 이후 → 409 `INVALID_STATE` |
| `test_fr33_request_cancel` | FR-33, DR-20 | `PAID`, `PREPARING`에서 200, `CANCEL_REQUESTED`, 요청 전 상태·사유 저장. 사유 비면 400, `SHIPPED` 409 |
| `test_fr34_shipped_order_shows_tracking` | FR-34, FR-35 | `SHIPPED` 주문 상세에 `courier_name`, `tracking_number`, `tracking_url`, `DELIVERED`면 `delivered_at` |
| `test_nfr15_last_stock_concurrent_orders` (`@tag("concurrency")`) | NFR-15, DR-5 | 재고 1 옵션에 회원 10명이 스레드로 동시 주문 → 201 1건, 409 9건, 재고 0, 잠금 오류 0 |

### 3.6 결제 (`orders/tests/test_payments_api.py`, 가짜 PG)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr25_start_payment` | FR-25, DR-15 | `POST /api/orders/{id}/payments/` 201, 결제 `READY` 1행, `amount` = 최종 결제 금액 |
| `test_fr26_confirm_success` | FR-26, DR-22 | `POST /api/payments/confirm/` 200, 결제 `SUCCESS`, 주문 `PAID` |
| `test_fr26_confirm_other_members_payment_is_404` | FR-26, NFR-11 | 다른 회원 토큰 → 404, 가짜 PG 호출 0회 |
| `test_fr27_amount_mismatch_closes_without_pg` | FR-27, DR-23 | 다른 금액으로 확인 → 409 `PAYMENT_MISMATCH`, 결제 `CANCELLED`, 주문 `PENDING`, PG 호출 0회 |
| `test_fr27_cancelled_order_cancels_at_pg` | FR-27, DR-22 | 취소된 주문 → 409 `ORDER_NOT_PENDING`, 주문 `CANCELLED` 유지 |
| `test_fr27_payment_cancelled_with_order_skips_pg` | FR-27, FR-32 | 결제 대기 주문을 먼저 취소한 뒤 확인 → 409 `ORDER_NOT_PENDING`, PG 호출 0회 |
| `test_fr28_confirm_failure_records_reason` | FR-28, DR-24 | PG 실패 → 402 `PAYMENT_FAILED`, 결제 `FAILED` + 사유, 주문 `PENDING` |
| `test_fr28_payment_window_failure_is_recorded` | FR-28 | `POST /api/payments/fail/` → 결제 `FAILED` + 사유, PG 호출 0회 |
| `test_fr28_failure_without_order_id_changes_nothing` | FR-28 | `orderId` 없는 실패 → 200, 결제 `READY` 그대로 |
| `test_fr28_failure_for_other_members_payment_is_404` | FR-28, NFR-11 | 다른 회원 결제의 실패 기록 → 404 |
| `test_fr29_retry_payment_adds_row` | FR-29, DR-24 | 실패 뒤 다시 결제 시작 → 201, 결제 2행 |
| `test_fr29_paid_order_retry_is_409` | FR-29 | 성공 결제가 있는 주문 → 409 `ALREADY_PAID` |
| `test_fr25_cancelled_order_cannot_start_payment` | FR-25, DR-22 | 취소된 주문 결제 시작 → 409 `INVALID_STATE` |
| `test_fr25_other_members_order_is_404` | FR-25, NFR-11 | 다른 회원 주문 결제 시작 → 404 |
| `test_nfr18_payments_table_has_no_card_columns` | NFR-18 | `payments` 열 이름에 `card`, `number`, `cvc`, `expiry` 없음 |

### 3.6.1 결제 끔 (`orders/tests/test_payments_disabled.py`, `PAYMENTS_ENABLED=False`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_nfr13_start_payment_is_503_without_a_row` | FR-60, FR-25 (2026-11-27 변경. 이전에는 NFR-13. 함수 이름의 `nfr13`은 그대로 둔다) | 결제 시작 503 `PAYMENTS_DISABLED`, 결제 기록 0행, PG 호출 0회 |
| `test_nfr13_confirm_is_503_and_keeps_ready` | FR-60, FR-26 | 확인 503, 결제 `READY` 그대로, PG 호출 0회 |
| `test_nfr13_cancel_approve_is_503_and_keeps_request` | FR-60, FR-50 | 관리자 취소 승인 503, 주문 `CANCEL_REQUESTED` 그대로, PG 호출 0회 |
| `test_nfr13_cart_and_orders_still_work` | FR-60, FR-19 | 결제를 꺼도 장바구니 담기 200·201 |

### 3.7 관리자 원두 (`products/tests/test_admin_products_api.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr36_list_includes_stopped` | FR-36 | `GET /api/admin/products/` 200, 판매 중지 포함, 옵션별 재고, `option_count`, `total_stock` |
| `test_fr36_filter_by_sales_status` | FR-36 | `?sales_status=STOPPED` → 판매 중지만. 모르는 값 400 |
| `test_fr36_product_without_options_has_zero_totals` | FR-36 | 옵션 없는 원두 → `option_count=0`, `total_stock=0` |
| `test_fr56_search_by_name_part` | FR-56 | `?search=에티` → 판매 중지 포함 이름 일치만 |
| `test_fr37_create_product_on_sale` | FR-37 | `POST /api/admin/products/` 201, `ON_SALE` |
| `test_fr37_create_ignores_sales_status` | FR-37, DR-6 | 본문에 `sales_status=SOLD_OUT` → 무시하고 `ON_SALE` |
| `test_fr37_create_rejects_bad_input` | FR-37 | 이름 없음, 음수 가격, 모르는 로스팅, 목록 밖 원산지, `http://` 이미지 → 각각 400 `fields`, 0행 |
| `test_fr38_detail_for_edit_form` | FR-38 | `GET /api/admin/products/{id}/` 200, 판매 중지 원두도 |
| `test_fr38_update_keeps_old_order_prices` | FR-38, DR-12 | `PATCH` 200, 기존 주문 항목 단가 그대로, 본문의 `sales_status` 무시 |
| `test_fr38_update_rejects_origin_outside_list` | FR-38 | 목록 밖 원산지로 수정 → 400 |
| `test_fr39_add_option` | FR-39, DR-2 ~ DR-4 | 201. 같은 용량·분쇄도 409 `DUPLICATE_OPTION`, 음수 추가 금액 400 |
| `test_fr39_first_option_with_zero_stock_marks_sold_out` | FR-39, DR-6 | 옵션 없는 `ON_SALE` 원두에 재고 0 옵션 → 201, `SOLD_OUT`(SDD 4.7.4) |
| `test_fr39_add_option_to_unknown_product_is_404` | FR-39 | 없는 원두 → 404 |
| `test_fr40_update_option_extra_price` | FR-40 | `PATCH .../options/{oid}/` 200, 고객 상세 `price` 바뀜 |
| `test_fr40_option_of_another_product_is_404` | FR-40 | 다른 원두의 옵션 ID → 404 |
| `test_fr40_option_keeps_size_and_grind` | FR-40 | 본문의 `weight_size`, `grind_type` 무시 |
| `test_fr40_fr41_price_and_stock_in_one_request` | FR-40, FR-41 | 추가 금액과 재고를 한 요청에 → 200, 둘 다 바뀜 |
| `test_fr41_stock_change_switches_sales_status` | FR-41, DR-6 | 마지막 재고 0 → `SOLD_OUT`, 1 → `ON_SALE`. 음수 400 |
| `test_fr42_stop_sales` | FR-42, DR-7 | `POST .../stop/` 200 `STOPPED`, 재고 바꿔도 `STOPPED`, 다시 중지 409 `INVALID_STATE` |
| `test_fr43_resume_sales` | FR-43 | `POST .../resume/` 200, 재고에 따라 `ON_SALE` 또는 `SOLD_OUT`, `STOPPED` 아닌 원두 409 |

### 3.8 관리자 주문 (`orders/tests/test_admin_orders_api.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr44_list_all_orders_newest_first` | FR-44 | 200, 모든 회원 주문, `created_at` 내림차순 |
| `test_fr45_filter_by_status` | FR-45 | `?status=CANCEL_REQUESTED` → 그 상태만 |
| `test_fr57_search_by_number_or_email` | FR-57 | 주문번호 일부, 회원 이메일로 각각 일치만 |
| `test_fr46_order_detail` | FR-46 | 200, 회원·항목·결제 기록·배송지·취소 사유 |
| `test_fr47_prepare` | FR-47 | `PAID` → 200 `PREPARING`. `PENDING` 409 |
| `test_fr48_ship` | FR-48 | 200 `SHIPPED`, `shipped_at`, `courier_code`. 송장번호 비면 400, 숫자 없는 송장번호(`---`) 400, 모르는 택배사 400 |
| `test_fr49_deliver` | FR-49 | 200 `DELIVERED`, `delivered_at` |
| `test_fr50_approve_cancel` | FR-50, DR-21 | 200 `CANCELLED`, 재고 복구, 결제 `CANCELLED`, PG `cancel` 1회. 두 번째 승인 409, 재고 한 번만 복구 |
| `test_fr50_pg_error_keeps_cancel_requested` | FR-50 | 가짜 PG 취소 오류 → 502 `PG_ERROR`, 주문 `CANCEL_REQUESTED`, 재고 그대로 |
| `test_fr51_reject_cancel_restores_previous_status` | FR-51 | 요청 전 `PAID` → `PAID`, `PREPARING` → `PREPARING`, 사유는 남음 |
| `test_nfr11_admin_routes_take_any_members_order` | FR-46, NFR-10 | 관리자는 어느 회원 주문이든 200, 없는 주문번호 404 |

### 3.9 운영과 공통 (`common/tests/test_common_api.py`, `users/tests/test_commands.py`, `products/tests/test_commands.py`)

| 테스트 | SRS | 기대 |
| --- | --- | --- |
| `test_fr52_health_ok` | FR-52 | `GET /api/health/` 토큰 없이 200, 본문 `{"status": "ok"}` |
| `test_fr52_health_503_when_db_fails` | FR-52 | DB 커서를 예외로 바꾼 상태 → 503, 본문에 내부 정보 없음 |
| `test_fr53_created_admin_can_use_admin_routes` | FR-53, NFR-10 | 명령으로 만든 관리자 토큰으로 `GET /api/admin/orders/` 200 |
| `test_fr53_create_admin_command` | FR-53 | `call_command("create_admin", ...)` 뒤 그 계정 토큰으로 `GET /api/admin/orders/` 200 |
| `test_nfr12_production_needs_allowed_hosts` (`common/tests/test_production_checks.py`) | NFR-12 | `DEBUG=False`에 `ALLOWED_HOSTS`가 비면 `ImproperlyConfigured` |
| `test_nfr13_only_test_toss_keys` | NFR-42, NFR-13 | `live_`·접두사 없는 키는 `ImproperlyConfigured`, `test_` 키는 켬, 빈 값은 끔 |
| `test_nfr12_error_bodies_have_no_trace` | NFR-12 | `DEBUG=False`에서 없는 경로 404, 일부러 낸 예외 500 본문에 파일 경로·`Traceback` 없음 |
| `test_nfr17_member_with_orders_cannot_be_deleted` | NFR-17 | 주문 있는 회원 `delete()` → `ProtectedError`, 회원 행 그대로 |
| `test_nfr28_responses_are_json` | NFR-28 | 상태 확인, 목록, 오류 응답 모두 `Content-Type: application/json` |
| `test_nfr35_logs_have_no_secrets_or_contacts` | NFR-35 | `assertLogs`로 로그인·주문 요청 동안 로그를 모아 비밀번호, 토큰, 연락처, 주소 문자열 0건 |
| `test_nfr3_seed_demo_counts` | NFR-3 | `seed_demo --products 5 --members 3 --orders 14`(작은 수) 뒤 행 수가 인수와 같음, 원두마다 옵션 1 ~ 9개, 회원마다 배송지 1 ~ 3개(기본 1개), `privacy_agreed_at` 채움 |
| `test_nfr3_same_seed_gives_same_data` | NFR-3 | 같은 인수로 두 번(사이에 비움) → 원두·옵션·재고·회원·배송지·주문·주문 항목이 같음(시각·키·비밀번호 제외) |
| `test_nfr3_orders_cover_every_status_with_matching_rows` | NFR-3, DR-13 ~ DR-15 | 주문 14건 → 상태 7가지가 2건씩, 금액·배송비·주문번호 형식이 규칙대로, 결제는 `PENDING`→`READY`, `CANCELLED`→`CANCELLED`, 나머지 `SUCCESS` 1건 |
| `test_nfr3_stock_matches_live_orders` | NFR-3, DR-6 | 시드 뒤 `SOLD_OUT` 원두는 재고 0, `ON_SALE` 원두는 재고 있음 |
| `test_nfr3_refuses_a_database_with_data` | NFR-3 | 데이터가 있는 DB에서 다시 돌리면 `CommandError` |
| `test_nfr3_needs_force_when_debug_is_off` | NFR-3 | `DEBUG=False`에서 `--force` 없이 `CommandError`, 0행. `--force`면 돈다 |
