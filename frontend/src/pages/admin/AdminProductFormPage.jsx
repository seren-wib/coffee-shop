import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  addOption,
  createProduct,
  getAdminProduct,
  resumeSales,
  stopSales,
  updateOption,
  updateProduct,
} from "../../api/admin";
import AdminTabs from "../../components/AdminTabs";
import Button from "../../components/Button";
import Notice from "../../components/Notice";
import SelectField from "../../components/SelectField";
import StatusBadge from "../../components/StatusBadge";
import TextField from "../../components/TextField";
import { errorMessage, fieldErrors, isOffline } from "../../lib/errors";
import { GRIND_TYPE, ROAST_LEVEL, WEIGHT_SIZE, label } from "../../lib/labels";
import { ORIGINS } from "../../lib/origins";

const ORIGIN_OPTIONS = ORIGINS.map((o) => ({ value: o, label: o }));
const ROAST_OPTIONS = Object.entries(ROAST_LEVEL).map(([value, name]) => ({
  value,
  label: name,
}));
const WEIGHT_OPTIONS = Object.entries(WEIGHT_SIZE).map(([value, name]) => ({
  value,
  label: name,
}));
const GRIND_OPTIONS = Object.entries(GRIND_TYPE).map(([value, name]) => ({
  value,
  label: name,
}));

const BLANK = {
  name: "",
  origin: ORIGINS[0],
  roast_level: "LIGHT",
  base_price: "",
  tasting_notes: "",
  description: "",
  image_url: "",
};

// SCR-12 (FR-37 ~ FR-41). New: product fields only; after saving, the edit screen adds options.
export default function AdminProductFormPage() {
  const { id } = useParams();
  const [loaded, setLoaded] = useState({
    id: null,
    product: null,
    error: null,
  });

  useEffect(() => {
    if (!id) return undefined;
    let active = true;
    getAdminProduct(id).then(
      (product) => active && setLoaded({ id, product, error: null }),
      (error) => active && setLoaded({ id, product: null, error }),
    );
    return () => {
      active = false;
    };
  }, [id]);

  if (!id) {
    return (
      <Page title="원두 등록">
        <ProductForm product={null} />
      </Page>
    );
  }

  const fresh = loaded.id === id;
  if (fresh && loaded.error) {
    return (
      <Page title="원두 수정">
        <Notice kind={isOffline(loaded.error) ? "offline" : "error"}>
          {errorMessage(loaded.error)}
        </Notice>
      </Page>
    );
  }
  if (!fresh || !loaded.product) {
    return (
      <Page title="원두 수정">
        <div aria-hidden="true" className="bg-cream-100 h-72 rounded-xl" />
      </Page>
    );
  }
  return (
    <ProductEditor
      key={id}
      product={loaded.product}
      onChange={(product) => setLoaded({ id, product, error: null })}
    />
  );
}

function Page({ title, aside, children }) {
  return (
    <div className="flex flex-col gap-6 px-12 pt-8 pb-14">
      <AdminTabs />
      <div className="flex flex-wrap items-center gap-4">
        <h1 className="font-serif text-[28px] font-bold">{title}</h1>
        {aside}
      </div>
      {children}
    </div>
  );
}

