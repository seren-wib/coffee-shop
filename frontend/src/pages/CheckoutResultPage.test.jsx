import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CheckoutResultPage from "./CheckoutResultPage";
import { payOrder } from "../lib/pay";
import { fakeApi } from "../test/fakeApi";

vi.mock("../lib/pay", async (importOriginal) => ({
  ...(await importOriginal()),
  payOrder: vi.fn(),
}));

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <CheckoutResultPage />
    </MemoryRouter>,
  );
}

const SUCCESS_QUERY =
  "/checkout/result?paymentKey=pk_1&orderId=ORD-20261123-001-P1&amount=36000";

describe("CheckoutResultPage", () => {
  beforeEach(() => {
    payOrder.mockReset();
  });

  it("confirms the payment once and shows the order (FR-26)", async () => {
    const calls = fakeApi({
      "POST /payments/confirm/": {
        data: {
          order_id: "ORD-20261123-001",
          status: "PAID",
          final_payment_amt: 36000,
        },
      },
    });
    renderAt(SUCCESS_QUERY);
    expect(
      await screen.findByRole("heading", { name: "결제가 완료되었습니다" }),
    ).toBeInTheDocument();
    expect(screen.getByText("ORD-20261123-001")).toBeInTheDocument();
    expect(screen.getByText("36,000원")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "주문 상세 보기" }),
    ).toHaveAttribute("href", "/orders/ORD-20261123-001");
    expect(calls).toHaveLength(1);
    expect(calls[0].data).toEqual({
      paymentKey: "pk_1",
      orderId: "ORD-20261123-001-P1",
      amount: 36000,
    });
  });

  it("shows the reason and offers paying again on a mismatch (FR-27)", async () => {
    fakeApi({
      "POST /payments/confirm/": {
        status: 409,
        data: {
          code: "PAYMENT_MISMATCH",
          message: "결제 금액이 주문 금액과 다릅니다.",
        },
      },
    });
    payOrder.mockResolvedValue(undefined);
    renderAt(SUCCESS_QUERY);
    expect(
      await screen.findByText("결제 금액이 주문 금액과 다릅니다."),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "다시 결제" }));
    expect(payOrder).toHaveBeenCalledWith("ORD-20261123-001");
  });

  it("offers checking again when the PG is slow (SDD 4.6.3 step 6)", async () => {
    let first = true;
    fakeApi({
      "POST /payments/confirm/": () => {
        if (first) {
          first = false;
          return {
            status: 502,
            data: {
              code: "PG_ERROR",
              message: "결제 확인이 늦어지고 있습니다.",
            },
          };
        }
        return {
          data: {
            order_id: "ORD-20261123-001",
            status: "PAID",
            final_payment_amt: 36000,
          },
        };
      },
    });
    renderAt(SUCCESS_QUERY);
    await userEvent.click(
      await screen.findByRole("button", { name: "다시 확인" }),
    );
    expect(
      await screen.findByRole("heading", { name: "결제가 완료되었습니다" }),
    ).toBeInTheDocument();
  });

  it("records a window failure and shows it (FR-28)", async () => {
    const calls = fakeApi({ "POST /payments/fail/": { data: {} } });
    renderAt(
      "/checkout/result?fail=1&code=PAY_PROCESS_CANCELED&message=%EC%82%AC%EC%9A%A9%EC%9E%90%EA%B0%80%20%EC%B7%A8%EC%86%8C&orderId=ORD-20261123-001-P2",
    );
    expect(
      await screen.findByRole("heading", { name: "결제하지 못했습니다" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/사용자가 취소/)).toBeInTheDocument();
    expect(calls[0]).toMatchObject({
      key: "POST /payments/fail/",
      data: {
        orderId: "ORD-20261123-001-P2",
        code: "PAY_PROCESS_CANCELED",
        message: "사용자가 취소",
      },
    });
    expect(
      screen.getByRole("link", { name: "주문 상세 보기" }),
    ).toHaveAttribute("href", "/orders/ORD-20261123-001");
  });
});
