import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import OrderListPage from "./OrderListPage";
import { fakeApi } from "../test/fakeApi";

const row = (overrides) => ({
  order_id: "ORD-20261120-003",
  created_at: "2026-11-20T14:03:11+09:00",
  final_payment_amt: 30000,
  status: "SHIPPED",
  item_count: 3,
  first_item_name: "브라질 산토스",
  ...overrides,
});

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <OrderListPage />
    </MemoryRouter>,
  );
}

describe("OrderListPage", () => {
  it("lists my orders with date, first item, amount and status (FR-30)", async () => {
    fakeApi({
      "GET /orders/": {
        data: { count: 1, next: null, previous: null, results: [row()] },
      },
    });
    renderAt("/orders");
    const line = await screen.findByRole("row", { name: /ORD-20261120-003/ });
    expect(within(line).getByText("2026-11-20")).toBeInTheDocument();
    expect(within(line).getByText("브라질 산토스 외 2건")).toBeInTheDocument();
    expect(within(line).getByText("30,000원")).toBeInTheDocument();
    expect(within(line).getByText("배송 중")).toBeInTheDocument();
    expect(
      within(line).getByRole("link", { name: "상세보기" }),
    ).toHaveAttribute("href", "/orders/ORD-20261120-003");
  });

  it("filters by the status tab in the URL (FR-55)", async () => {
    const calls = fakeApi({
      "GET /orders/": {
        data: { count: 0, next: null, previous: null, results: [] },
      },
    });
    renderAt("/orders?status=PAID&page=2");
    expect(await screen.findByText("주문 내역이 없습니다")).toBeInTheDocument();
    expect(calls[0].params).toEqual({ status: "PAID", page: "2" });
    const tabs = screen.getByRole("navigation", { name: "주문 상태" });
    expect(
      within(tabs).getByRole("link", { name: "결제 완료" }),
    ).toHaveAttribute("aria-current", "page");
    expect(within(tabs).getByRole("link", { name: "전체" })).toHaveAttribute(
      "href",
      "/orders",
    );
    expect(
      within(tabs).getByRole("link", { name: "취소 요청" }),
    ).toHaveAttribute("href", "/orders?status=CANCEL_REQUESTED");
  });

  it("shows a single item without the count", async () => {
    fakeApi({
      "GET /orders/": {
        data: {
          count: 1,
          next: null,
          previous: null,
          results: [row({ item_count: 1 })],
        },
      },
    });
    renderAt("/orders");
    expect(await screen.findByText("브라질 산토스")).toBeInTheDocument();
  });
});
