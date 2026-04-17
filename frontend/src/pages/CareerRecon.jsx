import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import {
  searchMilitaryCareers,
  getCareerDetail,
  enrichCareer,
} from "../api/onet";

const loadingKeyframes = `
@keyframes loading {
  0% { transform: translateX(-100%); }
  50% { transform: translateX(60%); }
  100% { transform: translateX(200%); }
}
`;

const BRANCHES = [
  { value: "all", label: "All Branches" },
  { value: "army", label: "Army" },
  { value: "navy", label: "Navy" },
  { value: "air_force", label: "Air Force" },
  { value: "marine_corps", label: "Marines" },
  { value: "coast_guard", label: "Coast Guard" },
];

function MatchBadge({ matchType }) {
  const styles = {
    most_duties: "bg-secondary/10 text-secondary",
    some_duties: "bg-primary/10 text-primary",
    crosswalk: "bg-surface-container-highest text-on-surface-variant",
    keyword: "bg-surface-container-highest text-on-surface-variant",
  };
  const labels = {
    most_duties: "STRONG MATCH",
    some_duties: "PARTIAL MATCH",
    crosswalk: "CROSSWALK",
    keyword: "KEYWORD",
  };

  return (
    <span
      className={`font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm ${styles[matchType] || styles.keyword}`}
    >
      {labels[matchType] || matchType?.toUpperCase() || "MATCH"}
    </span>
  );
}

function TagBadge({ label, active }) {
  if (!active) return null;
  return (
    <span className="bg-tertiary/10 text-tertiary font-label text-xs tracking-widest uppercase px-2 py-0.5 rounded-sm">
      {label}
    </span>
  );
}

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

