## 4.4 장바구니

`orders` 앱의 `CartItem`과 `orders/services.py`. 회원만 쓴다. 토큰이 없으면 401이고, 화면은 담기를 누른 비회원을 로그인 화면으로 보낸다(SRS 3.3절).

### 4.4.0 금액 계산 함수

```python
SHIPPING_FEE = 3000
FREE_SHIPPING_THRESHOLD = 30000

def shipping_fee_for(product_amount: int) -> int:
    if product_amount == 0:
        return 0
    return 0 if product_amount >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE  # DR-14
```

장바구니(FR-20), 주문 생성(FR-23), 주문 화면(FR-24)이 이 함수 하나를 쓴다. 프론트엔드는 배송비를 계산하지 않고 서버가 준 값을 보인다. 빈 장바구니의 배송비는 0으로 보인다(주문할 항목이 없으므로).

### 4.4.1 장바구니 담기 (FR-19)

- 경로: `POST /api/cart/items/`, 회원.
- 입력: `option_id`, `quantity`(1 이상).
- 처리(`add_to_cart`, 한 트랜잭션):
  1. 옵션을 원두와 함께 읽는다. 없으면 404.
  2. 원두가 `ON_SALE`이 아니면 409 `NOT_AVAILABLE`(DR-8).
  3. 이 회원의 같은 옵션 행이 있으면 `new = 기존 + quantity`, 없으면 `new = quantity`.
  4. `new > stock_quantity`이면 409 `OUT_OF_STOCK`(DR-10). 재고 0 옵션은 여기서 걸린다.
  5. 있으면 `quantity=new`로 UPDATE(200), 없으면 INSERT(201)(DR-9).
- 응답: 201 또는 200, `{cart_item_id, option_id, quantity}`.
- 담는 순간 재고를 잡아 두지 않는다. 재고 차감은 주문 생성 때 한다(SRS 2.6절).

### 4.4.2 장바구니 조회 (FR-20)

- 경로: `GET /api/cart/`, 회원.
- 응답: 200.

```json
{
  "items": [
    {
      "cart_item_id": 7,
      "option_id": 12,
      "product_id": 3,
      "product_name": "에티오피아 예가체프",
      "image_url": null,
      "weight_size": "200G",
      "grind_type": "HAND_DRIP",
      "price": 18000,
      "quantity": 2,
      "subtotal": 36000,
      "stock_quantity": 5,
      "is_available": true
    }
  ],
  "product_amount": 36000,
  "shipping_fee": 0,
  "total_amount": 36000,
  "can_order": true
}
```

- `is_available = 원두 ON_SALE and quantity <= stock_quantity`. 담은 뒤 품절됐거나 재고가 줄어 수량이 넘치면 거짓이다.
- `product_amount = Σ(price × quantity)`, 모든 항목을 더한다(FR-20 검증). 주문 생성도 장바구니 전체를 대상으로 하므로(4.5.3) 같은 기준이다. `is_available=false` 항목이 하나라도 있으면 응답 `can_order=false`이고, 화면은 그 항목을 표시하고 주문하기를 끈다.
- 판매 중지된 원두의 옵션도 장바구니에는 남는다(회원이 직접 뺀다). 그 원두의 상세는 404지만 장바구니 응답은 이름과 가격을 보여준다.

### 4.4.3 수량 변경 (FR-21)

- 경로: `PATCH /api/cart/items/{id}/`, 회원.
- 입력: `quantity`.
- 처리: `quantity < 1`이면 400 `VALIDATION_ERROR`. `quantity > stock_quantity`이면 409 `OUT_OF_STOCK`(DR-10). 그 밖에는 UPDATE.
- 응답: 200, `{cart_item_id, option_id, quantity}`. 화면은 이어서 4.4.2를 다시 불러 금액을 갱신한다.
- 오류: 404(다른 회원 항목).

### 4.4.4 항목 삭제 (FR-22)

- 경로: `DELETE /api/cart/items/{id}/`, 회원.
- 응답: 204. 다른 회원 항목은 404.
