## 11. 설계 근거

기술 결정이다. 바뀌면 옛 항목은 두고 새 항목을 단다. 요구사항 수준 정책은 SRS 7절에 있다.

### 11.1 확정

- 2026-11-17: Cloudflare 프록시를 켜고 SSL/TLS 모드는 Full (strict)로 한다. 원 서버(EC2)에는 Cloudflare Origin CA 인증서를 둔다. HTTP → HTTPS 전환은 Cloudflare의 Always Use HTTPS로 한다(NFR-4, NFR-5). 버린 것: DNS only + 서버에서 Let's Encrypt(인증서 갱신 작업이 생기고 EC2 주소가 DNS로 그대로 드러남), Flexible 모드(Cloudflare와 EC2 사이가 평문). 이유: 유지보수성(인증서 갱신 없음), 보안(공개 레포라 원 서버 주소를 숨기는 편이 낫다). (커피샵 Lead 결정, 팀장 위임)
- 2026-11-17: 운영 환경은 서울 리전(ap-northeast-2)의 EC2 t3.micro 한 대, Ubuntu 24.04 LTS, Elastic IP 하나다. 인스턴스 안에서 nginx가 프론트엔드 빌드 결과(정적 파일)를 `/`로, `/api/`는 gunicorn(Django)으로 넘긴다. 버린 것: 프론트엔드를 S3·CloudFront로 따로 배포(서비스가 둘로 늘고 도메인 라우팅이 복잡해짐), Vite 개발 서버 그대로 운영(개발용이라 운영에 맞지 않음), Elastic IP 없이 자동 공인 IP(인스턴스를 멈췄다 켜면 주소가 바뀌어 DNS를 다시 고쳐야 함). 이유: 종속성(서비스 하나), 유지보수성(SIP 절차가 짧음). 비용은 SPMP 4절. (커피샵 Lead 결정, 팀장 위임)
- 2026-11-17: 운영 DB는 SQLite를 그대로 쓴다. WAL 모드를 켜고, 하루 한 번 `sqlite3 .backup`으로 백업 파일을 만들어 7개를 남긴다(NFR-25). 버린 것: RDS(비용과 설정이 늘고, 시연 규모에선 동시 쓰기 부하가 작음). 이유: 비용, 종속성. NFR-15 동시 주문 테스트에서 잠금 오류가 나면 다시 정한다. (커피샵 Lead 결정, 팀장 위임)
- 2026-11-17: `users.User`를 Django 커스텀 사용자 모델(`AbstractBaseUser` + `PermissionsMixin`, `AUTH_USER_MODEL = "users.User"`)로 바꾸고 이메일을 로그인 ID로 쓴다. 비밀번호 열은 Django 규칙대로 `password`가 된다(SRS NFR-6 측정 열 이름도 같이 고친다). 버린 것: 지금 모델을 두고 로그인 처리를 직접 작성(토큰 발급, 해시 확인, 권한 확인을 따로 만들어야 하고 simplejwt와 어긋남). 이유: 유지보수성, 테스트 용이성. 아직 마이그레이션이 없어서 지금 바꾸는 비용이 가장 작다. (커피샵 Lead 결정, 팀장 위임)
- 2026-11-17: 운영 환경에서는 Django 관리 사이트(`/admin/`)를 URL에서 빼고, 개발 환경에서만 연다. 관리자 업무는 FR-36 ~ FR-51, FR-56, FR-57 화면으로, 관리자 계정은 관리 명령(FR-53)으로 만든다. 버린 것: 운영에서도 `/admin/` 공개(공격 대상 경로가 하나 늘고, 화면과 별도로 권한을 두 번 관리해야 함). 이유: 보안, 테스트 용이성. (커피샵 Lead 결정, 팀장 위임)
- 2026-11-17: 테이블 정의의 원본은 `backend/*/models.py`와 Django 마이그레이션이다. `backend/schema.sql`은 지우고, 필요하면 `sqlmigrate`로 뽑아 본다. 부분 유니크 인덱스(기본 배송지 하나, 성공 결제 하나)와 CHECK 제약은 모델 `Meta.constraints`로 둔다. 버린 것: `schema.sql`을 원본으로 두기(ORM과 이중 관리, 이미 두 곳이 서로 다름). 이유: 유지보수성, 배포 때 `migrate` 한 번으로 끝남. (커피샵 Lead 결정, 팀장 위임)
- 2026-11-17: `TIME_ZONE = "Asia/Seoul"`, `USE_TZ = True`로 하고, 주문번호 날짜(DR-11)는 `timezone.localdate()`로 정한다. 버린 것: UTC 유지(자정 전후 주문의 날짜가 한국 날짜와 하루 어긋남). 이유: DR-11. (커피샵 Lead 결정, 팀장 위임)

### 11.2 미결

- 없음.
