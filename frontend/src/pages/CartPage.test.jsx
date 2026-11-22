import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import CartPage from "./CartPage";
import { fakeApi } from "../test/fakeApi";

const item = (overrides) => ({
  cart_item_id: 7,
  option_id: 12,
  product_id: 3,
  product_name: "예가체프 G1",
  image_url: null,
  weight_size: "200G",
  grind_type: "HAND_DRIP",
  price: 18000,
  quantity: 2,
  subtotal: 36000,
  stock_quantity: 5,
  is_available: true,
  ...overrides,
});

const cart = (items, extra = {}) => ({
  status: 200,
  data: {
    items,
    product_amount: items.reduce((sum, i) => sum + i.subtotal, 0),
    shipping_fee: 0,
    total_amount: items.reduce((sum, i) => sum + i.subtotal, 0),
    can_order: items.every((i) => i.is_available),
    ...extra,
  },
});

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}

function renderCart() {
  return render(
    <MemoryRouter initialEntries={["/cart"]}>
      <Routes>
        <Route path="/cart" element={<CartPage />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

const row = (name) => screen.getByRole("row", { name: new RegExp(name) });

describe("CartPage", () => {
  it("lists items with option, price, quantity and subtotal, and the server totals (FR-20)", async () => {
    fakeApi({
      "GET /cart/": cart([item()], { shipping_fee: 3000, total_amount: 39000 }),
    });
    renderCart();
    const line = await screen.findByRole("row", { name: /예가체프 G1/ });
    expect(within(line).getByText("200g · 핸드드립용")).toBeInTheDocument();
    expect(within(line).getByText("18,000원")).toBeInTheDocument();
    expect(within(line).getByText("36,000원")).toBeInTheDocument();
    const summary = screen.getByRole("complementary", {
      name: "결제 예정 금액",
    });
    expect(within(summary).getByText("3,000원")).toBeInTheDocument();
    expect(within(summary).getByText("39,000원")).toBeInTheDocument();
  });

  it("changes the quantity on the server, then reloads the cart (FR-21)", async () => {
    let quantity = 2;
    const calls = fakeApi({
      "GET /cart/": () =>
        cart([item({ quantity, subtotal: 18000 * quantity })]),
      "PATCH /cart/items/7/": (config) => {
        quantity = JSON.parse(config.data).quantity;
        return { status: 200, data: {} };
      },
    });
    renderCart();
    await screen.findByRole("row", { name: /예가체프 G1/ });
    await userEvent.click(
      within(row("예가체프 G1")).getByRole("button", { name: "수량 더하기" }),
    );
    expect(
      await within(row("예가체프 G1")).findByText("54,000원"),
    ).toBeInTheDocument();
    expect(calls.map((c) => c.key)).toEqual([
      "GET /cart/",
      "PATCH /cart/items/7/",
      "GET /cart/",
    ]);
    expect(calls[1].data).toEqual({ quantity: 3 });
  });

  it("deletes an item, then reloads (FR-22)", async () => {
    let items = [item(), item({ cart_item_id: 8, product_name: "수프리모" })];
    fakeApi({
      "GET /cart/": () => cart(items),
      "DELETE /cart/items/8/": () => {
        items = items.filter((i) => i.cart_item_id !== 8);
        return { status: 204, data: "" };
      },
    });
    renderCart();
    await screen.findByRole("row", { name: /수프리모/ });
    await userEvent.click(
      within(row("수프리모")).getByRole("button", { name: "삭제" }),
    );
    expect(
      await screen.findByRole("row", { name: /예가체프 G1/ }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("row", { name: /수프리모/ }),
    ).not.toBeInTheDocument();
  });

  it("marks items that cannot be ordered and turns ordering off (SDD 6.5)", async () => {
    fakeApi({
      "GET /cart/": cart([
        item(),
        item({ cart_item_id: 9, product_name: "산토스", is_available: false }),
      ]),
    });
    renderCart();
    const bad = await screen.findByRole("row", { name: /산토스/ });
    expect(within(bad).getByText(/주문할 수 없는 상품/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "주문하기" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "이 상품을 빼거나 수량을 줄여 주세요",
    );
  });

  it("goes to checkout", async () => {
    fakeApi({ "GET /cart/": cart([item()]) });
    renderCart();
    await userEvent.click(
      await screen.findByRole("button", { name: "주문하기" }),
    );
    expect(screen.getByTestId("where")).toHaveTextContent("/checkout");
  });

  it("shows an empty cart with a way back to the list", async () => {
    fakeApi({ "GET /cart/": cart([]) });
    renderCart();
    expect(
      await screen.findByText("장바구니가 비어 있습니다"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "원두 보러 가기" }),
    ).toHaveAttribute("href", "/");
  });

  it("shows the server message when a change is refused", async () => {
    fakeApi({
      "GET /cart/": cart([item()]),
      "PATCH /cart/items/7/": {
        status: 409,
        data: { code: "OUT_OF_STOCK", message: "재고가 부족합니다." },
      },
    });
    renderCart();
    await screen.findByRole("row", { name: /예가체프 G1/ });
    await userEvent.click(
      within(row("예가체프 G1")).getByRole("button", { name: "수량 더하기" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "재고가 부족합니다.",
    );
  });
});
