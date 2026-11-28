import { useCallback, useEffect, useState } from "react";
import {
  createAddress,
  deleteAddress,
  listAddresses,
  setDefaultAddress,
  updateAddress,
} from "../api/addresses";
import AddressFields from "../components/AddressFields";
import Button from "../components/Button";
import MyPageTabs from "../components/MyPageTabs";
import Notice from "../components/Notice";
import { EMPTY_ADDRESS } from "../lib/address";
import { errorMessage, fieldErrors, isOffline } from "../lib/errors";

// SCR-10 (FR-14 ~ FR-18, UC-11). Cards on the left, one add/edit form on the right.
export default function AddressPage() {
  const [addresses, setAddresses] = useState(null);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(null);

  const reload = useCallback(
    () => listAddresses().then(setAddresses, setError),
    [],
  );

  useEffect(() => {
    let active = true;
    listAddresses().then(
      (data) => active && setAddresses(data),
      (err) => active && setError(err),
    );
    return () => {
      active = false;
    };
  }, []);

  // A change is followed by a fresh GET (SDD 7.0.3).
  async function run(action, { savedNotice = false } = {}) {
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await action();
      await reload();
      if (savedNotice) setSaved(true);
      return true;
    } catch (err) {
      setError(err);
      return false;
    } finally {
      setBusy(false);
    }
  }

  const formError =
    error && Object.keys(fieldErrors(error)).length > 0 ? error : null;
  const topError = error && !formError ? error : null;

  return (
    <div className="flex flex-col gap-6 px-12 pt-10 pb-14">
      <h1 className="font-serif text-[32px] font-bold">마이페이지</h1>
      <MyPageTabs />
      {topError && (
        <Notice kind={isOffline(topError) ? "offline" : "error"}>
          {errorMessage(topError)}
        </Notice>
      )}
      {saved && <Notice kind="success">배송지를 저장했습니다.</Notice>}

      <div className="flex flex-wrap items-start gap-8">
        <div className="grid min-w-0 flex-[999_1_560px] grid-cols-[repeat(auto-fill,minmax(280px,1fr))] gap-4">
          {!addresses && (
            <div aria-hidden="true" className="bg-cream-100 h-40 rounded-xl" />
          )}
          {addresses?.length === 0 && (
            <p className="text-brown-600 text-[15px]">
              저장된 배송지가 없습니다
            </p>
          )}
          {addresses?.map((a) => (
            <AddressCard
              key={a.address_id}
              address={a}
              busy={busy}
              onDefault={() => run(() => setDefaultAddress(a.address_id))}
              onEdit={() => {
                setEditing(a);
                setError(null);
                setSaved(false);
              }}
              onDelete={() => {
                if (window.confirm("이 배송지를 삭제할까요?")) {
                  run(() => deleteAddress(a.address_id));
                }
              }}
            />
          ))}
        </div>

        <AddressForm
          key={editing?.address_id ?? "new"}
          editing={editing}
          busy={busy}
          error={formError}
          onCancel={() => setEditing(null)}
          onSubmit={async (value, isDefault) => {
            const ok = await run(
              () =>
                editing
                  ? updateAddress(editing.address_id, value)
                  : createAddress({ ...value, is_default: isDefault }),
              { savedNotice: true },
            );
            if (ok) setEditing(null);
            return ok;
          }}
        />
      </div>
    </div>
  );
}

function AddressCard({ address: a, busy, onDefault, onEdit, onDelete }) {
  const titleId = `address-${a.address_id}`;
  return (
    <article
      aria-labelledby={titleId}
      className={`flex flex-col gap-2 rounded-xl p-5 text-sm ${
        a.is_default
          ? "border-espresso-950 border-2"
          : "border-cream-300 border"
      }`}
    >
      <span className={a.is_default ? "font-bold" : "text-brown-600"}>
        {a.is_default ? "● 기본 배송지" : "○ 기본 아님"}
      </span>
      <span id={titleId}>
        {a.recipient_name} · {a.recipient_phone} · ({a.zipcode}){" "}
        {a.base_address}
        {a.detail_address ? `, ${a.detail_address}` : ""}
      </span>
      <div className="mt-2 flex flex-wrap gap-2">
        {!a.is_default && (
          <Button
            size="sm"
            variant="outline"
            onClick={onDefault}
            disabled={busy}
          >
            기본으로 설정
          </Button>
        )}
        <Button size="sm" variant="secondary" onClick={onEdit} disabled={busy}>
          수정
        </Button>
        <Button size="sm" variant="danger" onClick={onDelete} disabled={busy}>
          삭제
        </Button>
      </div>
    </article>
  );
}

// Remounted per target (key), so the inputs start from the address being edited.
function AddressForm({ editing, busy, error, onCancel, onSubmit }) {
  const [value, setValue] = useState(() =>
    editing
      ? {
          recipient_name: editing.recipient_name,
          recipient_phone: editing.recipient_phone,
          zipcode: editing.zipcode,
          base_address: editing.base_address,
          detail_address: editing.detail_address ?? "",
        }
      : EMPTY_ADDRESS,
  );
  const [isDefault, setIsDefault] = useState(false);

  return (
    <form
      onSubmit={async (event) => {
        event.preventDefault();
        const ok = await onSubmit(value, isDefault);
        if (ok && !editing) {
          setValue(EMPTY_ADDRESS);
          setIsDefault(false);
        }
      }}
      className="border-cream-300 flex min-w-[300px] flex-[1_1_360px] flex-col gap-3.5 rounded-xl border p-6"
    >
      <h2 className="text-lg font-bold">
        {editing ? "배송지 수정" : "새 배송지 추가"}
      </h2>
      {error && <Notice>{errorMessage(error)}</Notice>}
      <AddressFields
        value={value}
        onChange={setValue}
        errors={fieldErrors(error)}
      />
      {!editing && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isDefault}
            onChange={(e) => setIsDefault(e.target.checked)}
            className="accent-espresso-950 size-4"
          />
          기본 배송지로 설정
        </label>
      )}
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>
          저장
        </Button>
        {editing && (
          <Button variant="ghost" onClick={onCancel}>
            취소
          </Button>
        )}
      </div>
    </form>
  );
}
