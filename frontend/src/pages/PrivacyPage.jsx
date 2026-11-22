// SCR-15 (FR-59). Static text, no API. No personal contact in a public repo: questions go to issues.
const SECTIONS = [
  {
    id: "p1",
    title: "1. 수집 항목",
    body: "이메일, 이름, 연락처, 배송지의 받는 사람·연락처·주소를 수집합니다.",
  },
  {
    id: "p2",
    title: "2. 목적",
    body: "회원을 식별하고 주문과 배송을 처리하는 데만 씁니다.",
  },
  {
    id: "p3",
    title: "3. 보유 기간과 파기",
    body: "시연·평가가 끝나면 운영 데이터베이스와 백업을 함께 지웁니다. 회원 탈퇴 기능은 없습니다.",
  },
  {
    id: "p4",
    title: "4. 결제대행사에 넘기는 정보",
    body: "토스페이먼츠 테스트 모드에 주문명, 금액, 주문자 이름을 넘깁니다. 카드 정보는 이 시스템이 받지 않습니다.",
  },
];

export default function PrivacyPage() {
  return (
    <div className="flex flex-wrap items-start gap-16 px-12 pt-10 pb-16">
      <nav
        aria-label="목차"
        className="flex flex-[1_1_240px] flex-col gap-2.5 pt-[72px] text-sm"
      >
        <span className="text-brown-600 text-[13px] font-medium">목차</span>
        {[...SECTIONS, { id: "p5", title: "5. 문의 방법" }].map((s) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            className="text-brown-900 hover:text-caramel-700 no-underline"
          >
            {s.title}
          </a>
        ))}
      </nav>
      <article className="flex max-w-[800px] min-w-0 flex-[999_1_640px] flex-col gap-7 text-[15px] leading-[1.8]">
        <h1 className="font-serif text-[32px] font-bold">개인정보 처리방침</h1>
        {SECTIONS.map((s) => (
          <section key={s.id} id={s.id} className="flex flex-col gap-2">
            <h2 className="text-lg font-bold">{s.title}</h2>
            <p>{s.body}</p>
          </section>
        ))}
        <section id="p5" className="flex flex-col gap-2">
          <h2 className="text-lg font-bold">5. 문의 방법</h2>
          <p>
            프로젝트{" "}
            <a
              href="https://github.com/seren-wib/coffee-shop/issues"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub 저장소의 이슈
            </a>
            로 문의해 주세요.
          </p>
        </section>
      </article>
    </div>
  );
}
