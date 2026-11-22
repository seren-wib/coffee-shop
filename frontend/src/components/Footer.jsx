import { Link } from "react-router-dom";

// VITE_APP_VERSION is the first 7 characters of the built commit (NFR-24).
const VERSION = import.meta.env.VITE_APP_VERSION || "dev";

export default function Footer() {
  return (
    <footer className="bg-espresso-950 text-brown-400 flex flex-wrap gap-4 px-12 py-5 text-[13px]">
      <span>© coffee-shop</span>
      <span>버전 {VERSION}</span>
      <Link to="/privacy" className="text-latte-100 underline hover:text-white">
        개인정보 처리방침
      </Link>
    </footer>
  );
}
