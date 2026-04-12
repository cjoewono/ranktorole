import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../api/client";
import NavBar from "../components/NavBar";
import PageHeader from "../components/PageHeader";

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

async function fetchOnetSkills(keyword) {
  const res = await apiFetch(
    `/api/v1/onet/search/?keyword=${encodeURIComponent(keyword)}`,
  );
  const data = await res.json();
  return data.skills || [];
}

function FieldLabel({ children }) {
  return (
    <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
      {children}
    </label>
  );
}

function TacticalSelect({ value, onChange, required, children }) {
  return (
    <select
      required={required}
      value={value}
      onChange={onChange}
      className="tactical-input appearance-none cursor-pointer"
    >
      {children}
    </select>
  );
}

export default function ForgeSetup() {
  const { user, updateUser } = useAuth();
  const navigate = useNavigate();
  const isEditing = Boolean(user?.profile_context);

  const [branch, setBranch] = useState(user?.profile_context?.branch || "");
  const [mos, setMos] = useState(user?.profile_context?.mos || "");
  const [targetSector, setTargetSector] = useState(
    user?.profile_context?.target_sector || "",
  );
  const [selectedSkills, setSelectedSkills] = useState(
    user?.profile_context?.skills || [],
  );
  const [onetSkills, setOnetSkills] = useState([]);
  const [loadingSkills, setLoadingSkills] = useState(false);
  const [onetFetched, setOnetFetched] = useState(false);
  const [customSkill, setCustomSkill] = useState("");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleMosBlur() {
    if (!mos.trim()) return;
    setLoadingSkills(true);
    setOnetFetched(false);
    try {
      const skills = await fetchOnetSkills(mos.trim());
      setOnetSkills(skills);
    } catch {
      setOnetSkills([]);
    } finally {
      setLoadingSkills(false);
      setOnetFetched(true);
    }
  }

  function toggleSkill(skill) {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill],
    );
  }

  function addCustomSkill() {
    const trimmed = customSkill.trim();
    if (!trimmed || selectedSkills.includes(trimmed)) {
      setCustomSkill("");
      return;
    }
    setSelectedSkills((prev) => [...prev, trimmed]);
    setCustomSkill("");
  }

  function handleCustomKeyDown(e) {
    if (e.key === "Enter") {
      e.preventDefault();
      addCustomSkill();
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const profileContext = {
        branch,
        mos: mos.trim(),
        target_sector: targetSector,
        skills: selectedSkills,
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

  // O*NET preset tags + any custom skills not already in O*NET list
  const presetTags = onetSkills;
  const customOnlySkills = selectedSkills.filter(
    (s) => !onetSkills.includes(s),
  );

  return (
    <div className="min-h-screen bg-background">
      <NavBar />

      <PageHeader
        label={isEditing ? "OPERATOR / PROFILE_UPDATE" : "FORGE / ONBOARDING"}
        title={
          isEditing ? (
            <>
              EDIT
              <br />
              PROFILE
            </>
          ) : (
            <>
              FORGE
              <br />
              SETUP
            </>
          )
        }
      />

      <main className="max-w-xl mx-auto px-4 py-8 pb-28 md:pb-8">
        {error && (
          <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3 mb-6">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-secondary/10 border border-secondary/20 text-secondary font-label text-xs tracking-widest uppercase px-4 py-3 mb-6">
            PROFILE UPDATED
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Military Branch */}
          <div>
            <FieldLabel>
              Military Branch <span className="text-error">*</span>
            </FieldLabel>
            <TacticalSelect
              required
              value={branch}
              onChange={(e) => setBranch(e.target.value)}
            >
              <option value="">Select branch</option>
              {BRANCHES.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
            </TacticalSelect>
          </div>

          {/* MOS */}
          <div>
            <FieldLabel>MOS / Rating / AFSC</FieldLabel>
            <input
              type="text"
              value={mos}
              onChange={(e) => setMos(e.target.value)}
              onBlur={handleMosBlur}
              placeholder="e.g., 11B, IT2, 3D0X4"
              className="tactical-input"
            />
            <p className="font-label text-xs tracking-widest text-outline mt-1">
              Leave field to auto-load matching skills from O*NET
            </p>
          </div>

          {/* Target Sector */}
          <div>
            <FieldLabel>
              Target Civilian Sector <span className="text-error">*</span>
            </FieldLabel>
            <TacticalSelect
              required
              value={targetSector}
              onChange={(e) => setTargetSector(e.target.value)}
            >
              <option value="">Select sector</option>
              {SECTORS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </TacticalSelect>
          </div>

          {/* Skills */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <FieldLabel>Transferable Skills</FieldLabel>
              {selectedSkills.length > 0 && (
                <span className="font-label text-xs tracking-widest uppercase text-primary">
                  {selectedSkills.length} selected
                </span>
              )}
            </div>

            {/* O*NET preset tags */}
            {loadingSkills && (
              <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                Scanning O*NET...
              </p>
            )}

            {!loadingSkills && onetFetched && presetTags.length === 0 && (
              <p className="font-label text-xs tracking-widest uppercase text-outline">
                No matching skills found for that code. Add your own below.
              </p>
            )}

            {!loadingSkills && presetTags.length > 0 && (
              <div>
                <p className="font-label text-xs tracking-widest uppercase text-outline mb-2">
                  O*NET suggestions — tap to select
                </p>
                <div className="flex flex-wrap gap-2">
                  {presetTags.map((skill) => {
                    const isSelected = selectedSkills.includes(skill);
                    return (
                      <button
                        key={skill}
                        type="button"
                        onClick={() => toggleSkill(skill)}
                        className={
                          isSelected
                            ? "bg-primary/15 text-primary border border-primary/40 font-label text-xs tracking-wide px-3 py-1.5 rounded-sm transition-colors flex items-center gap-1.5"
                            : "bg-surface-container-highest text-on-surface-variant border border-outline-variant font-label text-xs tracking-wide px-3 py-1.5 rounded-sm hover:border-primary/30 hover:text-on-surface transition-colors"
                        }
                      >
                        {skill}
                        {isSelected && (
                          <span className="text-primary/60 text-xs leading-none">
                            ×
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Custom-only skills (selected but not from O*NET list) */}
            {customOnlySkills.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {customOnlySkills.map((skill) => (
                  <button
                    key={skill}
                    type="button"
                    onClick={() => toggleSkill(skill)}
                    className="bg-primary/15 text-primary border border-primary/40 font-label text-xs tracking-wide px-3 py-1.5 rounded-sm transition-colors flex items-center gap-1.5"
                  >
                    {skill}
                    <span className="text-primary/60 text-xs leading-none">
                      ×
                    </span>
                  </button>
                ))}
              </div>
            )}

            {/* Custom skill input */}
            <div className="bg-surface-container-low p-4 space-y-2">
              <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                Add custom skill
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customSkill}
                  onChange={(e) => setCustomSkill(e.target.value)}
                  onKeyDown={handleCustomKeyDown}
                  placeholder="e.g., Cross-functional leadership"
                  className="tactical-input flex-1"
                />
                <button
                  type="button"
                  onClick={addCustomSkill}
                  className="font-label text-xs tracking-widest uppercase text-on-surface-variant bg-surface-container-highest hover:text-on-surface border border-outline-variant px-4 py-2 transition-colors shrink-0"
                >
                  Add
                </button>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="space-y-4 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 disabled:opacity-50 transition-opacity"
            >
              {saving
                ? "SAVING..."
                : isEditing
                  ? "SAVE CHANGES"
                  : "COMPLETE SETUP"}
            </button>

            {isEditing && (
              <p className="text-center">
                <Link
                  to="/dashboard"
                  className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
                >
                  Back to Dashboard
                </Link>
              </p>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
