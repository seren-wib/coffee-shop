import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import OrderDetailPage from "./OrderDetailPage";
import { payOrder } from "../lib/pay";
import { fakeApi } from "../test/fakeApi";

vi.mock("../lib/pay", async (importOriginal) => ({
  ...(await importOriginal()),
  payOrder: vi.fn(),
}));

const ID = "ORD-20261120-003";

const order = (overrides) => ({
  order_id: ID,
  status: "SHIPPED",
  created_at: "2026-11-20T14:03:11+09:00",
  items: [
    {
      product_name: "브라질 산토스",
      weight_size: "200G",
      grind_type: "WHOLE_BEAN",
      order_price: 15000,
      quantity: 2,
      subtotal: 30000,
    },
  ],
  total_product_amt: 30000,
  shipping_fee: 0,
  final_payment_amt: 30000,
  recipient_name: "홍길동",
  recipient_phone: "010-0000-0000",
  shipping_address: "(00000) 서울특별시 중구 1",
  payments: [
    {
      payment_id: 9,
      status: "SUCCESS",
      method: "CARD",
      paid_amount: 30000,
      failure_reason: null,
      approved_at: "2026-11-20T14:04:02+09:00",
    },
  ],
  courier_name: "CJ대한통운",
  tracking_number: "1234567890",
  tracking_url: "https://trace.example/track?no=1234567890",
  shipped_at: "2026-11-21T09:30:00+09:00",
  delivered_at: null,
  cancel_reason: null,
  can_pay: false,
  can_cancel: false,
  can_request_cancel: false,
  ...overrides,
});

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={[`/orders/${ID}`]}>
      <Routes>
        <Route path="/orders/:id" element={<OrderDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("OrderDetailPage", () => {
  beforeEach(() => {
    payOrder.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows items at order price, amounts, payments and shipping (FR-31, FR-34)", async () => {
    fakeApi({ [`GET /orders/${ID}/`]: { data: order() } });
    renderDetail();
    expect(
      await screen.findByRole("heading", { name: `주문 ${ID}` }),
    ).toBeInTheDocument();
    expect(screen.getByText("배송 중")).toBeInTheDocument();
    expect(screen.getByText(/주문 당시 15,000원/)).toBeInTheDocument();
    expect(
      screen.getByText("2026-11-20 14:04 · 카드 · 결제 성공"),
    ).toBeInTheDocument();
    const track = screen.getByRole("link", { name: "배송 조회" });
    expect(track).toHaveAttribute(
      "href",
      "https://trace.example/track?no=1234567890",
    );
    expect(track).toHaveAttribute("target", "_blank");
    expect(track).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("shows a shipped order's cancel button off with the reason (UC-9)", async () => {
    fakeApi({ [`GET /orders/${ID}/`]: { data: order() } });
    renderDetail();
    expect(
      await screen.findByRole("button", { name: "주문 취소" }),
    ).toBeDisabled();
    expect(
      screen.getByText("배송이 시작되어 취소할 수 없습니다."),
    ).toBeInTheDocument();
  });

  it("pays a pending order again (FR-29)", async () => {
    fakeApi({
      [`GET /orders/${ID}/`]: {
        data: order({
          status: "PENDING",
          can_pay: true,
          can_cancel: true,
          payments: [],
        }),
      },
    });
    payOrder.mockResolvedValue(undefined);
    renderDetail();
    await userEvent.click(
      await screen.findByRole("button", { name: "결제하기" }),
    );
    expect(payOrder).toHaveBeenCalledWith(ID);
  });

  it("cancels a pending order after confirming, then reloads (FR-32)", async () => {
    let status = "PENDING";
    const calls = fakeApi({
      [`GET /orders/${ID}/`]: () => ({
        data: order({
          status,
          can_pay: status === "PENDING",
          can_cancel: status === "PENDING",
        }),
      }),
      [`POST /orders/${ID}/cancel/`]: () => {
        status = "CANCELLED";
        return { data: {} };
      },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderDetail();
    await userEvent.click(
      await screen.findByRole("button", { name: "주문 취소" }),
    );
    expect(window.confirm).toHaveBeenCalled();
    expect(await screen.findByText("취소")).toBeInTheDocument();
    expect(calls.map((c) => c.key)).toContain(`POST /orders/${ID}/cancel/`);
  });

  it("does nothing when the confirm dialog is dismissed", async () => {
    const calls = fakeApi({
      [`GET /orders/${ID}/`]: {
        data: order({ status: "PENDING", can_cancel: true }),
      },
    });
    vi.spyOn(window, "confirm").mockReturnValue(false);
    renderDetail();
    await userEvent.click(
      await screen.findByRole("button", { name: "주문 취소" }),
    );
    expect(calls).toHaveLength(1);
  });

  it("sends a cancel request with a reason (FR-33)", async () => {
    const calls = fakeApi({
      [`GET /orders/${ID}/`]: () => ({
        data: order({ status: "PAID", can_request_cancel: true }),
      }),
      [`POST /orders/${ID}/cancel-request/`]: { data: {} },
    });
    renderDetail();
    await userEvent.click(
      await screen.findByRole("button", { name: "취소 요청" }),
    );
    await userEvent.type(
      screen.getByLabelText("취소 사유"),
      "주소를 잘못 넣었어요",
    );
    await userEvent.click(screen.getByRole("button", { name: "요청 보내기" }));
    expect(calls.find((c) => c.key.endsWith("cancel-request/")).data).toEqual({
      reason: "주소를 잘못 넣었어요",
    });
  });

  it("shows the reason while the request waits for the admin", async () => {
    fakeApi({
      [`GET /orders/${ID}/`]: {
        data: order({ status: "CANCEL_REQUESTED", cancel_reason: "단순 변심" }),
      },
    });
    renderDetail();
    const aside = await screen.findByRole("complementary", {
      name: "주문 관리",
    });
    expect(within(aside).getByText("단순 변심")).toBeInTheDocument();
    expect(within(aside).getByText("관리자 확인 중")).toBeInTheDocument();
  });

  it("says the order was not found for another member's order (NFR-11)", async () => {
    fakeApi({
      [`GET /orders/${ID}/`]: { status: 404, data: { code: "NOT_FOUND" } },
    });
    renderDetail();
    expect(
      await screen.findByRole("heading", { name: "주문을 찾을 수 없습니다" }),
    ).toBeInTheDocument();
  });
});
