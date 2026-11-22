import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { addCartItem } from "../api/cart";
import { getProduct } from "../api/products";
import { loginPath } from "../auth/next";
import { isLoggedIn } from "../auth/tokenStore";
import Button from "../components/Button";
import Notice from "../components/Notice";
import ProductImage from "../components/ProductImage";
import QuantityStepper from "../components/QuantityStepper";
import SelectField from "../components/SelectField";
import { errorMessage, isOffline } from "../lib/errors";
import { formatWon } from "../lib/format";
import { GRIND_TYPE, ROAST_LEVEL, WEIGHT_SIZE, label } from "../lib/labels";

const WEIGHT_ORDER = ["200G", "500G", "1KG"];

function firstPick(options) {
  return (options.find((o) => o.is_available) ?? options[0])?.option_id ?? null;
}

// SCR-02 (FR-6, FR-19). Weight buttons, then the grind within that weight.
export default function ProductDetailPage() {
  const { id } = useParams();
  // The answer is kept with the id it belongs to, so another id shows the placeholder.
  const [loaded, setLoaded] = useState({
    id: null,
    product: null,
    error: null,
  });

  useEffect(() => {
    let active = true;
    getProduct(id)
      .then((product) => {
        if (active) setLoaded({ id, product, error: null });
      })
      .catch((error) => {
        if (active) setLoaded({ id, product: null, error });
      });
    return () => {
      active = false;
    };
  }, [id]);

  const fresh = loaded.id === id;
  const product = fresh ? loaded.product : null;
  const loadError = fresh ? loaded.error : null;

  if (loadError?.response?.status === 404) {
    return (
      <div className="flex flex-col gap-3 px-12 pt-10 pb-14">
        <h1 className="font-serif text-[32px] font-bold">
          판매하지 않는 원두입니다
        </h1>
        <p className="text-[15px]">
          <Link to="/">원두 목록으로 가기</Link>
        </p>
      </div>
    );
  }
  if (loadError) {
    return (
      <div className="px-12 pt-10 pb-14">
        <Notice kind={isOffline(loadError) ? "offline" : "error"}>
          {errorMessage(loadError)}
        </Notice>
      </div>
    );
  }
  if (!product) return <DetailPlaceholder />;
  return <ProductView key={product.product_id} product={product} />;
}

