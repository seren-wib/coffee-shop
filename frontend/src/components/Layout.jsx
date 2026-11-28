import { Outlet } from "react-router-dom";
import DemoNoticeBanner from "./DemoNoticeBanner";
import Footer from "./Footer";
import Header from "./Header";

// Every route sits inside this layout, so no screen adds the demo notice itself (SDD 7.0.1).
// Full-width: no max-width container; screens use 48px side gutters (layout rules board).
export default function Layout() {
  return (
    <div className="flex min-h-screen flex-col">
      <DemoNoticeBanner />
      <Header />
      <main className="flex grow flex-col">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
