import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { login } from "../api/auth";
import { safeNext } from "../auth/next";
import { setTokens } from "../auth/tokenStore";
import Button from "../components/Button";
import Notice from "../components/Notice";
import TextField from "../components/TextField";
import { errorMessage, isOffline } from "../lib/errors";

// SCR-03 (FR-8, NFR-7). Split layout: brown panel on the left, form on the right.
export default function LoginPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const data = await login({ email, password });
      setTokens({ access: data.access, refresh: data.refresh });
      navigate(safeNext(params.get("next")), { replace: true });
    } catch (err) {
      setError(err);
      setPending(false);
    }
  }

  return (
    <div className="flex grow flex-wrap">
      <section className="bg-brown-900 text-latte-100 flex flex-[1_1_480px] flex-col justify-end gap-3 px-12 py-16">
        <p className="font-serif text-[40px] leading-snug font-bold">
          다시 오셨네요
        </p>
        <p className="text-brown-400 text-[15px]">
          로그인하면 장바구니와 주문 내역을 이어서 볼 수 있습니다.
        </p>
      </section>
      <section className="flex flex-[1_1_480px] flex-col justify-center px-12 py-16">
        <form
          onSubmit={handleSubmit}
          className="flex max-w-[440px] flex-col gap-4"
        >
          <h1 className="mb-2 text-[22px] font-bold">로그인</h1>
          {error && (
            <Notice kind={isOffline(error) ? "offline" : "error"}>
              {errorMessage(error)}
            </Notice>
          )}
          <TextField
            label="이메일"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <TextField
            label="비밀번호"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button type="submit" disabled={pending}>
            {pending ? "로그인 중…" : "로그인"}
          </Button>
          <p className="text-brown-600 text-sm">
            처음이신가요? <Link to="/signup">회원가입</Link>
          </p>
        </form>
      </section>
    </div>
  );
}
