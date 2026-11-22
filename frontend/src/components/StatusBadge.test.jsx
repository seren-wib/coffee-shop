import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import StatusBadge from "./StatusBadge";

describe("StatusBadge", () => {
  it("shows the Korean name for order and sales codes (NFR-30)", () => {
    render(
      <>
        <StatusBadge status="CANCEL_REQUESTED" />
        <StatusBadge type="sales" status="SOLD_OUT" />
      </>,
    );
    expect(screen.getByText("취소 요청")).toBeInTheDocument();
    expect(screen.getByText("품절")).toBeInTheDocument();
  });

  it("tells order and payment cancellation apart", () => {
    render(
      <>
        <StatusBadge status="CANCELLED" />
        <StatusBadge type="payment" status="CANCELLED" />
      </>,
    );
    expect(screen.getByText("취소")).toBeInTheDocument();
    expect(screen.getByText("결제 취소")).toBeInTheDocument();
  });

  it("falls back to the raw code for an unknown status", () => {
    render(<StatusBadge status="SOMETHING_NEW" />);
    expect(screen.getByText("SOMETHING_NEW")).toBeInTheDocument();
  });
});
