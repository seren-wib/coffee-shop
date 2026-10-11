# 2.2 클래스 명세 (Class Specification)

커피 원두 쇼핑몰 시스템의 백엔드 도메인 클래스 명세서이다. SDD(소프트웨어 설계 명세서) 2.2절에 해당하며, 클래스 다이어그램(`class-diagram.drawio.svg`), 요구사항 정의(`requirements.md`), 데이터베이스 테이블 명세(`table-specification.md`)를 기준으로 각 클래스의 **CRC(Class-Responsibility-Collaboration) 카드**와 **클래스 상세 명세(속성, 메서드, 비즈니스 규칙 및 알고리즘 개요)**를 기술한다.

---

## 1. 개요 (Overview)

### 1.1 설계 원칙
1. **도메인 모델 중심 설계**: 비즈니스 규칙과 상태 변경 로직을 도메인 모델 내부에 캡슐화하여 서비스 레이어의 중복을 방지한다.
2. **트랜잭션 일관성**: 주문 생성(`create_order`), 재고 차감(`decrease_stock`), 주문 취소 및 환불 처리(`process_cancellation`) 시 데이터 일관성을 위해 단일 트랜잭션으로 처리한다.
3. **불변 스냅샷(Audit Snapshotting)**: 원두 가격이나 상품명이 변경되더라도 기존 주문 내역의 정확성을 보장하기 위해, 주문 시점의 상품명·옵션·단가를 `OrderItem`에 스냅샷으로 보존한다.
4. **단일 배송지 및 주문 통합**: 주문 1건당 단일 배송지를 지원하는 구조에 맞추어 `Order` 모델에 배송 및 운송장 정보(`courier_name`, `tracking_number`, `shipped_at`, `delivered_at`)를 통합하여 주문-배송 상태 불일치 문제를 원천 차단한다.
5. **결제 재시도 이력 보존(1:N)**: 결제 실패 후 재시도(`Retry Payment`) 시 이전 실패 내역과 새로운 결제 시도를 모두 추적할 수 있도록 `Order 1 — 0..* Payment` 관계를 구성한다.

### 1.2 도메인 클래스 목록

| 클래스명 | 계층 / 모듈 | 주 역할 및 책임 요약 |
|---|---|---|
| `User` | 계정 관리 (`users`) | 회원/관리자 계정 생성, 자격 증명 검증(로그인), 비밀번호 변경, 프로필 수정 |
| `UserAddress` | 배송지 관리 (`users`) | 회원 배송지 등록/수정/삭제, 기본 배송지 설정 및 관리 |
| `Product` | 상품 관리 (`products`) | 원두 기본 정보 관리, 판매 상태 변경, 옵션별 최종 단가 계산 |
| `ProductOption` | 재고 관리 (`products`) | 용량/분쇄도 옵션 정의, 원자적 재고 차감/증가, 품절 판별 |
| `CartItem` | 장바구니 (`orders`) | 장바구니 품목 수량 조정, 품목별 소계(Subtotal) 계산 |
| `Order` | 주문/배송 (`orders`) | 주문 집합체 루트(Aggregate Root), 주문 생성, 취소 요청/승인 처리, 배송 추적 등록, 상태 전이 |
| `OrderItem` | 주문 상세 (`orders`) | 주문 시점의 상품명, 패키지 용량, 분쇄도, 구매 단가 스냅샷 보존 및 소계 계산 |
| `Payment` | 결제 관리 (`orders`) | PG 결제 승인 결과 저장, 결제 실패 사유 기록, 취소(환불) 처리 |

### 1.3 도메인 열거형 (Domain Enumerations)

| 열거형 (Enum) | 정의 값 (Values) | 설명 |
|---|---|---|
| `Role` | `MEMBER`, `ADMIN` | 사용자 권한 등급 (일반 회원, 시스템 관리자) |
| `SalesStatus` | `ON_SALE`, `SOLD_OUT`, `STOPPED` | 원두 판매 상태 (판매 중, 품절, 판매 중지) |
| `GrindType` | `WHOLE_BEAN`, `HAND_DRIP`, `ESPRESSO` | 원두 분쇄도 (홀빈/원두 상태, 핸드드립용, 에스프레소용) |
| `OrderStatus` | `PENDING`, `PAID`, `PREPARING`, `SHIPPED`, `DELIVERED`, `CANCEL_REQUESTED`, `CANCELLED` | 주문 생애주기 상태 (결제 대기, 결제 완료, 상품 준비 중, 배송 중, 배송 완료, 취소 요청, 주문 취소) |
| `PaymentStatus` | `READY`, `SUCCESS`, `FAILED`, `CANCELLED` | 결제 트랜잭션 상태 (결제 대기, 결제 성공, 결제 실패, 결제 취소) |
| `PaymentMethod` | `CARD`, `EASY_PAY`, `TRANSFER` | 결제 수단 (신용/체크카드, 간편결제, 계좌이체) |

