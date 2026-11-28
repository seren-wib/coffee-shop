import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import ProductListPage from "./ProductListPage";
import { fakeApi } from "../test/fakeApi";

const bean = (overrides) => ({
  product_id: 1,
  name: "예가체프 G1",
  origin: "에티오피아",
  roast_level: "LIGHT",
  base_price: 18000,
  lowest_price: 18000,
  image_url: null,
  sales_status: "ON_SALE",
  ...overrides,
});

function Where() {
  const { pathname, search } = useLocation();
  return <p data-testid="where">{pathname + search}</p>;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<ProductListPage />} />
        <Route path="*" element={<Where />} />
      </Routes>
      <Where />
    </MemoryRouter>,
  );
}

function page(results, count = results.length) {
  return { status: 200, data: { count, next: null, previous: null, results } };
}

describe("ProductListPage", () => {
  it("shows cards with origin, roast, starting price and links to detail (FR-1)", async () => {
    fakeApi({
      "GET /products/": page([
        bean({ product_id: 7, lowest_price: 15000 }),
        bean({ product_id: 8, name: "산토스", sales_status: "SOLD_OUT" }),
      ]),
    });
    renderAt("/");
    const card = await screen.findByRole("link", { name: /예가체프 G1/ });
    expect(card).toHaveAttribute("href", "/products/7");
    expect(within(card).getByText("에티오피아 · 라이트")).toBeInTheDocument();
    expect(within(card).getByText("15,000원~")).toBeInTheDocument();
    const soldOut = screen.getByRole("link", { name: /산토스/ });
    expect(within(soldOut).getByText("품절")).toBeInTheDocument();
  });

  it("sends the URL conditions to the API (SDD 7.0.3)", async () => {
    const calls = fakeApi({ "GET /products/": page([bean()]) });
    renderAt(
      "/?search=예가&origin=케냐&roast_level=DARK&min_price=10000&max_price=19999&page=2",
    );
    await screen.findByRole("link", { name: /예가체프 G1/ });
    expect(calls[0].params).toEqual({
      search: "예가",
      origin: "케냐",
      roast_level: "DARK",
      min_price: "10000",
      max_price: "19999",
      page: "2",
    });
    expect(screen.getByLabelText("원두 이름")).toHaveValue("예가");
    expect(screen.getByLabelText("가격")).toHaveValue("10000-19999");
  });

  it("puts the form into the URL and starts from page 1", async () => {
    fakeApi({ "GET /products/": page([bean()]) });
    renderAt("/?page=3");
    await screen.findByRole("link", { name: /예가체프 G1/ });
    await userEvent.type(screen.getByLabelText("원두 이름"), "케냐");
    await userEvent.selectOptions(screen.getByLabelText("가격"), "1만 원 미만");
    await userEvent.selectOptions(screen.getByLabelText("로스팅"), "미디엄");
    await userEvent.click(screen.getByRole("button", { name: "검색" }));
    const where = screen.getAllByTestId("where").at(-1);
    expect(where).toHaveTextContent(
      "/?search=%EC%BC%80%EB%83%90&max_price=9999&roast_level=MEDIUM",
    );
  });

  it("clears every condition with reset", async () => {
    fakeApi({ "GET /products/": page([bean()]) });
    renderAt("/?search=a&origin=케냐&page=2");
    await screen.findByRole("link", { name: /예가체프 G1/ });
    await userEvent.click(screen.getByRole("button", { name: "초기화" }));
    expect(screen.getAllByTestId("where").at(-1)).toHaveTextContent(/^\/$/);
  });

  it("says nothing matched for an empty result (UC-1)", async () => {
    fakeApi({ "GET /products/": page([]) });
    renderAt("/?search=없는원두");
    expect(
      await screen.findByText("조건에 맞는 원두가 없습니다"),
    ).toBeInTheDocument();
  });

  it("links pages and keeps the conditions", async () => {
    fakeApi({ "GET /products/": page([bean()], 45) });
    renderAt("/?roast_level=LIGHT");
    await screen.findByRole("link", { name: /예가체프 G1/ });
    const pager = screen.getByRole("navigation", { name: "페이지" });
    expect(within(pager).getByRole("link", { name: "1" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(within(pager).getByRole("link", { name: "3" })).toHaveAttribute(
      "href",
      "/?roast_level=LIGHT&page=3",
    );
    expect(screen.getByText("원두 45종 · 1 / 3 페이지")).toBeInTheDocument();
  });

  it("goes back to page 1 when the page is out of range", async () => {
    fakeApi({
      "GET /products/": (config) =>
        config.params.page === "9"
          ? { status: 404, data: { code: "NOT_FOUND" } }
          : page([bean()]),
    });
    renderAt("/?page=9");
    await screen.findByRole("link", { name: /예가체프 G1/ });
    expect(screen.getAllByTestId("where").at(-1)).toHaveTextContent(/^\/$/);
  });

  it("shows the server message when the filter is rejected (NFR-34)", async () => {
    fakeApi({
      "GET /products/": {
        status: 400,
        data: { code: "VALIDATION_ERROR", message: "입력값을 확인해 주세요." },
      },
    });
    renderAt("/?min_price=abc");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "입력값을 확인해 주세요.",
    );
  });
});
