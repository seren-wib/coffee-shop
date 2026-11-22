import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { RequireAdmin, RequireAuth } from "./RequireAuth";
import { setTokens } from "./tokenStore";
import { makeJwt } from "../test/jwt";

function Where() {
  const { pathname, search } = useLocation();
  return <p data-testid="where">{pathname + search}</p>;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route element={<RequireAuth />}>
          <Route path="/orders" element={<p>my orders</p>} />
        </Route>
        <Route element={<RequireAdmin />}>
          <Route path="/admin/orders" element={<p>admin orders</p>} />
        </Route>
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RequireAuth", () => {
  it("sends a guest to login with the path to come back to", () => {
    renderAt("/orders?status=PAID");
    expect(screen.getByTestId("where")).toHaveTextContent(
      "/login?next=%2Forders%3Fstatus%3DPAID",
    );
  });

  it("lets a member through", () => {
    setTokens({ access: makeJwt({ role: "MEMBER" }), refresh: "r" });
    renderAt("/orders");
    expect(screen.getByText("my orders")).toBeInTheDocument();
  });
});

describe("RequireAdmin", () => {
  it("sends a guest to login", () => {
    renderAt("/admin/orders");
    expect(screen.getByTestId("where")).toHaveTextContent(
      "/login?next=%2Fadmin%2Forders",
    );
  });

  it("sends a member to the product list", () => {
    setTokens({ access: makeJwt({ role: "MEMBER" }), refresh: "r" });
    renderAt("/admin/orders");
    expect(screen.getByTestId("where")).toHaveTextContent(/^\/$/);
  });

  it("lets an admin through", () => {
    setTokens({ access: makeJwt({ role: "ADMIN" }), refresh: "r" });
    renderAt("/admin/orders");
    expect(screen.getByText("admin orders")).toBeInTheDocument();
  });
});
