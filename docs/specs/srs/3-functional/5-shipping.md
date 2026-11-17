### 3.5 배송 조회 (1차)

| ID | 요구사항 | 검증 |
| --- | --- | --- |
| FR-34 | 배송 중이거나 배송 완료된 주문의 상세에 택배사, 송장번호, 배송 완료 시각을 보여준다. | `GET /api/orders/{id}/` 응답에 `courier_name`·`tracking_number`·`delivered_at` |
| FR-35 | 주문 상세에서 송장번호를 넣은 택배사 조회 페이지 링크를 새 탭으로 연다. | 링크 `href`에 송장번호 포함, `target="_blank"` |
