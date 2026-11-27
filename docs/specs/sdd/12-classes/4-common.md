## 12.4 common, config

모든 앱이 같이 쓰는 오류 형식, 페이지네이션, 권한, 상태 확인과 시작 시점 설정 검사.

### 12.4.1 오류 모듈 `common/exceptions.py`

| 클래스 | 맡는 일 | 메서드 |
| --- | --- | --- |
| `DomainError` | 업무 규칙 위반 예외. 오류 코드, 한국어 메시지, HTTP 상태, 부가 정보를 담는다 | `__init__(code, message, status=status.HTTP_409_CONFLICT, details=None)` |

#### error_body

- 시그니처: `error_body(code, message, fields=None, details=None)`
- 반환: API 오류 응답 본문 사전 `{code, message, fields?, details?}`. 예외 없음.
- 요구사항: NFR-28, NFR-34

#### api_exception_handler

- 시그니처: `api_exception_handler(exc, context)`
- 반환: 예외를 API 오류 형식으로 바꾼 `Response`. `DomainError`, 입력 검증 오류, DRF 예외를 다룬다. 그 밖의 예외는 `None`을 돌려줘 500 처리로 넘긴다. 예외 없음.
- 요구사항: NFR-28, NFR-30, NFR-34

내부 함수

- `_messages(value)`: 검증 오류 값을 문자열 목록으로 편다.
- `_fields(detail)`: 검증 오류를 필드별 메시지 사전으로 바꾼다.

### 12.4.2 페이지네이션 모듈 `common/pagination.py`

| 클래스 | 맡는 일 | 메서드 |
| --- | --- | --- |
| `StandardPagination` | 페이지 크기 20 고정 페이지네이션 | `get_next_link()`, `get_previous_link()`: 다음·이전 주소에서 스킴과 호스트를 뺀다 |

내부 함수

- `_path_only(url)`: 주소에서 경로와 쿼리만 남긴다. 프록시 뒤 내부 주소가 응답에 새지 않게 한다.

### 12.4.3 권한 모듈 `common/permissions.py`

| 클래스 | 맡는 일 | 메서드 |
| --- | --- | --- |
| `IsAdminRole` | 관리자 경로 권한 검사. 토큰 클레임이 아니라 DB의 역할을 본다(NFR-10) | `has_permission(request, view)`: 로그인했고 역할이 `ADMIN`이면 참 |

### 12.4.4 공통 뷰 모듈 `common/views.py`

#### health

- 시그니처: `health(request)`
- 반환: DB에 `SELECT 1`이 되면 200 `{"status": "ok"}`, 안 되면 503 `{"status": "unavailable"}`. 인증 없이 부른다. 예외 없음.
- 요구사항: FR-52

#### json_404

- 시그니처: `json_404(request, exception=None)`
- 반환: DRF가 다루지 않는 없는 경로에 대한 404 JSON 응답. 예외 없음.
- 요구사항: NFR-28

#### json_500

- 시그니처: `json_500(request)`
- 반환: 처리하지 못한 예외에 대한 500 JSON 응답. 예외 없음.
- 요구사항: NFR-28

### 12.4.5 설정 검사 모듈 `config/checks.py`

서버가 뜰 때 `.env` 값을 검사한다.

#### check_allowed_hosts

- 시그니처: `check_allowed_hosts(*, debug, hosts)`
- 반환: 없음. 예외: `ImproperlyConfigured`(`DEBUG`가 꺼져 있는데 호스트 목록이 비어 있음).
- 요구사항: NFR-12

#### check_toss_secret_key

- 시그니처: `check_toss_secret_key(key)`
- 반환: 결제를 켤 수 있으면 참, 키가 없으면 거짓. 예외: `ImproperlyConfigured`(테스트 키 `test_...`가 아님).
- 요구사항: NFR-13, FR-60
