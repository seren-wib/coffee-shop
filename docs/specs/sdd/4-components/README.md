## 4. 컴포넌트 설계

부품마다 파일 하나다. 파일 맨 위 표에 그 부품의 책임, 제공 인터페이스, 의존하는 부품, 구현 모듈을 적는다. 각 소절(`####`)은 기능 하나를 다루고, 제목에 그 기능이 구현하는 요구사항 ID를 단다. 소절마다 경로, 입력, 처리, 응답, 오류를 적는다. 오류 코드 이름과 응답 형식은 7.2절, 권한 묶음은 7.3절을 따른다. 여러 참여자가 오가는 흐름은 시퀀스 다이어그램을, 상태가 있는 부품은 상태 전환표를 둔다. 클래스와 모듈 단위의 명세(시그니처, 반환, 예외)는 12절에 따로 두고, 이 절과는 요구사항 ID로 잇는다.

| 파일 | 부품 | FR |
| --- | --- | --- |
| [1-auth.md](1-auth.md) | 4.1 회원과 인증 | FR-7 ~ FR-13, FR-54, FR-58 |
| [2-addresses.md](2-addresses.md) | 4.2 배송지 | FR-14 ~ FR-18 |
| [3-catalog.md](3-catalog.md) | 4.3 원두 조회 | FR-1 ~ FR-6 |
| [4-cart.md](4-cart.md) | 4.4 장바구니 | FR-19 ~ FR-22 |
| [5-orders.md](5-orders.md) | 4.5 주문 | FR-23, FR-24, FR-30 ~ FR-35, FR-55 |
| [6-payments.md](6-payments.md) | 4.6 결제 | FR-25 ~ FR-29, FR-60 |
| [7-admin-products.md](7-admin-products.md) | 4.7 관리자 원두·재고 | FR-36 ~ FR-43, FR-56 |
| [8-admin-orders.md](8-admin-orders.md) | 4.8 관리자 주문·배송·취소 | FR-44 ~ FR-51, FR-57 |
| [9-operations.md](9-operations.md) | 4.9 운영 | FR-52, FR-53 |

### 4.0 공통 규칙

- 서비스 함수는 `transaction.atomic()` 안에서 돈다. SQLite 연결은 `transaction_mode="IMMEDIATE"`라 트랜잭션이 시작될 때 쓰기 잠금을 잡는다(9절, 3.1절). 그래서 한 순간에 쓰기 트랜잭션은 하나뿐이고, 상태 확인과 변경 사이에 다른 요청이 끼지 않는다.
- 그 위에 상태를 바꾸는 문장은 모두 조건부 UPDATE(`UPDATE ... WHERE <현재 상태 조건>`)로 쓰고, 바뀐 행 수가 0이면 409 `INVALID_STATE`로 끝낸다. 잠금 방식이 바뀌어도(예: 다른 DB) 규칙이 깨지지 않게 하는 두 번째 방어선이다(DR-19, DR-21, NFR-15).
- 외부 HTTP 호출(토스페이먼츠)은 DB 트랜잭션 밖에서 한다. 쓰기 잠금을 잡은 채 외부 응답을 기다리지 않는다.
- 업무 예외는 `common/exceptions.py`의 `DomainError(code, message, status)` 하나로 던지고, 예외 처리기가 7.2절 형식으로 바꾼다.
- 회원 소유 객체(배송지, 장바구니 항목, 주문)는 쿼리셋을 `user=request.user`로 먼저 거른 뒤 ID로 찾는다. 다른 회원의 ID는 "없음"과 같아서 404다(NFR-11).
