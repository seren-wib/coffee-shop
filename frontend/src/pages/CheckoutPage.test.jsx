import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CheckoutPage from "./CheckoutPage";
import { payOrder } from "../lib/pay";
import { fakeApi } from "../test/fakeApi";

vi.mock("../lib/pay", async (importOriginal) => ({
  ...(await importOriginal()),
  payOrder: vi.fn(),
}));

const cart = {
  items: [
    {
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
    },
  ],
  product_amount: 36000,
  shipping_fee: 0,
  total_amount: 36000,
  can_order: true,
};

const address = (overrides) => ({
  address_id: 1,
  recipient_name: "김회원",
  recipient_phone: "010-1111-2222",
  zipcode: "28644",
  base_address: "충청북도 청주시 서원구 충대로 1",
  detail_address: "1호",
  is_default: false,
  ...overrides,
});

const order = {
  order_id: "ORD-20261123-001",
  status: "PENDING",
  final_payment_amt: 36000,
};

function renderCheckout() {
  return render(
    <MemoryRouter initialEntries={["/checkout"]}>
      <CheckoutPage />
    </MemoryRouter>,
  );
}

describe("CheckoutPage", () => {
  beforeEach(() => {
    payOrder.mockReset();
  });

  it("shows the cart and server amounts, with the default address chosen (FR-24)", async () => {
    fakeApi({
      "GET /cart/": { data: cart },
      "GET /me/addresses/": {
        data: [
          address(),
          address({ address_id: 2, is_default: true, detail_address: "2호" }),
        ],
      },
    });
    renderCheckout();
    expect(await screen.findByText(/예가체프 G1/)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /2호/ })).toBeChecked();
    expect(
      screen.getByRole("button", { name: "36,000원 결제하기" }),
    ).toBeEnabled();
  });

  it("creates the order with the chosen address, then opens payment (SDD 7.6)", async () => {
    const calls = fakeApi({
      "GET /cart/": { data: cart },
      "GET /me/addresses/": { data: [address({ is_default: true })] },
      "POST /orders/": { status: 201, data: order },
    });
    payOrder.mockResolvedValue(undefined);
    renderCheckout();
    await userEvent.click(
      await screen.findByRole("button", { name: "36,000원 결제하기" }),
    );
    expect(calls.find((c) => c.key === "POST /orders/").data).toEqual({
      address_id: 1,
    });
    expect(payOrder).toHaveBeenCalledWith("ORD-20261123-001");
  });

  it("opens the new address fields when there is no saved address", async () => {
    const calls = fakeApi({
      "GET /cart/": { data: cart },
      "GET /me/addresses/": { data: [] },
      "POST /orders/": { status: 201, data: order },
    });
    payOrder.mockResolvedValue(undefined);
    renderCheckout();
    await userEvent.type(await screen.findByLabelText("받는 사람"), "박받음");
    await userEvent.type(screen.getByLabelText("연락처"), "010-3333-4444");
    await userEvent.type(screen.getByLabelText("우편번호"), "12345");
    await userEvent.type(screen.getByLabelText("주소"), "서울특별시 중구 1");
    await userEvent.click(
      screen.getByRole("button", { name: "36,000원 결제하기" }),
    );
    expect(calls.find((c) => c.key === "POST /orders/").data).toEqual({
      address: {
        recipient_name: "박받음",
        recipient_phone: "010-3333-4444",
        zipcode: "12345",
        base_address: "서울특별시 중구 1",
        detail_address: "",
      },
    });
  });

  it("stops on 409 with the server message and makes no payment (UC-5)", async () => {
    fakeApi({
      "GET /cart/": { data: cart },
      "GET /me/addresses/": { data: [address({ is_default: true })] },
      "POST /orders/": {
        status: 409,
        data: {
          code: "OUT_OF_STOCK",
          message: "재고가 부족한 상품이 있습니다.",
          details: { cart_item_ids: [7] },
        },
      },
    });
    renderCheckout();
    await userEvent.click(
      await screen.findByRole("button", { name: "36,000원 결제하기" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "재고가 부족한 상품이 있습니다.",
    );
    expect(screen.getByText("주문할 수 없는 상품")).toBeInTheDocument();
    expect(payOrder).not.toHaveBeenCalled();
  });

  it("keeps the order and offers order detail when payment cannot open (FR-29)", async () => {
    const calls = fakeApi({
      "GET /cart/": { data: cart },
      "GET /me/addresses/": { data: [address({ is_default: true })] },
      "POST /orders/": { status: 201, data: order },
    });
    const error = new Error("disabled");
    error.response = {
      status: 503,
      data: {
        code: "PAYMENTS_DISABLED",
        message: "지금은 결제를 받을 수 없습니다.",
      },
    };
    payOrder.mockRejectedValueOnce(error).mockResolvedValueOnce(undefined);
    renderCheckout();
    await userEvent.click(
      await screen.findByRole("button", { name: "36,000원 결제하기" }),
    );
    const notice = await screen.findByRole("alert");
    expect(notice).toHaveTextContent("지금은 결제를 받을 수 없습니다.");
    expect(notice).toHaveTextContent("주문은 만들어졌습니다.");
    expect(
      within(notice).getByRole("link", { name: "주문 상세" }),
    ).toHaveAttribute("href", "/orders/ORD-20261123-001");
    // Paying again must not create a second order.
    await userEvent.click(screen.getByRole("button", { name: "다시 결제" }));
    expect(calls.filter((c) => c.key === "POST /orders/")).toHaveLength(1);
    expect(payOrder).toHaveBeenCalledTimes(2);
  });

  it("says the payment was cancelled when the window is closed", async () => {
    fakeApi({
      "GET /cart/": { data: cart },
      "GET /me/addresses/": { data: [address({ is_default: true })] },
      "POST /orders/": { status: 201, data: order },
    });
    payOrder.mockRejectedValue(
      Object.assign(new Error("closed"), { code: "USER_CANCEL" }),
    );
    renderCheckout();
    await userEvent.click(
      await screen.findByRole("button", { name: "36,000원 결제하기" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "결제를 취소했습니다.",
    );
  });

  it("sends an empty cart back to the list", async () => {
    fakeApi({
      "GET /cart/": {
        data: { ...cart, items: [], product_amount: 0, total_amount: 0 },
      },
      "GET /me/addresses/": { data: [] },
    });
    renderCheckout();
    expect(
      await screen.findByText("주문할 상품이 없습니다"),
    ).toBeInTheDocument();
  });
});
