import { useLocation } from "react-router-dom";
import Tabs from "./Tabs";

// Admin area tabs under the header's "관리자" menu (layout rules board).
export default function AdminTabs() {
  const { pathname } = useLocation();
  return (
    <Tabs
      label="관리자"
      items={[
        {
          key: "orders",
          to: "/admin/orders",
          label: "주문 관리",
          current: pathname.startsWith("/admin/orders"),
        },
        {
          key: "products",
          to: "/admin/products",
          label: "원두 관리",
          current: pathname.startsWith("/admin/products"),
        },
      ]}
    />
  );
}
