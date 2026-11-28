## 9. 보안과 개인정보

시스템은 이름, 이메일, 연락처, 주소를 저장하므로 개인정보 보호법의 안전성 확보 조치(비밀번호 일방향 암호화, 전송 구간 암호화, 접근 통제)를 따른다(SRS 1.4절). 레포가 공개라서 이 절에는 수단만 적고, 서버 주소·계정은 적지 않는다. 시연 규모라서 받아들인 한계는 그 근거와 함께 12.1절에 둔다.

### 9.1 해시

- 비밀번호는 Django 기본 PBKDF2-SHA256(`pbkdf2_sha256$<반복 수>$<솔트>$<해시>`)로만 `users.password`에 저장한다(NFR-6). 반복 수는 Django 6.1 기본값을 쓰고 직접 정하지 않는다. Django를 올리면 다음 로그인 때 해시가 새 반복 수로 바뀐다.
- 원문 비밀번호는 요청 처리 중 메모리에만 있다. 응답, 로그, 오류 메시지에 넣지 않는다.
- 최소 길이 8자는 `MinimumLengthValidator`가 가입(FR-7), 비밀번호 변경(FR-13), 관리자 생성 명령(FR-53) 세 곳에서 같은 설정으로 확인한다.

### 9.2 암호화와 전송

| 구간 | 수단 | 요구사항 |
| --- | --- | --- |
| 브라우저 ↔ Cloudflare | HTTPS. Cloudflare 엣지 인증서. 최소 TLS 버전 1.2. Always Use HTTPS로 80 → 443 | NFR-4, NFR-5 |
| Cloudflare ↔ EC2 | HTTPS. SSL/TLS 모드 Full (strict), 원 서버에 Cloudflare Origin CA 인증서. strict는 인증서 호스트명을 검사하므로 운영 도메인의 호스트명을 넣어 발급한다(SIP 3절) | 12.1절 |
| EC2 ↔ 토스페이먼츠 | HTTPS(인증서 검증 켬) | FR-26 |
| 저장 데이터 | SQLite 파일은 암호화하지 않는다. EBS 볼륨 암호화를 켠다 | 11.2절 |
| 토큰 | JWT 서명(HS256, 키는 `SECRET_KEY`). 암호화가 아니므로 토큰에 개인정보를 넣지 않는다(`user_id`, `role`만) | NFR-8 |

