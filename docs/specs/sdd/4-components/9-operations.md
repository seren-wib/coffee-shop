## 4.9 운영

`common/views.py`, `users/management/commands/create_admin.py`, `products/management/commands/seed_demo.py`.

### 4.9.1 상태 확인 (FR-52)

- 경로: `GET /api/health/`, 공개(`AllowAny`, 인증 클래스 없음).
- 처리: `connection.cursor().execute("SELECT 1")`.
- 응답: 200 `{"status": "ok"}`. DB 오류면 503 `{"status": "unavailable"}`. 버전, 호스트 이름, 오류 내용은 넣지 않는다(FR-52, NFR-12).
- 쓰는 곳: 배포 뒤 확인(NFR-24, FR-61, FR-62), 재부팅 뒤 확인(NFR-22), 외부 감시(NFR-23, 10.5절).
- nginx 접근 로그에서 이 경로는 남기지 않는다(감시 요청이 5분마다 오므로).

### 4.9.2 관리자 계정 생성 (FR-53)

- 명령: `python manage.py create_admin --email <이메일>`. 비밀번호는 인자로 받지 않고 `getpass`로 두 번 입력받는다. 셸 기록과 프로세스 목록에 비밀번호가 남지 않게 하려는 것이다.
- 처리: `validate_password`로 8자 이상 확인, `User.objects.create_user(..., role=ADMIN)`. 같은 이메일이 있으면 그 계정의 `role`을 `ADMIN`으로 바꿀지 묻는다.
- 운영 환경에는 관리자를 만드는 API가 없다. 가입 API는 늘 `MEMBER`다(FR-7).
- `createsuperuser`는 쓰지 않는다. `role`을 채우지 않기 때문이다.

### 4.9.3 시연 데이터 (NFR-3)

- 명령: `python manage.py seed_demo --products 100 --members 50 --orders 500`. 무작위 시드를 고정해 같은 데이터가 다시 나온다.
- 원두 100종(옵션 1 ~ 9개), 회원 50명(배송지 1 ~ 3개), 주문 500건(상태 7가지가 고루)을 만든다. 주문은 4.5.3 서비스를 거치지 않고 직접 넣되 재고·금액 규칙(DR-12 ~ DR-15)을 지킨다.
- 회원 비밀번호는 실행할 때 무작위로 만들고 화면에 한 번 보여준다. 레포에 고정 비밀번호를 두지 않는다. 시드 회원 전체가 이 비밀번호 하나를 쓴다(이메일 `demo001@example.com` ~).
- 결제 기록(2026-11-19 정함): `PENDING` 주문은 `READY` 1건, `PAID` 이후 상태(`PAID`, `PREPARING`, `SHIPPED`, `DELIVERED`, `CANCEL_REQUESTED`)는 `SUCCESS` 1건, `CANCELLED`는 승인 뒤 취소된 `CANCELLED` 1건이다. 취소 주문은 재고를 돌려준 것으로 보고 재고를 빼지 않고, 나머지는 `decrease_stock`으로 뺀다.
- 원두 옵션 재고와 판매 중지(원두의 5%)는 `products.services`를 거친다. 무작위 시드는 `--seed`(기본 20261130)이고, 원두·주문·회원이 이미 있는 DB에서는 돌지 않는다.
- 로컬(Windows, 파일 SQLite, 테스트 설정)에서 기본값 100·50·500이 1.71초에 끝났다(2026-11-19 한 번 잼). 주문 상태별 71 ~ 72건.
- 시드 회원은 가입 경로를 거친 회원과 같게 `privacy_agreed_at`을 생성 시각으로 채운다(FR-58, 2026-11-19 추가).
- 운영 환경에서는 `DEBUG=False`면 `--force` 없이는 돌지 않는다.

### 4.9.4 로그

- Django 로그는 표준 출력으로 내보내고 systemd journald가 모은다. 수준은 `LOG_LEVEL`(기본 `INFO`).
- 요청 본문, `Authorization` 헤더, 비밀번호, 토큰, 연락처, 주소는 로그에 남기지 않는다(NFR-35, 8.5절).
- 업무 이벤트는 ID만 남긴다: `order.created order_id=... user_id=...`, `payment.confirmed payment_id=...`, `payment.cancelled payment_id=... reason=AMOUNT_MISMATCH`.