---

## 2. CRC 카드 (Class-Responsibility-Collaboration Cards)

### 2.1 `User`
```
+--------------------------------------------------------------------------+
| Class: User                                                              |
| Role: Entity / Aggregate Root (User Context)                             |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. 신규 회원 계정 등록 (비밀번호 해싱)    | UserAddress                   |
| 2. 사용자 로그인 자격증명 검증           | CartItem                      |
| 3. 비밀번호 확인 및 안전한 변경          | Order                         |
| 4. 사용자 기본 프로필(이름, 연락처) 갱신  |                               |
| 5. 관리자/회원 권한 식별                 |                               |
+------------------------------------------+-------------------------------+
```

### 2.2 `UserAddress`
```
+--------------------------------------------------------------------------+
| Class: UserAddress                                                       |
| Role: Entity (User Context)                                              |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. 회원의 배송지 정보(수령인, 주소) 유지 | User                          |
| 2. 기본 배송지 단일 지정 및 기존 해제    | Order (주문 시 참조)          |
| 3. 배송지 정보 수정                      |                               |
+------------------------------------------+-------------------------------+
```

### 2.3 `Product`
```
+--------------------------------------------------------------------------+
| Class: Product                                                           |
| Role: Entity / Aggregate Root (Catalog Context)                          |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. 원두 마스터 메타데이터 유지 및 수정   | ProductOption                 |
| 2. 원두 판매 상태(판매중/품절/중지) 변경 |                               |
| 3. 특정 옵션과의 결합 가격 계산          |                               |
| 4. 옵션 전량 품절 시 상태 자동 연동      |                               |
+------------------------------------------+-------------------------------+
```

### 2.4 `ProductOption`
```
+--------------------------------------------------------------------------+
| Class: ProductOption                                                     |
| Role: Entity (Catalog / Inventory Context)                               |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. 용량/분쇄도별 추가 금액 및 재고 유지   | Product                       |
| 2. 주문 시 원자적 재고 차감 (재고 부족 방지)| CartItem                     |
| 3. 취소/환불 시 재고 수량 복원           | OrderItem                     |
| 4. 요청 수량에 대한 주문 가능 여부 검증   | Order                         |
+------------------------------------------+-------------------------------+
```

### 2.5 `CartItem`
```
+--------------------------------------------------------------------------+
| Class: CartItem                                                          |
| Role: Entity (Cart Context)                                              |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. 사용자가 담은 옵션 및 수량 유지       | User                          |
| 2. 장바구니 담긴 품목 수량 변경          | ProductOption                 |
| 3. 품목별 소계(단가 * 수량) 계산         | Product                       |
+------------------------------------------+-------------------------------+
```

### 2.6 `Order`
```
+--------------------------------------------------------------------------+
| Class: Order                                                             |
| Role: Entity / Aggregate Root (Fulfillment Context)                      |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. 장바구니 품목 기반 주문 및 상세 생성   | User                          |
| 2. 총 상품 금액 및 배송비 합산 검증      | OrderItem                     |
| 3. 고객의 주문 취소 요청 접수            | ProductOption                 |
| 4. 관리자의 취소 승인/반려 및 재고 롤백  | Payment                       |
| 5. 송장번호 등록 및 배송 완료 상태 갱신  | CartItem (주문 후 삭제)       |
+------------------------------------------+-------------------------------+
```

### 2.7 `OrderItem`
```
+--------------------------------------------------------------------------+
| Class: OrderItem                                                         |
| Role: Entity / Value Object Snapshot (Fulfillment Context)               |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. 주문 시점의 상품명, 옵션, 단가 스냅샷  | Order                         |
| 2. 구매 품목별 부분합(orderPrice*수량) 계산| ProductOption                |
+------------------------------------------+-------------------------------+
```

