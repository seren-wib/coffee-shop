## 4. 비용 산정

### 4.1 외부 비용

금액은 2026-11-19에 본 공개 가격표로 낸 추정이고 실제 청구서가 아니다. 미국 달러, 세금 별도, 한 달은 730시간으로 셈했다. AWS 프리 티어 적용 여부는 운영자 계정에 달려 있어 빼고 셈했다. 운영 기간은 첫 배포(늦어도 2026-11-30)부터 시연·평가가 끝날 때까지이고, 끝나는 날은 미정이다(SRS 7.2절).

| 항목 | 비용 | 비고 |
| --- | --- | --- |
| EC2 t3.micro 온디맨드, 서울(Linux) | 시간당 $0.013, 월 약 $9.49(추정) | 사양은 SDD 10.2절. 출처: [AWS EC2 온디맨드 요금](https://aws.amazon.com/ec2/pricing/on-demand/), 서울 값은 [aws-pricing.com t3.micro](https://aws-pricing.com/t3.micro.html)에서 확인(제3자 집계) |
| EBS gp3 20GiB, 서울 | GB-월 $0.0912, 월 약 $1.82(추정) | 기본 IOPS·처리량 안에서 쓴다. 출처: [AWS EBS 요금](https://aws.amazon.com/ebs/pricing/), 서울 값은 같은 페이지가 읽는 AWS 공개 가격 데이터 |
| Elastic IP(공인 IPv4 하나) | 시간당 $0.005, 월 약 $3.65(추정) | 2024-02-01부터 사용 중인 주소도 과금. 출처: [AWS 공인 IPv4 요금 공지](https://aws.amazon.com/blogs/aws/new-aws-public-ipv4-address-charge-public-ip-insights/) |
| 도메인 | 이 프로젝트로 늘어나는 비용 0 | 운영자가 이미 가진 Cloudflare 영역의 도메인을 쓴다(SDD 11.1절). 등록·갱신비는 이 프로젝트 비용에 넣지 않았다 |
| Cloudflare(DNS, 프록시, Origin CA) | $0 | Free 요금제 기능만 쓴다. 출처: [Cloudflare 요금제](https://www.cloudflare.com/plans/) |
| 토스페이먼츠 테스트 모드 | $0 | 테스트 키는 실제 돈이 오가지 않아 수수료가 없다. 출처: [토스페이먼츠 API 키 문서](https://docs.tosspayments.com/reference/using-api/api-keys) |
| 외부 감시(UptimeRobot 무료) | $0 | SDD 11.1절. 출처: [UptimeRobot 요금](https://uptimerobot.com/pricing/) |
| AWS IAM, OIDC 공급자, Systems Manager Run Command(자동 배포, 2026-11-27 추가) | $0 | IAM과 Run Command는 추가 요금이 없다. 출처: [AWS Systems Manager 요금](https://aws.amazon.com/systems-manager/pricing/) |
| GitHub, GitHub Actions(CI, 문서 동기화, 자동 배포. 2026-11-27 자동 배포 추가) | $0 | 공개 레포의 표준 실행기는 무료다. 출처: [GitHub Actions 요금](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions) |
| 합계 | 월 약 $14.96(추정) | EC2 + EBS + Elastic IP. 평가가 끝나면 운영 DB와 백업을 지우고(SDD 8.7절) 인스턴스, 볼륨, Elastic IP도 지워 과금을 멈춘다 |

### 4.2 규모

기능 점수는 SRS 6.2절 API 목록과 SDD 5절 테이블로 센 미보정 기능 점수다. 가중치는 IFPUG 평균값(EI 4, EO 5, EQ 4, ILF 10, EIF 7)을 일괄로 썼고, 항목별 복잡도는 따지지 않았다(추정).

| 차수 | EI | EO | EQ | ILF | EIF | LOC |
| --- | --- | --- | --- | --- | --- | --- |
| 1차 | 27 | 2 | 12 | 8 | 1 | 2026-11-19 기준 백엔드 1,315줄, 프론트엔드 40줄(잰 값). 완성 규모는 추정하지 않았다 |

- EI 27: 데이터를 바꾸는 경로. 가입 1, 내 정보·배송지 6, 장바구니 3, 주문 4(생성, 취소, 취소 요청, 결제 시작), 결제 2(확인, 실패 기록), 관리자 원두 6, 관리자 주문 5.
- EO 2: 서버가 계산한 값을 내보내는 조회. 장바구니(합계, 배송비), 관리자 주문 목록(취소 요청 건수 배지, SDD 4.8.2절).
- EQ 12: 나머지 조회 10개(상태 확인, 내 정보, 배송지 목록, 원두 목록·상세, 내 주문 목록·상세, 관리자 원두 목록·상세, 관리자 주문 상세)와 로그인, 토큰 재발급.
- ILF 8: `users`, `user_addresses`, `products`, `product_options`, `cart_items`, `orders`, `order_items`, `payments`.
- EIF 1: 토스페이먼츠 결제 API. 택배사는 링크만 만들고 데이터를 주고받지 않아 넣지 않았다.
- 미보정 기능 점수: 27×4 + 2×5 + 12×4 + 8×10 + 1×7 = 253(추정).
- LOC는 `main` 0770de3에서 `wc -l`로 쟀다. 백엔드는 마이그레이션을 뺀 `*.py`, 프론트엔드는 `src/`의 `*.js`, `*.jsx`, `*.css`다.
