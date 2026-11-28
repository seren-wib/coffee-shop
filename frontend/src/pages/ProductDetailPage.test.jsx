import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import ProductDetailPage from "./ProductDetailPage";
import { setTokens } from "../auth/tokenStore";
import { fakeApi } from "../test/fakeApi";
import { makeJwt } from "../test/jwt";

const option = (overrides) => ({
  option_id: 1,
  weight_size: "200G",
  grind_type: "WHOLE_BEAN",
  extra_price: 0,
  price: 18000,
  stock_quantity: 3,
  is_available: true,
  ...overrides,
});

const product = {
  product_id: 5,
  name: "예가체프 G1",
  origin: "에티오피아",
  roast_level: "LIGHT",
  base_price: 18000,
  tasting_notes: "자스민, 레몬",
  description: "밝은 산미",
  image_url: null,
  sales_status: "ON_SALE",
  options: [
    option({ option_id: 1 }),
    option({ option_id: 2, grind_type: "HAND_DRIP" }),
    option({
      option_id: 3,
      weight_size: "500G",
      extra_price: 12000,
      price: 30000,
    }),
    option({
      option_id: 4,
      weight_size: "1KG",
      extra_price: 30000,
      price: 48000,
      stock_quantity: 0,
      is_available: false,
    }),
  ],
};

function Where() {
  const { pathname, search } = useLocation();
  return <p data-testid="where">{pathname + search}</p>;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/products/:id" element={<ProductDetailPage />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

const member = () =>
  setTokens({ access: makeJwt({ role: "MEMBER" }), refresh: "r" });

describe("ProductDetailPage", () => {
  it("shows the product and the first available option's price (FR-6)", async () => {
    fakeApi({ "GET /products/5/": { data: product } });
    renderAt("/products/5");
    expect(
      await screen.findByRole("heading", { name: "예가체프 G1" }),
    ).toBeInTheDocument();
    expect(screen.getByText("맛 노트: 자스민, 레몬")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "200g" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(
      screen.getByRole("button", { name: "500g +12,000원" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "1kg 품절" })).toBeDisabled();
    expect(screen.getByText("재고 3개")).toBeInTheDocument();
    expect(screen.getByTestId("total")).toHaveTextContent("18,000원");
  });

  it("stops + at the option's stock and updates the total (DR-10)", async () => {
    fakeApi({ "GET /products/5/": { data: product } });
    renderAt("/products/5");
    const plus = await screen.findByRole("button", { name: "수량 더하기" });
    await userEvent.click(plus);
    await userEvent.click(plus);
    expect(plus).toBeDisabled();
    expect(screen.getByTestId("quantity")).toHaveTextContent("3");
    expect(screen.getByTestId("total")).toHaveTextContent("54,000원");
  });

  it("adds the chosen option to the cart (FR-19)", async () => {
    member();
    const calls = fakeApi({
      "GET /products/5/": { data: product },
      "POST /cart/items/": {
        status: 201,
        data: { cart_item_id: 9, option_id: 3, quantity: 1 },
      },
    });
    renderAt("/products/5");
    await userEvent.click(
      await screen.findByRole("button", { name: "500g +12,000원" }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "장바구니 담기" }),
    );
    expect(calls.at(-1)).toMatchObject({
      key: "POST /cart/items/",
      data: { option_id: 3, quantity: 1 },
    });
    const done = await screen.findByRole("status");
    expect(done).toHaveTextContent("장바구니에 담았습니다");
    expect(
      within(done).getByRole("link", { name: "장바구니로 가기" }),
    ).toHaveAttribute("href", "/cart");
  });

  it("picks the grind within the chosen weight", async () => {
    member();
    const calls = fakeApi({
      "GET /products/5/": { data: product },
      "POST /cart/items/": { status: 201, data: {} },
    });
    renderAt("/products/5");
    await userEvent.selectOptions(
      await screen.findByLabelText("분쇄도"),
      "핸드드립용",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "장바구니 담기" }),
    );
    expect(calls.at(-1).data).toEqual({ option_id: 2, quantity: 1 });
  });

  it("sends a guest to login and back (SDD 7.2)", async () => {
    fakeApi({ "GET /products/5/": { data: product } });
    renderAt("/products/5");
    await userEvent.click(
      await screen.findByRole("button", { name: "장바구니 담기" }),
    );
    expect(screen.getByTestId("where")).toHaveTextContent(
      "/login?next=%2Fproducts%2F5",
    );
  });

  it("shows the 409 message from the server", async () => {
    member();
    fakeApi({
      "GET /products/5/": { data: product },
      "POST /cart/items/": {
        status: 409,
        data: { code: "OUT_OF_STOCK", message: "재고가 부족합니다." },
      },
    });
    renderAt("/products/5");
    await userEvent.click(
      await screen.findByRole("button", { name: "장바구니 담기" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "재고가 부족합니다.",
    );
  });

  it("turns the add button off when no option can be sold (UC-4)", async () => {
    fakeApi({
      "GET /products/5/": {
        data: {
          ...product,
          sales_status: "SOLD_OUT",
          options: [option({ stock_quantity: 0, is_available: false })],
        },
      },
    });
    renderAt("/products/5");
    expect(await screen.findByRole("button", { name: "품절" })).toBeDisabled();
  });

  it("says the bean is not sold on 404", async () => {
    fakeApi({
      "GET /products/5/": { status: 404, data: { code: "NOT_FOUND" } },
    });
    renderAt("/products/5");
    expect(
      await screen.findByRole("heading", { name: "판매하지 않는 원두입니다" }),
    ).toBeInTheDocument();
  });
});
