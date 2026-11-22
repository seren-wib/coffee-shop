import { Link, useLocation, useNavigate } from "react-router-dom";
import { clearTokens, getRole, isLoggedIn } from "../auth/tokenStore";

const MENUS = [
  {
    to: "/",
    label: "원두 목록",
    match: (path) => path === "/" || path.startsWith("/products"),
  },
  {
    to: "/cart",
    label: "장바구니",
    match: (path) => path.startsWith("/cart") || path.startsWith("/checkout"),
  },
  {
    to: "/orders",
    label: "주문 내역",
    match: (path) => path.startsWith("/orders"),
  },
  { to: "/me", label: "마이페이지", match: (path) => path.startsWith("/me") },
];

const ADMIN_MENU = {
  to: "/admin/orders",
  label: "관리자",
  match: (path) => path.startsWith("/admin"),
};

const ACCOUNT_LINK =
  "cursor-pointer text-sm text-latte-100 underline underline-offset-4 hover:text-white";

export default function Header() {
  // Login state is read from tokenStore on every render (SDD 6.0.3).
  // Login and logout both navigate, and the route change re-renders the header.
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const loggedIn = isLoggedIn();
  const menus = getRole() === "ADMIN" ? [...MENUS, ADMIN_MENU] : MENUS;

  function logout() {
    clearTokens();
    navigate("/");
  }

  return (
    <header className="bg-espresso-950 text-latte-100 flex min-h-16 flex-wrap items-center gap-10 px-12 py-3">
      <Link
        to="/"
        className="text-latte-100 hover:text-latte-100 font-serif text-[22px] font-bold no-underline"
      >
        BeanShop
      </Link>
      <nav
        aria-label="주 메뉴"
        className="flex grow flex-wrap gap-7 text-[15px]"
      >
        {menus.map((menu) => {
          const current = menu.match(pathname);
          return (
            <Link
              key={menu.to}
              to={menu.to}
              aria-current={current ? "page" : undefined}
              className={
                current
                  ? "font-medium text-amber-400 no-underline hover:text-amber-400"
                  : "text-latte-100 no-underline hover:text-white"
              }
            >
              {menu.label}
            </Link>
          );
        })}
      </nav>
      <div className="flex items-center gap-5">
        {loggedIn ? (
          <button type="button" onClick={logout} className={ACCOUNT_LINK}>
            로그아웃
          </button>
        ) : (
          <>
            <Link to="/login" className={ACCOUNT_LINK}>
              로그인
            </Link>
            <Link to="/signup" className={ACCOUNT_LINK}>
              회원가입
            </Link>
          </>
        )}
      </div>
    </header>
  );
}
