# coffee-shop 요구사항 명세서 (SRS)

작성일 2026-11-17. 커피 원두 쇼핑몰 시스템의 요구사항을 정의한다. HW1 요구사항 명세서(`docs/old/backend/requirements.md`, `docs/old/backend/external-interfaces.md`)를 바탕으로 다시 쓰면서, 로컬 PC 시연이던 실행 환경을 AWS EC2 배포와 Cloudflare 도메인으로 바꿨다. 이번 학기 범위를 모두 1차로 두고 차수는 나누지 않는다. 요구사항에는 ID가 붙고, 테스트 이름과 PR 본문이 그 ID를 적는다. 이 문서가 확정되면 SDD로 넘어간다.

Google Docs: (아직 없음)

| 파일 | 내용 | ID |
| --- | --- | --- |
| [1-overview.md](1-overview.md) | 개요 | |
| [2-domain.md](2-domain.md) | 도메인 요구사항 | DR-1 ~ DR-24 |
| [3-functional/](3-functional/README.md) | 기능 요구사항 | FR-1 ~ FR-57 |
| [4-nonfunctional.md](4-nonfunctional.md) | 비기능 요구사항 | NFR-1 ~ NFR-35 |
| [5-use-cases.md](5-use-cases.md) | 사용사례 | UC-1 ~ UC-14 |
| [6-interfaces.md](6-interfaces.md) | 외부 인터페이스 | |
| [7-decisions.md](7-decisions.md) | 확정과 미결 | |

## HW1 식별번호 대응

HW1의 외부 인터페이스 식별번호는 아래 새 ID로 옮겼다. HW1 기능·비기능·도메인 요구사항에는 식별번호가 없었다.

| HW1 | 새 ID | 비고 |
| --- | --- | --- |
| HW-01, HW-02 | NFR-20, NFR-21 | 로컬 PC 실행에서 EC2 배포로 바뀜 |
| HW-03, SW-06 | NFR-26 | |
| SW-01 ~ SW-04 | NFR-19 | |
| SW-05 | NFR-27 | 대상이 개발 환경으로 좁아짐 |
| SW-07 | NFR-31 | |
| NW-01, NW-02 | NFR-28 | |
| NW-03, NW-04 | NFR-8, NFR-9 | |
| NW-05 | FR-9, FR-10 | |
