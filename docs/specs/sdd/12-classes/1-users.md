## 12.1 users 앱

회원, 인증, 배송지. 4절의 "회원과 인증", "배송지" 부품을 구현한다.

### 12.1.1 모델 `users/models.py`

| 클래스 | 맡는 일 | 테이블 | 직접 정의한 메서드 |
| --- | --- | --- | --- |
| `Role` | 회원 역할 열거형. `MEMBER`, `ADMIN` | | |
| `UserManager` | `User`를 만드는 매니저 | | `create_user(email, password=None, **fields)`: 이메일을 소문자로 바꾸고 비밀번호를 해시해 저장한다 |
| `User` | 회원 계정. 이메일이 로그인 ID다 | `users` | `is_staff`(속성): 역할이 `ADMIN`이면 참. 개발 환경 관리 사이트만 읽는다 |
| `UserAddress` | 회원 한 명의 배송지 한 건 | `user_addresses` | |

### 12.1.2 서비스 모듈 `users/services.py`

#### register_member

- 시그니처: `register_member(*, email, password, user_name, phone_number)`
- 반환: 만든 `User`. 역할은 항상 `MEMBER`이고 개인정보 동의 시각을 지금으로 적는다. 예외 없음(이메일 중복은 `RegisterSerializer`가 막는다).
- 요구사항: FR-7, FR-58

#### change_password

- 시그니처: `change_password(user, new_password)`
- 반환: 없음. 새 비밀번호를 해시해 저장한다. 예외 없음(현재 비밀번호 확인은 `PasswordChangeSerializer`가 한다).
- 요구사항: FR-13

#### create_address

- 시그니처: `create_address(user, *, is_default=False, **fields)`
- 반환: 만든 `UserAddress`. 첫 배송지는 `is_default`와 무관하게 기본이 된다. 예외 없음.
- 요구사항: FR-15, DR-16

#### update_address

- 시그니처: `update_address(user, address_id, **fields)`
- 반환: 고친 `UserAddress`. `fields`의 `is_default`는 버린다. 예외: 404 `NOT_FOUND`(다른 회원의 배송지, 없는 ID).
- 요구사항: FR-16

#### set_default_address

- 시그니처: `set_default_address(user, address_id)`
- 반환: 기본으로 지정한 `UserAddress`. 예외: 404 `NOT_FOUND`.
- 요구사항: FR-18, DR-16

#### delete_address

- 시그니처: `delete_address(user, address_id)`
- 반환: 없음. 예외: 404 `NOT_FOUND`, 409 `DEFAULT_ADDRESS_DELETE`(배송지가 둘 이상인데 기본 배송지를 지울 때).
- 요구사항: FR-17, DR-17

내부 함수

- `_own_address(user, address_id)`: 회원 소유로 먼저 거른 뒤 배송지를 찾는다. 없으면 404(NFR-11).
- `_clear_default(user)`: 그 회원의 기본 배송지 표시를 푼다.

### 12.1.3 뷰 `users/views.py`

| 클래스 | 경로 | HTTP 메서드 | 부르는 서비스 | 요구사항 |
| --- | --- | --- | --- | --- |
| `RegisterView` | `/api/auth/register/` | POST | `register_member` | FR-7, FR-58 |
| `LoginView` | `/api/auth/token/` | POST | simplejwt 토큰 발급 | FR-8, NFR-7 |
| `RefreshView` | `/api/auth/token/refresh/` | POST | simplejwt 토큰 재발급 | FR-9 |
| `MeView` | `/api/me/` | GET, PATCH | 없음(`ProfileSerializer`로 조회·수정) | FR-11, FR-12 |
| `PasswordChangeView` | `/api/me/password/` | POST | `change_password` | FR-13 |
| `AddressListView` | `/api/me/addresses/` | GET, POST | `create_address` | FR-14, FR-15 |
| `AddressDetailView` | `/api/me/addresses/{id}/` | PATCH, DELETE | `update_address`, `delete_address` | FR-16, FR-17 |
| `AddressDefaultView` | `/api/me/addresses/{id}/default/` | POST | `set_default_address` | FR-18 |

- `RegisterView`, `LoginView`, `RefreshView`는 공개 경로(`AllowAny`)다. `RegisterView`와 `LoginView`에는 요청 수 제한이 걸린다.
- `LoginView`는 없는 이메일, 틀린 비밀번호, 비활성 계정을 모두 401 `INVALID_CREDENTIALS` 한 가지로 답한다(NFR-7). `RefreshView`는 토큰 오류를 401 `INVALID_TOKEN`으로 답한다.

### 12.1.4 시리얼라이저 `users/serializers.py`

| 클래스 | 맡는 일 |
| --- | --- |
| `ProfileSerializer` | 내 정보 응답과 수정 입력. `user_id`, `email`, `role`은 읽기 전용 |
| `RegisterSerializer` | 가입 입력 검증. 이메일 중복, 비밀번호 규칙, 개인정보 동의. `role` 필드가 없어 무엇을 보내도 `MEMBER`다 |
| `LoginSerializer` | 로그인 입력 검증과 토큰 발급. 토큰에 `role` 클레임을 넣고 응답에 회원 요약을 붙인다 |
| `PasswordChangeSerializer` | 현재 비밀번호 확인과 새 비밀번호 규칙 검증 |
| `AddressSerializer` | 배송지 입력 검증(연락처, 우편번호 형식)과 응답 |

내부 함수

- `_check_password(value, user=None)`: Django 비밀번호 검증기를 돌리고 실패 메시지를 시리얼라이저 오류로 바꾼다.

### 12.1.5 관리 명령

| 클래스 | 파일 | 메서드 | 맡는 일 | 요구사항 |
| --- | --- | --- | --- | --- |
| `Command` | `users/management/commands/create_admin.py` | `add_arguments(parser)`, `handle(*args, email, name, phone, **options)` | 관리자 계정을 만든다 | FR-53 |
