import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { logout } = useAuth();

  const linkClass = ({ isActive }) =>
    isActive
      ? "text-white font-semibold border-b-2 border-white pb-0.5"
      : "text-slate-300 hover:text-white transition-colors duration-200";

  return (
    <nav className="bg-slate-900 px-6 h-16 flex items-center justify-between border-b border-white/5">
      <span className="text-white font-bold text-lg tracking-tight">
        RankToRole
      </span>
      <div className="flex items-center gap-7 text-sm">
        <NavLink to="/dashboard" className={linkClass}>
          Dashboard
        </NavLink>
        <NavLink to="/contacts" className={linkClass}>
          Contacts
        </NavLink>
        <button
          onClick={logout}
          className="text-slate-300 hover:text-white transition-colors duration-200"
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}
