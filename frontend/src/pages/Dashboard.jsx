import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import NavBar from "../components/NavBar";
import { listTranslations, deleteTranslation } from "../api/translations";

/*
 * ResumeBuilder re-entry contract (for Agent 1 to implement):
 *
 * Dashboard navigates to /resume-builder with these URL params:
 *   ?id={uuid}&mode=continue  → load resume from GET /api/v1/resumes/{id}/
 *                                restore draft.roles, chatHistory display from resume.chat_history
 *                                set phase = "REVIEWING"
 *   ?id={uuid}&mode=edit      → load resume from GET /api/v1/resumes/{id}/
 *                                restore draft.roles, aiInitialDraft from resume.ai_initial_draft
 *                                set phase = "FINALIZING"
 *   (no params)               → fresh session, phase = "IDLE"
 *
 * ResumeBuilder should call getResume(id) on mount when id param is present.
 */

function StatusBadge({ resume }) {
  if (resume.is_finalized) {
    return (
      <span className="bg-emerald-100 text-emerald-700 text-xs font-semibold px-3 py-1 rounded-full">
        Finalized
      </span>
    );
  }
  if (resume.roles?.length > 0) {
    return (
      <span className="bg-amber-100 text-amber-700 text-xs font-semibold px-3 py-1 rounded-full">
        In Progress
      </span>
    );
  }
  return (
    <span className="bg-slate-100 text-slate-600 text-xs font-semibold px-3 py-1 rounded-full">
      Not Started
    </span>
  );
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function Dashboard() {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    listTranslations()
      .then(setResumes)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(id) {
    try {
      await deleteTranslation(id);
      setResumes((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <NavBar />
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold text-slate-900">Your Resumes</h1>
          <Link
            to="/resume-builder"
            className="bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            New Resume
          </Link>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3 mb-6">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center text-slate-400 py-16 text-sm">
            Loading...
          </div>
        ) : resumes.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <p className="text-slate-400 text-sm">No resumes yet.</p>
            <Link
              to="/resume-builder"
              className="text-blue-600 text-sm hover:underline"
            >
              Build your first resume
            </Link>
          </div>
        ) : (
          <ul className="space-y-4">
            {resumes.map((resume) => (
              <li
                key={resume.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    {/* Title + status badge */}
                    <div className="flex items-center gap-2 flex-wrap">
                      {resume.civilian_title ? (
                        <h2 className="font-bold text-slate-900 truncate">
                          {resume.civilian_title}
                        </h2>
                      ) : (
                        <h2 className="font-bold text-slate-400 italic truncate">
                          Untitled Resume
                        </h2>
                      )}
                      <StatusBadge resume={resume} />
                    </div>

                    {/* Summary — one line, truncated */}
                    {resume.summary && (
                      <p className="text-sm text-slate-500 mt-1 truncate">
                        {resume.summary}
                      </p>
                    )}

                    {/* Created date */}
                    <p className="text-xs text-slate-400 mt-2">
                      {formatDate(resume.created_at)}
                    </p>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 shrink-0">
                    {resume.is_finalized ? (
                      <button
                        onClick={() =>
                          navigate(`/resume-builder?id=${resume.id}&mode=edit`)
                        }
                        className="border border-blue-600 text-blue-600 hover:bg-blue-50 text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors"
                      >
                        Edit &amp; Export
                      </button>
                    ) : (
                      <button
                        onClick={() =>
                          navigate(
                            `/resume-builder?id=${resume.id}&mode=continue`,
                          )
                        }
                        className="bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors"
                      >
                        Continue
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(resume.id)}
                      className="text-red-400 hover:text-red-600 text-sm transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
