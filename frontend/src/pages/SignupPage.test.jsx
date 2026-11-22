import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import LoginPage from "./LoginPage";
import SignupPage from "./SignupPage";
import { fakeApi } from "../test/fakeApi";

function renderSignup() {
  return render(
    <MemoryRouter initialEntries={["/signup"]}>
      <Routes>
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function fill({
  password = "password123",
  confirm = password,
  agree = true,
} = {}) {
  await userEvent.type(screen.getByLabelText("이메일"), "new@example.com");
  await userEvent.type(screen.getByLabelText("비밀번호 (8자 이상)"), password);
  await userEvent.type(screen.getByLabelText("비밀번호 확인"), confirm);
  await userEvent.type(screen.getByLabelText("이름"), "새회원");
  await userEvent.type(screen.getByLabelText("연락처"), "010-1234-5678");
  if (agree) {
    await userEvent.click(
      screen.getByLabelText("개인정보 수집·이용에 동의합니다(필수)"),
    );
  }
  await userEvent.click(screen.getByRole("button", { name: "회원가입" }));
}

describe("SignupPage", () => {
  it("shows the privacy notice with a link to the policy (FR-58)", () => {
    renderSignup();
    expect(
      screen.getByRole("rowheader", { name: "보유 기간" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "개인정보 처리방침 전체 보기" }),
    ).toHaveAttribute("href", "/privacy");
  });

  it("registers with privacy_agreed and sends the member to login (FR-7, UC-2)", async () => {
    const calls = fakeApi({
      "POST /auth/register/": { status: 201, data: {} },
    });
    renderSignup();
    await fill();
    expect(calls[0].data).toEqual({
      email: "new@example.com",
      password: "password123",
      user_name: "새회원",
      phone_number: "010-1234-5678",
      privacy_agreed: true,
    });
    expect(
      await screen.findByText("가입이 완료되었습니다. 로그인해 주세요."),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "로그인" })).toBeInTheDocument();
  });

  it("sends nothing for a short password, a mismatch or no consent", async () => {
    const calls = fakeApi({});
    renderSignup();
    await fill({ password: "1234567" });
    expect(
      screen.getByText("비밀번호는 8자 이상이어야 합니다."),
    ).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText("비밀번호 (8자 이상)"));
    await userEvent.type(
      screen.getByLabelText("비밀번호 (8자 이상)"),
      "password123",
    );
    await userEvent.clear(screen.getByLabelText("비밀번호 확인"));
    await userEvent.type(screen.getByLabelText("비밀번호 확인"), "password999");
    await userEvent.click(screen.getByRole("button", { name: "회원가입" }));
    expect(screen.getByText("비밀번호가 서로 다릅니다.")).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("asks for consent before sending", async () => {
    const calls = fakeApi({});
    renderSignup();
    await fill({ agree: false });
    expect(
      screen.getByText("개인정보 수집·이용에 동의해야 가입할 수 있습니다."),
    ).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it("shows server field errors under the inputs (NFR-34)", async () => {
    fakeApi({
      "POST /auth/register/": {
        status: 400,
        data: {
          code: "VALIDATION_ERROR",
          message: "입력값을 확인해 주세요.",
          fields: { email: ["이미 가입된 이메일입니다"] },
        },
      },
    });
    renderSignup();
    await fill();
    expect(
      await screen.findByText("이미 가입된 이메일입니다"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("이메일")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });
});
