import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import { submitBrainstorm } from "../api/recon";

const BRANCHES = [
  "Army",
  "Navy",
  "Air Force",
  "Marine Corps",
  "Coast Guard",
  "Space Force",
];

const GRADES = {
  Enlisted: ["E-1", "E-2", "E-3", "E-4", "E-5", "E-6", "E-7", "E-8", "E-9"],
  "Warrant Officer": ["W-1", "W-2", "W-3", "W-4", "W-5"],
  Officer: [
    "O-1",
    "O-2",
    "O-3",
    "O-4",
    "O-5",
    "O-6",
    "O-7",
    "O-8",
    "O-9",
    "O-10",
  ],
};

const US_STATES = [
  "Alabama",
  "Alaska",
  "Arizona",
  "Arkansas",
  "California",
  "Colorado",
  "Connecticut",
  "Delaware",
  "District of Columbia",
  "Florida",
  "Georgia",
  "Hawaii",
  "Idaho",
  "Illinois",
  "Indiana",
  "Iowa",
  "Kansas",
  "Kentucky",
  "Louisiana",
  "Maine",
  "Maryland",
  "Massachusetts",
  "Michigan",
  "Minnesota",
  "Mississippi",
  "Missouri",
  "Montana",
  "Nebraska",
  "Nevada",
  "New Hampshire",
  "New Jersey",
  "New Mexico",
  "New York",
  "North Carolina",
  "North Dakota",
  "Ohio",
  "Oklahoma",
  "Oregon",
  "Pennsylvania",
  "Puerto Rico",
  "Rhode Island",
  "South Carolina",
  "South Dakota",
  "Tennessee",
  "Texas",
  "Utah",
  "Vermont",
  "Virginia",
  "Washington",
  "West Virginia",
  "Wisconsin",
  "Wyoming",
];

function MatchScoreBadge({ score }) {
  let color = "bg-error/10 text-error";
  let label = "LOW MATCH";
  if (score >= 80) {
    color = "bg-secondary/10 text-secondary";
    label = "STRONG MATCH";
  } else if (score >= 60) {
    color = "bg-primary/10 text-primary";
    label = "GOOD MATCH";
  } else if (score >= 40) {
    color = "bg-tertiary/10 text-tertiary";
    label = "PARTIAL MATCH";
  }
  return (
    <span
      className={`font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm ${color}`}
    >
      {score}% — {label}
    </span>
  );
}

function OptionalLabel() {
  return (
    <span className="text-outline normal-case tracking-normal font-body font-normal text-xs ml-1">
      (optional)
    </span>
  );
}

