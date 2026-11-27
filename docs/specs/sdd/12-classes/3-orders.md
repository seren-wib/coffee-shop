## 12.3 orders 앱

장바구니, 주문, 결제, 관리자 주문 처리. 4절의 "장바구니", "주문", "결제", "관리자 주문·배송·취소" 부품을 구현한다.

### 12.3.1 모델 `orders/models.py`

| 클래스 | 맡는 일 | 테이블 | 직접 정의한 메서드 |
| --- | --- | --- | --- |
| `OrderStatus` | 주문 상태 열거형. `PENDING`, `PAID`, `PREPARING`, `SHIPPED`, `DELIVERED`, `CANCEL_REQUESTED`, `CANCELLED` | | |
| `PaymentStatus` | 결제 상태 열거형. `READY`, `SUCCESS`, `FAILED`, `CANCELLED` | | |
| `PaymentMethod` | 결제 수단 열거형 | | |
| `Courier` | 택배사 열거형 | | |
| `CartItem` | 회원의 장바구니 항목 한 건(옵션, 수량) | `cart_items` | |
| `Order` | 주문 한 건. 금액과 배송지를 주문 시점 값으로 복사해 둔다 | `orders` | |
| `OrderItem` | 주문 항목 한 건. 원두 이름, 옵션, 단가를 주문 시점 값으로 복사해 둔다 | `order_items` | |
| `Payment` | 결제 시도 한 건 | `payments` | |

### 12.3.2 서비스 모듈 `orders/services.py`: 장바구니

#### shipping_fee_for

- 시그니처: `shipping_fee_for(product_amount: int) -> int`
- 반환: 배송비. 상품 금액이 0이면 0, 30,000원 이상이면 0, 그 밖에는 3,000. 트랜잭션 밖. 예외 없음.
- 요구사항: DR-14, FR-20, FR-24

#### add_to_cart

- 시그니처: `add_to_cart(user, option_id: int, quantity: int)`
- 반환: `(item, created)`. 같은 옵션이 이미 있으면 수량을 더하고 `created`가 거짓이다. 예외: 404 `NOT_FOUND`(없는 옵션), 409 `NOT_AVAILABLE`(판매 중이 아님), 409 `OUT_OF_STOCK`(더한 수량이 재고보다 많음).
- 요구사항: FR-19

#### change_cart_quantity

- 시그니처: `change_cart_quantity(user, cart_item_id: int, quantity: int)`
- 반환: 수량을 바꾼 `CartItem`. 예외: 404 `NOT_FOUND`(다른 회원의 항목, 없는 ID), 409 `OUT_OF_STOCK`.
- 요구사항: FR-21

#### remove_cart_item

- 시그니처: `remove_cart_item(user, cart_item_id: int) -> None`
- 반환: 없음. 예외: 404 `NOT_FOUND`.
- 요구사항: FR-22

#### cart_items

- 시그니처: `cart_items(user)`
- 반환: 그 회원의 `CartItem` 쿼리셋(옵션과 원두 포함, 담은 순). 트랜잭션 밖. 예외 없음.
- 요구사항: FR-20, FR-23

#### is_available

- 시그니처: `is_available(item) -> bool`
- 반환: 원두가 판매 중이고 수량이 재고 이하이면 참. 트랜잭션 밖. 예외 없음.
- 요구사항: FR-20

#### cart_summary

- 시그니처: `cart_summary(user)`
- 반환: `{items, product_amount, shipping_fee, total_amount, can_order}` 사전. 지금 가격으로 계산한다. 트랜잭션 밖. 예외 없음.
- 요구사항: FR-20

### 12.3.3 서비스 모듈 `orders/services.py`: 주문

#### invalid_state

- 시그니처: `invalid_state(current, action)`
- 반환: 409 `INVALID_STATE` 오류 객체. 메시지에 지금 상태 이름을 넣는다. 던지지 않고 돌려준다. 트랜잭션 밖.
- 요구사항: DR-19

#### filter_by_status

- 시그니처: `filter_by_status(orders, value)`
- 반환: `value` 상태로 거른 주문 쿼리셋. 빈 값이면 그대로 돌려준다. 트랜잭션 밖. 예외: 400 `VALIDATION_ERROR`(모르는 상태).
- 요구사항: FR-45, FR-55

