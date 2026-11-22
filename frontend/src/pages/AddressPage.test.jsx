import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import AddressPage from "./AddressPage";
import { fakeApi } from "../test/fakeApi";

const address = (overrides) => ({
  address_id: 1,
  recipient_name: "김회원",
  recipient_phone: "010-1111-2222",
  zipcode: "28644",
  base_address: "충청북도 청주시 서원구 충대로 1",
  detail_address: "101호",
  is_default: true,
  ...overrides,
});

const two = [
  address(),
  address({ address_id: 2, is_default: false, detail_address: "202호" }),
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/me/addresses"]}>
      <AddressPage />
    </MemoryRouter>,
  );
}

const card = (text) => screen.getByRole("article", { name: new RegExp(text) });

describe("AddressPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("lists addresses with the default marked (FR-14)", async () => {
    fakeApi({ "GET /me/addresses/": { data: two } });
    renderPage();
    await screen.findByText(/101호/);
    expect(
      within(card("101호")).getByText("● 기본 배송지"),
    ).toBeInTheDocument();
    expect(within(card("202호")).getByText("○ 기본 아님")).toBeInTheDocument();
    expect(
      within(card("202호")).getByRole("button", { name: "기본으로 설정" }),
    ).toBeInTheDocument();
    expect(
      within(card("101호")).queryByRole("button", { name: "기본으로 설정" }),
    ).not.toBeInTheDocument();
  });

  it("adds an address, then reloads (FR-15)", async () => {
    let list = [];
    const calls = fakeApi({
      "GET /me/addresses/": () => ({ data: list }),
      "POST /me/addresses/": (config) => {
        list = [address({ ...JSON.parse(config.data), address_id: 5 })];
        return { status: 201, data: list[0] };
      },
    });
    renderPage();
    expect(
      await screen.findByText("저장된 배송지가 없습니다"),
    ).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("받는 사람"), "박받음");
    await userEvent.type(screen.getByLabelText("연락처"), "010-3333-4444");
    await userEvent.type(screen.getByLabelText("우편번호"), "12345");
    await userEvent.type(screen.getByLabelText("주소"), "서울특별시 중구 1");
    await userEvent.click(screen.getByLabelText("기본 배송지로 설정"));
    await userEvent.click(screen.getByRole("button", { name: "저장" }));
    expect(calls.find((c) => c.key === "POST /me/addresses/").data).toEqual({
      recipient_name: "박받음",
      recipient_phone: "010-3333-4444",
      zipcode: "12345",
      base_address: "서울특별시 중구 1",
      detail_address: "",
      is_default: true,
    });
    expect(
      await screen.findByText("배송지를 저장했습니다."),
    ).toBeInTheDocument();
    expect(screen.getByText(/서울특별시 중구 1/)).toBeInTheDocument();
  });

  it("edits an address without sending is_default (FR-16)", async () => {
    const calls = fakeApi({
      "GET /me/addresses/": { data: two },
      "PATCH /me/addresses/2/": { data: two[1] },
    });
    renderPage();
    await screen.findByText(/202호/);
    await userEvent.click(
      within(card("202호")).getByRole("button", { name: "수정" }),
    );
    expect(
      screen.getByRole("heading", { name: "배송지 수정" }),
    ).toBeInTheDocument();
    const detail = screen.getByLabelText("상세 주소");
    expect(detail).toHaveValue("202호");
    await userEvent.clear(detail);
    await userEvent.type(detail, "303호");
    await userEvent.click(screen.getByRole("button", { name: "저장" }));
    const patch = calls.find((c) => c.key === "PATCH /me/addresses/2/").data;
    expect(patch.detail_address).toBe("303호");
    expect(patch).not.toHaveProperty("is_default");
  });

  it("makes another address the default (FR-18)", async () => {
    const calls = fakeApi({
      "GET /me/addresses/": { data: two },
      "POST /me/addresses/2/default/": { data: two[1] },
    });
    renderPage();
    await screen.findByText(/202호/);
    await userEvent.click(
      within(card("202호")).getByRole("button", { name: "기본으로 설정" }),
    );
    expect(calls.map((c) => c.key)).toEqual([
      "GET /me/addresses/",
      "POST /me/addresses/2/default/",
      "GET /me/addresses/",
    ]);
  });

  it("shows the server message when the default cannot be deleted (UC-11)", async () => {
    fakeApi({
      "GET /me/addresses/": { data: two },
      "DELETE /me/addresses/1/": {
        status: 409,
        data: {
          code: "DEFAULT_ADDRESS_DELETE",
          message: "다른 배송지를 먼저 기본으로 정해 주세요.",
        },
      },
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    renderPage();
    await screen.findByText(/101호/);
    await userEvent.click(
      within(card("101호")).getByRole("button", { name: "삭제" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "다른 배송지를 먼저 기본으로 정해 주세요.",
    );
  });
});