### 2.8 `Payment`
```
+--------------------------------------------------------------------------+
| Class: Payment                                                           |
| Role: Entity (Payment Context)                                           |
+--------------------------------------------------------------------------+
| Responsibilities (책임)                  | Collaborators (협력자)        |
+------------------------------------------+-------------------------------+
| 1. PG 승인 번호 및 결제 성공 내역 기록   | Order                         |
| 2. 결제 실패 시 사유 기록 및 재시도 허용 |                               |
| 3. 관리자 취소 승인 시 PG 결제 취소 기록 |                               |
| 4. 결제 완료 시 주문 상태를 PAID로 전이  |                               |
+------------------------------------------+-------------------------------+
```

---

## 3. 클래스 상세 명세 (Class Descriptions)

---

### 3.1 `User` 클래스 명세

- **패키지/모듈**: `backend.users.models`
- **설명**: 쇼핑몰을 이용하는 회원 및 관리자의 기본 계정 정보를 관리하는 엔티티이다. 비밀번호는 단방향 암호화 해시로 저장하며, 인증 및 권한 확인의 주체이다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `user_id` | `int` | Auto | PK, Auto Increment | 사용자 고유 식별자 |
| `-` | `email` | `String` | None | Unique, Max 255 | 로그인용 이메일 주소 |
| `-` | `password_hash` | `String` | None | Max 255 | 단방향 해싱 암호화된 비밀번호 |
| `-` | `user_name` | `String` | None | Max 100 | 사용자 본명 또는 표시 이름 |
| `-` | `phone_number` | `String` | None | Max 20 | 연락처 전화번호 |
| `-` | `role` | `Role` | `Role.MEMBER` | Choices (`MEMBER`, `ADMIN`) | 사용자 역할 권한 |
| `-` | `created_at` | `DateTime` | Now | Auto Add | 회원가입 일시 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `register(email, password, user_name, phone_number, role=MEMBER)` | `User` | **회원가입 팩토리 메서드**: 비밀번호를 안전한 해시 함수(`make_password`)로 변환한 후 신규 사용자 인스턴스를 생성하여 데이터베이스에 저장한다. |
| `+` | `login(password: String)` | `bool` | **로그인 자격증명 검증**: 입력된 평문 비밀번호를 기존의 `password_hash`와 대조(`check_password`)하여 일치 여부를 반환한다. |
| `+` | `update_profile(name: String, phone: String)` | `void` | **프로필 수정**: 이름과 연락처를 갱신하고 변경된 필드를 영속화한다. |
| `+` | `change_password(old_pw: String, new_pw: String)` | `bool` | **비밀번호 변경**: 기존 비밀번호(`old_pw`) 일치 여부를 먼저 검증한 뒤, 검증 통과 시 새 비밀번호(`new_pw`)를 해싱하여 저장한다. |

#### 비즈니스 규칙 및 제약사항
- 이메일은 시스템 전체에서 중복될 수 없다 (`UNIQUE`).
- 비밀번호 평문은 메모리상에만 일시 존재하며 데이터베이스에 직접 저장될 수 없다.
- 주문 이력이 존재하는 회원은 데이터 무결성을 위해 외래키가 보호(`PROTECT`)되어 강제 삭제되지 않는다.

---

### 3.2 `UserAddress` 클래스 명세

- **패키지/모듈**: `backend.users.models`
- **설명**: 회원이 주문 시 사용할 수 있도록 사전에 등록해 둔 배송지 목록을 관리하는 엔티티이다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `address_id` | `int` | Auto | PK, Auto Increment | 배송지 고유 식별자 |
| `-` | `user` | `User` | None | FK (CASCADE) | 배송지를 소유한 회원 참조 |
| `-` | `recipient_name` | `String` | None | Max 100 | 수령인 성명 |
| `-` | `recipient_phone` | `String` | None | Max 20 | 수령인 연락처 |
| `-` | `zipcode` | `String` | None | Max 10 | 5자리 우편번호 |
| `-` | `base_address` | `String` | None | Max 255 | 기본 도로명/지번 주소 |
| `-` | `detail_address` | `String` | None | Nullable, Max 255 | 상세 주소 (동/호수 등) |
| `-` | `is_default` | `bool` | `False` | Boolean | 기본 배송지 여부 플래그 |
| `-` | `created_at` | `DateTime` | Now | Auto Add | 배송지 등록 일시 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `set_default()` | `void` | **기본 배송지 지정**: 동일 회원의 다른 모든 배송지의 `is_default`를 `False`로 일괄 해제한 뒤, 현재 배송지를 `True`로 지정하여 저장한다. |
| `+` | `update_address(...)` | `void` | **배송지 수정**: 전달된 파라미터(수령인, 연락처, 주소, 기본 여부 등)를 반영하여 갱신한다. |

