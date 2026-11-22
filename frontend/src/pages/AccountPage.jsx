import { useEffect, useState } from "react";
import { changePassword, getMe, updateMe } from "../api/auth";
import Button from "../components/Button";
import MyPageTabs from "../components/MyPageTabs";
import Notice from "../components/Notice";
import TextField from "../components/TextField";
import { errorMessage, fieldErrors, isOffline } from "../lib/errors";

// SCR-09 (FR-11 ~ FR-13, UC-10). Info form and password form side by side.
export default function AccountPage() {
  const [me, setMe] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    let active = true;
    getMe().then(
      (data) => active && setMe(data),
      (err) => active && setLoadError(err),
    );
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6 px-12 pt-10 pb-14">
      <h1 className="font-serif text-[32px] font-bold">마이페이지</h1>
      <MyPageTabs />
      {loadError && (
        <Notice kind={isOffline(loadError) ? "offline" : "error"}>
          {errorMessage(loadError)}
        </Notice>
      )}
      {!me && !loadError && (
        <div aria-hidden="true" className="bg-cream-100 h-72 rounded-xl" />
      )}
      {me && (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(360px,1fr))] items-start gap-8">
          <InfoForm me={me} onSaved={setMe} />
          <PasswordForm />
        </div>
      )}
    </div>
  );
}

const card = "flex flex-col gap-4 rounded-xl border border-cream-300 p-7";

function InfoForm({ me, onSaved }) {
  const [form, setForm] = useState({
    user_name: me.user_name,
    phone_number: me.phone_number,
  });
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setSaved(false);
    try {
      onSaved(await updateMe(form));
      setSaved(true);
    } catch (err) {
      setError(err);
    }
    setPending(false);
  }

  const errors = fieldErrors(error);
  return (
    <form onSubmit={handleSubmit} className={card}>
      <h2 className="text-lg font-bold">기본 정보</h2>
      {saved && <Notice kind="success">회원정보를 저장했습니다.</Notice>}
      {error && Object.keys(errors).length === 0 && (
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      )}
      <div className="flex flex-col gap-1.5">
        <TextField
          label="이메일"
          type="email"
          value={me.email}
          readOnly
          className="[&_input]:bg-cream-100"
        />
        <span className="text-brown-600 text-xs">
          이메일은 바꿀 수 없습니다.
        </span>
      </div>
      <TextField
        label="이름"
        required
        autoComplete="name"
        value={form.user_name}
        onChange={(e) => setForm({ ...form, user_name: e.target.value })}
        error={errors.user_name}
      />
      <TextField
        label="연락처"
        required
        type="tel"
        autoComplete="tel"
        value={form.phone_number}
        onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
        error={errors.phone_number}
      />
      <div>
        <Button type="submit" disabled={pending}>
          수정 저장
        </Button>
      </div>
    </form>
  );
}

const EMPTY_PASSWORDS = { current: "", next: "", confirm: "" };

function PasswordForm() {
  const [form, setForm] = useState(EMPTY_PASSWORDS);
  const [localErrors, setLocalErrors] = useState({});
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setDone(false);
    const found = {};
    if (form.next.length < 8) found.next = "비밀번호는 8자 이상이어야 합니다.";
    else if (form.next !== form.confirm)
      found.confirm = "비밀번호가 서로 다릅니다.";
    setLocalErrors(found);
    if (Object.keys(found).length > 0) return;
    setPending(true);
    setError(null);
    try {
      await changePassword({
        currentPassword: form.current,
        newPassword: form.next,
      });
      setForm(EMPTY_PASSWORDS);
      setDone(true);
    } catch (err) {
      setError(err);
    }
    setPending(false);
  }

  const server = fieldErrors(error);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  return (
    <form onSubmit={handleSubmit} noValidate className={card}>
      <h2 className="text-lg font-bold">비밀번호 변경</h2>
      {done && <Notice kind="success">비밀번호를 바꿨습니다.</Notice>}
      {error && Object.keys(server).length === 0 && (
        <Notice kind={isOffline(error) ? "offline" : "error"}>
          {errorMessage(error)}
        </Notice>
      )}
      <TextField
        label="현재 비밀번호"
        type="password"
        autoComplete="current-password"
        value={form.current}
        onChange={set("current")}
        error={server.current_password}
      />
      <TextField
        label="새 비밀번호 (8자 이상)"
        type="password"
        autoComplete="new-password"
        value={form.next}
        onChange={set("next")}
        error={localErrors.next ?? server.new_password}
      />
      <TextField
        label="새 비밀번호 확인"
        type="password"
        autoComplete="new-password"
        value={form.confirm}
        onChange={set("confirm")}
        error={localErrors.confirm}
      />
      <div>
        <Button type="submit" variant="outline" disabled={pending}>
          비밀번호 변경
        </Button>
      </div>
    </form>
  );
}
