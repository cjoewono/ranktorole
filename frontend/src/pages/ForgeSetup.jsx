import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../api/client";
import PageHeader from "../components/PageHeader";
import { createPortalSession } from "../api/billing";
import UpgradeModal from "../components/UpgradeModal";
import TacticalLabel from "../components/forms/TacticalLabel";
import TacticalSelect from "../components/forms/TacticalSelect";

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
  try {
    const data = await apiFetch(
      `/api/v1/onet/search/?keyword=${encodeURIComponent(keyword)}`,
    );
    return data.skills || [];
  } catch {
    return [];
  }
}

export default function ForgeSetup() {
  const { user, updateUser, logout } = useAuth();
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
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState(null);
  const [passwordSuccess, setPasswordSuccess] = useState(null);
  const [changingPassword, setChangingPassword] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);
  const [portalError, setPortalError] = useState("");
  const [upgradeOpen, setUpgradeOpen] = useState(false);

  async function handleManageBilling() {
    setPortalError("");
    setPortalLoading(true);
    try {
      const returnUrl = `${window.location.origin}/profile`;
      const { url } = await createPortalSession(returnUrl);
      if (!url) throw new Error("Portal URL missing.");
      window.location.assign(url);
    } catch (err) {
      setPortalError(
        err?.message || "Could not open billing portal. Please try again.",
      );
      setPortalLoading(false);
    }
  }

  async function handleMosBlur() {
    if (!mos.trim()) return;
    setLoadingSkills(true);
    setOnetFetched(false);
    const skills = await fetchOnetSkills(mos.trim());
    setOnetSkills(skills);
    setLoadingSkills(false);
    setOnetFetched(true);
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

  async function handlePasswordChange(e) {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("New password must be at least 8 characters.");
      return;
    }

    setChangingPassword(true);
    try {
      await apiFetch("/api/v1/auth/change-password/", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setPasswordSuccess("Password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => setPasswordSuccess(null), 5000);
    } catch (err) {
      setPasswordError(
        err.data?.error || err.message || "Failed to change password.",
      );
    } finally {
      setChangingPassword(false);
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
    <>
      <PageHeader
        label={isEditing ? "OPERATOR / PROFILE_UPDATE" : "FORGE / ONBOARDING"}
        title={isEditing ? "EDIT PROFILE" : "FORGE SETUP"}
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

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* ─── Section 1: Military Background ─── */}
          <div className="bg-surface-container-low p-6">
            <div className="flex items-center gap-2 mb-5">
              <span className="w-2 h-2 rounded-full bg-primary inline-block" />
              <h2 className="font-label text-xs tracking-widest uppercase text-primary">
                Military Background
              </h2>
            </div>
            <div className="space-y-5">
              <div>
                <TacticalLabel>
                  Military Branch <span className="text-error">*</span>
                </TacticalLabel>
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
                <p className="font-label text-xs tracking-widest text-outline mt-1.5">
                  Determines service-specific terminology mapping
                </p>
              </div>

              <div className="border-t border-outline-variant/10 pt-5">
                <TacticalLabel>MOS / Rating / AFSC</TacticalLabel>
                <input
                  type="text"
                  value={mos}
                  onChange={(e) => setMos(e.target.value)}
                  onBlur={handleMosBlur}
                  placeholder="e.g., 11B, IT2, 3D0X4"
                  className="tactical-input"
                />
                <p className="font-label text-xs tracking-widest text-outline mt-1.5">
                  Leave field to auto-load matching skills from O*NET
                </p>
              </div>
            </div>
          </div>

          {/* ─── Section 2: Career Goals ─── */}
          <div className="bg-surface-container-low p-6">
            <div className="flex items-center gap-2 mb-5">
              <span className="w-2 h-2 rounded-full bg-primary inline-block" />
              <h2 className="font-label text-xs tracking-widest uppercase text-primary">
                Career Goals
              </h2>
            </div>
            <div className="space-y-5">
              <div>
                <TacticalLabel>
                  Target Civilian Sector <span className="text-error">*</span>
                </TacticalLabel>
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
                <p className="font-label text-xs tracking-widest text-outline mt-1.5">
                  Tunes vocabulary and job title suggestions to your target
                  industry
                </p>
              </div>

              <div className="border-t border-outline-variant/10 pt-5 space-y-4">
                <div className="flex items-center justify-between">
                  <TacticalLabel>Transferable Skills</TacticalLabel>
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
                <p className="font-label text-xs tracking-widest text-outline mt-1.5">
                  Selected skills are prioritized in your translated resume
                  bullets
                </p>
              </div>
            </div>
          </div>

          {/* ─── Section 3: Profile Strength + Save ─── */}
          <div className="bg-surface-container-low p-6 space-y-5">
            {/* Profile completeness */}
            {(() => {
              const filled =
                [branch, mos, targetSector].filter(Boolean).length +
                (selectedSkills.length > 0 ? 1 : 0);
              const total = 4;
              const pct = Math.round((filled / total) * 100);
              return (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                      Profile signal strength
                    </span>
                    <span
                      className={`font-label text-xs tracking-widest uppercase ${
                        pct === 100
                          ? "text-secondary"
                          : pct >= 50
                            ? "text-primary"
                            : "text-outline"
                      }`}
                    >
                      {pct}%
                    </span>
                  </div>
                  <div className="h-1 bg-surface-container-highest overflow-hidden">
                    <div
                      className={`h-full transition-all duration-500 ${
                        pct === 100 ? "bg-secondary" : "bg-primary"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  {pct < 100 && (
                    <p className="font-label text-xs tracking-widest text-outline">
                      {pct < 50
                        ? "Add more details for better translation accuracy"
                        : "Almost there — complete all fields for best results"}
                    </p>
                  )}
                </div>
              );
            })()}
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

        {/* ─── Section 4: Account Settings (only when editing) ─── */}
        {isEditing && (
          <div className="space-y-6 mt-6">
            {/* Account Info card */}
            <div className="bg-surface-container-low p-6">
              <div className="flex items-center gap-2 mb-5">
                <span className="w-2 h-2 rounded-full bg-on-surface-variant inline-block" />
                <h2 className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                  Account
                </h2>
              </div>
              <div className="space-y-4">
                <div>
                  <TacticalLabel>Email</TacticalLabel>
                  <p className="tactical-input opacity-60 cursor-not-allowed">
                    {user?.email}
                  </p>
                  <p className="font-label text-xs tracking-widest text-outline mt-1.5">
                    Email cannot be changed
                  </p>
                </div>

                <div className="border-t border-outline-variant/10 pt-4">
                  <TacticalLabel>Account Tier</TacticalLabel>
                  <p className="tactical-input opacity-60 cursor-not-allowed uppercase">
                    {user?.tier || "free"}
                  </p>
                </div>
              </div>
            </div>

            {/* Password Change card */}
            <div className="bg-surface-container-low p-6">
              <div className="flex items-center gap-2 mb-5">
                <span className="w-2 h-2 rounded-full bg-on-surface-variant inline-block" />
                <h2 className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                  Security
                </h2>
              </div>

              {passwordError && (
                <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3 mb-4">
                  {passwordError}
                </div>
              )}
              {passwordSuccess && (
                <div className="bg-secondary/10 text-secondary font-body text-sm px-4 py-3 mb-4">
                  {passwordSuccess}
                </div>
              )}

              <form onSubmit={handlePasswordChange} className="space-y-5">
                <div>
                  <TacticalLabel>Current Password</TacticalLabel>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="tactical-input"
                    required
                  />
                </div>
                <div className="border-t border-outline-variant/10 pt-5">
                  <TacticalLabel>New Password</TacticalLabel>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    className="tactical-input"
                    required
                  />
                </div>
                <div className="border-t border-outline-variant/10 pt-5">
                  <TacticalLabel>Confirm New Password</TacticalLabel>
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="tactical-input"
                    required
                  />
                </div>
                <button
                  type="submit"
                  disabled={changingPassword}
                  className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {changingPassword ? "UPDATING..." : "UPDATE PASSWORD"}
                </button>
              </form>
            </div>

            {/* Subscription */}
            <div className="bg-surface-container-low p-6">
              <h2 className="font-headline font-bold text-lg uppercase text-on-surface mb-4">
                Subscription
              </h2>
              <div className="mb-4">
                <span className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                  Current Plan
                </span>
                <p className="font-headline font-bold text-xl text-on-surface mt-1">
                  {user?.tier === "pro" ? "PRO" : "FREE"}
                </p>
              </div>

              {portalError && (
                <p className="mb-3 text-sm text-error" role="alert">
                  {portalError}
                </p>
              )}

              {user?.tier === "pro" ? (
                <button
                  type="button"
                  onClick={handleManageBilling}
                  disabled={portalLoading}
                  className="w-full mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md disabled:opacity-50"
                >
                  {portalLoading ? "Opening..." : "Manage Billing"}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setUpgradeOpen(true)}
                  className="w-full mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md"
                >
                  Upgrade to Pro
                </button>
              )}

              <p className="mt-3 text-xs text-on-surface-variant">
                {user?.tier === "pro"
                  ? "Opens Stripe's secure billing portal. Cancel, update card, or view invoices."
                  : "Unlimited tailoring and chat — $10/month, cancel anytime."}
              </p>
            </div>

            {/* Sign Out card */}
            <div className="bg-surface-container-low p-6">
              <button
                onClick={logout}
                className="w-full border border-error text-error font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md hover:bg-error hover:text-on-primary transition-colors"
              >
                SIGN OUT
              </button>
            </div>

            <UpgradeModal
              open={upgradeOpen}
              onClose={() => setUpgradeOpen(false)}
              variant="upgrade"
            />
          </div>
        )}
      </main>
    </>
  );
}