#### 비즈니스 규칙 및 제약사항
- 한 회원당 `is_default == True`인 배송지는 최대 1개만 유지된다.
- 회원이 삭제될 경우 등록된 배송지 목록은 함께 삭제된다 (`ON DELETE CASCADE`).

---

### 3.3 `Product` 클래스 명세

- **패키지/모듈**: `backend.products.models`
- **설명**: 판매하는 커피 원두의 마스터 정보를 관리하는 엔티티이다. 원산지, 로스팅 정도, 기본 가격 및 전반적인 판매 상태를 유지한다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `product_id` | `int` | Auto | PK, Auto Increment | 상품 마스터 고유 식별자 |
| `-` | `name` | `String` | None | Max 200 | 원두 상품명 (예: 에티오피아 예가체프 G1) |
| `-` | `origin` | `String` | None | Max 100 | 원산지 국가/지역 |
| `-` | `roast_level` | `String` | None | Max 50 | 로스팅 정도 (Light, Medium, Dark 등) |
| `-` | `base_price` | `int` | None | Non-negative (>= 0) | 기본 상품 단가 (KRW) |
| `-` | `tasting_notes` | `String` | None | Nullable, Text | 컵 노트 / 향미 특징 |
| `-` | `description` | `String` | None | Nullable, Text | 상세 상품 설명 |
| `-` | `sales_status` | `SalesStatus` | `ON_SALE` | Choices (`ON_SALE`, `SOLD_OUT`, `STOPPED`) | 판매 가능 상태 |
| `-` | `created_at` | `DateTime` | Now | Auto Add | 상품 등록 일시 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `update_info(...)` | `void` | **상품 정보 수정**: 원두명, 원산지, 로스팅, 기본가, 설명 등의 정보를 갱신한다. |
| `+` | `change_sales_status(status: SalesStatus)` | `void` | **판매 상태 변경**: 관리자 또는 재고 연동 로직에 의해 상품 판매 상태를 변경한다. |
| `+` | `calculate_price(option: ProductOption)` | `int` | **옵션 결합 단가 계산**: `base_price + option.extra_price`를 합산하여 최종 판매 단가를 계산한다. |

---

### 3.4 `ProductOption` 클래스 명세

- **패키지/모듈**: `backend.products.models`
- **설명**: 원두 상품의 구체적인 판매 단위(용량 패키지, 분쇄도)와 옵션별 추가 금액 및 실시간 재고를 관리하는 엔티티이다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `option_id` | `int` | Auto | PK, Auto Increment | 옵션 SKU 고유 식별자 |
| `-` | `product` | `Product` | None | FK (CASCADE) | 상위 원두 상품 참조 |
| `-` | `weight_size` | `String` | None | Max 50 | 포장 용량 (예: 200g, 500g, 1kg) |
| `-` | `grind_type` | `GrindType` | `WHOLE_BEAN` | Choices (`WHOLE_BEAN`, `HAND_DRIP`, `ESPRESSO`) | 분쇄도 설정 |
| `-` | `extra_price` | `int` | `0` | Non-negative (>= 0) | 옵션 추가 금액 (KRW) |
| `-` | `stock_quantity` | `int` | `0` | Non-negative (>= 0) | 현재 보유 물리 재고 수량 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `decrease_stock(quantity: int)` | `bool` | **원자적 재고 차감**: 현재 `stock_quantity >= quantity`를 검증하고, 재고가 충분하면 `stock_quantity`를 차감한 뒤 저장한다. 차감 후 해당 상품의 모든 옵션 재고가 0이 되면 부모 상품 상태를 `SOLD_OUT`으로 전환한다. 성공 시 `True`, 재고 부족 시 `False` 반환. |
| `+` | `increase_stock(quantity: int)` | `void` | **재고 보충/복원**: 취소/반품 또는 관리자 입고 시 재고를 가산한다. 부모 상품이 `SOLD_OUT` 상태였고 재고가 1 이상이 되면 부모 상태를 `ON_SALE`로 자동 복구한다. |
| `+` | `is_available(quantity: int)` | `bool` | **구매 가능 검증**: 요청 수량만큼의 재고가 남아있는지 확인한다 (`stock_quantity >= quantity`). |