// Every admin product call answers with the whole product (SDD 4.7.12), so the screen shows that.
function ProductEditor({ product, onChange }) {
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const stopped = product.sales_status === "STOPPED";

  async function run(action) {
    setBusy(true);
    setError(null);
    try {
      onChange(await action());
      return true;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setBusy(false);
    }
  }

  return (
    <Page
      title={`원두 수정 · ${product.name}`}
      aside={
        <>
          <StatusBadge type="sales" status={product.sales_status} />
          <Button
            size="sm"
            variant={stopped ? "outline" : "danger"}
            disabled={busy}
            onClick={() =>
              run(() => (stopped ? resumeSales : stopSales)(product.product_id))
            }
          >
            {stopped ? "판매 재개" : "판매 중지"}
          </Button>
        </>
      }
    >
      {error && Object.keys(fieldErrors(error)).length === 0 && (
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      )}
      <ProductForm product={product} onSaved={onChange} />
      <section className="flex flex-col gap-3">
        <h2 className="border-brown-900 border-b pb-2.5 text-lg font-bold">
          옵션
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left text-sm">
            <thead>
              <tr className="text-brown-600 text-[13px]">
                <th scope="col" className="py-2 pr-4 font-medium">
                  용량
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  분쇄도
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  추가금액
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  재고수량
                </th>
                <th scope="col" className="py-2 pr-4 font-medium">
                  판매 가능
                </th>
                <th scope="col" className="py-2">
                  <span className="sr-only">동작</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {product.options.map((o) => (
                <OptionRow
                  key={o.option_id}
                  option={o}
                  busy={busy}
                  onSave={(body) =>
                    run(() =>
                      updateOption(product.product_id, o.option_id, body),
                    )
                  }
                />
              ))}
              <NewOptionRow
                busy={busy}
                onAdd={(body) => run(() => addOption(product.product_id, body))}
              />
            </tbody>
          </table>
        </div>
        <p className="text-brown-600 text-[13px]">
          품절은 고르지 않습니다. 모든 옵션의 재고가 0이면 서버가 품절로
          표시합니다.
        </p>
      </section>
    </Page>
  );
}

const cellInput =
  "h-7 w-28 rounded-md border border-cream-300 bg-white px-2.5 text-[13px] outline-none focus:border-brown-900";

function OptionRow({ option, busy, onSave }) {
  const [extra, setExtra] = useState(String(option.extra_price));
  const [stock, setStock] = useState(String(option.stock_quantity));
  return (
    <tr className="border-cream-300 border-t">
      <td className="py-2 pr-4">{label(WEIGHT_SIZE, option.weight_size)}</td>
      <td className="py-2 pr-4">{label(GRIND_TYPE, option.grind_type)}</td>
      <td className="py-2 pr-4">
        <input
          type="number"
          min={0}
          aria-label="추가금액"
          value={extra}
          onChange={(e) => setExtra(e.target.value)}
          className={cellInput}
        />
      </td>
      <td className="py-2 pr-4">
        <input
          type="number"
          min={0}
          aria-label="재고수량"
          value={stock}
          onChange={(e) => setStock(e.target.value)}
          className={cellInput}
        />
      </td>
      <td className="py-2 pr-4">{option.is_available ? "가능" : "불가"}</td>
      <td className="py-2 text-right">
        <Button
          size="sm"
          variant="secondary"
          disabled={busy}
          onClick={() =>
            onSave({
              extra_price: Number(extra),
              stock_quantity: Number(stock),
            })
          }
        >
          저장
        </Button>
      </td>
    </tr>
  );
}

