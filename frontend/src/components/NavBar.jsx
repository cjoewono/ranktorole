import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { logout } = useAuth();

  const linkClass = ({ isActive }) =>
    isActive
      ? "text-white font-semibold border-b-2 border-white pb-0.5"
      : "text-blue-100 hover:text-white transition-colors";

  return (
    <nav className="bg-blue-800 px-6 py-3 flex items-center justify-between">
      <span className="text-white font-bold text-lg tracking-wide">
        RankToRole
      </span>
      <div className="flex items-center gap-6 text-sm">
        <NavLink to="/dashboard" className={linkClass}>
          Dashboard
        </NavLink>
        <NavLink to="/contacts" className={linkClass}>
          Contacts
        </NavLink>
        <button
          onClick={logout}
          className="text-blue-100 hover:text-white transition-colors"
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