#### 비즈니스 규칙 및 제약사항
- 동일 상품 내에서 `(product, weight_size, grind_type)`의 조합은 중복될 수 없다 (`UNIQUE`).
- 재고 수량은 0 미만으로 감소할 수 없다 (`CHECK stock_quantity >= 0`).

---

### 3.5 `CartItem` 클래스 명세

- **패키지/모듈**: `backend.orders.models`
- **설명**: 회원이 구매를 결정하기 전 임시로 담아둔 장바구니 항목 엔티티이다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `cart_item_id` | `int` | Auto | PK, Auto Increment | 장바구니 항목 고유 식별자 |
| `-` | `user` | `User` | None | FK (CASCADE) | 장바구니 소유 회원 |
| `-` | `option` | `ProductOption` | None | FK (CASCADE) | 선택한 원두 옵션 SKU |
| `-` | `quantity` | `int` | `1` | Positive (> 0) | 담은 수량 |
| `-` | `created_at` | `DateTime` | Now | Auto Add | 장바구니 추가 일시 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `update_quantity(quantity: int)` | `void` | **수량 변경**: 수량이 1 이상인 경우 새로운 수량으로 변경 후 저장한다. |
| `+` | `get_subtotal()` | `int` | **소계 계산**: `(option.product.base_price + option.extra_price) * quantity`를 계산하여 반환한다. |

#### 비즈니스 규칙 및 제약사항
- 한 사용자의 장바구니에 동일한 `ProductOption`은 1개의 행만 존재하며, 중복 추가 시 행이 추가되지 않고 기존 수량이 합산된다 (`UNIQUE (user, option)`).

---

### 3.6 `Order` 클래스 명세

