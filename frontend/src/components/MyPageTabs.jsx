import { useLocation } from "react-router-dom";
import Tabs from "./Tabs";

// My page tabs shared by SCR-09 and SCR-10 (layout rules board).
export default function MyPageTabs() {
  const { pathname } = useLocation();
  return (
    <Tabs
      label="마이페이지"
      items={[
        {
          key: "me",
          to: "/me",
          label: "회원정보",
          current: pathname === "/me",
        },
        {
          key: "addresses",
          to: "/me/addresses",
          label: "배송지 관리",
          current: pathname === "/me/addresses",
        },
      ]}
    />
  );
}
