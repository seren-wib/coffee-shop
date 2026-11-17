### 3.6 관리자 원두 관리 (1차)

관리자 계정만 쓸 수 있다(NFR-10). 판매 상태는 DR-6, DR-7에 따라 자동으로도 바뀐다.

| ID | 요구사항 | 검증 |
| --- | --- | --- |
| FR-36 | 관리자는 판매 중지 원두를 포함한 전체 원두를 옵션별 재고와 함께 본다. | `GET /api/admin/products/` 200, 판매 중지 원두 포함 |
| FR-37 | 관리자는 원두(이름, 원산지, 로스팅 정도, 맛 노트, 설명, 기본 가격)를 등록한다. 새 원두는 판매 중이다. | `POST /api/admin/products/` 201, `sales_status=ON_SALE`. 회원 토큰 403 |
| FR-38 | 관리자는 원두 정보와 기본 가격을 고친다. 기존 주문은 바뀌지 않는다(DR-12). | `PATCH /api/admin/products/{id}/` 200, 기존 주문 항목 단가 그대로 |
| FR-39 | 관리자는 원두에 옵션(용량, 분쇄도, 추가 금액, 재고)을 추가한다(DR-2 ~ DR-4). | `POST /api/admin/products/{id}/options/` 201. 같은 용량·분쇄도 조합 409, 음수 추가 금액 400 |
| FR-40 | 관리자는 옵션의 추가 금액을 고친다. | `PATCH /api/admin/products/{id}/options/{oid}/` 200, 바뀐 옵션 가격이 상세에 반영 |
| FR-41 | 관리자는 옵션 재고를 늘리거나 줄인다. 재고에 따라 품절과 판매 중이 자동으로 바뀐다(DR-5, DR-6). | `PATCH .../options/{oid}/` 200. 마지막 재고 0 → 원두 `SOLD_OUT`, 다시 1 → `ON_SALE`. 음수 재고 400 |
| FR-42 | 관리자는 원두 판매를 중지한다. 재고가 바뀌어도 판매 중지는 유지된다(DR-7). | `POST /api/admin/products/{id}/stop/` 200 → `STOPPED`, 재고 바꿔도 `STOPPED` |
| FR-43 | 관리자는 판매 중지한 원두의 판매를 다시 시작한다. | `POST /api/admin/products/{id}/resume/` 200 → 재고 있으면 `ON_SALE`, 없으면 `SOLD_OUT` |
| FR-56 | 관리자는 원두를 이름의 일부로 검색한다. | `GET /api/admin/products/?search=에티` 200, 이름에 "에티"가 든 원두만(판매 중지 포함) |
