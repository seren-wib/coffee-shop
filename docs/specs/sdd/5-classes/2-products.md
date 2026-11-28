## 5.2 products 앱

원두, 옵션, 재고, 판매 상태. 4절의 "원두 조회", "관리자 원두·재고" 부품을 구현한다.

### 5.2.1 모델 `products/models.py`

| 클래스 | 맡는 일 | 테이블 | 직접 정의한 메서드 |
| --- | --- | --- | --- |
| `RoastLevel` | 로스팅 정도 열거형 | | |
| `WeightSize` | 용량 열거형 | | |
| `GrindType` | 분쇄 방식 열거형 | | |
| `SalesStatus` | 판매 상태 열거형. `ON_SALE`, `SOLD_OUT`, `STOPPED` | | |
| `Product` | 원두 한 종 | `products` | |
| `ProductOption` | 원두의 옵션 한 건(용량 × 분쇄 방식)과 그 재고 | `product_options` | `price`(속성): 기본 가격 + 추가 금액. 저장하지 않고 그때 계산한다(DR-4) |

`products/origins.py`는 원산지 고정 목록을 담은 상수 모듈이다. 클래스와 함수가 없다.

### 5.2.2 서비스 모듈 `products/services.py`

재고(`product_options.stock_quantity`)와 판매 상태(`products.sales_status`)를 바꾸는 함수는 이 모듈에만 있다. 모든 변경은 조건부 UPDATE다.

#### decrease_stock

- 시그니처: `decrease_stock(option_id: int, quantity: int) -> None`
- 반환: 없음. 재고가 0이 되면 판매 중인 원두를 품절로 바꾼다. 예외: 400 `VALIDATION_ERROR`(수량이 0 이하), 409 `OUT_OF_STOCK`(재고 부족. 없는 옵션도 조건부 UPDATE가 0행이라 같은 오류다).
- 요구사항: DR-5, DR-6, NFR-14, NFR-15

#### increase_stock

- 시그니처: `increase_stock(option_id: int, quantity: int) -> None`
- 반환: 없음. 품절이던 원두를 판매 중으로 되돌린다. 판매 중지 원두는 그대로 둔다. 예외: 400 `VALIDATION_ERROR`(수량이 0 이하), 404 `NOT_FOUND`.
- 요구사항: DR-6, DR-7, DR-21

#### set_stock

- 시그니처: `set_stock(option_id: int, quantity: int) -> None`
- 반환: 없음. 재고를 그 값으로 정하고 0이면 품절, 0보다 크면 판매 중으로 맞춘다. 예외: 400 `VALIDATION_ERROR`(음수), 404 `NOT_FOUND`.
- 요구사항: FR-41, DR-6

#### stop_sales

- 시그니처: `stop_sales(product_id: int) -> None`
- 반환: 없음. 판매 중 또는 품절을 판매 중지로 바꾼다. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(이미 판매 중지).
- 요구사항: FR-42, DR-7

#### resume_sales

- 시그니처: `resume_sales(product_id: int) -> None`
- 반환: 없음. 판매 중지를 풀어 재고가 있거나 옵션이 없으면 판매 중, 아니면 품절로 바꾼다. 예외: 404 `NOT_FOUND`, 409 `INVALID_STATE`(판매 중지가 아님).
- 요구사항: FR-43

#### add_option

- 시그니처: `add_option(product_id: int, weight_size: str, grind_type: str, extra_price: int = 0, stock_quantity: int = 0) -> ProductOption`
- 반환: 만든 `ProductOption`. 재고 0으로 넣은 뒤 `set_stock`으로 재고를 정한다. 예외: 404 `NOT_FOUND`(없는 원두), 409 `DUPLICATE_OPTION`(같은 용량·분쇄 방식이 이미 있음).
- 요구사항: FR-39

#### update_option

- 시그니처: `update_option(product_id: int, option_id: int, extra_price: int | None = None, stock_quantity: int | None = None) -> None`
- 반환: 없음. 온 값만 바꾼다. 재고는 `set_stock`으로 바꾼다. 예외: 404 `NOT_FOUND`(그 원두의 옵션이 아님).
- 요구사항: FR-40, FR-41

내부 함수

- `_not_found()`: 404 `NOT_FOUND` 오류를 만든다.
- `_invalid_quantity()`: 400 `VALIDATION_ERROR` 오류를 만든다.
- `_product_id_of(option_id)`: 옵션이 속한 원두 ID를 찾는다. 없으면 404.
- `_mark_sold_out_if_empty(product_id)`: 재고 있는 옵션이 하나도 없으면 판매 중을 품절로 바꾼다.
- `_mark_on_sale_if_sold_out(product_id)`: 품절을 판매 중으로 바꾼다.
- `_invalid_state_or_not_found(product_id)`: 원두가 없으면 404, 있으면 409 `INVALID_STATE` 오류를 만든다.

### 5.2.3 조회 모듈 `products/queries.py`

읽기 전용 쿼리셋을 만든다. 트랜잭션을 열지 않는다.

#### ordered_options

