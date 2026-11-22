// Korean display names for the enum codes the API returns (SDD 5.0.2, NFR-30).
export const ROLE = { MEMBER: "회원", ADMIN: "관리자" };

export const ROAST_LEVEL = { LIGHT: "라이트", MEDIUM: "미디엄", DARK: "다크" };

export const WEIGHT_SIZE = { "200G": "200g", "500G": "500g", "1KG": "1kg" };

export const GRIND_TYPE = {
  WHOLE_BEAN: "홀빈",
  HAND_DRIP: "핸드드립용",
  ESPRESSO: "에스프레소용",
};

export const SALES_STATUS = {
  ON_SALE: "판매 중",
  SOLD_OUT: "품절",
  STOPPED: "판매 중지",
};

export const ORDER_STATUS = {
  PENDING: "결제 대기",
  PAID: "결제 완료",
  PREPARING: "배송 준비",
  SHIPPED: "배송 중",
  DELIVERED: "배송 완료",
  CANCEL_REQUESTED: "취소 요청",
  CANCELLED: "취소",
};

export const PAYMENT_STATUS = {
  READY: "결제 대기",
  SUCCESS: "결제 성공",
  FAILED: "결제 실패",
  CANCELLED: "결제 취소",
};

export const PAYMENT_METHOD = {
  CARD: "카드",
  EASY_PAY: "간편결제",
  TRANSFER: "계좌이체",
  OTHER: "기타",
};

export const COURIER = {
  CJ: "CJ대한통운",
  HANJIN: "한진택배",
  LOTTE: "롯데택배",
  EPOST: "우체국택배",
  LOGEN: "로젠택배",
};

export function label(table, code) {
  return table[code] ?? code;
}
