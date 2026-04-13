import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useResumes } from "../context/ResumeContext";

const NAV_ITEMS = [
  { to: "/dashboard", label: "Dashboard", icon: "⊞" },
  { to: "/contacts", label: "Intel", icon: "◈" },
];

export default function NavBar() {
  const { logout, token } = useAuth();
  const { resumes } = useResumes();
  const navigate = useNavigate();

  function handleEditorClick() {
    const inProgress = resumes.find((r) => r.is_finalized === false);
    if (inProgress) {
      navigate(`/resume-builder?id=${inProgress.id}&mode=continue`);
    } else {
      navigate("/resume-builder");
    }
  }

  return (
    <>
      {/* Desktop top bar */}
      <nav className="hidden md:flex items-center justify-between bg-surface-container-low border-b border-outline-variant px-6 py-3">
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="text-primary font-headline font-bold text-sm hover:opacity-80 transition-opacity"
          >
            ▣ RankToRole
          </Link>
          <span className="font-headline font-bold text-primary tracking-wide text-sm"></span>
        </div>
        <div className="flex items-center gap-8">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `font-label text-xs tracking-widest uppercase transition-colors ${
                isActive
                  ? "text-secondary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`
            }
          >
            Dashboard
          </NavLink>
          <button
            onClick={handleEditorClick}
            className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-on-surface transition-colors"
          >
            Editor
          </button>
          <NavLink
            to="/recon"
            className={({ isActive }) =>
              `font-label text-xs tracking-widest uppercase transition-colors ${
                isActive
                  ? "text-secondary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`
            }
          >
            Recon
          </NavLink>
          <NavLink
            to="/contacts"
            className={({ isActive }) =>
              `font-label text-xs tracking-widest uppercase transition-colors ${
                isActive
                  ? "text-secondary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`
            }
          >
            Intel
          </NavLink>
          <NavLink
            to="/profile"
            className={({ isActive }) =>
              `font-label text-xs tracking-widest uppercase transition-colors ${
                isActive
                  ? "text-secondary"
                  : "text-on-surface-variant hover:text-on-surface"
              }`
            }
          >
            Profile
          </NavLink>
          <button
            onClick={logout}
            className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-error transition-colors"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface-container-low border-t border-outline-variant/15 flex">
        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center py-3 gap-1 font-label text-[10px] tracking-widest uppercase transition-colors ${
              isActive ? "text-primary" : "text-on-surface-variant"
            }`
          }
        >
          <span className="text-base">⊞</span>
          Dashboard
        </NavLink>
        <button
          onClick={handleEditorClick}
          className="flex-1 flex flex-col items-center py-3 gap-1 font-label text-[10px] tracking-widest uppercase transition-colors text-on-surface-variant"
        >
          <span className="text-base">⊟</span>
          Editor
        </button>
        <NavLink
          to="/recon"
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center py-3 gap-1 font-label text-[10px] tracking-widest uppercase transition-colors ${
              isActive ? "text-primary" : "text-on-surface-variant"
            }`
          }
        >
          <span className="text-base">◎</span>
          Recon
        </NavLink>
        <NavLink
          to="/contacts"
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center py-3 gap-1 font-label text-[10px] tracking-widest uppercase transition-colors ${
              isActive ? "text-primary" : "text-on-surface-variant"
            }`
          }
        >
          <span className="text-base">◈</span>
          Intel
        </NavLink>
      </nav>
    </>
  );
}
