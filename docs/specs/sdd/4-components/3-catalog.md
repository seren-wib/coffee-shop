## 4.3 원두 조회

`products` 앱의 고객용 뷰. 비회원과 회원 모두 쓴다(NFR-9 공개 경로). 판매 중지 원두는 고객에게 없는 것처럼 보인다(FR-1, FR-6).

### 4.3.0 고객용 쿼리셋

```python
def customer_products():
    return (Product.objects
            .exclude(sales_status=SalesStatus.STOPPED)
            .prefetch_related("options")
            .order_by("-created_at", "-product_id"))
```

목록과 상세가 이 함수 하나를 쓴다. 그래서 판매 중지 원두가 목록에서 빠지는 규칙과 상세 404 규칙이 어긋나지 않는다.

### 4.3.1 원두 목록 (FR-1)

- 경로: `GET /api/products/`, 공개.
- 입력: `page`(기본 1). 검색·필터는 4.3.2 ~ 4.3.5.
- 응답: 200, 7.4절 페이지 형식. `results` 항목은 `{product_id, name, origin, roast_level, base_price, lowest_price, image_url, sales_status}`. `lowest_price`는 옵션 가격 중 가장 낮은 값이다(옵션이 없으면 `base_price`).
- 페이지 크기는 20 고정이다. `page_size` 매개변수는 받지 않는다.
- 결과가 없으면 `results: []`, 화면은 "조건에 맞는 원두가 없습니다"를 보인다(UC-1 2단계).

### 4.3.2 이름 검색 (FR-2)

- 매개변수 `search`. `name__icontains=search`. 앞뒤 공백은 지운다. 빈 문자열이면 조건을 걸지 않는다.
- SQLite의 `LIKE`는 ASCII만 대소문자를 무시한다. 한국어 이름은 그대로 부분 일치한다.

### 4.3.3 원산지 필터 (FR-3)

- 매개변수 `origin`. `origin__exact=origin`. 화면의 원산지 선택 목록은 4.3.7절의 고정 목록이다.

### 4.3.4 가격 범위 필터 (FR-4)

- 매개변수 `min_price`, `max_price`(0 이상 정수). `base_price__gte`, `base_price__lte`. 둘 중 하나만 와도 된다.
- `min_price > max_price`이거나 숫자가 아니면 400 `VALIDATION_ERROR`.
- 기준은 원두 기본 가격이다. 옵션 추가 금액은 넣지 않는다(FR-4 검증 열).

### 4.3.5 로스팅 정도 필터 (FR-5)

- 매개변수 `roast_level`. `LIGHT`, `MEDIUM`, `DARK` 밖의 값은 400.
- 4.3.2 ~ 4.3.5는 django-filter 없이 `products/queries.py`의 함수가 `customer_products()`(4.3.0)에 차례로 `filter()`를 이어 붙이고, 뷰의 `get_queryset()`이 그 함수를 부른다. 여러 조건이 함께 오면 AND다(SRS 3.1절).

### 4.3.6 원두 상세 (FR-6)

- 경로: `GET /api/products/{id}/`, 공개.
- 응답: 200, `{product_id, name, origin, roast_level, base_price, tasting_notes, description, image_url, sales_status, options: [...]}`. 옵션 항목은 `{option_id, weight_size, grind_type, extra_price, price, stock_quantity, is_available}`.
  - `price = base_price + extra_price`(DR-4).
  - `is_available = product.sales_status == ON_SALE and stock_quantity > 0`(DR-8).
  - 옵션 순서는 용량(200G, 500G, 1KG), 분쇄도(WHOLE_BEAN, HAND_DRIP, ESPRESSO) 순.
- 오류: 판매 중지 원두와 없는 ID는 404 `NOT_FOUND`.
- 화면(SCR-02): `is_available=false`인 옵션을 고르면 "품절"을 보이고 담기 버튼을 끈다(UC-4 1단계). 서버도 담기·주문 때 다시 확인한다(NFR-16).

### 4.3.7 원산지 선택 목록

- FR-3의 선택 목록은 별도 API 없이 프론트엔드 `src/lib/origins.js`의 고정 배열로 둔다. 시드 데이터(NFR-3)도 이 배열에서만 원산지를 고른다. 관리자 원두 등록·수정도 이 목록에서만 고른다(4.7.2절). 같은 배열을 백엔드 `products/origins.py`에도 두고 시리얼라이저가 검증한다. 원산지를 더하려면 두 파일을 같은 PR에서 고친다(11.1절).
