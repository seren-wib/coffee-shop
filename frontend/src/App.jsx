import { useEffect } from "react";
import { Route, Routes, useNavigate } from "react-router-dom";
import { setAuthFailureHandler } from "./api/client";
import { loginPath } from "./auth/next";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";

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
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