// Remounted per product (key), so the option choice starts from the first sellable one.
function ProductView({ product }) {
  const navigate = useNavigate();
  const id = product.product_id;
  const [optionId, setOptionId] = useState(() => firstPick(product.options));
  const [quantity, setQuantity] = useState(1);
  const [pending, setPending] = useState(false);
  const [added, setAdded] = useState(false);
  const [addError, setAddError] = useState(null);

  const selected =
    product.options.find((o) => o.option_id === optionId) ?? null;
  const weights = WEIGHT_ORDER.filter((w) =>
    product.options.some((o) => o.weight_size === w),
  );
  const grinds = product.options.filter(
    (o) => o.weight_size === selected?.weight_size,
  );

  function chooseWeight(weight) {
    const inWeight = product.options.filter((o) => o.weight_size === weight);
    const sameGrind = inWeight.find(
      (o) => o.grind_type === selected?.grind_type && o.is_available,
    );
    setOptionId(sameGrind?.option_id ?? firstPick(inWeight));
    setQuantity(1);
    setAdded(false);
  }

  function chooseOption(nextId) {
    setOptionId(nextId);
    setQuantity(1);
    setAdded(false);
  }

  async function addToCart() {
    if (!isLoggedIn()) {
      navigate(loginPath(`/products/${id}`));
      return;
    }
    setPending(true);
    setAdded(false);
    setAddError(null);
    try {
      await addCartItem({ optionId: selected.option_id, quantity });
      setAdded(true);
    } catch (err) {
      setAddError(err);
    } finally {
      setPending(false);
    }
  }

  const canAdd = selected?.is_available ?? false;

  return (
    <div className="flex flex-col gap-6 px-12 pt-8 pb-14">
      <nav aria-label="경로" className="text-brown-600 flex gap-2 text-[13px]">
        <Link to="/" className="text-brown-600 hover:text-brown-900">
          원두 목록
        </Link>
        <span aria-hidden="true">/</span>
        <span>{product.name}</span>
      </nav>

      <div className="flex flex-wrap items-start gap-12">
        <ProductImage
          src={product.image_url}
          alt={product.name}
          lazy={false}
          className="aspect-[4/3] min-w-0 flex-[1_1_480px] rounded-xl"
        />

        <div className="flex min-w-0 flex-[1_1_480px] flex-col gap-6">
          <div className="flex flex-col gap-2">
            <span className="text-brown-600 text-[13px]">
              {product.origin} · {label(ROAST_LEVEL, product.roast_level)}{" "}
              로스팅
            </span>
            <h1 className="font-serif text-[32px] font-bold">{product.name}</h1>
            {product.tasting_notes && (
              <span className="text-brown-600 text-sm">
                맛 노트: {product.tasting_notes}
              </span>
            )}
          </div>
          {product.description && (
            <p className="text-[15px] leading-[1.7] whitespace-pre-line">
              {product.description}
            </p>
          )}

          <div className="bg-cream-300 h-px" />

          <fieldset className="flex flex-col gap-2.5">
            <legend className="mb-2.5 text-[13px] font-medium">용량</legend>
            <div className="flex flex-wrap gap-2">
              {weights.map((weight) => (
                <WeightButton
                  key={weight}
                  weight={weight}
                  options={product.options.filter(
                    (o) => o.weight_size === weight,
                  )}
                  pressed={selected?.weight_size === weight}
                  onClick={() => chooseWeight(weight)}
                />
              ))}
            </div>
          </fieldset>

          <SelectField
            label="분쇄도"
            className="max-w-80"
            value={optionId ?? ""}
            onChange={(e) => chooseOption(Number(e.target.value))}
            options={grinds.map((o) => ({
              value: o.option_id,
              label: o.is_available
                ? label(GRIND_TYPE, o.grind_type)
                : `${label(GRIND_TYPE, o.grind_type)} (품절)`,
              disabled: !o.is_available,
            }))}
          />

          <div className="flex flex-wrap items-end gap-6">
            <div className="flex flex-col gap-1.5">
              <span className="text-[13px] font-medium">수량</span>
              <QuantityStepper
                value={quantity}
                max={selected?.stock_quantity ?? 1}
                disabled={!canAdd}
                onChange={(n) => {
                  setQuantity(n);
                  setAdded(false);
                }}
                testId="quantity"
              />
            </div>
            <span className="text-brown-600 pb-[7px] text-[13px]">
              {canAdd ? `재고 ${selected.stock_quantity}개` : "품절"}
            </span>
          </div>

          <div className="border-cream-300 flex items-baseline justify-between border-t py-4">
            <span className="text-brown-600 text-sm">합계</span>
            <span data-testid="total" className="text-2xl font-bold">
              {formatWon((selected?.price ?? 0) * quantity)}
            </span>
          </div>

          <div className="flex gap-3">
            <Button onClick={addToCart} disabled={!canAdd || pending}>
              {canAdd ? "장바구니 담기" : "품절"}
            </Button>
          </div>

          {added && (
            <Notice kind="success">
              장바구니에 담았습니다 · <Link to="/cart">장바구니로 가기</Link>
            </Notice>
          )}
          {addError && (
            <Notice kind={isOffline(addError) ? "offline" : "error"}>
              {errorMessage(addError)}
            </Notice>
          )}
        </div>
      </div>
    </div>
  );
}

function WeightButton({ weight, options, pressed, onClick }) {
  const available = options.some((o) => o.is_available);
  const extra = Math.min(...options.map((o) => o.extra_price));
  const name = label(WEIGHT_SIZE, weight);
  if (!available) {
    return (
      <button
        type="button"
        aria-pressed={false}
        disabled
        className="border-cream-300 text-brown-500 h-8 cursor-not-allowed rounded-md border border-dashed bg-white px-3.5 text-sm"
      >
        {name} 품절
      </button>
    );
  }
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={`h-8 cursor-pointer rounded-md border px-3.5 text-sm ${
        pressed
          ? "border-espresso-950 bg-espresso-950 text-latte-100 font-medium"
          : "border-cream-300 text-brown-900 hover:border-brown-600 bg-white"
      }`}
    >
      {extra > 0 ? `${name} +${formatWon(extra)}` : name}
    </button>
  );
}

function DetailPlaceholder() {
  return (
    <div
      aria-hidden="true"
      className="flex flex-wrap items-start gap-12 px-12 pt-16 pb-14"
    >
      <div className="bg-cream-100 aspect-[4/3] min-w-0 flex-[1_1_480px] rounded-xl" />
      <div className="flex min-w-0 flex-[1_1_480px] flex-col gap-4">
        <div className="bg-cream-100 h-4 w-40 rounded-sm" />
        <div className="bg-cream-100 h-8 w-64 rounded-sm" />
        <div className="bg-cream-100 h-4 w-full rounded-sm" />
        <div className="bg-cream-100 h-4 w-3/4 rounded-sm" />
      </div>
    </div>
  );
}
