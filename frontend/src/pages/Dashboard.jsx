import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import { deleteTranslation } from "../api/translations";
import { useResumes } from "../context/ResumeContext";
import { exportPDF } from "../utils/pdfExport";

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

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
  return (
    <span className="bg-surface-container-highest text-on-surface-variant font-label text-xs tracking-widest uppercase px-3 py-1 rounded-sm">
      NOT STARTED
    </span>
  );
}

export default function Dashboard() {
  const { resumes, loading, refreshResumes } = useResumes();
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  async function handleDelete(id) {
    try {
      await deleteTranslation(id);
      await refreshResumes();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleNewResume() {
    const inProgress = resumes.find((r) => r.is_finalized === false);
    if (inProgress) {
      navigate(`/resume-builder?id=${inProgress.id}&mode=continue`);
    } else {
      navigate("/resume-builder");
    }
  }

  const finalized = resumes.filter((r) => r.is_finalized).length;
  const inProgress = resumes.filter(
    (r) => !r.is_finalized && (r.roles?.length ?? 0) > 0,
  ).length;

  return (
    <>
      <PageHeader
        label="SYSTEM ACTIVE / CORE_OPERATIONS"
        title="YOUR DEPLOYMENTS"
        action={
          <button
            onClick={handleNewResume}
            className="mission-gradient font-label text-xs tracking-widest font-semibold uppercase text-on-primary px-4 py-2.5 rounded-md transition-opacity hover:opacity-90"
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

        {loading ? (
          <div className="text-center text-on-surface-variant py-16 font-label text-xs tracking-widest uppercase">
            LOADING DEPLOYMENTS...
          </div>
        ) : resumes.length === 0 ? (
          <div className="text-center py-16 space-y-3">
            <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
              No deployments yet.
            </p>
            <Link
              to="/resume-builder"
              className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
            >
              BUILD YOUR FIRST RESUME
            </Link>
          </div>
        ) : (
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
                      onClick={() =>
                        navigate(
                          resume.is_finalized
                            ? `/resume-builder?id=${resume.id}&mode=edit`
                            : `/resume-builder?id=${resume.id}&mode=continue`,
                        )
                      }
                      className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
                    >
                      {resume.is_finalized ? "EDIT" : "CONTINUE"}
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
