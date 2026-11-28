import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteCartItem, getCart, updateCartItem } from "../api/cart";
import Button from "../components/Button";
import Notice from "../components/Notice";
import ProductImage from "../components/ProductImage";
import QuantityStepper from "../components/QuantityStepper";
import { errorMessage, isOffline } from "../lib/errors";
import { formatWon } from "../lib/format";
import { GRIND_TYPE, WEIGHT_SIZE, label } from "../lib/labels";

// SCR-05 (FR-20 ~ FR-22). Amounts and can_order come from the server as is (SDD 7.0.3).
export default function CartPage() {
  const navigate = useNavigate();
  const [cart, setCart] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(
    () =>
      getCart().then(
        (data) => setCart(data),
        (err) => setError(err),
      ),
    [],
  );

  useEffect(() => {
    let active = true;
    getCart().then(
      (data) => active && setCart(data),
      (err) => active && setError(err),
    );
    return () => {
      active = false;
    };
  }, []);

  // A change is followed by a fresh GET; the screen never patches totals itself.
  async function change(action) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err);
    }
    await load();
    setBusy(false);
  }

  const empty = cart && cart.items.length === 0;

  return (
    <div className="flex flex-col gap-6 px-12 pt-10 pb-14">
      <h1 className="font-serif text-[32px] font-bold">장바구니</h1>

      {error && (
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      )}

      {!cart && !error && (
        <div aria-hidden="true" className="bg-cream-100 h-60 rounded-xl" />
      )}

      {empty && (
        <div className="flex flex-col items-start gap-3 py-10">
          <p className="text-brown-600 text-[15px]">장바구니가 비어 있습니다</p>
          <Link to="/">원두 보러 가기</Link>
        </div>
      )}

      {cart && !empty && (
        <div className="flex flex-wrap items-start gap-8">
          <section className="min-w-0 flex-[999_1_560px] overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-left">
              <thead>
                <tr className="border-brown-900 text-brown-600 border-b text-[13px]">
                  <th scope="col" colSpan={2} className="py-2.5 font-medium">
                    상품
                  </th>
                  <th scope="col" className="py-2.5 text-right font-medium">
                    단가
                  </th>
                  <th scope="col" className="py-2.5 pl-6 font-medium">
                    수량
                  </th>
                  <th scope="col" className="py-2.5 text-right font-medium">
                    소계
                  </th>
                  <th scope="col" className="py-2.5">
                    <span className="sr-only">삭제</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {cart.items.map((item) => (
                  <CartRow
                    key={item.cart_item_id}
                    item={item}
                    busy={busy}
                    onQuantity={(n) =>
                      change(() => updateCartItem(item.cart_item_id, n))
                    }
                    onDelete={() =>
                      change(() => deleteCartItem(item.cart_item_id))
                    }
                  />
                ))}
              </tbody>
            </table>
          </section>

          <aside
            aria-label="결제 예정 금액"
            className="border-cream-300 flex min-w-[280px] flex-[1_1_320px] flex-col gap-3.5 rounded-xl border p-6"
          >
            <h2 className="text-lg font-bold">결제 예정 금액</h2>
            <div className="flex justify-between text-sm">
              <span className="text-brown-600">상품 금액</span>
              <span>{formatWon(cart.product_amount)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-brown-600">예상 배송비</span>
              <span>{formatWon(cart.shipping_fee)}</span>
            </div>
            <div className="bg-cream-300 h-px" />
            <div className="flex items-baseline justify-between">
              <span className="text-sm font-medium">예상 결제금액</span>
              <span className="text-[22px] font-bold">
                {formatWon(cart.total_amount)}
              </span>
            </div>
            <Button
              disabled={!cart.can_order || busy}
              onClick={() => navigate("/checkout")}
            >
              주문하기
            </Button>
            {!cart.can_order && (
              <Notice className="text-[13px]">
                이 상품을 빼거나 수량을 줄여 주세요.
              </Notice>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function CartRow({ item, busy, onQuantity, onDelete }) {
  const muted = item.is_available ? "" : "text-brown-600";
  return (
    <tr className="border-cream-300 border-b align-middle">
      <td className="w-[112px] py-4 pr-4">
        <ProductImage
          src={item.image_url}
          alt=""
          className={`aspect-square w-24 rounded-lg ${item.is_available ? "" : "opacity-60"}`}
        />
      </td>
      <td className="py-4 pr-4">
        <div className="flex flex-col items-start gap-1">
          <Link
            to={`/products/${item.product_id}`}
            className={`font-serif text-base font-bold no-underline ${
              item.is_available
                ? "text-brown-900 hover:text-caramel-700"
                : "text-brown-600"
            }`}
          >
            {item.product_name}
          </Link>
          <span className="text-brown-600 text-[13px]">
            {label(WEIGHT_SIZE, item.weight_size)} ·{" "}
            {label(GRIND_TYPE, item.grind_type)}
          </span>
          {!item.is_available && (
            <span className="bg-espresso-950 text-latte-100 mt-0.5 inline-flex items-center gap-1.5 rounded-sm px-2 py-[3px] text-xs font-medium">
              <span
                aria-hidden="true"
                className="bg-dot-red size-1.5 rounded-[1px]"
              />
              주문할 수 없는 상품 (품절·판매 중지·재고 부족)
            </span>
          )}
        </div>
      </td>
      <td className={`py-4 text-right text-sm whitespace-nowrap ${muted}`}>
        {formatWon(item.price)}
      </td>
      <td className="py-4 pl-6">
        <QuantityStepper
          value={item.quantity}
          max={Math.max(item.stock_quantity, 1)}
          disabled={busy}
          onChange={onQuantity}
        />
      </td>
      <td
        className={`py-4 text-right text-[15px] font-bold whitespace-nowrap ${muted}`}
      >
        {formatWon(item.subtotal)}
      </td>
      <td className="py-4 pl-4 text-right">
        <button
          type="button"
          disabled={busy}
          onClick={onDelete}
          className={`cursor-pointer text-[13px] underline underline-offset-4 disabled:cursor-not-allowed ${
            item.is_available
              ? "text-brown-600"
              : "text-caramel-700 font-medium"
          }`}
        >
          삭제
        </button>
      </td>
    </tr>
  );
}
