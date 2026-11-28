import { Link } from "react-router-dom";

// Unknown path (SDD 7.0, NFR-30).
export default function NotFoundPage() {
  return (
    <div className="flex flex-col gap-3 px-12 pt-10 pb-14">
      <h1 className="font-serif text-[32px] font-bold">
        페이지를 찾을 수 없습니다
      </h1>
      <p className="text-brown-600 text-[15px]">
        주소가 바뀌었거나 없는 화면입니다.
      </p>
      <p className="text-[15px]">
        <Link to="/">원두 목록으로 가기</Link>
      </p>
    </div>
  );
}