export default function CareerRecon() {
  const [services, setServices] = useState([{ branch: "Army", mos_code: "" }]);
  const [grade, setGrade] = useState("");
  const [position, setPosition] = useState("");
  const [targetField, setTargetField] = useState("");
  const [education, setEducation] = useState([""]);
  const [certifications, setCertifications] = useState([""]);
  const [licenses, setLicenses] = useState([""]);
  const [state, setState] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const resultRef = useRef(null);

  const canSubmit = services.some((s) => s.branch.trim() && s.mos_code.trim());

  function addService() {
    setServices((prev) =>
      prev.length < 5 ? [...prev, { branch: "Army", mos_code: "" }] : prev,
    );
  }
  function updateService(i, field, val) {
    setServices((prev) =>
      prev.map((s, idx) => (idx === i ? { ...s, [field]: val } : s)),
    );
  }
  function removeService(i) {
    setServices((prev) => prev.filter((_, idx) => idx !== i));
  }

  function addRow(setter, cap) {
    setter((prev) => (prev.length < cap ? [...prev, ""] : prev));
  }
  function updateRow(setter, i, val) {
    setter((prev) => prev.map((v, idx) => (idx === i ? val : v)));
  }
  function removeRow(setter, i) {
    setter((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    const payload = {
      services: services.filter((s) => s.branch.trim() && s.mos_code.trim()),
      grade: grade.trim(),
      position: position.trim(),
      target_career_field: targetField.trim(),
      education: education.map((v) => v.trim()).filter(Boolean),
      certifications: certifications.map((v) => v.trim()).filter(Boolean),
      licenses: licenses.map((v) => v.trim()).filter(Boolean),
      state: state.trim(),
    };

    try {
      const data = await submitBrainstorm(payload);
      setResult(data);
      setTimeout(
        () => resultRef.current?.scrollIntoView({ behavior: "smooth" }),
        50,
      );
    } catch (err) {
      const s = err.status;
      if (s === 400)
        setError({
          type: "validation",
          message: "Please check your entries and try again.",
        });
      else if (s === 429)
        setError({
          type: "throttle",
          message:
            "You've hit your daily Recon limit. Try again tomorrow or upgrade to Pro.",
        });
      else if (s === 502)
        setError({
          type: "onet",
          message:
            "O*NET Web Services is unreachable. This usually clears in a few minutes.",
        });
      else if (s === 503)
        setError({
          type: "ceiling",
          message: "Recon is at peak capacity. Please try again shortly.",
        });
      else
        setError({
          type: "unknown",
          message: "Something went wrong. Please try again.",
        });
    } finally {
      setSubmitting(false);
    }
  }

  const bm = result?.best_match;
  const knowledgeTop6 = bm?.knowledge?.slice(0, 6) ?? [];
  const techTop6 = (bm?.technology ?? [])
    .flatMap((cat) =>
      (cat.examples ?? []).map((ex) => ({ ...ex, category: cat.category })),
    )
    .slice(0, 6);

  return (
    <>
      <div className="bg-surface-container-low px-4 pt-4 pb-6">
        <div className="flex items-center gap-2 mb-3">
          <span className="w-2 h-2 rounded-full bg-on-surface-variant/40 inline-block" />
          <span className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
            RECON / BRAINSTORM
          </span>
        </div>
        <h1 className="font-headline font-bold text-4xl uppercase text-on-surface leading-tight">
          CAREER RECON
        </h1>
      </div>

      <main className="max-w-3xl mx-auto px-4 py-8 md:py-12">
        <div className="bg-surface-container-high rounded-2xl border border-outline/40 shadow-lg p-6 md:p-8">
          <div className="mb-8 pb-6 border-b border-outline/20">
            <h2 className="font-headline text-xl text-on-surface mb-2">
              Find Your Civilian Mission
            </h2>
            <p className="font-body text-sm text-on-surface-variant">
              Tell us about your service. We'll map your military experience to
              civilian careers using O*NET data and AI analysis.
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <div
              role="alert"
              className="flex items-start justify-between gap-3 bg-error-container text-on-error-container font-body text-sm px-4 py-3 rounded-md mb-6"
            >
              <span>{error.message}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                className="shrink-0 text-on-error-container hover:opacity-70 transition-opacity font-label text-lg leading-none"
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Services */}
            <fieldset>
              <legend className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-3">
                Service Branch &amp; MOS / AFSC / Rating{" "}
                <span className="text-primary">*</span>
              </legend>
              <div className="space-y-3">
                {services.map((svc, i) => (
                  <div key={i} className="flex gap-2 items-end">
                    <div className="flex-1">
                      {i === 0 && (
                        <label
                          htmlFor={`branch-${i}`}
                          className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1"
                        >
                          Branch
                        </label>
                      )}
                      <select
                        id={`branch-${i}`}
                        value={svc.branch}
                        onChange={(e) =>
                          updateService(i, "branch", e.target.value)
                        }
                        className="tactical-input appearance-none cursor-pointer"
                      >
                        {BRANCHES.map((b) => (
                          <option key={b} value={b}>
                            {b}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex-1">
                      {i === 0 && (
                        <label
                          htmlFor={`mos-${i}`}
                          className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1"
                        >
                          MOS / AFSC / Rating
                        </label>
                      )}
                      <input
                        id={`mos-${i}`}
                        type="text"
                        value={svc.mos_code}
                        onChange={(e) =>
                          updateService(i, "mos_code", e.target.value)
                        }
                        placeholder="e.g. 11B, 3D0X4, IT2"
                        className="tactical-input"
                      />
                    </div>
                    {services.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeService(i)}
                        className="shrink-0 pb-2 text-outline hover:text-error transition-colors font-label text-xl leading-none"
                        aria-label={`Remove service entry ${i + 1}`}
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {services.length < 5 && (
                <button
                  type="button"
                  onClick={addService}
                  className="mt-3 font-label text-xs tracking-widest uppercase text-tertiary hover:opacity-70 transition-opacity"
                >
                  + ADD ANOTHER
                </button>
              )}
            </fieldset>

            {/* Grade */}
            <div>
              <label
                htmlFor="grade"
                className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1"
              >
                Grade <OptionalLabel />
              </label>
              <select
                id="grade"
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                className="tactical-input appearance-none cursor-pointer"
              >
                <option value="">Select grade...</option>
                {Object.entries(GRADES).map(([group, grades]) => (
                  <optgroup key={group} label={group}>
                    {grades.map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            {/* Position */}
            <div>
              <label
                htmlFor="position"
                className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1"
              >
                Position / Job Title <OptionalLabel />
              </label>
              <input
                id="position"
                type="text"
                value={position}
                onChange={(e) => setPosition(e.target.value)}
                placeholder="e.g. Platoon Leader, Avionics Technician"
                className="tactical-input"
                maxLength={100}
              />
            </div>

            {/* Target Career Field */}
            <div>
              <label
                htmlFor="targetField"
                className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1"
              >
                Target Career Field <OptionalLabel />
              </label>
              <input
                id="targetField"
                type="text"
                value={targetField}
                onChange={(e) => setTargetField(e.target.value)}
                placeholder="e.g. Cybersecurity, Project Management, Healthcare"
                className="tactical-input"
                maxLength={100}
              />
            </div>

            {/* Education */}
            <fieldset>
              <legend className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-3">
                Education <OptionalLabel />
              </legend>
              <div className="space-y-2">
                {education.map((edu, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <label htmlFor={`edu-${i}`} className="sr-only">
                      Education entry {i + 1}
                    </label>
                    <input
                      id={`edu-${i}`}
                      type="text"
                      value={edu}
                      onChange={(e) =>
                        updateRow(setEducation, i, e.target.value)
                      }
                      placeholder="e.g. Bachelor's in Computer Science"
                      className="tactical-input"
                    />
                    {education.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRow(setEducation, i)}
                        className="shrink-0 text-outline hover:text-error transition-colors font-label text-xl leading-none"
                        aria-label={`Remove education entry ${i + 1}`}
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {education.length < 10 && (
                <button
                  type="button"
                  onClick={() => addRow(setEducation, 10)}
                  className="mt-3 font-label text-xs tracking-widest uppercase text-tertiary hover:opacity-70 transition-opacity"
                >
                  + ADD
                </button>
              )}
            </fieldset>

            {/* Certifications */}
            <fieldset>
              <legend className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-3">
                Certifications <OptionalLabel />
              </legend>
              <div className="space-y-2">
                {certifications.map((cert, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <label htmlFor={`cert-${i}`} className="sr-only">
                      Certification entry {i + 1}
                    </label>
                    <input
                      id={`cert-${i}`}
                      type="text"
                      value={cert}
                      onChange={(e) =>
                        updateRow(setCertifications, i, e.target.value)
                      }
                      placeholder="e.g. CompTIA Security+, PMP"
                      className="tactical-input"
                    />
                    {certifications.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRow(setCertifications, i)}
                        className="shrink-0 text-outline hover:text-error transition-colors font-label text-xl leading-none"
                        aria-label={`Remove certification entry ${i + 1}`}
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {certifications.length < 20 && (
                <button
                  type="button"
                  onClick={() => addRow(setCertifications, 20)}
                  className="mt-3 font-label text-xs tracking-widest uppercase text-tertiary hover:opacity-70 transition-opacity"
                >
                  + ADD
                </button>
              )}
            </fieldset>

            {/* Licenses */}
            <fieldset>
              <legend className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-3">
                Licenses <OptionalLabel />
              </legend>
              <div className="space-y-2">
                {licenses.map((lic, i) => (
                  <div key={i} className="flex gap-2 items-center">
                    <label htmlFor={`lic-${i}`} className="sr-only">
                      License entry {i + 1}
                    </label>
                    <input
                      id={`lic-${i}`}
                      type="text"
                      value={lic}
                      onChange={(e) =>
                        updateRow(setLicenses, i, e.target.value)
                      }
                      placeholder="e.g. FAA Airframe & Powerplant, CDL Class A"
                      className="tactical-input"
                    />
                    {licenses.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeRow(setLicenses, i)}
                        className="shrink-0 text-outline hover:text-error transition-colors font-label text-xl leading-none"
                        aria-label={`Remove license entry ${i + 1}`}
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {licenses.length < 20 && (
                <button
                  type="button"
                  onClick={() => addRow(setLicenses, 20)}
                  className="mt-3 font-label text-xs tracking-widest uppercase text-tertiary hover:opacity-70 transition-opacity"
                >
                  + ADD
                </button>
              )}
            </fieldset>

            {/* State */}
            <div>
              <label
                htmlFor="state"
                className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1"
              >
                State <OptionalLabel />
              </label>
              <select
                id="state"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="tactical-input appearance-none cursor-pointer"
              >
                <option value="">Select state...</option>
                {US_STATES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>

            {/* Submit */}
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={!canSubmit || submitting}
                aria-busy={submitting}
                className="mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase px-8 py-3 rounded-md hover:opacity-90 transition-opacity disabled:opacity-50 w-full sm:w-auto"
              >
                {submitting ? "ANALYZING..." : "ANALYZE CAREERS"}
              </button>
            </div>
          </form>
        </div>
      </main>

      {/* Results */}
      {result && (
        <div
          ref={resultRef}
          className="max-w-3xl mx-auto px-4 mt-8 space-y-6 pb-12"
        >
          {result.degraded && (
            <div className="bg-surface-container-low rounded-xl px-4 py-3">
              <p className="font-label text-xs tracking-widest uppercase text-outline">
                Match reasoning unavailable — showing strongest O*NET crosswalk
              </p>
            </div>
          )}

          {/* Best match card */}
          {bm && (
            <div className="bg-surface-container-low rounded-2xl p-6 space-y-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <p className="font-label text-xs tracking-widest uppercase text-secondary mb-1">
                    BEST MATCH
                  </p>
                  <h2 className="font-headline font-bold text-2xl uppercase text-on-surface leading-tight">
                    {bm.title}
                  </h2>
                  <p className="font-label text-xs tracking-widest text-outline uppercase mt-1">
                    {bm.code}
                  </p>
                </div>
                {!result.degraded && bm.reasoning?.match_score != null && (
                  <MatchScoreBadge score={bm.reasoning.match_score} />
                )}
              </div>

              {bm.description && (
                <p className="font-body text-sm text-on-surface-variant leading-relaxed">
                  {bm.description}
                </p>
              )}

              {!result.degraded && bm.reasoning?.match_rationale && (
                <div className="pt-3 border-t border-outline-variant">
                  <p className="font-label text-xs tracking-widest uppercase text-primary mb-2">
                    WHY THIS ROLE
                  </p>
                  <p className="font-body text-sm text-on-surface-variant leading-relaxed">
                    {bm.reasoning.match_rationale}
                  </p>
                </div>
              )}

              {!result.degraded &&
                (bm.reasoning?.transferable_skills?.length > 0 ||
                  bm.reasoning?.skill_gaps?.length > 0) && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-outline-variant">
                    {bm.reasoning?.transferable_skills?.length > 0 && (
                      <div>
                        <p className="font-label text-xs tracking-widest uppercase text-secondary mb-2">
                          TRANSFERABLE SKILLS
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {bm.reasoning.transferable_skills.map((skill, i) => (
                            <span
                              key={i}
                              className="bg-secondary/10 text-secondary font-body text-xs px-2 py-1 rounded-sm"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {bm.reasoning?.skill_gaps?.length > 0 && (
                      <div>
                        <p className="font-label text-xs tracking-widest uppercase text-error mb-2">
                          SKILL GAPS
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {bm.reasoning.skill_gaps.map((gap, i) => (
                            <span
                              key={i}
                              className="bg-error/10 text-error font-body text-xs px-2 py-1 rounded-sm"
                            >
                              {gap}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

              {knowledgeTop6.length > 0 && (
                <div className="pt-3 border-t border-outline-variant">
                  <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-2">
                    KEY KNOWLEDGE AREAS
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {knowledgeTop6.map((k, i) => (
                      <span
                        key={i}
                        className="bg-surface-container text-on-surface-variant font-body text-xs px-2 py-1 rounded-sm"
                      >
                        {k.name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {techTop6.length > 0 && (
                <div className="pt-3 border-t border-outline-variant">
                  <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-2">
                    TOP TECHNOLOGY
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {techTop6.map((ex, i) => (
                      <span
                        key={i}
                        className={`font-body text-xs px-2 py-1 rounded-sm ${
                          ex.hot
                            ? "bg-primary/10 text-primary"
                            : "bg-surface-container text-on-surface-variant"
                        }`}
                      >
                        {ex.name}
                        {ex.hot ? " 🔥" : ""}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {bm.outlook?.salary && (
                <div className="pt-3 border-t border-outline-variant">
                  <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-3">
                    SALARY RANGE
                  </p>
                  <div className="grid grid-cols-3 gap-4">
                    {bm.outlook.salary.annual_10th && (
                      <div>
                        <p className="font-label text-xs tracking-widest text-outline uppercase">
                          10TH PCTL
                        </p>
                        <p className="font-headline font-semibold text-lg text-on-surface">
                          $
                          {Number(
                            bm.outlook.salary.annual_10th,
                          ).toLocaleString()}
                        </p>
                      </div>
                    )}
                    {bm.outlook.salary.annual_median && (
                      <div>
                        <p className="font-label text-xs tracking-widest text-outline uppercase">
                          MEDIAN
                        </p>
                        <p className="font-headline font-semibold text-lg text-primary">
                          $
                          {Number(
                            bm.outlook.salary.annual_median,
                          ).toLocaleString()}
                        </p>
                      </div>
                    )}
                    {bm.outlook.salary.annual_90th && (
                      <div>
                        <p className="font-label text-xs tracking-widest text-outline uppercase">
                          90TH PCTL
                        </p>
                        <p className="font-headline font-semibold text-lg text-on-surface">
                          $
                          {Number(
                            bm.outlook.salary.annual_90th,
                          ).toLocaleString()}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {bm.outlook?.category && (
                <div className="flex items-center gap-2 pt-2">
                  <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
                  <span className="font-label text-xs tracking-widest uppercase text-secondary">
                    {bm.outlook.category}
                  </span>
                  {bm.outlook.description && (
                    <span className="font-body text-xs text-on-surface-variant">
                      — {bm.outlook.description}
                    </span>
                  )}
                </div>
              )}

              <div className="pt-4 border-t border-outline-variant">
                <Link
                  to="/resume-builder"
                  className="inline-block mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-6 py-3 rounded-md hover:opacity-90 transition-opacity"
                >
                  TRANSLATE YOUR RESUME FOR THIS ROLE →
                </Link>
              </div>
            </div>
          )}

          {/* Also consider */}
          {result.also_consider?.length > 0 && (
            <div className="space-y-3">
              <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant px-1">
                ALSO CONSIDER
              </p>
              {result.also_consider.map((c) => (
                <div
                  key={c.code}
                  className="bg-surface-container-low rounded-xl p-4"
                >
                  <div className="flex items-start justify-between gap-4 flex-wrap mb-1">
                    <h3 className="font-headline font-semibold text-base uppercase text-on-surface">
                      {c.title}
                    </h3>
                    {!result.degraded && c.match_score != null && (
                      <MatchScoreBadge score={c.match_score} />
                    )}
                  </div>
                  <p className="font-label text-xs tracking-widest text-outline uppercase mb-2">
                    {c.code}
                  </p>
                  {c.match_rationale && (
                    <p className="font-body text-sm text-on-surface-variant">
                      {c.match_rationale}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* O*NET Attribution */}
          <div className="pt-4 border-t border-outline-variant flex items-center gap-3">
            <a
              href="https://services.onetcenter.org/"
              target="_blank"
              rel="noopener noreferrer"
              title="This site incorporates information from O*NET Web Services. Click to learn more."
            >
              <img
                src="https://www.onetcenter.org/image/link/onet-in-it.svg"
                alt="O*NET in-it"
                className="h-7 w-auto opacity-60 hover:opacity-100 transition-opacity"
              />
            </a>
            <p className="font-body text-xs text-outline leading-relaxed">
              Career data from{" "}
              <a
                href="https://services.onetcenter.org/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-tertiary hover:underline"
              >
                O*NET Web Services
              </a>{" "}
              · USDOL/ETA. O*NET® is a trademark of USDOL/ETA.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