#### own_order

- 시그니처: `own_order(user, order_id)`
- 반환: 그 회원의 `Order`. 트랜잭션 밖. 예외: 404 `NOT_FOUND`(다른 회원의 주문, 없는 ID).
- 요구사항: FR-31, NFR-11

#### create_order

- 시그니처: `create_order(user, *, address_id=None, address=None)`
- 반환: 만든 `PENDING` 상태 `Order`. 장바구니 전체가 주문 하나가 되거나 아무것도 바뀌지 않는다. `address_id`(저장된 배송지)와 `address`(새 주소) 가운데 하나만 온다. 예외: 400 `EMPTY_CART`, 404 `NOT_FOUND`(없는 배송지), 409 `NOT_AVAILABLE`(판매 중이 아닌 원두, `details.cart_item_ids`), 409 `OUT_OF_STOCK`(재고 부족, `details.cart_item_ids`), 409 `RETRY`(주문번호 충돌), 503 `ORDER_LIMIT`(하루 주문 수 초과).
- 요구사항: FR-23, DR-11, DR-18, NFR-14 ~ NFR-16

#### cancel_pending_order

- 시그니처: `cancel_pending_order(user, order_id)`
- 반환: `CANCELLED`가 된 `Order`. 재고를 되돌리고 열린 결제 시도를 닫는다. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(결제 대기가 아님).
- 요구사항: FR-32, DR-21

#### request_cancel

- 시그니처: `request_cancel(user, order_id, reason)`
- 반환: `CANCEL_REQUESTED`가 된 `Order`. 요청 전 상태와 사유를 적어 둔다. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(결제 완료나 배송 준비 중이 아님).
- 요구사항: FR-33, DR-20

내부 함수

- `_not_found()`: 404 `NOT_FOUND` 오류를 만든다.
- `_out_of_stock()`: 409 `OUT_OF_STOCK` 오류를 만든다.
- `_own_cart_item(user, cart_item_id)`: 회원 소유로 먼저 거른 뒤 장바구니 항목을 찾는다. 없으면 404.
- `_shipping_address(zipcode, base_address, detail_address)`: 주문에 복사할 주소 한 줄을 만든다.
- `_address_snapshot(user, address_id, address)`: 저장된 배송지나 새 주소에서 주문에 복사할 수령인·연락처·주소를 만든다.
- `_short_items(cart_item_ids)`: 재고가 모자란 항목 ID를 담은 409 `OUT_OF_STOCK` 오류를 만든다.

### 12.3.4 서비스 모듈 `orders/services.py`: 관리자 주문 처리

#### admin_order

- 시그니처: `admin_order(order_id)`
- 반환: 회원 정보를 붙인 `Order`. 소유자를 거르지 않는다. 트랜잭션 밖. 예외: 404 `NOT_FOUND`.
- 요구사항: FR-46

#### prepare

- 시그니처: `prepare(order_id)`
- 반환: `PREPARING`이 된 `Order`. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(결제 완료가 아님).
- 요구사항: FR-47

#### ship

- 시그니처: `ship(order_id, courier_code, tracking_number)`
- 반환: `SHIPPED`가 된 `Order`. 택배사, 송장 번호, 배송 시작 시각을 같은 UPDATE로 적는다. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(배송 준비 중이 아님).
- 요구사항: FR-48

#### deliver

- 시그니처: `deliver(order_id)`
- 반환: `DELIVERED`가 된 `Order`. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(배송 중이 아님).
- 요구사항: FR-49

#### approve_cancel

- 시그니처: `approve_cancel(order_id)`
- 반환: `CANCELLED`가 된 `Order`. 성공한 결제가 있으면 PG 취소를 트랜잭션 밖에서 먼저 하고, 그 뒤 상태를 바꾸고 재고를 되돌린다. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(취소 요청 상태가 아님), 502 `PG_ERROR`, 503 `PAYMENTS_DISABLED`.
- 요구사항: FR-50, DR-21

#### reject_cancel

