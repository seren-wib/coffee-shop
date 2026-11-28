import { Suspense, lazy, useEffect } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { setAuthFailureHandler } from "./api/client";
import { loginPath } from "./auth/next";
import { RequireAdmin, RequireAuth } from "./auth/RequireAuth";
import Layout from "./components/Layout";
import AccountPage from "./pages/AccountPage";
import AddressPage from "./pages/AddressPage";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import CheckoutResultPage from "./pages/CheckoutResultPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import OrderDetailPage from "./pages/OrderDetailPage";
import OrderListPage from "./pages/OrderListPage";
import PrivacyPage from "./pages/PrivacyPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import ProductListPage from "./pages/ProductListPage";
import SignupPage from "./pages/SignupPage";

// Admin screens load separately so the first customer screen stays small (SDD 7.1, NFR-2).
const AdminOrderListPage = lazy(
  () => import("./pages/admin/AdminOrderListPage"),
);
const AdminOrderDetailPage = lazy(
  () => import("./pages/admin/AdminOrderDetailPage"),
);
const AdminProductListPage = lazy(
  () => import("./pages/admin/AdminProductListPage"),
);
const AdminProductFormPage = lazy(
  () => import("./pages/admin/AdminProductFormPage"),
);

// Route table (SDD 7.0).
export default function App() {
  const navigate = useNavigate();

  // When a token refresh fails, go to login inside the app instead of reloading the page.
  useEffect(() => {
    setAuthFailureHandler(() => {
      navigate(loginPath(window.location.pathname + window.location.search));
    });
  }, [navigate]);

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<ProductListPage />} />
        <Route path="/products/:id" element={<ProductDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route element={<RequireAuth />}>
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/checkout/result" element={<CheckoutResultPage />} />
          <Route path="/orders" element={<OrderListPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />
          <Route path="/me" element={<AccountPage />} />
          <Route path="/me/addresses" element={<AddressPage />} />
        </Route>
        <Route element={<RequireAdmin />}>
          <Route
            path="/admin/orders"
            element={<Lazy page={AdminOrderListPage} />}
          />
          <Route
            path="/admin/orders/:id"
            element={<Lazy page={AdminOrderDetailPage} />}
          />
          <Route
            path="/admin/products"
            element={<Lazy page={AdminProductListPage} />}
          />
          <Route
            path="/admin/products/new"
            element={<Lazy page={AdminProductFormPage} />}
          />
          <Route
            path="/admin/products/:id"
            element={<Lazy page={AdminProductFormPage} />}
          />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

function Lazy({ page: Page }) {
  return (
    <Suspense
      fallback={
        <div aria-hidden="true" className="bg-cream-100 m-12 h-60 rounded-xl" />
      }
    >
      <Page />
    </Suspense>
  );
}