export default function CareerRecon() {
  // Search state
  const [keyword, setKeyword] = useState("");
  const [branch, setBranch] = useState("all");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);

  // Results state
  const [results, setResults] = useState(null);

  // Detail state
  const [selectedCode, setSelectedCode] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [enrichment, setEnrichment] = useState(null);
  const [enrichError, setEnrichError] = useState(null);
  const latestClickRef = useRef(null);

  const phase = detail ? "DETAIL" : results ? "RESULTS" : "SEARCH";

  async function handleSearch(e) {
    e.preventDefault();
    if (!keyword.trim()) return;
    setSearching(true);
    setSearchError(null);
    setDetail(null);
    setSelectedCode(null);

    try {
      const data = await searchMilitaryCareers(keyword.trim(), branch);
      if (data.careers?.length > 0) {
        setResults(data);
      } else {
        setResults(null);
        setSearchError(
          `No civilian career matches found for "${keyword.trim()}". Try a different code or broaden the branch filter.`,
        );
      }
    } catch (err) {
      setResults(null);
      setSearchError(err.message || "Search failed. Please try again.");
    } finally {
      setSearching(false);
    }
  }

  async function handleCareerClick(onetCode) {
    latestClickRef.current = onetCode;
    setSelectedCode(onetCode);
    setLoadingDetail(true);
    setEnrichment(null);
    setEnrichError(null);
    setDetail(null);

    const [careerResult, enrichResult] = await Promise.allSettled([
      getCareerDetail(onetCode),
      enrichCareer(onetCode),
    ]);

    // Ignore if user clicked a different career while this fetch was in flight
    if (latestClickRef.current !== onetCode) return;

    if (careerResult.status === "fulfilled") {
      setDetail(careerResult.value);
    } else {
      setSelectedCode(null);
      setLoadingDetail(false);
      return;
    }

    if (enrichResult.status === "fulfilled") {
      setEnrichment(enrichResult.value?.enrichment ?? null);
    } else {
      setEnrichError("Personalized analysis unavailable.");
    }

    setLoadingDetail(false);
  }

  function handleBackToResults() {
    setDetail(null);
    setSelectedCode(null);
    setEnrichment(null);
    setEnrichError(null);
  }

  function handleNewSearch() {
    setResults(null);
    setDetail(null);
    setSelectedCode(null);
    setEnrichment(null);
    setEnrichError(null);
    setKeyword("");
    setBranch("all");
  }

  return (
    <>
      <style>{loadingKeyframes}</style>
      <PageHeader
        label={
          phase === "DETAIL"
            ? "RECON / CAREER_DETAIL"
            : phase === "RESULTS"
              ? "RECON / SEARCH_RESULTS"
              : "RECON / INITIALIZE"
        }
        title={
          phase === "DETAIL"
            ? detail?.title?.toUpperCase() || "CAREER DETAIL"
            : "CAREER RECON"
        }
        action={
          phase !== "SEARCH" ? (
            <button
              onClick={
                phase === "DETAIL" ? handleBackToResults : handleNewSearch
              }
              className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
            >
              {phase === "DETAIL" ? "← RESULTS" : "← NEW SEARCH"}
            </button>
          ) : null
        }
      />

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* ─── SEARCH PHASE ─── */}
        {phase === "SEARCH" && (
          <div className="max-w-lg mx-auto space-y-6">
            <div className="bg-surface-container-low p-6 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
                <span className="font-label text-xs tracking-widest uppercase text-secondary">
                  O*NET VETERANS DATABASE
                </span>
              </div>
              <p className="font-body text-sm text-on-surface-variant">
                Enter your military occupation code or job title. We'll search
                the Department of Labor's veterans career database for matching
                civilian careers with salary data, required skills, and
                transition guidance.
              </p>

              <form onSubmit={handleSearch} className="space-y-4">
                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    MOS / Rating / AFSC
                  </label>
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="e.g., 11B, IT2, 3D0X4, Infantryman"
                    className="tactical-input"
                    required
                  />
                </div>

                <div>
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Service Branch
                  </label>
                  <select
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    className="tactical-input appearance-none cursor-pointer"
                  >
                    {BRANCHES.map((b) => (
                      <option key={b.value} value={b.value}>
                        {b.label}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={searching || !keyword.trim()}
                  className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
                >
                  {searching ? "SCANNING..." : "SEARCH CAREERS"}
                </button>
              </form>

              {searchError && (
                <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
                  {searchError}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ─── RESULTS PHASE ─── */}
        {phase === "RESULTS" && results && (
          <div className="space-y-4">
            {/* Military match confirmation */}
            {results.military_matches?.length > 0 && (
              <div className="bg-surface-container-low p-4 flex items-center gap-3">
                <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
                <span className="font-label text-xs tracking-widest uppercase text-secondary">
                  MATCH CONFIRMED
                </span>
                <span className="font-body text-sm text-on-surface">
                  {results.military_matches[0].title}
                  {results.military_matches[0].branch
                    ? ` · ${results.military_matches[0].branch.toUpperCase()}`
                    : ""}
                </span>
              </div>
            )}

            {/* Inline search bar for refinement */}
            <form
              onSubmit={handleSearch}
              className="bg-surface-container-low p-4 space-y-3"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
                <span className="font-label text-xs tracking-widest uppercase text-secondary">
                  SEARCH
                </span>
              </div>
              <div className="flex gap-2">
                <div className="flex-1">
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    MOS / Rating / AFSC
                  </label>
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="e.g., 11B, IT2, 3D0X4"
                    className="tactical-input w-full"
                    required
                  />
                </div>
                <div className="w-40">
                  <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                    Branch
                  </label>
                  <select
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    className="tactical-input appearance-none cursor-pointer w-full"
                  >
                    {BRANCHES.map((b) => (
                      <option key={b.value} value={b.value}>
                        {b.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    type="submit"
                    disabled={searching || !keyword.trim()}
                    className="mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-xs px-6 py-3 rounded-md hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {searching ? "..." : "GO"}
                  </button>
                </div>
              </div>
            </form>

            {loadingDetail && (
              <div className="bg-surface-container-low p-4 flex items-center gap-3">
                <div className="w-full">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="inline-block w-2 h-2 rounded-full bg-primary animate-pulse" />
                    <span className="font-label text-xs tracking-widest uppercase text-primary">
                      LOADING CAREER INTEL
                    </span>
                  </div>
                  <div className="w-full bg-surface-container-highest rounded-full h-1 overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full animate-[loading_1.5s_ease-in-out_infinite]"
                      style={{ width: "60%" }}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Empty state */}
            {results.careers?.length === 0 && (
              <div className="bg-surface-container-low p-6 text-center">
                <p className="font-body text-sm text-on-surface-variant">
                  No civilian career matches found for "{results.keyword}". Try
                  a different code or broaden the branch filter.
                </p>
              </div>
            )}

            {/* Career cards */}
            <div
              className={`space-y-2 ${searching ? "opacity-40 pointer-events-none" : ""}`}
            >
              {results.careers?.map((career) => (
                <button
                  key={career.code}
                  onClick={() => handleCareerClick(career.code)}
                  disabled={loadingDetail && selectedCode === career.code}
                  className={`w-full text-left bg-surface-container-low p-4 hover:bg-surface-container transition-colors group ${loadingDetail && selectedCode === career.code ? "opacity-60" : ""}`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 flex-wrap mb-1">
                        <h3 className="font-headline font-semibold text-base uppercase text-on-surface">
                          {career.title}
                        </h3>
                        <MatchBadge matchType={career.match_type} />
                        <TagBadge
                          label="BRIGHT OUTLOOK"
                          active={career.tags?.bright_outlook}
                        />
                        <TagBadge
                          label="APPRENTICESHIP"
                          active={career.tags?.apprenticeship}
                        />
                      </div>
                      <div className="flex items-center gap-4 mt-1">
                        <span className="font-label text-xs tracking-widest text-outline uppercase">
                          {career.code}
                        </span>
                        {career.pay_grade && (
                          <span className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
                            MIN GRADE: {career.pay_grade}
                          </span>
                        )}
                        {career.preparation_needed && (
                          <span className="font-label text-xs tracking-widest text-on-surface-variant uppercase">
                            PREP: {career.preparation_needed}
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="text-outline-variant group-hover:text-on-surface-variant transition-colors shrink-0 mt-1">
                      {loadingDetail && selectedCode === career.code
                        ? "..."
                        : "→"}
                    </span>
                  </div>
                </button>
              ))}
            </div>

            {/* Funnel CTA */}
            <div className="bg-surface-container-low p-6 text-center space-y-3 mt-6">
              <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                FOUND A TARGET ROLE?
              </p>
              <Link
                to="/resume-builder"
                className="inline-block mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-8 py-3 rounded-md hover:opacity-90 transition-opacity"
              >
                TRANSLATE YOUR RESUME →
              </Link>
            </div>
          </div>
        )}

        {/* ─── DETAIL PHASE ─── */}
        {phase === "DETAIL" && detail && (
          <div className="space-y-6">
            {/* Enrichment — Claude Haiku personalized analysis */}
            {enrichment && (
              <div className="bg-surface-container-low p-6 space-y-4">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary inline-block" />
                    <span className="font-label text-xs tracking-widest uppercase text-primary">
                      PERSONALIZED CAREER INTELLIGENCE
                    </span>
                  </div>
                  <MatchScoreBadge score={enrichment.match_score ?? 0} />
                </div>

                <p className="font-body text-sm text-on-surface-variant leading-relaxed">
                  {enrichment.personalized_description}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <p className="font-label text-xs tracking-widest uppercase text-secondary">
                      <span className="text-secondary mr-1">✓</span>
                      TRANSFERABLE SKILLS
                    </p>
                    <div className="space-y-1">
                      {(enrichment.transferable_skills ?? []).map((skill, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span className="text-secondary shrink-0 mt-0.5 text-xs">✓</span>
                          <span className="font-body text-sm text-on-surface">{skill}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-2">
                    <p className="font-label text-xs tracking-widest uppercase text-error">
                      <span className="text-error mr-1">△</span>
                      SKILL GAPS TO BRIDGE
                    </p>
                    <div className="space-y-1">
                      {(enrichment.skill_gaps ?? []).map((gap, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span className="text-error shrink-0 mt-0.5 text-xs">△</span>
                          <span className="font-body text-sm text-on-surface">{gap}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-outline-variant space-y-1">
                  <p className="font-label text-xs tracking-widest uppercase text-tertiary">
                    <span className="text-tertiary mr-1">◆</span>
                    EDUCATION PATH
                  </p>
                  <p className="font-body text-sm text-on-surface-variant">
                    {enrichment.education_recommendation}
                  </p>
                </div>
              </div>
            )}

            {enrichError && !enrichment && (
              <div className="bg-surface-container-low px-4 py-3 font-body text-sm text-on-surface-variant">
                {enrichError} Showing O*NET data only.
              </div>
            )}

            {/* Overview */}
            <div className="bg-surface-container-low p-6 space-y-3">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="font-label text-xs tracking-widest text-outline uppercase">
                  {detail.code}
                </span>
                <TagBadge
                  label="BRIGHT OUTLOOK"
                  active={detail.tags?.bright_outlook}
                />
              </div>
              {detail.description && (
                <p className="font-body text-sm text-on-surface-variant leading-relaxed">
                  {detail.description}
                </p>
              )}
            </div>

            {/* Salary & Outlook */}
            {detail.outlook &&
              (detail.outlook.category || detail.outlook.salary) && (
                <div className="bg-surface-container-low p-6 space-y-3">
                  <h2 className="font-headline font-semibold text-sm uppercase text-on-surface tracking-wide">
                    Job Outlook & Salary
                  </h2>
                  {detail.outlook.category && (
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
                      <span className="font-label text-xs tracking-widest uppercase text-secondary">
                        {detail.outlook.category}
                      </span>
                    </div>
                  )}
                  {detail.outlook.description && (
                    <p className="font-body text-sm text-on-surface-variant">
                      {detail.outlook.description}
                    </p>
                  )}
                  {detail.outlook.salary && (
                    <div className="grid grid-cols-3 gap-4 mt-2">
                      {detail.outlook.salary.annual_10th && (
                        <div>
                          <p className="font-label text-xs tracking-widest text-outline uppercase">
                            10TH PCTL
                          </p>
                          <p className="font-headline font-semibold text-lg text-on-surface">
                            $
                            {Number(
                              detail.outlook.salary.annual_10th,
                            ).toLocaleString()}
                          </p>
                        </div>
                      )}
                      {detail.outlook.salary.annual_median && (
                        <div>
                          <p className="font-label text-xs tracking-widest text-outline uppercase">
                            MEDIAN
                          </p>
                          <p className="font-headline font-semibold text-lg text-primary">
                            $
                            {Number(
                              detail.outlook.salary.annual_median,
                            ).toLocaleString()}
                          </p>
                        </div>
                      )}
                      {detail.outlook.salary.annual_90th && (
                        <div>
                          <p className="font-label text-xs tracking-widest text-outline uppercase">
                            90TH PCTL
                          </p>
                          <p className="font-headline font-semibold text-lg text-on-surface">
                            $
                            {Number(
                              detail.outlook.salary.annual_90th,
                            ).toLocaleString()}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

            {/* Skills */}
            {detail.skills?.length > 0 && (
              <div className="bg-surface-container-low p-6 space-y-3">
                <h2 className="font-headline font-semibold text-sm uppercase text-on-surface tracking-wide">
                  Key Skills
                </h2>
                <div className="space-y-2">
                  {detail.skills.map((s) => (
                    <div key={s.name} className="flex items-start gap-2">
                      <span className="text-secondary shrink-0 mt-0.5">✓</span>
                      <div>
                        <span className="font-body text-sm font-medium text-on-surface">
                          {s.name}
                        </span>
                        {s.description && (
                          <span className="font-body text-sm text-on-surface-variant">
                            {" — "}
                            {s.description}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Knowledge */}
            {detail.knowledge?.length > 0 && (
              <div className="bg-surface-container-low p-6 space-y-3">
                <h2 className="font-headline font-semibold text-sm uppercase text-on-surface tracking-wide">
                  Knowledge Areas
                </h2>
                <div className="space-y-2">
                  {detail.knowledge.map((k) => (
                    <div key={k.name} className="flex items-start gap-2">
                      <span className="text-primary shrink-0 mt-0.5">◆</span>
                      <div>
                        <span className="font-body text-sm font-medium text-on-surface">
                          {k.name}
                        </span>
                        {k.description && (
                          <span className="font-body text-sm text-on-surface-variant">
                            {" — "}
                            {k.description}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Technology */}
            {detail.technology?.length > 0 && (
              <div className="bg-surface-container-low p-6 space-y-3">
                <h2 className="font-headline font-semibold text-sm uppercase text-on-surface tracking-wide">
                  Technology Skills
                </h2>
                <div className="space-y-4">
                  {detail.technology.map((cat) => (
                    <div key={cat.category}>
                      <p className="font-label text-xs tracking-widest text-on-surface-variant uppercase mb-1">
                        {cat.category}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        {cat.examples.map((ex) => (
                          <span
                            key={ex.name}
                            className={`font-body text-xs px-2 py-1 rounded-sm ${
                              ex.hot
                                ? "bg-primary/10 text-primary"
                                : "bg-surface-container text-on-surface-variant"
                            }`}
                          >
                            {ex.name}
                            {ex.hot && " 🔥"}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Funnel CTA */}
            <div className="bg-surface-container-low p-6 text-center space-y-3">
              <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
                READY TO TARGET THIS ROLE?
              </p>
              <Link
                to="/resume-builder"
                className="inline-block mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-8 py-3 rounded-md hover:opacity-90 transition-opacity"
              >
                TRANSLATE YOUR RESUME FOR THIS ROLE →
              </Link>
            </div>
          </div>
        )}
        {/* O*NET Attribution */}
        <div className="mt-8 pt-4 border-t border-outline-variant flex items-center gap-3">
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
      </main>
    </>
  );
}
