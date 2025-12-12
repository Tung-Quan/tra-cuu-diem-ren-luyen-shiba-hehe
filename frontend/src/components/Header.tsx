import { Link, NavLink } from "react-router-dom";
import type { ReactNode } from "react";

interface NavItemProps {
  to: string;
  children: ReactNode;
}

const NavItem = ({ to, children }: NavItemProps) => (
  <NavLink
    to={to}
    className={({ isActive }) =>
      `px-3 py-2 rounded-lg ${isActive ? "bg-black text-white" : "hover:bg-gray-100"}`
    }
  >
    {children}
  </NavLink>
);

export default function Header() {
  return (
    <header className="bg-white border-b">
      <div className="mx-auto max-w-6xl flex items-center justify-between p-4">
        <Link to="/" className="font-semibold">CTV Search</Link>
        <nav className="flex gap-2">
          <NavItem to="/">Trang chủ</NavItem>
          {/* <NavItem to="/search">Tìm kiếm</NavItem> */}
          <NavItem to="/mysql">search nhanh hơn</NavItem>
          <NavItem to="/add-link">Thêm Link</NavItem>
          <NavItem to="/sheets">Sheets</NavItem>
          <NavItem to="/health">Health</NavItem>
        </nav>
      </div>
    </header>
  );
}