- Django 보안 설정(운영):
  - `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`. nginx가 붙인 헤더로 HTTPS 요청임을 안다.
  - `SECURE_SSL_REDIRECT = False`. 전환은 Cloudflare가 하고, nginx는 443만 연다. 이중 전환으로 루프가 생기지 않게 한다.
  - `SECURE_HSTS_SECONDS`는 Django가 아니라 Cloudflare HSTS 설정으로 둔다. 처음엔 짧은 값으로 시작한다.
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`, `X_FRAME_OPTIONS = "DENY"`.

### 9.3 접근 통제

| 대상 | 수단 | 요구사항 |
| --- | --- | --- |
| 회원 경로 | JWT 필수, 기본 권한 `IsAuthenticated` | NFR-9 |
| 관리자 경로 | `IsAdminRole`(DB의 `role`) | NFR-10 |
| 남의 객체 | 쿼리셋을 `request.user`로 먼저 거름, 404 | NFR-11 |
| 권한 올리기 | 가입·내 정보 수정 시리얼라이저에 `role` 필드 없음 | FR-7 |
| 관리 사이트 | 운영 URL에 `/admin/` 없음 | 12.1절 |
| 로그인 시도 | DRF `ScopedRateThrottle`: 로그인 IP당 분당 10회, 가입 IP당 시간당 20회. 초과는 429 | NFR-7 보강 |
| 서버 접속 | SSH 키 인증만, 비밀번호 로그인 끔. 보안 그룹은 22번을 운영자 주소에만, 443을 Cloudflare 주소 대역에만 연다 | NFR-20 |
| 자동 배포 | GitHub는 서버에 접속하지 않는다. SSM 에이전트가 나가는 443으로 명령을 받는다. 배포 역할은 이 레포 `main`에서 온 OIDC 토큰만 받고, 운영 인스턴스 하나에 `AWS-RunShellScript`를 보내고 결과를 읽는 것만 한다(`deploy/aws/`) (2026-11-27 추가) | NFR-43 |

- 요청 제한은 기본 캐시(로컬 메모리)를 쓴다. gunicorn 워커마다 따로 세므로 실제 한도는 워커 수(3)배까지 느슨하다. 시연 규모에서 받아들인다.
- 클라이언트 IP: nginx `real_ip` 모듈이 Cloudflare 주소 대역에서 온 요청의 `CF-Connecting-IP`를 `$remote_addr`로 바꾸고, `/api/`로 넘길 때 `X-Forwarded-For`를 그 값 하나로 덮어쓴다(클라이언트가 보낸 값은 버림). DRF는 `X-Forwarded-For`와 `NUM_PROXIES=1`로 IP를 읽는다(DRF는 `X-Real-IP`를 읽지 않는다).

### 9.4 시크릿

| 시크릿 | 어디에 | 누가 읽나 |
| --- | --- | --- |
| Django `SECRET_KEY` | EC2 `.env`(권한 600, 소유자는 앱 실행 계정) | gunicorn |
| 토스페이먼츠 시크릿 키 `TOSS_SECRET_KEY` | EC2 `.env` | gunicorn |
| Cloudflare Origin CA 인증서 개인 키 | EC2 인증서 폴더(권한 600, root) | nginx |
| 토스페이먼츠 클라이언트 키 | 빌드 때 환경 변수. 브라우저에 공개되는 값이라 시크릿은 아니지만 레포에 두지 않는다 | 빌드 |
| SSH 개인 키 | 운영자 PC만 | 운영자 |
| 자동 배포 AWS 권한 | 저장하지 않는다. `deploy` 실행마다 GitHub OIDC 토큰으로 1시간짜리 임시 자격 증명을 받는다(NFR-43, 11.4절) (2026-11-27 추가) | `deploy` 워크플로 |

- 레포에는 `.env.example`에 이름만 둔다(NFR-13, 10절). 값을 실수로 커밋하면 지우는 것으로 끝내지 않고 그 키를 새로 발급한다(히스토리에 남기 때문).
- 테스트는 가짜 키만 쓴다. 테스트 설정의 `SECRET_KEY`는 테스트 전용 문자열이다.
- `TOSS_SECRET_KEY`는 토스페이먼츠 테스트 키(`test_`)만 받는다. 다른 값이면 서버가 뜨지 않는다(NFR-42, 10.1절). (2026-11-27 추가)

### 9.5 로그 규칙 (NFR-35)

| 남기는 것 | 남기지 않는 것 |
| --- | --- |
| 요청 메서드, 경로(쿼리 문자열 뺌), 상태 코드, 응답 시간, 클라이언트 IP | 요청·응답 본문 |
| 업무 이벤트의 ID(`order_id`, `payment_id`, `user_id`) | 비밀번호, 액세스·리프레시 토큰, `Authorization` 헤더 |
| PG 오류 코드와 메시지 | 토스 `paymentKey` 전체(뒤 8자만), 시크릿 키 |
| 예외 종류와 스택 트레이스(서버 로그에만) | 연락처, 주소, 받는 사람 이름 |

- nginx 접근 로그는 쿼리 문자열을 빼고 경로(`$uri`)만 남기는 형식을 쓴다. 관리자 주문 검색의 회원 이메일(`?search=`)과 토스가 결과 화면에 붙여 보내는 `paymentKey`(`/checkout/result?paymentKey=...`)가 로그에 남지 않게 하려는 것이다. `Authorization`, `Cookie` 헤더도 넣지 않는다.
- Django `DEBUG=False`에서 500 오류 이메일(`ADMINS`)은 쓰지 않는다.
- 확인: 로그인·주문 요청 뒤 `journalctl`과 nginx 로그에서 테스트 연락처·토큰 문자열을 검색해 0건(NFR-35, STP 9절).

### 9.6 CSP와 브라우저 보안 헤더

nginx가 `index.html`과 정적 파일(`/assets/`) 응답에 붙인다(11.3절 두 `location` 모두 같은 헤더 파일을 넣는다).

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://js.tosspayments.com;
  frame-src https://*.tosspayments.com;
  connect-src 'self' https://*.tosspayments.com;
  img-src 'self' https: data:;
  style-src 'self' 'unsafe-inline';
  object-src 'none';
  base-uri 'self';
  frame-ancestors 'none';
  form-action 'self' https://*.tosspayments.com
Referrer-Policy: strict-origin-when-cross-origin
X-Content-Type-Options: nosniff
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

- 토큰을 `localStorage`에 두므로(4.1.5) XSS가 곧 토큰 유출이다. 그래서 인라인 스크립트를 막는(`script-src`에 `'unsafe-inline'` 없음) CSP를 둔다. Vite 빌드 결과는 외부 파일 스크립트라 이 정책에서 돈다.
- `style-src 'unsafe-inline'`은 토스페이먼츠 결제창 SDK가 넣는 인라인 스타일 때문에 둔다. 실제로 필요한 출처는 3.2절 스파이크에서 브라우저 콘솔의 CSP 위반으로 확인하고 줄인다.
- `img-src https:`는 관리자가 넣는 외부 이미지 URL(SRS 7.1) 때문이다.
- React는 문자열을 이스케이프해서 그린다. `dangerouslySetInnerHTML`은 쓰지 않는다. 원두 설명·맛 노트도 일반 텍스트로 그린다.
- 링크로 여는 외부 페이지(택배사)는 `rel="noopener noreferrer"`로 연다(4.5.7).

### 9.7 개인정보 보관과 최소 수집

- 수집 항목은 가입(이메일, 이름, 연락처)과 배송지(받는 사람, 연락처, 주소)뿐이다. 결제 수단 정보는 저장하지 않는다(NFR-18).
- 주문에 복사한 배송지는 회원이 배송지를 지워도 남는다(DR-18). 거래 기록 보존 때문이다.
- 회원 탈퇴 기능은 범위 밖이다(SRS에 없음). 시연이 끝나면 운영 DB와 백업을 함께 지운다(SMP 3절).
- 가입할 때 수집 항목·목적·보유 기간을 보이고 동의를 받으며, 동의 시각을 `users.privacy_agreed_at`에 남긴다(FR-58, 4.1.1). 같은 내용을 처리방침 화면(SCR-15, FR-59)에 두고, 모든 화면에 데모 고지 배너를 둔다(NFR-36). (2026-11-19 추가)
