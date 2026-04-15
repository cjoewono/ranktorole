import { useState } from "react";
import { uploadResume } from "../api/resumes";

const TIPS = [
  "Include the full job description, not just requirements",
  "Include responsibilities, qualifications, and preferred skills",
  "Focus on quantifiable achievements and keywords from the posting",
];

export default function UploadForm({
  state,
  dispatch,
  onGenerateDraft = () => {},
}) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");

  const isUploaded = state.phase === "UPLOADED";
  const jdLength = (state.jobDescription ?? "").trim().length;
  const canGenerate = isUploaded && jdLength >= 10;

  async function handleUpload() {
    if (!file) return;
    if (file.type !== "application/pdf") {
      dispatch({ type: "ERROR", message: "Only PDF files are accepted." });
      return;
    }
    setUploading(true);
    try {
      const result = await uploadResume(file);
      dispatch({ type: "UPLOADED", resumeId: result.id });
    } catch (err) {
      dispatch({ type: "ERROR", message: err.message });
    } finally {
      setUploading(false);
    }
  }

  function handleGenerateDraft() {
    onGenerateDraft({ jobTitle, company });
  }

  return (
    <div className="bg-surface-container-low p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
        <span className="font-label text-xs tracking-widest uppercase text-secondary">
          UPLOAD RESUME / INITIALIZE
        </span>
      </div>

      <h2 className="font-headline font-bold text-2xl uppercase text-on-surface">
        Upload Your Resume
      </h2>

      {/* PDF upload */}
      <div>
        <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-2">
          Resume PDF
        </label>
        <input
          type="file"
          accept=".pdf"
          disabled={isUploaded}
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="block w-full font-body text-sm text-on-surface-variant
            file:mr-3 file:py-1.5 file:px-4 file:rounded-md file:border-0
            file:font-label file:text-xs file:tracking-widest file:uppercase
            file:mission-gradient file:text-on-primary
            hover:file:opacity-90 disabled:opacity-50 transition-opacity"
        />
        {isUploaded && (
          <p className="font-label text-xs tracking-widest uppercase text-secondary mt-1.5">
            ✓ PDF UPLOADED
          </p>
        )}
      </div>

      {/* Job title + Company row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
            Job Title{" "}
            <span className="normal-case text-on-surface-variant/60">
              (optional)
            </span>
          </label>
          <input
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="e.g. Operations Manager"
            className="tactical-input"
          />
        </div>
        <div>
          <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
            Company / Agency{" "}
            <span className="normal-case text-on-surface-variant/60">
              (optional)
            </span>
          </label>
          <input
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Amazon"
            className="tactical-input"
          />
        </div>
      </div>

      {/* Job description */}
      <div>
        <div className="flex items-baseline justify-between mb-1">
          <label className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
            Target Job Description
          </label>
          <span
            className={`font-label text-xs tabular-nums ${
              jdLength === 0
                ? "text-on-surface-variant/50"
                : jdLength < 10
                  ? "text-error"
                  : jdLength >= 200
                    ? "text-secondary"
                    : "text-on-surface-variant"
            }`}
          >
            {jdLength > 0
              ? jdLength < 10
                ? `${10 - jdLength} more chars needed`
                : `${jdLength} chars`
              : ""}
          </span>
        </div>
        <textarea
          rows={8}
          value={state.jobDescription}
          onChange={(e) =>
            dispatch({ type: "JD_CHANGED", value: e.target.value })
          }
          placeholder="Paste the complete job description here..."
          className="tactical-input resize-none"
        />
      </div>

      {/* Tips panel */}
      <div className="rounded-lg border border-outline-variant/40 bg-surface-container px-4 py-3 space-y-2">
        <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
          Tips for best results
        </p>
        {TIPS.map((tip) => (
          <div key={tip} className="flex items-start gap-2">
            <span className="text-secondary mt-0.5 text-xs">✓</span>
            <span className="font-body text-xs text-on-surface-variant leading-relaxed">
              {tip}
            </span>
          </div>
        ))}
      </div>

      {/* Error */}
      {state.error && (
        <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3 rounded-md">
          {state.error}
        </div>
      )}

      {/* Action buttons */}
      {!isUploaded ? (
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-6 py-2.5 rounded-md disabled:opacity-50 transition-opacity"
        >
          {uploading ? "UPLOADING..." : "UPLOAD PDF"}
        </button>
      ) : (
        <button
          onClick={handleGenerateDraft}
          disabled={!canGenerate}
          className="w-full mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-6 py-3 rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          GENERATE TAILORED RESUME →
        </button>
      )}
    </div>
  );
}
