import { useEffect } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { setAuthFailureHandler } from "./api/client";
import { loginPath } from "./auth/next";
import { RequireAuth } from "./auth/RequireAuth";
import Layout from "./components/Layout";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import CheckoutResultPage from "./pages/CheckoutResultPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import OrderDetailPage from "./pages/OrderDetailPage";
import OrderListPage from "./pages/OrderListPage";
import ProductDetailPage from "./pages/ProductDetailPage";
import ProductListPage from "./pages/ProductListPage";

// Route table (SDD 6.0). Screens are added here as their pull requests land.
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
        <Route element={<RequireAuth />}>
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/checkout/result" element={<CheckoutResultPage />} />
          <Route path="/orders" element={<OrderListPage />} />
          <Route path="/orders/:id" element={<OrderDetailPage />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
