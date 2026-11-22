import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import LoginPage from "./LoginPage";
import client from "../api/client";
import { getAccess, getRefresh } from "../auth/tokenStore";

const originalAdapter = client.defaults.adapter;

function answer(status, data) {
  const calls = [];
  client.defaults.adapter = async (config) => {
    calls.push({ url: config.url, data: JSON.parse(config.data) });
    const response = { data, status, statusText: "", headers: {}, config };
    if (status >= 400) {
      const error = new Error("failed");
      error.config = config;
      error.response = response;
      throw error;
    }
    return response;
  };
  return calls;
}

function Where() {
  return <p data-testid="where">{useLocation().pathname}</p>;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function fillAndSubmit() {
  await userEvent.type(screen.getByLabelText("이메일"), "member@example.com");
  await userEvent.type(screen.getByLabelText("비밀번호"), "password123");
  await userEvent.click(screen.getByRole("button", { name: "로그인" }));
}

describe("LoginPage", () => {
  afterEach(() => {
    client.defaults.adapter = originalAdapter;
  });

  it("stores the tokens and goes back to next", async () => {
    const calls = answer(200, {
      access: "a1",
      refresh: "r1",
      user: { role: "MEMBER" },
    });
    renderAt("/login?next=%2Forders");
    await fillAndSubmit();
    expect(calls[0]).toEqual({
      url: "/auth/token/",
      data: { email: "member@example.com", password: "password123" },
    });
    expect(getAccess()).toBe("a1");
    expect(getRefresh()).toBe("r1");
    expect(await screen.findByTestId("where")).toHaveTextContent("/orders");
  });

  it("ignores a next that leaves the site", async () => {
    answer(200, { access: "a1", refresh: "r1", user: { role: "MEMBER" } });
    renderAt("/login?next=https%3A%2F%2Fevil.example");
    await fillAndSubmit();
    expect(await screen.findByTestId("where")).toHaveTextContent(/^\/$/);
  });

  it("shows one line on 401 without saying which field was wrong (NFR-7)", async () => {
    answer(401, {
      code: "INVALID_CREDENTIALS",
      message: "이메일 또는 비밀번호가 올바르지 않습니다.",
    });
    renderAt("/login");
    await fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "이메일 또는 비밀번호가 올바르지 않습니다.",
    );
    expect(getAccess()).toBeNull();
  });

  it("says the server is unreachable on a network error (NFR-34)", async () => {
    client.defaults.adapter = async () => {
      throw new Error("Network Error");
    };
    renderAt("/login");
    await fillAndSubmit();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "서버에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.",
    );
  });

  it("links to signup", () => {
    renderAt("/login");
    expect(screen.getByRole("link", { name: "회원가입" })).toHaveAttribute(
      "href",
      "/signup",
    );
  });
});
