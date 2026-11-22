// Fixed demo notice on every screen, no close button (NFR-36).
export default function DemoNoticeBanner() {
  return (
    <div className="text-espresso-950 bg-amber-400 px-4 py-2 text-center text-[13px] font-medium">
      학교 과제 데모입니다. 실제 판매와 결제는 이뤄지지 않습니다.
    </div>
  );
}
