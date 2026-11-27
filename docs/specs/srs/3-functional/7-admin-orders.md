### 3.7 관리자 주문·배송·취소 (1차)

관리자 계정만 쓸 수 있다(NFR-10). 상태 전환은 DR-19를 따르고, 표에 없는 전환은 409다.

| ID | 요구사항 | 검증 |
| --- | --- | --- |
| FR-44 | 관리자는 전체 주문을 최근 순으로 본다. | `GET /api/admin/orders/` 200, 모든 회원의 주문, `created_at` 내림차순 |
| FR-45 | 관리자는 주문 목록을 상태로 거른다. | `GET /api/admin/orders/?status=CANCEL_REQUESTED` 200, 그 상태만 |
| FR-46 | 관리자는 주문 상세(회원, 주문 항목, 결제 기록, 배송지, 취소 사유)를 본다. | `GET /api/admin/orders/{id}/` 200 |
| FR-47 | 관리자는 결제 완료 주문을 배송 준비로 바꾼다. | `POST /api/admin/orders/{id}/prepare/` 200, `PREPARING`. 결제 대기 주문 409 |
| FR-48 | 관리자는 배송 준비 주문에 택배사와 송장번호를 등록해 배송 중으로 바꾼다. | `POST /api/admin/orders/{id}/ship/` 200, `SHIPPED`, `shipped_at` 저장. 송장번호 비면 400 |
| FR-49 | 관리자는 배송 중 주문을 배송 완료로 바꾸고 완료 시각을 기록한다. | `POST /api/admin/orders/{id}/deliver/` 200, `DELIVERED`, `delivered_at` 저장 |
| FR-50 | 관리자는 취소 요청을 승인한다. 주문은 취소되고, 재고가 돌아오고, 성공한 결제는 PG에서 취소된다(DR-21). 결제가 꺼져 있으면 FR-60을 따른다. (2026-11-27 FR-60 연결 추가) | `POST /api/admin/orders/{id}/cancel-approve/` 200, `CANCELLED`, 재고 복구, 결제 `CANCELLED`. 두 번 보내도 재고는 한 번만 복구 |
| FR-51 | 관리자는 취소 요청을 반려한다. 주문은 요청 전 상태로 돌아간다. | `POST /api/admin/orders/{id}/cancel-reject/` 200, `PAID` 또는 `PREPARING`(요청 전 상태) |
| FR-57 | 관리자는 주문을 주문번호나 회원 이메일로 검색한다. | `GET /api/admin/orders/?search=ORD-20261011` 200, 주문번호나 회원 이메일이 맞는 주문만 |
