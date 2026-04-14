import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { token } = useAuth();

  const navLinkClass = ({ isActive }) =>
    `font-label text-xs tracking-widest uppercase transition-colors ${
      isActive
        ? "text-secondary"
        : "text-on-surface-variant hover:text-on-surface"
    }`;

  const mobileTabClass = ({ isActive }) =>
    `flex-1 flex flex-col items-center py-3 gap-1 font-label text-[10px] tracking-widest uppercase transition-colors ${
      isActive ? "text-primary" : "text-on-surface-variant"
    }`;

  return (
    <>
      {/* Desktop top bar */}
      <nav className="hidden md:flex items-center justify-between bg-surface-container-low border-b border-outline-variant px-6 py-3">
        <div className="flex items-center gap-3">
          <Link
            to={token ? "/dashboard" : "/"}
            className="text-primary font-headline font-bold text-sm hover:opacity-80 transition-opacity"
          >
            ▣ RankToRole
          </Link>
          <span className="font-headline font-bold text-primary tracking-wide text-sm"></span>
        </div>
        <div className="flex items-center gap-8">
          <NavLink to="/dashboard" className={navLinkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/recon" className={navLinkClass}>
            Recon
          </NavLink>
          <NavLink to="/contacts" className={navLinkClass}>
            Contacts
          </NavLink>
          <NavLink to="/profile" className={navLinkClass}>
            Profile
          </NavLink>
        </div>
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface-container-low border-t border-outline-variant/15 flex">
        <NavLink to="/dashboard" className={mobileTabClass}>
          <span className="text-base">⊞</span>
          Dashboard
        </NavLink>
        <NavLink to="/recon" className={mobileTabClass}>
          <span className="text-base">◎</span>
          Recon
        </NavLink>
        <NavLink to="/contacts" className={mobileTabClass}>
          <span className="text-base">◈</span>
          Contacts
        </NavLink>
        <NavLink to="/profile" className={mobileTabClass}>
          <span className="text-base">◇</span>
          Profile
        </NavLink>
      </nav>
    </>
  );
}
