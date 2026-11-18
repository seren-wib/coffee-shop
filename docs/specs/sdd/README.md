# coffee-shop 설계 명세서 (SDD)

작성일 2026-11-17. 커피 원두 쇼핑몰 시스템을 어떻게 만들지 정한다. 요구사항 명세서(SRS, `docs/specs/srs/`)의 DR·FR·NFR·UC ID를 절마다 달아, 각 설계가 어느 요구사항을 실현하는지 추적한다. 운영 환경은 AWS EC2 한 대와 Cloudflare 도메인이다. SRS와 같이 이번 학기 범위 전체를 1차로 두고 차수는 나누지 않는다. 코드는 이 문서를 따른다. 둘이 어긋나면 같은 PR에서 한쪽을 고친다. 이 문서가 확정되면 테스트 계획서(STP)와 구현으로 넘어간다.

Google Docs: https://docs.google.com/document/d/1PlaC-17Gyowrh1pv8trCXmzSOFiTax6zaEr2K5VWSrA/edit

| 파일 | 내용 | ID |
| --- | --- | --- |
| [1-architecture.md](1-architecture.md) | 아키텍처: 시스템 맥락, 배포 단위, 통신, 데이터 위치, 백엔드 논리 구조 | NFR-19 ~ NFR-21, NFR-28 |
| [2-directories.md](2-directories.md) | 디렉터리 구조와 폴더 규칙 | NFR-29, NFR-31, NFR-32 |
| [3-spikes.md](3-spikes.md) | 스파이크: SQLite 동시 주문, 토스페이먼츠 승인·취소 (둘 다 아직 안 돌림) | NFR-15, FR-25 ~ FR-29 |
| [4-components/](4-components/README.md) | 컴포넌트 설계: 부품 9개, 상태 기계, 시퀀스 | FR-1 ~ FR-58 |
| [5-data-model.md](5-data-model.md) | 데이터 모델: ERD, 테이블 8개, 제약, 택배사 조회 주소 | DR-1 ~ DR-24 |
| [6-screens.md](6-screens.md) | 화면 설계: 라우트, 레이아웃, 디자인 가이드, 화면 16개 | SCR-01 ~ SCR-15, NFR-30, NFR-33, NFR-34, NFR-36 |
| [7-api.md](7-api.md) | API 설계 규칙: 오류 형식, 경로 묶음별 인증, 페이지네이션 | NFR-9 ~ NFR-11, NFR-28 |
| [8-security.md](8-security.md) | 보안과 개인정보: 해시, 전송 암호화, 접근 통제, 시크릿, 로그, CSP | NFR-4 ~ NFR-13, NFR-18, NFR-35 |
| [9-environment.md](9-environment.md) | 환경과 시크릿: 변수 이름과 설정 위치 | NFR-13 |
| [10-deployment.md](10-deployment.md) | 배포: 브랜치 모델, 서버 배치, nginx, 배포 흐름, 백업·감시 | NFR-20 ~ NFR-25 |
| [11-rationale.md](11-rationale.md) | 설계 근거: 확정한 기술 결정과 미결 | |
