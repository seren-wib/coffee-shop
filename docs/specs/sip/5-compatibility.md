## 5. 호환 확인 기록

| 날짜 | 환경 | 확인 | 결과 |
| --- | --- | --- | --- |
| 2026-11-27 | Ubuntu 24.04 컨테이너(linux/amd64), nginx 1.24.0, git 2.43.0, Node.js 24.22.3 | `deploy.sh` 첫 배포(systemctl만 대체) | 54초에 `done ... health 200`. `/api/health/` 200, `/api/nope/` 404 JSON, 보안 헤더 3개, `journal_mode` `wal` |
| 2026-11-27 | 같은 컨테이너 | 상태 확인이 실패하는 태그, 마이그레이션이 실패하는 태그, `main`에 없는 태그, 형식이 다른 태그 | 각각 rc 1·1·1·2. 마이그레이션 실패와 `main` 밖 태그는 `current`를 안 바꿈 |

### 5.1 발견

1. nginx 오류 로그(`coffee-shop.error.log`)는 업스트림 오류 때 요청 줄을 쿼리 문자열째 남긴다. 접근 로그와 달리 형식을 바꿀 수 없다. 오류 로그는 서버 안에만 두고 밖으로 복사하지 않는다(SDD 8.5).
2. `deploy/*.sh`가 git에 실행 권한 없이(100644) 들어가 있었다. 서버에서 `sudo deploy/install.sh`, 그 안의 `cloudflare-real-ip.sh`, 백업 타이머의 `backup.sh`가 모두 Permission denied로 실패한다. 실행 권한을 줬다(2026-11-27).
3. 첫 배포는 `current`가 없는데 `readlink -f`는 없는 경로도 그대로 내준다. 첫 배포에서 상태 확인이 실패하면 `current`가 자기 자신을 가리키는 링크가 된다. `readlink -e`로 바꿔서 첫 배포 실패 때는 되돌리지 않는다(2026-11-27).
4. gunicorn 27은 기본으로 `$HOME/.gunicorn/`에 제어 소켓을 만들려 한다. 앱 계정은 홈이 없고 `ProtectHome=true`라 시작할 때마다 `Control server error: Permission denied`가 남는다. 제어 소켓을 끈다(`control_socket_disable`, 2026-11-27).
5. 실패한 태그의 릴리스 폴더는 남는다. 같은 태그로 다시 배포하면 "already exists"로 멈추므로(2.1) 고친 뒤에는 `-N`을 올린 새 태그로 배포한다.
