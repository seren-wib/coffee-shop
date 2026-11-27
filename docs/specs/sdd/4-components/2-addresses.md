## 4.2 배송지

| 항목 | 내용 |
| --- | --- |
| 책임 | 회원의 배송지를 관리하고 기본 배송지를 정확히 하나로 유지한다 (DR-16, DR-17) |
| 제공 인터페이스 | `/api/me/addresses/`, `/api/me/addresses/{id}/`, `/api/me/addresses/{id}/default/` (FR-14 ~ FR-18) |
| 의존 | 회원과 인증 |
| 구현 모듈 | `users/models.py`의 `UserAddress`, `users/services.py`, `users/serializers.py`, `users/views.py` |

`users` 앱의 `UserAddress`와 `users/services.py`. 핵심 규칙은 "배송지가 있는 회원의 기본 배송지는 정확히 하나"다(DR-16, DR-17). DB의 부분 유니크 제약 `uq_user_addresses_one_default`가 "둘 이상"을 막고, 아래 서비스 함수가 "0개"를 막는다.

### 4.2.0 기본 배송지 상태

| 지금 | 일어난 일 | 다음 | 처리 |
| --- | --- | --- | --- |
| 배송지 0개 | 등록 | 1개, 그것이 기본 | 첫 배송지는 요청의 `is_default`와 무관하게 기본(DR-16) |
| 1개 이상 | 등록(`is_default=false`) | 기본 그대로 | |
| 1개 이상 | 등록(`is_default=true`) | 새 배송지가 기본 | 기존 기본 해제 후 지정, 한 트랜잭션 |
| 2개 이상 | 다른 배송지를 기본으로 지정 | 그 배송지가 기본 | FR-18 |
| 2개 이상 | 기본 배송지 삭제 | 거부 | 409 `DEFAULT_ADDRESS_DELETE`(DR-17) |
| 2개 이상 | 기본이 아닌 배송지 삭제 | 기본 그대로 | |
| 1개 | 그 배송지 삭제 | 0개 | 허용(DR-17) |

### 4.2.1 배송지 목록 (FR-14)

- 경로: `GET /api/me/addresses/`, 회원.
- 처리: `UserAddress.objects.filter(user=request.user).order_by("-is_default", "-created_at")`.
- 응답: 200, 배열(페이지네이션 없음. 회원당 배송지는 많지 않다). 항목은 `{address_id, recipient_name, recipient_phone, zipcode, base_address, detail_address, is_default}`.

### 4.2.2 배송지 등록 (FR-15)

- 경로: `POST /api/me/addresses/`, 회원.
- 입력: `recipient_name`, `recipient_phone`, `zipcode`(숫자 5자리), `base_address`, `detail_address`(선택), `is_default`(선택, 기본 false).
- 처리(`create_address`, 한 트랜잭션):
  1. 이 회원의 배송지가 없으면 `is_default=True`로 만든다.
  2. 있고 `is_default=true`로 왔으면 `UPDATE user_addresses SET is_default=FALSE WHERE user_id=? AND is_default=TRUE` 뒤 새 행을 기본으로 만든다.
- 응답: 201, 만든 배송지.
- 오류: 400(필수 항목 빈 값, 우편번호 형식).

### 4.2.3 배송지 수정 (FR-16)

- 경로: `PATCH /api/me/addresses/{id}/`, 회원.
- 입력: 4.2.2의 필드 중 바꿀 것. `is_default`는 이 수정 경로에서 받지 않는다(기본 지정은 등록 4.2.2와 지정 4.2.5에서만, 해제는 다른 배송지를 지정해서만).
- 응답: 200.
- 오류: 404(다른 회원 배송지, 없는 ID), 400.
- 이미 만든 주문의 배송지는 바뀌지 않는다. 주문은 주문 시점에 복사해 둔다(DR-18, 5.6절).

### 4.2.4 배송지 삭제 (FR-17)

- 경로: `DELETE /api/me/addresses/{id}/`, 회원.
- 처리(`delete_address`): 대상이 기본이고 이 회원의 배송지가 2개 이상이면 409 `DEFAULT_ADDRESS_DELETE`, "다른 배송지를 먼저 기본으로 정해 주세요". 그 밖에는 지운다.
- 응답: 204.

### 4.2.5 기본 배송지 지정 (FR-18)

- 경로: `POST /api/me/addresses/{id}/default/`, 회원.
- 처리(`set_default_address`, 한 트랜잭션): 다른 기본을 해제하는 UPDATE, 대상의 `is_default=TRUE` UPDATE 순서. 해제를 먼저 해야 부분 유니크 제약에 걸리지 않는다.
- 응답: 200, 지정한 배송지.