- 시그니처: `reject_cancel(order_id)`
- 반환: 요청 전 상태로 돌아간 `Order`. 사유는 남긴다. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(취소 요청 상태가 아님).
- 요구사항: FR-51

내부 함수

- `_transition(order_id, expected, action, **changes)`: 지금 상태가 `expected`일 때만 바꾸는 조건부 UPDATE. 바뀐 행이 0이면 409 `INVALID_STATE`.
- `_close_cancelled(order_id)`: 취소 요청을 취소로 바꾸고, 바꾼 호출만 재고를 되돌린다.

### 12.3.5 주문번호 모듈 `orders/order_number.py`

#### next_order_id

- 시그니처: `next_order_id(today: date) -> str`
- 반환: `ORD-YYYYMMDD-NNN` 형식의 다음 주문번호. `create_order`의 트랜잭션 안에서 부른다. 예외: 503 `ORDER_LIMIT`(그날 999건 초과).
- 요구사항: DR-11

### 12.3.6 택배사 모듈 `orders/couriers.py`

#### courier_name

- 시그니처: `courier_name(code)`
- 반환: 택배사 한국어 이름. 코드가 없으면 `None`. 예외 없음.
- 요구사항: FR-34

#### tracking_url

- 시그니처: `tracking_url(code, tracking_number)`
- 반환: 택배사 배송 조회 주소. 코드나 송장 번호가 없으면 `None`. 예외 없음.
- 요구사항: FR-35

### 12.3.7 결제 모듈 `orders/payments.py`

PG 호출은 DB 트랜잭션 밖에서 한다. 결제 상태 변경은 `READY` 또는 `SUCCESS`를 조건으로 건 UPDATE다.

#### order_name

- 시그니처: `order_name(order)`
- 반환: 결제창에 보일 주문 이름. 항목이 하나면 원두 이름, 여럿이면 "첫 원두 이름 외 N건". 트랜잭션 밖. 예외 없음.
- 요구사항: FR-25

#### start_payment

- 시그니처: `start_payment(user, order_id)`
- 반환: 만든 `READY` 상태 `Payment`. 열려 있던 이전 시도는 닫는다. 예외: 503 `PAYMENTS_DISABLED`, 404 `NOT_FOUND`, 409 `ALREADY_PAID`, 409 `INVALID_STATE`(결제 대기가 아님).
- 요구사항: FR-25, FR-29, FR-60

#### confirm_payment

- 시그니처: `confirm_payment(user, *, payment_key, pg_order_id, amount)`
- 반환: `PAID`가 된 `Order`. 이미 성공한 결제면 PG를 다시 부르지 않고 같은 주문을 돌려준다. 함수 전체를 한 트랜잭션으로 묶지 않는다. 예외: 503 `PAYMENTS_DISABLED`, 404 `NOT_FOUND`, 409 `INVALID_STATE`(이미 끝난 결제, 새 시도로 대체됨), 409 `PAYMENT_MISMATCH`(금액 불일치), 409 `ORDER_NOT_PENDING`(이미 취소된 주문), 409 `ALREADY_PAID`, 402 `PAYMENT_FAILED`(PG가 승인하지 않음), 502 `PG_ERROR`(PG 응답 없음, 상태 모름).
- 요구사항: FR-26 ~ FR-28, DR-22 ~ DR-24

#### fail_payment

- 시그니처: `fail_payment(user, *, pg_order_id=None, code="", message="")`
- 반환: 없음. 열린 시도를 `FAILED`로 닫고 사유를 적는다. `pg_order_id`가 없으면 아무것도 하지 않는다. 예외: 404 `NOT_FOUND`.
- 요구사항: FR-28

#### cancel_success_payment

- 시그니처: `cancel_success_payment(payment, reason)`
- 반환: 없음. PG에 취소를 요청하고 성공 결제를 `CANCELLED`로 닫는다. 같은 멱등 키를 써서 다시 불러도 결과가 같다. 트랜잭션 밖. 예외: 502 `PG_ERROR`, 503 `PAYMENTS_DISABLED`.
- 요구사항: FR-50

내부 함수