- **패키지/모듈**: `backend.orders.models`
- **설명**: 쇼핑몰 구매 트랜잭션의 집합체 루트(Aggregate Root) 엔티티이다. 결제 금액 계산, 주문 상태 머신 전이, 고객 취소 요청 접수, 관리자 취소 승인/반려, 배송 및 운송장 추적 정보를 총괄한다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `order_id` | `String` | None | PK, Max 50 | 고유 비즈니스 주문 번호 (예: ORD-2026-X) |
| `-` | `user` | `User` | None | FK (PROTECT) | 주문을 접수한 회원 |
| `-` | `order_status` | `OrderStatus` | `PENDING` | Choices | 주문 및 배송 종합 상태 |
| `-` | `total_product_amt` | `int` | None | Non-negative (>= 0) | 주문 상품 총액 합계 (KRW) |
| `-` | `shipping_fee` | `int` | `0` | Non-negative (>= 0) | 적용된 배송비 (기본 3,000원 등) |
| `-` | `final_payment_amt` | `int` | None | Non-negative (>= 0) | 최종 결제 대상 금액 (`total + fee`) |
| `-` | `recipient_name` | `String` | None | Max 100 | 주문 시점의 수령인 성명 스냅샷 |
| `-` | `recipient_phone` | `String` | None | Max 20 | 주문 시점의 수령인 연락처 스냅샷 |
| `-` | `shipping_address` | `String` | None | Max 255 | 주문 시점의 전체 배송 주소 스냅샷 |
| `-` | `courier_name` | `String` | None | Nullable, Max 50 | 발송 택배사 명칭 (출고 전 NULL) |
| `-` | `tracking_number` | `String` | None | Nullable, Max 100 | 운송장 번호 (출고 전 NULL) |
| `-` | `ordered_at` | `DateTime` | Now | Auto Add | 주문 접수 일시 |
| `-` | `shipped_at` | `DateTime` | None | Nullable | 출고/발송 일시 |
| `-` | `delivered_at` | `DateTime` | None | Nullable | 배송 완료 일시 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `create_order(user, order_id, recipient_name, recipient_phone, shipping_address, cart_items, shipping_fee=3000)` | `Order` | **주문 생성 (Class Method, Atomic)**: <br>1. 단일 데이터베이스 트랜잭션(`@transaction.atomic`) 시작.<br>2. 장바구니의 각 품목에 대해 단가 계산 및 `option.decrease_stock()` 원자적 호출 (재고 부족 시 `ValueError` 발생 후 롤백).<br>3. 품목별 불변 스냅샷 인스턴스(`OrderItem`) 준비.<br>4. 주문 마스터(`Order`) 인스턴스를 생성하고 상태를 `PENDING`으로 설정.<br>5. `OrderItem` 저장 및 결제 진행된 `CartItem` 삭제 후 생성된 `Order` 반환. |
| `+` | `request_cancellation()` | `bool` | **회원 주문 취소 요청**: <br>- `order_status == PENDING`인 경우: 즉시 `CANCELLED` 처리 및 재고 롤백 수행.<br>- `order_status in [PAID, PREPARING]`인 경우: 관리자 확인이 필요하므로 상태를 `CANCEL_REQUESTED`로 전이.<br>- 배송 시작 이후(`SHIPPED`, `DELIVERED`)는 취소 불가 (`False` 반환). |
| `+` | `process_cancellation(approved: bool)` | `bool` | **관리자 취소 요청 처리 (Atomic)**: <br>- 현재 상태가 `CANCEL_REQUESTED`인지 확인.<br>- `approved == True`인 경우: 주문 상태를 `CANCELLED`로 변경하고, 모든 `OrderItem`의 재고를 원상 복구(`increase_stock`)하며, 성공된 결제 건(`Payment`)의 `cancel_payment()`를 호출하여 환불 처리.<br>- `approved == False`인 경우: 취소 거절로 간주하여 주문 상태를 `PREPARING`으로 복귀. |
| `+` | `register_tracking(courier: String, tracking_no: String)` | `void` | **송장 등록 및 출고 처리**: 관리자가 택배사와 운송장 번호를 등록하면 `courier_name`, `tracking_number`, `shipped_at`을 설정하고 상태를 `SHIPPED`로 전이한다. |
| `+` | `mark_as_delivered()` | `void` | **배송 완료 처리**: 배송이 완료되면 `delivered_at`을 기록하고 상태를 `DELIVERED`로 전이한다. |
| `+` | `update_status(new_status: OrderStatus)` | `void` | **주문 상태 갱신**: 주문 상태 머신 규칙에 따라 상태를 갱신한다. |
| `+` | `calculate_total()` | `int` | **총 금액 계산**: 상품 금액 합계와 배송비를 합산한 값을 반환한다. |

---

### 3.7 `OrderItem` 클래스 명세

- **패키지/모듈**: `backend.orders.models`
- **설명**: 주문서에 포함된 개별 상품 라인 아이템이다. 주문 이후 마스터 상품의 가격이나 명칭이 수정되더라도 거래 기록이 왜곡되지 않도록 주문 시점의 스냅샷을 영구 보존한다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `order_item_id` | `int` | Auto | PK, Auto Increment | 주문 상세 라인 아이템 고유 식별자 |
| `-` | `order` | `Order` | None | FK (CASCADE) | 부모 주문 참조 |
| `-` | `option` | `ProductOption` | None | FK (PROTECT) | 원본 옵션 SKU 참조 |
| `-` | `product_name` | `String` | None | Max 200 | 주문 시점의 원두 상품명 스냅샷 |
| `-` | `weight_size` | `String` | None | Max 50 | 주문 시점의 패키지 용량 스냅샷 |
| `-` | `grind_type` | `String` | None | Max 50 | 주문 시점의 분쇄도 명칭 스냅샷 |
| `-` | `order_price` | `int` | None | Non-negative (>= 0) | 주문 시점의 옵션 결합 구매 단가 (KRW) |
| `-` | `quantity` | `int` | None | Positive (> 0) | 구매 수량 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `calculate_subtotal()` | `int` | **품목 소계 계산**: `order_price * quantity`를 계산하여 반환한다. |

---

### 3.8 `Payment` 클래스 명세

- **패키지/모듈**: `backend.orders.models`
- **설명**: 외부 결제대행사(PG)를 통한 결제 시도 및 승인/취소 트랜잭션을 기록하는 엔티티이다. 1건의 주문에 대해 결제 실패 후 재시도가 발생할 수 있으므로 `Order`와 1:N 관계를 맺는다.