- 시그니처: `ordered_options()`
- 반환: 용량, 분쇄 방식 순으로 정렬한 `ProductOption` 쿼리셋. 예외 없음.
- 요구사항: FR-6

#### customer_products

- 시그니처: `customer_products()`
- 반환: 판매 중지를 뺀 `Product` 쿼리셋(옵션 포함, 최신순). 예외 없음.
- 요구사항: FR-1, FR-6

#### filter_customer_products

- 시그니처: `filter_customer_products(params)`
- 반환: `params`(쿼리 문자열)의 검색어와 필터를 모두 AND로 건 쿼리셋. 항목마다 `lowest_price`가 붙는다. 예외: 400 `VALIDATION_ERROR`(가격이 음수이거나 정수가 아님, 최저가가 최고가보다 큼, 모르는 로스팅 정도).
- 요구사항: FR-1 ~ FR-5

#### admin_products

- 시그니처: `admin_products(params)`
- 반환: 판매 중지를 포함한 모든 `Product` 쿼리셋. 항목마다 `option_count`, `total_stock`이 붙고 이름 검색과 판매 상태 필터를 건다. 예외: 400 `VALIDATION_ERROR`(모르는 판매 상태).
- 요구사항: FR-36, FR-56

#### admin_product_detail

- 시그니처: `admin_product_detail()`
- 반환: 옵션을 정렬해 붙인 `Product` 쿼리셋. 예외 없음.
- 요구사항: FR-37 ~ FR-41

내부 함수

- `_rank(field, values)`: 열거형 값의 순서대로 정렬하는 `Case` 식을 만든다.
- `_price_param(params, name)`: 가격 조건을 정수로 읽는다. 음수이거나 정수가 아니면 400.

### 5.2.4 뷰 `products/views.py`, `products/admin_views.py`

| 클래스 | 경로 | HTTP 메서드 | 부르는 함수 | 요구사항 |
| --- | --- | --- | --- | --- |
| `ProductListView` | `/api/products/` | GET | `filter_customer_products` | FR-1 ~ FR-5 |
| `ProductDetailView` | `/api/products/{id}/` | GET | `customer_products` | FR-6 |
| `AdminProductListView` | `/api/admin/products/` | GET, POST | `admin_products`, 등록은 `AdminProductSerializer.save` | FR-36, FR-37, FR-56 |
| `AdminProductDetailView` | `/api/admin/products/{id}/` | GET, PATCH | `admin_product_detail` | FR-38 |
| `AdminOptionCreateView` | `/api/admin/products/{id}/options/` | POST | `add_option` | FR-39 |
| `AdminOptionUpdateView` | `/api/admin/products/{id}/options/{oid}/` | PATCH | `update_option` | FR-40, FR-41 |
| `AdminStopSalesView` | `/api/admin/products/{id}/stop/` | POST | `stop_sales` | FR-42 |
| `AdminResumeSalesView` | `/api/admin/products/{id}/resume/` | POST | `resume_sales` | FR-43 |

- `ProductListView`, `ProductDetailView`는 공개 경로(`AllowAny`)다(NFR-9). 관리자 뷰 여섯 개는 `IsAuthenticated`와 `IsAdminRole`을 함께 건다(NFR-10).
- 관리자 뷰는 바꾼 뒤 원두 상세를 같은 모양으로 돌려준다. 내부 함수 `_detail(product_id, status_code=200)`이 그 응답을 만든다.

### 5.2.5 시리얼라이저 `products/serializers.py`

| 클래스 | 맡는 일 |
| --- | --- |
| `OptionSerializer` | 고객용 옵션 한 줄. 가격과 살 수 있는지(`is_available`)를 붙인다 |
| `ProductListSerializer` | 고객용 원두 목록 한 줄 |
| `ProductDetailSerializer` | 고객용 원두 상세와 옵션 목록 |
| `AdminOptionSummarySerializer` | 관리자 목록에 붙는 옵션 요약 |
| `AdminProductListSerializer` | 관리자 원두 목록 한 줄. 옵션 수와 재고 합계를 붙인다 |
| `AdminProductSerializer` | 원두 등록·수정 입력 검증(원산지, 이미지 주소)과 관리자 상세 응답 |
| `AdminOptionCreateSerializer` | 옵션 추가 입력 검증 |
| `AdminOptionUpdateSerializer` | 옵션 수정 입력 검증. 추가 금액과 재고만 받는다 |

### 5.2.6 관리 명령

| 클래스 | 파일 | 메서드 | 맡는 일 | 요구사항 |
| --- | --- | --- | --- | --- |
| `Command` | `products/management/commands/seed_demo.py` | `add_arguments(parser)`, `handle(*args, **opts)` | 시연용 원두, 회원, 주문 데이터를 만든다 | NFR-3 |

내부 메서드: `_products`, `_stop_some`, `_members`, `_orders`, `_pick_items`, `_order`, `_payment`. 각각 원두, 판매 중지 표본, 회원, 주문 묶음, 주문 항목 고르기, 주문 한 건, 결제 기록을 만든다.
