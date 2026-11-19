## 7. CI

GitHub Actions 워크플로 `.github/workflows/ci.yml` 하나다. 2026-11-19 준비 단계에 테스트 설정(`config/test_settings.py`, `config/test_settings_file.py`), `requirements-dev.txt`와 함께 들어왔다(#77). (2026-11-19 변경. 이전에는 기반 단계에서 설정, 커스텀 사용자 모델과 함께 들어온다고 적었다)

| 브랜치 | 어디서 따서 | 어디로 | CI |
| --- | --- | --- | --- |
| `main` | | | push마다 `backend`, `frontend` 작업. 운영 배포 태그는 두 작업이 통과한 커밋에만 단다(SDD 10.1절) |
| 작업 브랜치(`cart-api` 같은 이름) | `main` | `main`, PR 스쿼시 머지 | PR을 열거나 커밋을 더할 때마다 `backend`, `frontend` 작업. 둘 다 통과해야 머지 |

- 문서만 바꾼 PR(`docs/**`)도 같은 작업이 돈다. 경로로 건너뛰면 필수 검사가 "대기"로 남아 머지가 막히기 때문이다. 문서 동기화는 따로 `docs-sync.yml`이 `main` push에서 한다.
- 운영 배포는 CI가 하지 않는다. 운영자가 서버에서 `deploy/deploy.sh <태그>`를 실행한다(SDD 10.4절, 11.1절).

### 7.1 작업

트리거는 `pull_request`(대상 `main`)와 `push`(`main`)다. 두 작업은 동시에 돌고, 같은 브랜치에 새 커밋이 오면 진행 중인 실행을 취소한다(`concurrency`, `cancel-in-progress`). Actions 시크릿은 쓰지 않는다. 테스트 설정의 가짜 값만 쓴다(1.2절).

`backend` 작업(`ubuntu-latest`, 작업 폴더 `backend`):

1. `actions/checkout`.
2. `actions/setup-python`, Python 3.12(NFR-19), `pip` 캐시는 `backend/requirements*.txt` 기준.
3. `pip install -r requirements.txt -r requirements-dev.txt`.
4. `black --check .`(NFR-29).
5. `python manage.py makemigrations --check --dry-run --settings=config.test_settings`. 모델을 바꾸고 마이그레이션을 빠뜨린 PR을 막는다. CI에는 `.env`가 없으므로 테스트 설정으로 돈다.
6. `python manage.py test --settings=config.test_settings --exclude-tag=concurrency`(2절, 3절).
7. `python manage.py test --settings=config.test_settings_file --tag=concurrency`(NFR-15).

`frontend` 작업(`ubuntu-latest`, 작업 폴더 `frontend`):

1. `actions/checkout`.
2. `actions/setup-node`, Node.js 24(NFR-19), `npm` 캐시는 `frontend/package-lock.json` 기준.
3. `npm ci`.
4. `npx prettier --check .`(NFR-29).
5. `npm run lint`(oxlint, NFR-29).
6. `npm test`(2.5절, 4절).
7. `npm run build`. `VITE_APP_VERSION`에 커밋 앞 7자리를 넣어 빌드가 되는지만 본다. 결과물은 올리지 않는다.

### 7.2 필수 검사

- `main` 브랜치 보호 규칙에서 `backend`, `frontend` 두 상태 검사를 필수로 두고, PR 없이 `main`에 push하지 못하게 한다(CONTRIBUTING). 설정은 레포 관리자(팀장)가 GitHub 레포 Settings → Branches에서 한 번 한다. 워크플로가 처음 한 번 돌아야 검사 이름이 목록에 뜨므로 `ci.yml`을 머지한 다음에 건다.
- 2026-11-19에 걸었다(레포 관리자 결정). 필수 검사는 `backend`, `frontend` 둘이고, PR 없이는 `main`에 넣지 못하며 필수 승인 수는 0이다. 관리자에게도 똑같이 적용하고(enforce admins), force push와 브랜치 삭제는 막는다. 검사 전에 브랜치를 `main` 최신으로 맞추라는 조건(strict)은 켜지 않았다. (2026-11-19 변경. 이전에는 "아직 걸지 않았다. 그 전까지는 PR 작성자가 두 작업 통과를 확인하고 머지한다")
- 필수 승인 수는 0이다(CONTRIBUTING). 사람 리뷰는 권장이고, 자동 검사 통과는 필수다.
- 검사가 실패한 PR은 고쳐서 다시 올린다. 테스트를 지우거나 건너뛰기(`skip`)로 통과시키지 않는다. 일부러 미룬 테스트는 PR 본문에 이유와 함께 적는다.
