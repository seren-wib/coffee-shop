import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import Layout from "./Layout";
import { getAccess, setTokens } from "../auth/tokenStore";
import { makeJwt } from "../test/jwt";

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="*" element={<Where />} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

const header = () => screen.getByRole("banner");

describe("Layout", () => {
  it("always shows the fixed demo notice with no close button (NFR-36)", () => {
    renderAt("/");
    expect(
      screen.getByText(
        "학교 과제 데모입니다. 실제 판매와 결제는 이뤄지지 않습니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /닫기/ }),
    ).not.toBeInTheDocument();
  });

  it("shows login and signup links when logged out", () => {
    renderAt("/");
    expect(screen.getByRole("link", { name: "로그인" })).toHaveAttribute(
      "href",
      "/login",
    );
    expect(screen.getByRole("link", { name: "회원가입" })).toHaveAttribute(
      "href",
      "/signup",
    );
    expect(
      screen.queryByRole("button", { name: "로그아웃" }),
    ).not.toBeInTheDocument();
  });

  it("hides the admin menu from members", () => {
    setTokens({
      access: makeJwt({ user_id: 2, role: "MEMBER" }),
      refresh: "r",
    });
    renderAt("/");
    expect(
      screen.queryByRole("link", { name: "관리자" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "로그아웃" }),
    ).toBeInTheDocument();
  });

  it("shows the admin menu to admins, pointing at order management (FR-54)", () => {
    setTokens({ access: makeJwt({ user_id: 1, role: "ADMIN" }), refresh: "r" });
    renderAt("/");
    expect(screen.getByRole("link", { name: "관리자" })).toHaveAttribute(
      "href",
      "/admin/orders",
    );
  });

  it("marks the current menu", () => {
    renderAt("/products/3");
    expect(screen.getByRole("link", { name: "원두 목록" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "장바구니" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("logs out without a server call and goes to the product list", async () => {
    setTokens({
      access: makeJwt({ user_id: 2, role: "MEMBER" }),
      refresh: "r",
    });
    renderAt("/orders");
    await userEvent.click(screen.getByRole("button", { name: "로그아웃" }));
    expect(getAccess()).toBeNull();
    expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/);
    expect(screen.getByRole("link", { name: "로그인" })).toBeInTheDocument();
  });

  it("puts the build version and the privacy link in the footer (NFR-24, FR-59)", () => {
    renderAt("/");
    const footer = screen.getByRole("contentinfo");
    expect(footer).toHaveTextContent("버전");
    expect(
      screen.getByRole("link", { name: "개인정보 처리방침" }),
    ).toHaveAttribute("href", "/privacy");
    expect(header()).toBeInTheDocument();
  });
});
