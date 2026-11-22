import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/auth";
import Button from "../components/Button";
import Notice from "../components/Notice";
import TextField from "../components/TextField";
import { errorMessage, fieldErrors, isOffline } from "../lib/errors";

const EMPTY = {
  email: "",
  password: "",
  confirm: "",
  user_name: "",
  phone_number: "",
  privacy_agreed: false,
};

// Same checks the server makes, so a bad form is not sent (FR-7, FR-58).
function checkForm(form) {
  const errors = {};
  if (form.password.length < 8)
    errors.password = "비밀번호는 8자 이상이어야 합니다.";
  else if (form.password !== form.confirm)
    errors.confirm = "비밀번호가 서로 다릅니다.";
  if (!form.privacy_agreed)
    errors.privacy_agreed = "개인정보 수집·이용에 동의해야 가입할 수 있습니다.";
  return errors;
}

// SCR-04 (FR-7, FR-58, UC-2). Split layout like login.
export default function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [localErrors, setLocalErrors] = useState({});
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  const set = (key) => (event) =>
    setForm({ ...form, [key]: event.target.value });

  async function handleSubmit(event) {
    event.preventDefault();
    const found = checkForm(form);
    setLocalErrors(found);
    if (Object.keys(found).length > 0) return;
    setPending(true);
    setError(null);
    try {
      await register({
        email: form.email,
        password: form.password,
        user_name: form.user_name,
        phone_number: form.phone_number,
        privacy_agreed: true,
      });
      navigate("/login", { state: { registered: true } });
    } catch (err) {
      setError(err);
      setPending(false);
    }
  }

  const errors = { ...fieldErrors(error), ...localErrors };
  const showTop = error && Object.keys(fieldErrors(error)).length === 0;

  return (
    <div className="flex grow flex-wrap">
      <section className="bg-brown-900 text-latte-100 flex flex-[1_1_400px] flex-col justify-end gap-3 px-12 py-16">
        <h1 className="font-serif text-[40px] leading-snug font-bold">
          회원가입
        </h1>
        <p className="text-brown-400 text-[15px]">
          가입하면 원두를 장바구니에 담고 주문할 수 있습니다.
        </p>
      </section>
      <section className="flex flex-[2_1_640px] flex-col p-12">
        <form
          onSubmit={handleSubmit}
          noValidate
          className="flex max-w-[720px] flex-col gap-5"
        >
          {showTop && (
            <Notice kind={isOffline(error) ? "offline" : "error"}>
              {errorMessage(error)}
            </Notice>
          )}
          <div className="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-4">
            <TextField
              label="이메일"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              required
              value={form.email}
              onChange={set("email")}
              error={errors.email}
            />
            <TextField
              label="비밀번호 (8자 이상)"
              type="password"
              autoComplete="new-password"
              required
              value={form.password}
              onChange={set("password")}
              error={errors.password}
            />
            <TextField
              label="비밀번호 확인"
              type="password"
              autoComplete="new-password"
              required
              value={form.confirm}
              onChange={set("confirm")}
              error={errors.confirm}
            />
            <TextField
              label="이름"
              autoComplete="name"
              required
              value={form.user_name}
              onChange={set("user_name")}
              error={errors.user_name}
            />
            <TextField
              label="연락처"
              type="tel"
              autoComplete="tel"
              placeholder="010-0000-0000"
              required
              value={form.phone_number}
              onChange={set("phone_number")}
              error={errors.phone_number}
            />
          </div>

          <section className="border-cream-300 flex flex-col gap-3 rounded-lg border p-5">
            <h2 className="text-[15px] font-bold">개인정보 수집·이용 안내</h2>
            <table className="w-full border-collapse text-[13px]">
              <tbody>
                <PrivacyRow name="수집 항목">
                  이메일, 이름, 연락처, 배송지의 받는 사람·연락처·주소
                </PrivacyRow>
                <PrivacyRow name="목적">회원 식별, 주문·배송 처리</PrivacyRow>
                <PrivacyRow name="보유 기간">
                  시연·평가가 끝나 운영 DB와 백업을 지울 때까지
                </PrivacyRow>
              </tbody>
            </table>
            <Link to="/privacy" className="self-start text-[13px]">
              개인정보 처리방침 전체 보기
            </Link>
            <label className="flex items-center gap-2 text-sm font-medium">
              <input
                type="checkbox"
                checked={form.privacy_agreed}
                onChange={(e) =>
                  setForm({ ...form, privacy_agreed: e.target.checked })
                }
                aria-invalid={errors.privacy_agreed ? true : undefined}
                className="accent-espresso-950 size-4"
              />
              개인정보 수집·이용에 동의합니다(필수)
            </label>
            {errors.privacy_agreed && (
              <p className="text-error text-xs">
                {[errors.privacy_agreed].flat().join(" ")}
              </p>
            )}
          </section>

          <div className="flex flex-wrap items-center gap-4">
            <Button type="submit" disabled={pending}>
              회원가입
            </Button>
            <span className="text-brown-600 text-sm">
              이미 회원이신가요? <Link to="/login">로그인</Link>
            </span>
          </div>
        </form>
      </section>
    </div>
  );
}

function PrivacyRow({ name, children }) {
  return (
    <tr className="border-cream-300 border-t last:border-b">
      <th
        scope="row"
        className="text-brown-600 w-24 py-2 pr-3 text-left font-medium"
      >
        {name}
      </th>
      <td className="py-2">{children}</td>
    </tr>
  );
}