- `_pg_error()`: 502 `PG_ERROR` 오류를 만든다.
- `_not_found()`: 404 `NOT_FOUND` 오류를 만든다.
- `_own_payment(user, pg_order_id)`: 회원 소유로 거른 결제 시도를 찾는다. 없으면 404.
- `_closed(reason)`: 닫은 사유에 맞는 409 오류를 만든다.
- `_mark_paid(payment, order, payment_key, method, result)`: 결제를 `SUCCESS`로, 주문을 `PAID`로 같은 세이브포인트에서 바꾼다. `PAID` 또는 승인이 성립할 수 없는 사유를 돌려준다.
- `_not_pending_reason(order)`: 주문이 결제 대기가 아닌 까닭(취소됨, 이미 결제됨)을 돌려준다.

### 12.3.8 PG 모듈 `orders/pg.py`

토스페이먼츠와 말하는 유일한 모듈이다.

| 클래스 | 맡는 일 | 메서드 |
| --- | --- | --- |
| `PgResult` | PG 응답에서 남기는 값만 담는 데이터 클래스. 원본 응답은 저장하지 않는다(NFR-18) | `approved`(속성): 성공 응답이고 상태가 `DONE`이면 참 |
| `PgError` | PG에 닿지 못했거나 제때 답이 없어 결과를 모를 때의 예외 | `__init__(code, message="")` |
| `TossPaymentsClient` | 토스페이먼츠 API 클라이언트. 제한 시간 10초 | `confirm(payment_key, pg_order_id, amount)`, `cancel(payment_key, reason, idempotency_key=None)`, `get(payment_key)` |
| `FakePaymentsClient` | 테스트용 대역. 실제 PG를 부르지 않고 준비한 결과를 돌려주며 호출을 기록한다 | `confirm`, `cancel`, `get`(시그니처는 위와 같다), `reset()`, `calls_to(method)` |

- `TossPaymentsClient`와 `FakePaymentsClient`의 `confirm`, `cancel`, `get`은 `PgResult`를 돌려주고, 결과를 알 수 없으면 `PgError`를 던진다. PG가 거절한 응답(4xx)은 예외가 아니라 `ok=False`인 `PgResult`다.
- 내부 메서드: `TossPaymentsClient._call(method, path, body=None, idempotency_key=None)`(HTTP 호출과 오류 분류), `TossPaymentsClient._result(payload)`(응답을 `PgResult`로 바꿈), `FakePaymentsClient._next(method, default)`(준비한 결과를 꺼냄).

#### ensure_payments_enabled

- 시그니처: `ensure_payments_enabled()`
- 반환: 없음. 예외: 503 `PAYMENTS_DISABLED`(서버에 토스 키가 없어 결제가 꺼져 있음).
- 요구사항: FR-60

#### get_client

- 시그니처: `get_client()`
- 반환: 설정 `PAYMENTS_CLIENT`가 가리키는 클라이언트 객체. 예외: 503 `PAYMENTS_DISABLED`.
- 요구사항: FR-60, NFR-42

#### masked

- 시그니처: `masked(payment_key)`
- 반환: 로그에 남길 결제 키. 끝 8자만 남긴다. 예외 없음.
- 요구사항: NFR-18

내부 함수

- `_json(raw)`: PG 응답 본문을 JSON으로 읽는다. 못 읽으면 `PgError`.

### 12.3.9 뷰 `orders/views.py`

