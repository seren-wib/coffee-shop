import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import AccountPage from "./AccountPage";
import { fakeApi } from "../test/fakeApi";

const me = {
  user_id: 2,
  email: "member@example.com",
  user_name: "회원",
  phone_number: "010-0000-0000",
  role: "MEMBER",
};

function renderAccount() {
  return render(
    <MemoryRouter initialEntries={["/me"]}>
      <AccountPage />
    </MemoryRouter>,
  );
}

describe("AccountPage", () => {
  it("shows my info with the email read-only and links to addresses (FR-11)", async () => {
    fakeApi({ "GET /me/": { data: me } });
    renderAccount();
    expect(await screen.findByLabelText("이메일")).toHaveValue(
      "member@example.com",
    );
    expect(screen.getByLabelText("이메일")).toHaveAttribute("readonly");
    expect(screen.getByRole("link", { name: "배송지 관리" })).toHaveAttribute(
      "href",
      "/me/addresses",
    );
  });

  it("saves name and phone (FR-12)", async () => {
    const calls = fakeApi({
      "GET /me/": { data: me },
      "PATCH /me/": { data: { ...me, user_name: "새이름" } },
    });
    renderAccount();
    const name = await screen.findByLabelText("이름");
    await userEvent.clear(name);
    await userEvent.type(name, "새이름");
    await userEvent.click(screen.getByRole("button", { name: "수정 저장" }));
    expect(calls.find((c) => c.key === "PATCH /me/").data).toEqual({
      user_name: "새이름",
      phone_number: "010-0000-0000",
    });
    expect(
      await screen.findByText("회원정보를 저장했습니다."),
    ).toBeInTheDocument();
  });

  it("changes the password, then clears the fields (FR-13)", async () => {
    const calls = fakeApi({
      "GET /me/": { data: me },
      "POST /me/password/": { status: 204, data: "" },
    });
    renderAccount();
    await userEvent.type(
      await screen.findByLabelText("현재 비밀번호"),
      "oldpass123",
    );
    await userEvent.type(
      screen.getByLabelText("새 비밀번호 (8자 이상)"),
      "newpass123",
    );
    await userEvent.type(
      screen.getByLabelText("새 비밀번호 확인"),
      "newpass123",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "비밀번호 변경" }),
    );
    expect(calls.find((c) => c.key === "POST /me/password/").data).toEqual({
      current_password: "oldpass123",
      new_password: "newpass123",
    });
    expect(
      await screen.findByText("비밀번호를 바꿨습니다."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("현재 비밀번호")).toHaveValue("");
  });

  it("checks the new password before sending", async () => {
    const calls = fakeApi({ "GET /me/": { data: me } });
    renderAccount();
    await userEvent.type(
      await screen.findByLabelText("현재 비밀번호"),
      "oldpass123",
    );
    await userEvent.type(
      screen.getByLabelText("새 비밀번호 (8자 이상)"),
      "newpass123",
    );
    await userEvent.type(
      screen.getByLabelText("새 비밀번호 확인"),
      "different1",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "비밀번호 변경" }),
    );
    expect(screen.getByText("비밀번호가 서로 다릅니다.")).toBeInTheDocument();
    expect(calls).toHaveLength(1);
  });

  it("shows a wrong current password under its field", async () => {
    fakeApi({
      "GET /me/": { data: me },
      "POST /me/password/": {
        status: 400,
        data: {
          code: "VALIDATION_ERROR",
          message: "입력값을 확인해 주세요.",
          fields: { current_password: ["현재 비밀번호가 올바르지 않습니다"] },
        },
      },
    });
    renderAccount();
    await userEvent.type(
      await screen.findByLabelText("현재 비밀번호"),
      "wrongpass",
    );
    await userEvent.type(
      screen.getByLabelText("새 비밀번호 (8자 이상)"),
      "newpass123",
    );
    await userEvent.type(
      screen.getByLabelText("새 비밀번호 확인"),
      "newpass123",
    );
    await userEvent.click(
      screen.getByRole("button", { name: "비밀번호 변경" }),
    );
    expect(
      await screen.findByText("현재 비밀번호가 올바르지 않습니다"),
    ).toBeInTheDocument();
  });
});
