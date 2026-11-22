import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import AdminProductFormPage from "./AdminProductFormPage";
import AdminProductListPage from "./AdminProductListPage";
import { fakeApi } from "../../test/fakeApi";

function Where() {
  const { pathname, search } = useLocation();
  return <p data-testid="where">{pathname + search}</p>;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/products" element={<AdminProductListPage />} />
        <Route path="/admin/products/new" element={<AdminProductFormPage />} />
        <Route path="/admin/products/:id" element={<AdminProductFormPage />} />
      </Routes>
      <Where />
    </MemoryRouter>,
  );
}

const listItem = (overrides) => ({
  product_id: 5,
  name: "예가체프 G1",
  origin: "에티오피아",
  roast_level: "LIGHT",
  base_price: 18000,
  sales_status: "ON_SALE",
  option_count: 3,
  total_stock: 42,
  options: [],
  ...overrides,
});

const product = (overrides) => ({
  product_id: 5,
  name: "예가체프 G1",
  origin: "에티오피아",
  roast_level: "LIGHT",
  base_price: 18000,
  tasting_notes: "자스민",
  description: "밝은 산미",
  image_url: "",
  sales_status: "ON_SALE",
  created_at: "2026-11-20T10:00:00+09:00",
  options: [
    {
      option_id: 11,
      weight_size: "200G",
      grind_type: "WHOLE_BEAN",
      extra_price: 0,
      price: 18000,
      stock_quantity: 10,
      is_available: true,
    },
  ],
  ...overrides,
});

describe("AdminProductListPage", () => {
  it("lists products with options and stock, and stops sales (FR-36, FR-42)", async () => {
    let status = "ON_SALE";
    const calls = fakeApi({
      "GET /admin/products/": () => ({
        data: {
          count: 1,
          next: null,
          previous: null,
          results: [listItem({ sales_status: status })],
        },
      }),
      "POST /admin/products/5/stop/": () => {
        status = "STOPPED";
        return { data: product({ sales_status: "STOPPED" }) };
      },
    });
    renderAt("/admin/products");
    const line = await screen.findByRole("row", { name: /예가체프 G1/ });
    expect(within(line).getByText("3 / 42")).toBeInTheDocument();
    expect(within(line).getByRole("link", { name: "수정" })).toHaveAttribute(
      "href",
      "/admin/products/5",
    );
    await userEvent.click(
      within(line).getByRole("button", { name: "판매 중지" }),
    );
    expect(
      await within(screen.getByRole("row", { name: /예가체프 G1/ })).findByRole(
        "button",
        {
          name: "판매 재개",
        },
      ),
    ).toBeInTheDocument();
    expect(calls.map((c) => c.key)).toContain("POST /admin/products/5/stop/");
  });

  it("searches by name and sales status in the URL (FR-56)", async () => {
    const calls = fakeApi({
      "GET /admin/products/": {
        data: { count: 0, next: null, previous: null, results: [] },
      },
    });
    renderAt("/admin/products");
    await screen.findByText("조건에 맞는 원두가 없습니다");
    await userEvent.type(screen.getByLabelText("원두 이름"), "케냐");
    await userEvent.selectOptions(
      screen.getByLabelText("판매 상태"),
      "판매 중지",
    );
    await userEvent.click(screen.getByRole("button", { name: "검색" }));
    expect(calls.at(-1).params).toEqual({
      search: "케냐",
      sales_status: "STOPPED",
    });
  });
});

describe("AdminProductFormPage", () => {
  it("creates a product, then goes to its edit screen for options (FR-37)", async () => {
    const calls = fakeApi({
      "POST /admin/products/": {
        status: 201,
        data: product({ product_id: 9 }),
      },
      "GET /admin/products/9/": { data: product({ product_id: 9 }) },
    });
    renderAt("/admin/products/new");
    await userEvent.type(screen.getByLabelText("원두명"), "새 원두");
    await userEvent.selectOptions(screen.getByLabelText("원산지"), "케냐");
    await userEvent.selectOptions(screen.getByLabelText("로스팅 정도"), "다크");
    await userEvent.type(screen.getByLabelText("기본 가격 (원)"), "21000");
    await userEvent.click(screen.getByRole("button", { name: "저장" }));
    expect(calls[0].data).toEqual({
      name: "새 원두",
      origin: "케냐",
      roast_level: "DARK",
      base_price: 21000,
      tasting_notes: "",
      description: "",
      image_url: "",
    });
    expect(
      await screen.findByRole("heading", { name: "원두 수정 · 예가체프 G1" }),
    ).toBeInTheDocument();
    expect(screen.getAllByTestId("where").at(-1)).toHaveTextContent(
      "/admin/products/9",
    );
  });

  it("adds an option and shows the server's duplicate message (FR-39, DR-3)", async () => {
    fakeApi({
      "GET /admin/products/5/": { data: product() },
      "POST /admin/products/5/options/": {
        status: 409,
        data: { code: "DUPLICATE_OPTION", message: "이미 있는 옵션입니다." },
      },
    });
    renderAt("/admin/products/5");
    await screen.findByRole("heading", { name: "원두 수정 · 예가체프 G1" });
    await userEvent.type(screen.getByLabelText("새 옵션 재고수량"), "5");
    await userEvent.click(screen.getByRole("button", { name: "옵션 추가" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "이미 있는 옵션입니다.",
    );
  });

  it("saves an option's extra price and stock in one request (FR-40, FR-41)", async () => {
    const calls = fakeApi({
      "GET /admin/products/5/": { data: product() },
      "PATCH /admin/products/5/options/11/": { data: product() },
    });
    renderAt("/admin/products/5");
    const row = (await screen.findAllByRole("row", { name: /200g/ }))[0];
    const stock = within(row).getByLabelText("재고수량");
    await userEvent.clear(stock);
    await userEvent.type(stock, "25");
    await userEvent.click(within(row).getByRole("button", { name: "저장" }));
    expect(calls.find((c) => c.key.startsWith("PATCH")).data).toEqual({
      extra_price: 0,
      stock_quantity: 25,
    });
  });
});
