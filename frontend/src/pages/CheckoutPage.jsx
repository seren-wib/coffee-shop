import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listAddresses } from "../api/addresses";
import { getCart } from "../api/cart";
import { createOrder } from "../api/orders";
import AddressFields, { EMPTY_ADDRESS } from "../components/AddressFields";
import Button from "../components/Button";
import Notice from "../components/Notice";
import { errorMessage, fieldErrors, isOffline } from "../lib/errors";
import { formatWon } from "../lib/format";
import { GRIND_TYPE, WEIGHT_SIZE, label } from "../lib/labels";
import { payErrorMessage, payOrder } from "../lib/pay";

const NEW_ADDRESS = "new";

// SCR-06 (FR-23 ~ FR-25). One press creates the order, then opens the payment window.
export default function CheckoutPage() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [choice, setChoice] = useState(null);
  const [newAddress, setNewAddress] = useState(EMPTY_ADDRESS);
  const [pending, setPending] = useState(false);
  const [orderError, setOrderError] = useState(null);
  const [blockedIds, setBlockedIds] = useState([]);
  const [order, setOrder] = useState(null);
  const [payError, setPayError] = useState(null);

  useEffect(() => {
    let active = true;
    Promise.all([getCart(), listAddresses()]).then(
      ([cart, addresses]) => {
        if (!active) return;
        setData({ cart, addresses });
        const preferred = addresses.find((a) => a.is_default) ?? addresses[0];
        setChoice(preferred ? preferred.address_id : NEW_ADDRESS);
      },
      (err) => active && setLoadError(err),
    );
    return () => {
      active = false;
    };
  }, []);

  async function pay(orderId) {
    setPayError(null);
    try {
      await payOrder(orderId);
    } catch (err) {
      setPayError(err);
    }
  }

  async function handlePay() {
    setPending(true);
    setOrderError(null);
    setBlockedIds([]);
    if (order) {
      // The order already exists: pay again, never create a second one (FR-29).
      await pay(order.order_id);
      setPending(false);
      return;
    }
    let created;
    try {
      created = await createOrder(
        choice === NEW_ADDRESS
          ? { address: newAddress }
          : { address_id: choice },
      );
    } catch (err) {
      setOrderError(err);
      setBlockedIds(err.response?.data?.details?.cart_item_ids ?? []);
      setPending(false);
      return;
    }
    setOrder(created);
    await pay(created.order_id);
    setPending(false);
  }

  if (loadError) {
    return (
      <Page>
        <Notice kind={isOffline(loadError) ? "offline" : "error"}>
          {errorMessage(loadError)}
        </Notice>
      </Page>
    );
  }
  if (!data) {
    return (
      <Page>
        <div aria-hidden="true" className="bg-cream-100 h-72 rounded-xl" />
      </Page>
    );
  }

  const { cart, addresses } = data;
  if (cart.items.length === 0) {
    return (
      <Page>
        <p className="text-brown-600 text-[15px]">주문할 상품이 없습니다</p>
        <Link to="/">원두 보러 가기</Link>
      </Page>
    );
  }

  const errors = fieldErrors(orderError);
  const addressErrors =
    typeof errors.address === "object" && !Array.isArray(errors.address)
      ? errors.address
      : errors;

  return (
    <Page>
      {orderError && (
        <Notice kind={isOffline(orderError) ? "offline" : "error"}>
          {errorMessage(orderError)}
        </Notice>
      )}
      {!cart.can_order && (
        <Notice>
          주문할 수 없는 상품이 있습니다. <Link to="/cart">장바구니</Link>에서
          빼거나 수량을 줄여 주세요.
        </Notice>
      )}

      <div className="flex flex-wrap items-start gap-8">
        <div className="flex min-w-0 flex-[999_1_560px] flex-col gap-8">
          <section className="flex flex-col gap-3">
            <SectionTitle>주문 상품 {cart.items.length}건</SectionTitle>
            <ul className="flex flex-col">
              {cart.items.map((item) => (
                <li
                  key={item.cart_item_id}
                  className="border-cream-300 flex items-baseline justify-between gap-4 border-b py-2.5 text-sm"
                >
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{item.product_name}</span>
                    <span className="text-brown-600">
                      · {label(WEIGHT_SIZE, item.weight_size)} ·{" "}
                      {label(GRIND_TYPE, item.grind_type)} · {item.quantity}개
                    </span>
                    {blockedIds.includes(item.cart_item_id) && (
                      <span className="bg-espresso-950 text-latte-100 inline-flex items-center gap-1.5 rounded-sm px-2 py-[3px] text-xs font-medium">
                        <span
                          aria-hidden="true"
                          className="bg-dot-red size-1.5 rounded-[1px]"
                        />
                        주문할 수 없는 상품
                      </span>
                    )}
                  </span>
                  <span className="whitespace-nowrap">
                    {formatWon(item.subtotal)}
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section className="flex flex-col gap-4">
            <SectionTitle>배송지</SectionTitle>
            <fieldset
              className="flex flex-col gap-2.5"
              disabled={Boolean(order)}
            >
              <legend className="sr-only">배송지 선택</legend>
              {addresses.map((a) => (
                <AddressChoice
                  key={a.address_id}
                  checked={choice === a.address_id}
                  onChange={() => setChoice(a.address_id)}
                >
                  {a.is_default && (
                    <span className="font-bold">● 기본 배송지</span>
                  )}
                  <span>
                    {a.recipient_name} · {a.recipient_phone}
                  </span>
                  <span className="text-brown-600">
                    ({a.zipcode}) {a.base_address} {a.detail_address}
                  </span>
                </AddressChoice>
              ))}
              <AddressChoice
                dashed
                checked={choice === NEW_ADDRESS}
                onChange={() => setChoice(NEW_ADDRESS)}
              >
                <span>새 배송지 입력</span>
              </AddressChoice>
            </fieldset>
            {choice === NEW_ADDRESS && (
              <AddressFields
                value={newAddress}
                onChange={setNewAddress}
                errors={addressErrors}
              />
            )}
          </section>

          <section className="flex flex-col gap-3">
            <SectionTitle>결제 수단</SectionTitle>
            <p className="text-brown-600 text-sm">
              결제하기를 누르면 토스페이먼츠 결제창이 열립니다. 카드, 간편결제,
              계좌이체는 결제창에서 고릅니다.
            </p>
          </section>
        </div>

        <aside
          aria-label="결제 금액"
          className="border-cream-300 flex min-w-[280px] flex-[1_1_320px] flex-col gap-3.5 rounded-xl border p-6"
        >
          <h2 className="text-lg font-bold">결제 금액</h2>
          <div className="flex justify-between text-sm">
            <span className="text-brown-600">상품 금액</span>
            <span>{formatWon(cart.product_amount)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-brown-600">배송비</span>
            <span>{formatWon(cart.shipping_fee)}</span>
          </div>
          <div className="bg-cream-300 h-px" />
          <div className="flex items-baseline justify-between">
            <span className="text-sm font-medium">최종 결제금액</span>
            <span className="text-[22px] font-bold">
              {formatWon(cart.total_amount)}
            </span>
          </div>
          <Button onClick={handlePay} disabled={pending || !cart.can_order}>
            {order ? "다시 결제" : `${formatWon(cart.total_amount)} 결제하기`}
          </Button>
          {payError && order && (
            <Notice
              kind={payError.code === "USER_CANCEL" ? "offline" : "error"}
              className="text-[13px]"
            >
              {payErrorMessage(payError)} 주문은 만들어졌습니다.{" "}
              <Link to={`/orders/${order.order_id}`}>주문 상세</Link>에서 다시
              결제할 수 있습니다.
            </Notice>
          )}
        </aside>
      </div>
    </Page>
  );
}

function Page({ children }) {
  return (
    <div className="flex flex-col gap-6 px-12 pt-10 pb-14">
      <h1 className="font-serif text-[32px] font-bold">주문/결제</h1>
      {children}
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <h2 className="border-brown-900 border-b pb-2.5 text-lg font-bold">
      {children}
    </h2>
  );
}

function AddressChoice({ checked, onChange, dashed = false, children }) {
  const border = checked
    ? "border-2 border-espresso-950"
    : `border ${dashed ? "border-dashed" : ""} border-cream-300`;
  return (
    <label
      className={`flex cursor-pointer gap-3 rounded-lg p-4 text-sm ${border}`}
    >
      <input
        type="radio"
        name="address"
        checked={checked}
        onChange={onChange}
        className="accent-espresso-950 mt-[3px]"
      />
      <span className="flex flex-col gap-1">{children}</span>
    </label>
  );
}
