## 3. 설치 절차

운영자가 서비스마다 처음 한 번 한다. 끝나면 항목 끝에 날짜를 적는다. 시크릿은 이름만 적고 값은 서버 `.env`와 각 서비스 화면에만 둔다(NFR-13). 계정 이름, 주소, 도메인 이름은 적지 않는다.

### 3.1 AWS (SDD 10.4, 12.1)

1. 리전 서울(ap-northeast-2)에 키 페어를 만들고 개인 키는 운영자 PC에만 둔다.
2. 보안 그룹: 인바운드 443은 Cloudflare 주소 대역(https://www.cloudflare.com/ips/)만, 22는 운영자 주소 하나만. 아웃바운드는 기본(전체).
3. EC2: Ubuntu 24.04 LTS(x86_64), t3.micro, EBS gp3 20GiB 암호화 켬, 위 키 페어와 보안 그룹.
4. Elastic IP 하나를 만들어 인스턴스에 붙인다.
5. 날짜: 아직

### 3.2 Cloudflare (SDD 11.3, NFR-4)

1. 도메인 DNS 영역에 A 레코드(도메인 → Elastic IP), 프록시 켬(주황 구름).
2. SSL/TLS 모드 Full (strict), Always Use HTTPS 켬, 최소 TLS 1.2.
3. SSL/TLS → Origin Server에서 Origin CA 인증서를 만든다(호스트 이름은 도메인). 인증서는 서버 `/etc/nginx/ssl/coffee-shop-origin.pem`(644), 개인 키는 `/etc/nginx/ssl/coffee-shop-origin.key`(600)로 둔다. 개인 키는 이 화면에서 한 번만 보인다.
4. 날짜: 아직

### 3.3 서버 (SDD 11.2)

1. SSH로 들어가 레포를 받는다(공개 레포라 인증이 필요 없다).

   ```bash
   git clone https://github.com/seren-wib/coffee-shop.git ~/coffee-shop
   ```

2. `/srv/coffee-shop/.env`를 `.env.example` 이름대로 쓴다. `DEBUG=False`, `ALLOWED_HOSTS=<도메인>`, `SQLITE_PATH=/srv/coffee-shop/data/db.sqlite3`, `SECRET_KEY`는 서버에서 새로 만든 값(50자 이상, 아래 명령). 결제를 켜기 전에는 `TOSS_SECRET_KEY`와 `VITE_TOSS_CLIENT_KEY`를 비워 둔다.

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

3. 설치 스크립트: 패키지(nginx, python3-venv, sqlite3, git), 스왑 1GiB, Node.js 24(빌드 전용, nodejs.org 배포본을 SHA-256으로 확인), 앱 계정 `coffee-shop`, 폴더, journald 200MB, nginx 설정, Cloudflare 실제 IP 대역, systemd 단위를 놓는다. `.env`나 인증서가 없으면 멈춘다. 다시 돌려도 된다.

   ```bash
   sudo ~/coffee-shop/deploy/install.sh
   ```

4. 첫 배포: 2절 2번으로 태그를 단 뒤 클론의 스크립트로 배포한다. 빈 DB를 `migrate`가 만든다.

   ```bash
   sudo ~/coffee-shop/deploy/deploy.sh release-YYYYMMDD-1
   ```

5. 관리자 계정(FR-53). 비밀번호는 화면에서 입력하고 어디에도 적지 않는다.

   ```bash
   cd /srv/coffee-shop/current/backend && sudo -u coffee-shop env DOTENV_PATH=/srv/coffee-shop/.env ../.venv/bin/python manage.py create_admin
   ```

6. 시연 데이터(NFR-3, 빈 DB에만): 같은 위치에서 `manage.py seed_demo`.
7. 날짜: 아직

### 3.4 토스페이먼츠 결제 켜기 (SDD 4.6.5, 10.1)

이 프로젝트 전용 토스페이먼츠 계정의 테스트 키만 쓴다. 다른 프로젝트와 함께 쓰는 키와 라이브 키는 서버에 두지 않는다. `TOSS_SECRET_KEY`가 `test_`로 시작하지 않으면 서버가 뜨지 않는다.

1. 전용 계정 개발자 센터에서 테스트 시크릿 키와 테스트 클라이언트 키를 확인한다.
2. 서버 `.env`에 `TOSS_SECRET_KEY`, `VITE_TOSS_CLIENT_KEY`를 넣는다.
3. 새 태그로 다시 배포한다(클라이언트 키는 빌드에 들어간다).
4. 4절 결제 항목을 확인한다.
5. 날짜: 아직

### 3.5 외부 감시 (NFR-23, SDD 11.5)

1. UptimeRobot 무료 요금제에 HTTP(S) 감시 하나: `https://<도메인>/api/health/`, 5분 간격.
2. 날짜: 아직

### 3.6 자동 배포 (FR-61, NFR-43, SDD 11.4) (2026-11-27 추가)

정책 틀은 레포 `deploy/aws/`에 있다. 계정 번호와 인스턴스 ID는 틀에 넣어 쓰고 레포에는 남기지 않는다.

1. IAM OIDC 공급자: URL `https://token.actions.githubusercontent.com`, 대상 `sts.amazonaws.com`.
2. 배포 역할 `coffee-shop-github-deploy`: 신뢰 정책 `deploy/aws/github-deploy-trust.json`(이 레포 `main`만), 인라인 정책 `deploy/aws/github-deploy-policy.json`(운영 인스턴스 하나에 `AWS-RunShellScript`, 결과 읽기).
3. 인스턴스 역할 `coffee-shop-ec2-ssm`: AWS 관리형 정책 `AmazonSSMManagedInstanceCore`를 붙이고 인스턴스 프로파일로 EC2에 연결한다. 보안 그룹은 바꾸지 않는다(SSM 에이전트는 나가는 443만 쓴다).
4. SSM 에이전트: Ubuntu 24.04 AMI에 snap으로 들어 있다. 서버에서 `sudo snap services amazon-ssm-agent`가 active인지, Systems Manager Fleet Manager에 인스턴스가 온라인인지 본다.
5. GitHub 레포 Settings → Secrets and variables → Actions: 시크릿 `AWS_DEPLOY_ROLE_ARN`, `PROD_INSTANCE_ID`, `PROD_URL`(`https://<도메인>`), 변수 `DEPLOY_ENABLED`=`true`. 시크릿 셋은 자격 증명이 아니라 식별자인데, 공개 실행 로그에서 가리려고 시크릿에 둔다.
6. 확인: 코드가 바뀐 PR 하나를 머지하고 2절 순서가 끝까지 도는지 본다(STP 8절 1번).
7. 날짜: 아직
