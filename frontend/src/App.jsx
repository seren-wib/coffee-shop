import { useEffect } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { setAuthFailureHandler } from "./api/client";
import { loginPath } from "./auth/next";
import { RequireAuth } from "./auth/RequireAuth";
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
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
