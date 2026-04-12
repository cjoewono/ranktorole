import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../api/client";
import NavBar from "../components/NavBar";

const BRANCHES = [
  "Army",
  "Navy",
  "Air Force",
  "Marines",
  "Coast Guard",
  "Space Force",
  "Other",
];

const SECTORS = [
  "Technology",
  "Finance",
  "Operations",
  "Healthcare",
  "Government / Defense",
  "Consulting",
  "Manufacturing",
  "Other",
];

export default function ForgeSetup() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const isEditing = Boolean(user?.profile_context);
  const [branch, setBranch] = useState(user?.profile_context?.branch || "");
  const [mos, setMos] = useState(user?.profile_context?.mos || "");
  const [targetSector, setTargetSector] = useState(
    user?.profile_context?.target_sector || "",
  );
  const [skills, setSkills] = useState(
    user?.profile_context?.skills?.join(", ") || "",
  );
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const profileContext = {
        branch,
        mos: mos.trim(),
        target_sector: targetSector,
        skills: skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      };
      const userData = await apiFetch("/api/v1/auth/profile/", {
        method: "PATCH",
        body: JSON.stringify({ profile_context: profileContext }),
      });
      updateUser(userData);
      if (isEditing) {
        setSuccess(true);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <div className="max-w-md mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-900">
              {isEditing ? "Edit Profile" : "Set Up Your Profile"}
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              {isEditing
                ? "Update your background and goals."
                : "Help us tailor your resume translation by telling us about your background and goals."}
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 text-sm rounded-lg px-4 py-3">
              Profile updated
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Military Branch <span className="text-red-400">*</span>
              </label>
              <select
                required
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">Select branch</option>
                {BRANCHES.map((b) => (
                  <option key={b} value={b}>
                    {b}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                MOS / Rating / AFSC
              </label>
              <input
                type="text"
                value={mos}
                onChange={(e) => setMos(e.target.value)}
                placeholder="e.g., 11B, IT2, 3D0X4"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Target Civilian Sector <span className="text-red-400">*</span>
              </label>
              <select
                required
                value={targetSector}
                onChange={(e) => setTargetSector(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">Select sector</option>
                {SECTORS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Top Transferable Skills
              </label>
              <input
                type="text"
                value={skills}
                onChange={(e) => setSkills(e.target.value)}
                placeholder="e.g., Cross-functional leadership, Agile, Cloud infrastructure"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Separate skills with commas
              </p>
            </div>

            <button
              type="submit"
              disabled={saving}
              className="w-full bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors"
            >
              {saving
                ? "Saving..."
                : isEditing
                  ? "Save Changes"
                  : "Complete Setup"}
            </button>
          </form>

          {isEditing && (
            <p className="text-center text-sm text-gray-500">
              <Link to="/dashboard" className="text-blue-600 hover:underline">
                Back to Dashboard
              </Link>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
