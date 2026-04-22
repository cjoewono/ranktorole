import { useState } from "react";
import { useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { deleteResume, reopenResume } from "../api/resumes";
import { useResumes } from "../context/ResumeContext";
import { exportPDF } from "../utils/pdfExport";
import { formatDate } from "../utils/formatDate";

function StatusBadge({ resume }) {
  if (resume.is_finalized) {
    return (
      <span className="bg-secondary/10 text-secondary font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm">
        FINALIZED
      </span>
    );
  }
  if (resume.roles?.length > 0) {
    return (
      <span className="bg-primary/10 text-primary font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm">
        IN PROGRESS
      </span>
    );
  }
  // Pre-draft: PDF uploaded, no draft yet. CONTINUE routes to UPLOADED
  // phase where the user can paste a JD and finish the generate flow.
  return (
    <span className="bg-tertiary/10 text-tertiary font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm">
      UPLOADED
    </span>
  );
}

export default function Dashboard() {
  const { resumes, loading, refreshResumes } = useResumes();
  const [error, setError] = useState(null);
  const [reopeningId, setReopeningId] = useState(null);
  const navigate = useNavigate();

  async function handleDelete(id) {
    try {
      await deleteResume(id);
      await refreshResumes();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleOpen(resume) {
    // Not finalized → continue, no server mutation
    if (!resume.is_finalized) {
      navigate(`/resume-builder?id=${resume.id}&mode=continue`);
      return;
    }
    // Finalized → reopen on the server FIRST (explicit user action),
    // then navigate. Replaces the old mount-effect reopen that fired
    // on every remount with ?mode=edit in the URL.
    setReopeningId(resume.id);
    setError(null);
    try {
      await reopenResume(resume.id);
      await refreshResumes();
      navigate(`/resume-builder?id=${resume.id}&mode=edit`);
    } catch (err) {
      setError(err.message || "Could not reopen this resume. Try again.");
    } finally {
      setReopeningId(null);
    }
  }

  function handleNewResume() {
    navigate("/resume-builder?new=1");
  }

  const finalized = resumes.filter((r) => r.is_finalized).length;
  // "In progress" now includes pre-draft orphans (uploaded PDF, no draft
  // yet) — these show the UPLOADED badge and resume via CONTINUE.
  const inProgress = resumes.filter((r) => !r.is_finalized).length;

  return (
    <>
      <PageHeader
        label="SYSTEM ACTIVE / CORE_OPERATIONS"
        title="YOUR DEPLOYMENTS"
        action={
          <button
            onClick={handleNewResume}
            className="mission-gradient font-label text-sm tracking-widest font-semibold uppercase text-on-primary px-6 py-3 rounded-md transition-opacity hover:opacity-90"
          >
            + NEW RESUME
          </button>
        }
      />

      <main className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {error && (
          <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
            {error}
          </div>
        )}

        <div className="grid grid-cols-3 gap-3">
          <div className="bg-surface-container-low p-4">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
              Total
            </p>
            <p className="font-headline font-bold text-4xl text-on-surface">
              {resumes.length}
            </p>
          </div>
          <div className="bg-surface-container-low p-4">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
              Finalized
            </p>
            <p className="font-headline font-bold text-4xl text-secondary">
              {finalized}
            </p>
          </div>
          <div className="bg-surface-container-low p-4">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
              In Progress
            </p>
            <p className="font-headline font-bold text-4xl text-primary">
              {inProgress}
            </p>
          </div>
        </div>

        {!loading && !resumes.some((r) => !r.is_finalized) && (
          <button
            onClick={handleNewResume}
            className="w-full bg-surface-container-low border border-primary/20 p-6 text-left hover:bg-surface-container transition-colors group"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-label text-xs tracking-widest uppercase text-primary mb-1">
                  READY FOR YOUR NEXT MISSION?
                </p>
                <p className="font-headline font-semibold text-lg text-on-surface">
                  Translate your military experience into a civilian resume
                </p>
                <p className="font-body text-sm text-on-surface-variant mt-1">
                  Upload your military resume and target a job description — AI
                  handles the translation.
                </p>
              </div>
              <span className="text-primary text-2xl group-hover:translate-x-1 transition-transform shrink-0 ml-4">
                →
              </span>
            </div>
          </button>
        )}

        {loading ? (
          <div className="text-center text-on-surface-variant py-16 font-label text-xs tracking-widest uppercase">
            LOADING DEPLOYMENTS...
          </div>
        ) : resumes.length === 0 ? null : (
          <ul className="space-y-3">
            {resumes.map((resume) => (
              <li key={resume.id} className="bg-surface-container p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 min-w-0 flex-1">
                    <div className="shrink-0 w-8 h-10 bg-surface-container-highest rounded-sm flex items-center justify-center mt-0.5">
                      <span className="text-on-surface-variant text-xs">▤</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        {resume.civilian_title ? (
                          <h2 className="font-headline font-semibold text-on-surface uppercase truncate">
                            {resume.civilian_title}
                          </h2>
                        ) : (
                          <h2 className="font-headline font-semibold text-on-surface-variant uppercase italic truncate">
                            UNTITLED RESUME
                          </h2>
                        )}
                        <StatusBadge resume={resume} />
                      </div>
                      {resume.summary && (
                        <p className="font-body text-sm text-on-surface-variant truncate">
                          {resume.summary}
                        </p>
                      )}
                      <p className="font-label text-xs tracking-widest uppercase text-outline mt-2">
                        {formatDate(resume.created_at)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <button
                      onClick={() => handleOpen(resume)}
                      disabled={reopeningId === resume.id}
                      className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors disabled:opacity-50"
                    >
                      {reopeningId === resume.id
                        ? "OPENING..."
                        : resume.is_finalized
                          ? "EDIT"
                          : "CONTINUE"}
                    </button>
                    {resume.is_finalized && (
                      <button
                        onClick={() =>
                          exportPDF({
                            civilian_title: resume.civilian_title,
                            summary: resume.summary,
                            roles: resume.roles ?? [],
                          })
                        }
                        className="font-label text-xs tracking-widest uppercase text-secondary hover:opacity-80 transition-opacity"
                      >
                        EXPORT PDF
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(resume.id)}
                      className="font-label text-xs tracking-widest uppercase text-error hover:opacity-80 transition-opacity"
                    >
                      DELETE
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </main>
    </>
  );
}
