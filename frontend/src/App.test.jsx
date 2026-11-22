import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App routes", () => {
  it("shows the not-found screen inside the layout for an unknown path", () => {
    render(
      <MemoryRouter initialEntries={["/no-such-page"]}>
        <App />
      </MemoryRouter>,
    );
    expect(
      screen.getByRole("heading", { name: "페이지를 찾을 수 없습니다" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "학교 과제 데모입니다. 실제 판매와 결제는 이뤄지지 않습니다.",
      ),
    ).toBeInTheDocument();
  });

  it("serves the login screen at /login", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "로그인" })).toBeInTheDocument();
  });
});