#### 속성 (Attributes)
| 가시성 | 속성명 | 타입 | 기본값 | 제약사항 | 설명 |
|---|---|---|---|---|---|
| `-` | `payment_id` | `int` | Auto | PK, Auto Increment | 결제 트랜잭션 고유 식별자 |
| `-` | `order` | `Order` | None | FK (CASCADE) | 대상 주문 참조 (1:N 다중도) |
| `-` | `pg_provider` | `String` | None | Max 50 | PG사 식별자 (예: TOSS, INICIS, NAVERPAY) |
| `-` | `pg_tid` | `String` | None | Nullable, Unique, Max 100 | PG사 발급 고유 승인 거래 번호 |
| `-` | `payment_method` | `PaymentMethod` | None | Choices | 사용된 결제 수단 (`CARD`, `EASY_PAY`, `TRANSFER`) |
| `-` | `payment_status` | `PaymentStatus` | `READY` | Choices | 결제 진행 상태 (`READY`, `SUCCESS`, `FAILED`, `CANCELLED`) |
| `-` | `paid_amount` | `int` | None | Non-negative (>= 0) | 승인 요청/완료된 결제 금액 (KRW) |
| `-` | `failure_reason` | `String` | None | Nullable, Text | 결제 실패 시 PG사 반환 오류 진단 사유 |
| `-` | `approved_at` | `DateTime` | None | Nullable | PG 최종 승인 일시 |

#### 메서드 (Operations)
| 가시성 | 메서드 시그니처 | 반환형 | 설명 및 알고리즘 개요 |
|---|---|---|---|
| `+` | `process_payment(pg_tid: String)` | `bool` | **결제 승인 완료**: 외부 PG사 승인 성공 콜백 접수 시, `pg_tid`를 저장하고 상태를 `SUCCESS`로 변경하며 승인 일시를 기록한다. 연관된 부모 주문(`order`)의 상태를 `PAID`로 전이시킨다. |
| `+` | `cancel_payment(reason: String)` | `bool` | **결제 취소 및 환불**: 관리자 취소 승인에 따른 환불 처리 시 상태를 `CANCELLED`로 변경하고 취소 사유(`failure_reason`)를 기록한다. |

---

## 4. 핵심 비즈니스 로직 알고리즘 연계 (#17 연계 요약)

클래스 명세에서 정의된 주요 연산 중 다중 객체 상태 변경 및 트랜잭션 정합성이 요구되는 알고리즘의 동작 순서 요약이다. 상세 의사코드 및 제어 흐름은 **#17 메소드 알고리즘 설계**에서 구체화된다.

### 4.1 주문 생성 알고리즘 (`Order.create_order`)
```
Input: user, order_id, recipient info, shipping_address, cart_items, shipping_fee
Output: Order instance

1. [트랜잭션 시작]
2. total_product_amt <- 0
3. order_item_instances <- []
4. FOR EACH item IN cart_items:
     a. unit_price <- item.option.product.base_price + item.option.extra_price
     b. total_product_amt <- total_product_amt + (unit_price * item.quantity)
     c. is_decreased <- item.option.decrease_stock(item.quantity)
     d. IF NOT is_decreased THEN:
          ROLLBACK AND RAISE InsufficientStockException
     e. APPEND OrderItem(option, snapshot_name, snapshot_options, unit_price, quantity) TO order_item_instances
5. final_payment_amt <- total_product_amt + shipping_fee
6. order <- CREATE Order(user, order_id, totals, recipient info, status=PENDING)
7. FOR EACH oi IN order_item_instances:
     oi.order <- order
     SAVE oi
8. DELETE ALL cart_items
9. [트랜잭션 커밋]
10. RETURN order
```

### 4.2 주문 취소 및 환불 알고리즘 (`Order.process_cancellation`)
```
Input: approved (Boolean)
Output: Boolean (성공 여부)

1. IF order.order_status != CANCEL_REQUESTED THEN RETURN False
2. [트랜잭션 시작]
3. IF approved == True THEN:
     a. order.order_status <- CANCELLED
     b. SAVE order
     c. FOR EACH item IN order.items:
          item.option.increase_stock(item.quantity)
     d. FOR EACH payment IN order.payments WHERE payment.payment_status == SUCCESS:
          payment.cancel_payment("Admin approved cancellation request")
4. ELSE (approved == False):
     a. order.order_status <- PREPARING
     b. SAVE order
5. [트랜잭션 커밋]
6. RETURN True
```
