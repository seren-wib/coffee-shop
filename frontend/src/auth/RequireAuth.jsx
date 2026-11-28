import { Navigate, Outlet, useLocation } from "react-router-dom";
import { loginPath } from "./next";
import { getRole, isLoggedIn } from "./tokenStore";

// Route guards (SDD 7.0). They are a convenience: the server's 401/403 is the real check (NFR-10).
export function RequireAuth() {
  const { pathname, search } = useLocation();
  if (!isLoggedIn())
    return <Navigate to={loginPath(pathname + search)} replace />;
  return <Outlet />;
}

export function RequireAdmin() {
  const { pathname, search } = useLocation();
  if (!isLoggedIn())
    return <Navigate to={loginPath(pathname + search)} replace />;
  if (getRole() !== "ADMIN") return <Navigate to="/" replace />;
  return <Outlet />;
}