| 클래스 | 경로 | HTTP 메서드 | 부르는 서비스 | 요구사항 |
| --- | --- | --- | --- | --- |
| `CartView` | `/api/cart/` | GET | `cart_summary` | FR-20 |
| `CartItemListView` | `/api/cart/items/` | POST | `add_to_cart` | FR-19 |
| `CartItemDetailView` | `/api/cart/items/{id}/` | PATCH, DELETE | `change_cart_quantity`, `remove_cart_item` | FR-21, FR-22 |
| `OrderListView` | `/api/orders/` | GET, POST | `filter_by_status`, `create_order` | FR-23, FR-30, FR-55 |
| `OrderDetailView` | `/api/orders/{order_id}/` | GET | `own_order` | FR-31, FR-34, FR-35 |
| `OrderCancelView` | `/api/orders/{order_id}/cancel/` | POST | `cancel_pending_order` | FR-32 |
| `OrderCancelRequestView` | `/api/orders/{order_id}/cancel-request/` | POST | `request_cancel` | FR-33 |
| `PaymentStartView` | `/api/orders/{order_id}/payments/` | POST | `start_payment`, `order_name` | FR-25, FR-29 |
| `PaymentConfirmView` | `/api/payments/confirm/` | POST | `confirm_payment` | FR-26, FR-27 |
| `PaymentFailView` | `/api/payments/fail/` | POST | `fail_payment` | FR-28 |
| `AdminView` | (경로 없음) | | 관리자 주문 뷰의 부모. `IsAuthenticated`와 `IsAdminRole`을 건다 | NFR-10 |
| `AdminOrderListView` | `/api/admin/orders/` | GET | `filter_by_status` | FR-44, FR-45, FR-57 |
| `AdminOrderDetailView` | `/api/admin/orders/{order_id}/` | GET | `admin_order` | FR-46 |
| `AdminPrepareView` | `/api/admin/orders/{order_id}/prepare/` | POST | `prepare` | FR-47 |
| `AdminShipView` | `/api/admin/orders/{order_id}/ship/` | POST | `ship` | FR-48 |
| `AdminDeliverView` | `/api/admin/orders/{order_id}/deliver/` | POST | `deliver` | FR-49 |
| `AdminCancelApproveView` | `/api/admin/orders/{order_id}/cancel-approve/` | POST | `approve_cancel` | FR-50 |
| `AdminCancelRejectView` | `/api/admin/orders/{order_id}/cancel-reject/` | POST | `reject_cancel` | FR-51 |

- 관리자 뷰는 바꾼 뒤 관리자 주문 상세를 같은 모양으로 돌려준다. 내부 함수 `_admin_detail(order)`가 그 응답을 만든다.

### 12.3.10 시리얼라이저 `orders/serializers.py`

| 클래스 | 맡는 일 |
| --- | --- |
| `CartAddSerializer` | 장바구니 담기 입력 검증(옵션 ID, 수량 1 이상) |
| `CartQuantitySerializer` | 수량 변경 입력 검증 |
| `CartItemRefSerializer` | 담기·수량 변경 응답. 항목 ID, 옵션 ID, 수량 |
| `CartLineSerializer` | 장바구니 조회의 항목 한 줄. 지금 가격, 소계, 살 수 있는지를 붙인다 |
| `CartSerializer` | 장바구니 조회 응답. 항목 목록과 금액 합계 |
| `OrderAddressSerializer` | 주문할 때 새로 적는 배송지 입력 검증 |
| `OrderCreateSerializer` | 주문 생성 입력 검증. 저장된 배송지 ID와 새 주소 가운데 정확히 하나만 받는다 |
| `CancelRequestSerializer` | 취소 요청 사유 입력 검증 |
| `OrderItemLineSerializer` | 주문 상세의 항목 한 줄과 소계 |
| `PaymentLineSerializer` | 주문 상세의 결제 기록 한 줄 |
| `OrderDetailSerializer` | 회원용 주문 상세 응답. 배송 정보, 조회 주소, 할 수 있는 동작(`can_pay`, `can_cancel`, `can_request_cancel`)을 붙인다 |
| `OrderSummarySerializer` | 회원용 주문 목록 한 줄. 항목 수와 첫 원두 이름 |
| `ConfirmSerializer` | 결제 승인 확인 입력 검증(`paymentKey`, `orderId`, `amount`) |
| `FailSerializer` | 결제창 실패 입력 검증. 모든 필드가 선택이다 |
| `ShipSerializer` | 송장 등록 입력 검증(택배사 코드, 송장 번호 형식) |
| `AdminOrderSummarySerializer` | 관리자 주문 목록 한 줄. 회원 이메일과 이름을 붙인다 |
| `AdminPaymentLineSerializer` | 관리자용 결제 기록 한 줄. 결제 키는 끝 8자만 보인다 |
| `AdminOrderDetailSerializer` | 관리자 주문 상세 응답. 회원 정보와 지금 상태에서 할 수 있는 동작(`allowed_actions`)을 붙인다 |
