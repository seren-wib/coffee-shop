import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import AdminOrderDetailPage from "./AdminOrderDetailPage";
import AdminOrderListPage from "./AdminOrderListPage";
import { fakeApi } from "../../test/fakeApi";

const ID = "ORD-20261108-002";

function Where() {
  const { pathname, search } = useLocation();
  return <p data-testid="where">{pathname + search}</p>;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/orders" element={<AdminOrderListPage />} />
        <Route path="/admin/orders/:id" element={<AdminOrderDetailPage />} />
      </Routes>
      <Where />
    </MemoryRouter>,
  );
}

const page = (results, count = results.length) => ({
  data: { count, next: null, previous: null, results },
});

const listRow = {
  order_id: ID,
  created_at: "2026-11-08T10:21:00+09:00",
  member_email: "member@example.com",
  member_name: "회원",
  final_payment_amt: 20000,
  status: "CANCEL_REQUESTED",
};

const detail = (overrides) => ({
  order_id: ID,
  status: "PAID",
  created_at: "2026-11-08T10:21:00+09:00",
  items: [
    {
      product_name: "우일라",
      weight_size: "200G",
      grind_type: "HAND_DRIP",
      order_price: 17000,
      quantity: 1,
      subtotal: 17000,
    },
  ],
  total_product_amt: 17000,
  shipping_fee: 3000,
  final_payment_amt: 20000,
  recipient_name: "받는이",
  recipient_phone: "010-0000-0000",
  shipping_address: "(00000) 충청북도 청주시 1",
  payments: [
    {
      payment_id: 3,
      status: "SUCCESS",
      method: "CARD",
      paid_amount: 20000,
      failure_reason: null,
      approved_at: "2026-11-08T10:22:00+09:00",
      pg_order_id: `${ID}-P1`,
      pg_tid: "tviva20261108abcdefa1b2c3d4",
    },
  ],
  member: {
    user_id: 2,
    email: "member@example.com",
    user_name: "회원",
    phone_number: "010-1",
  },
  status_before_cancel: null,
  cancel_reason: null,
  allowed_actions: ["prepare"],
  ...overrides,
});

describe("AdminOrderListPage", () => {
  it("lists orders with member and status, and counts cancel requests (FR-44, SDD 6.14)", async () => {
    fakeApi({
      "GET /admin/orders/": (config) =>
        config.params.status === "CANCEL_REQUESTED"
          ? page([listRow], 2)
          : page([listRow]),
    });
    renderAt("/admin/orders");
    const line = await screen.findByRole("row", { name: new RegExp(ID) });
    expect(within(line).getByText("member@example.com")).toBeInTheDocument();
    expect(within(line).getByText("20,000원")).toBeInTheDocument();
    const tabs = screen.getByRole("navigation", { name: "주문 상태" });
    expect(await within(tabs).findByText("2")).toBeInTheDocument();
  });

  it("searches by order number or email in the URL (FR-57)", async () => {
    const calls = fakeApi({ "GET /admin/orders/": page([listRow]) });
    renderAt("/admin/orders?status=PAID");
    await screen.findByRole("row", { name: new RegExp(ID) });
    await userEvent.type(
      screen.getByLabelText("주문번호 또는 회원 이메일"),
      "member",
    );
    await userEvent.click(screen.getByRole("button", { name: "검색" }));
    expect(screen.getByTestId("where")).toHaveTextContent(
      "/admin/orders?status=PAID&search=member",
    );
    expect(calls.at(-1).params).toMatchObject({
      status: "PAID",
      search: "member",
    });
  });
});

describe("AdminOrderDetailPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows member, payments with the last 8 of the PG id, and the allowed action (FR-46)", async () => {
    fakeApi({ [`GET /admin/orders/${ID}/`]: { data: detail() } });
    renderAt(`/admin/orders/${ID}`);
    expect(
      await screen.findByRole("heading", { name: `주문 ${ID}` }),
    ).toBeInTheDocument();
    expect(screen.getByText(/거래 ID …a1b2c3d4/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "배송 준비" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "배송 완료" }),
    ).not.toBeInTheDocument();
  });

  it("runs prepare, then reloads (FR-47)", async () => {
    let status = "PAID";
    const calls = fakeApi({
      [`GET /admin/orders/${ID}/`]: () => ({
        data: detail({
          status,
          allowed_actions: status === "PAID" ? ["prepare"] : ["ship"],
        }),
      }),
      [`POST /admin/orders/${ID}/prepare/`]: () => {
        status = "PREPARING";
        return { data: {} };
      },
    });
    renderAt(`/admin/orders/${ID}`);
    await userEvent.click(
      await screen.findByRole("button", { name: "배송 준비" }),
    );
    expect(
      await screen.findByRole("button", { name: "송장 등록" }),
    ).toBeInTheDocument();
    expect(calls.map((c) => c.key)).toContain(
      `POST /admin/orders/${ID}/prepare/`,
    );
  });

  it("registers the courier and tracking number (FR-48)", async () => {
    const calls = fakeApi({
      [`GET /admin/orders/${ID}/`]: {
        data: detail({ status: "PREPARING", allowed_actions: ["ship"] }),
      },
      [`POST /admin/orders/${ID}/ship/`]: { data: {} },
    });
    renderAt(`/admin/orders/${ID}`);
    await userEvent.selectOptions(
      await screen.findByLabelText("택배사"),
      "한진택배",
    );
    await userEvent.type(screen.getByLabelText("송장번호"), "1234-5678");
    await userEvent.click(screen.getByRole("button", { name: "송장 등록" }));
    expect(calls.find((c) => c.key.endsWith("/ship/")).data).toEqual({
      courier_code: "HANJIN",
      tracking_number: "1234-5678",
    });
  });

  it("approves a cancel request after confirming and shows a PG failure (FR-50)", async () => {
    fakeApi({
      [`GET /admin/orders/${ID}/`]: {
        data: detail({
          status: "CANCEL_REQUESTED",
          cancel_reason: "주소를 잘못 입력했습니다.",
          status_before_cancel: "PREPARING",
          allowed_actions: ["cancel_approve", "cancel_reject"],
        }),
      },
      [`POST /admin/orders/${ID}/cancel-approve/`]: {
        status: 502,
        data: { code: "PG_ERROR", message: "PG 오류" },
      },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderAt(`/admin/orders/${ID}`);
    const aside = await screen.findByRole("complementary", {
      name: "취소 요청",
    });
    expect(
      within(aside).getByText("주소를 잘못 입력했습니다."),
    ).toBeInTheDocument();
    expect(within(aside).getByText("배송 준비")).toBeInTheDocument();
    await userEvent.click(
      within(aside).getByRole("button", { name: "취소 승인" }),
    );
    expect(window.confirm).toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "결제 취소에 실패했습니다. 잠시 후 다시 승인해 주세요.",
    );
  });
});