function NewOptionRow({ busy, onAdd }) {
  const [weight, setWeight] = useState("200G");
  const [grind, setGrind] = useState("WHOLE_BEAN");
  const [extra, setExtra] = useState("");
  const [stock, setStock] = useState("");
  const select =
    "h-7 rounded-md border border-cream-300 bg-white px-2 text-[13px] outline-none focus:border-brown-900";
  return (
    <tr className="border-cream-300 bg-cream-100/40 border-t">
      <td className="py-2 pr-4">
        <select
          aria-label="새 옵션 용량"
          value={weight}
          onChange={(e) => setWeight(e.target.value)}
          className={select}
        >
          {WEIGHT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </td>
      <td className="py-2 pr-4">
        <select
          aria-label="새 옵션 분쇄도"
          value={grind}
          onChange={(e) => setGrind(e.target.value)}
          className={select}
        >
          {GRIND_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </td>
      <td className="py-2 pr-4">
        <input
          type="number"
          min={0}
          placeholder="0"
          aria-label="새 옵션 추가금액"
          value={extra}
          onChange={(e) => setExtra(e.target.value)}
          className={cellInput}
        />
      </td>
      <td className="py-2 pr-4">
        <input
          type="number"
          min={0}
          placeholder="0"
          aria-label="새 옵션 재고수량"
          value={stock}
          onChange={(e) => setStock(e.target.value)}
          className={cellInput}
        />
      </td>
      <td className="py-2 pr-4" />
      <td className="py-2 text-right">
        <Button
          size="sm"
          disabled={busy}
          onClick={async () => {
            const ok = await onAdd({
              weight_size: weight,
              grind_type: grind,
              extra_price: Number(extra || 0),
              stock_quantity: Number(stock || 0),
            });
            if (ok) {
              setExtra("");
              setStock("");
            }
          }}
        >
          옵션 추가
        </Button>
      </td>
    </tr>
  );
}

function ProductForm({ product, onSaved }) {
  const navigate = useNavigate();
  const [form, setForm] = useState(() =>
    product
      ? {
          name: product.name,
          origin: product.origin,
          roast_level: product.roast_level,
          base_price: String(product.base_price),
          tasting_notes: product.tasting_notes ?? "",
          description: product.description ?? "",
          image_url: product.image_url ?? "",
        }
      : BLANK,
  );
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  async function handleSubmit(event) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setSaved(false);
    const body = { ...form, base_price: Number(form.base_price) };
    try {
      if (product) {
        onSaved(await updateProduct(product.product_id, body));
        setSaved(true);
      } else {
        const created = await createProduct(body);
        navigate(`/admin/products/${created.product_id}`, { replace: true });
        return;
      }
    } catch (err) {
      setError(err);
    }
    setPending(false);
  }

  const errors = fieldErrors(error);
  return (
    <form
      onSubmit={handleSubmit}
      className="border-cream-300 grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4 rounded-xl border p-6"
    >
      {saved && (
        <Notice kind="success" className="col-span-full">
          원두 정보를 저장했습니다.
        </Notice>
      )}
      {error && Object.keys(errors).length === 0 && (
        <Notice
          kind={isOffline(error) ? "offline" : "error"}
          className="col-span-full"
        >
          {errorMessage(error)}
        </Notice>
      )}
      <TextField
        label="원두명"
        required
        value={form.name}
        onChange={set("name")}
        error={errors.name}
      />
      <SelectField
        label="원산지"
        options={ORIGIN_OPTIONS}
        value={form.origin}
        onChange={set("origin")}
      />
      <SelectField
        label="로스팅 정도"
        options={ROAST_OPTIONS}
        value={form.roast_level}
        onChange={set("roast_level")}
      />
      <TextField
        label="기본 가격 (원)"
        type="number"
        min={0}
        required
        value={form.base_price}
        onChange={set("base_price")}
        error={errors.base_price}
      />
      <TextField
        label="테이스팅 노트"
        value={form.tasting_notes}
        onChange={set("tasting_notes")}
        error={errors.tasting_notes}
      />
      <TextField
        label="이미지 URL"
        type="url"
        placeholder="https://"
        value={form.image_url}
        onChange={set("image_url")}
        error={errors.image_url}
      />
      <div className="col-span-full flex flex-col gap-1.5">
        <label
          htmlFor="product-description"
          className="text-[13px] font-medium"
        >
          설명
        </label>
        <textarea
          id="product-description"
          rows={3}
          value={form.description}
          onChange={set("description")}
          className="border-cream-300 focus:border-brown-900 rounded-md border bg-white p-3 text-sm outline-none"
        />
      </div>
      <div className="col-span-full flex gap-2">
        <Button type="submit" disabled={pending}>
          저장
        </Button>
        <Link
          to="/admin/products"
          className="text-brown-900 inline-flex h-8 items-center px-2 text-sm underline underline-offset-4"
        >
          취소
        </Link>
      </div>
    </form>
  );
}
