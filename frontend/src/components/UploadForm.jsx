import { useState } from "react";
import { uploadResume } from "../api/resumes";

export default function UploadForm({
  state,
  dispatch,
  onGenerateDraft = () => {},
}) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);

  const isUploaded = state.phase === "UPLOADED";

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

  return (
    <div className="bg-surface-container-low p-6 space-y-5">
      {/* Status chip */}
      <div className="flex items-center gap-2 mb-1">
        <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
        <span className="font-label text-xs tracking-widest uppercase text-secondary">
          UPLOAD RESUME / INITIALIZE
        </span>
      </div>

      <h2 className="font-headline font-bold text-2xl uppercase text-on-surface">
        Upload Your Resume
      </h2>

      {/* File input */}
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
      </div>

      {/* Job description */}
      <div>
        <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
          Target Job Description
        </label>
        <textarea
          rows={6}
          value={state.jobDescription}
          onChange={(e) =>
            dispatch({ type: "JD_CHANGED", value: e.target.value })
          }
          placeholder="Paste the job description here..."
          className="tactical-input resize-none"
        />
        {(state.jobDescription ?? "").trim().length > 0 &&
          (state.jobDescription ?? "").trim().length < 10 && (
            <p className="font-label text-xs tracking-widest text-error mt-1">
              {10 - (state.jobDescription ?? "").trim().length} more characters
              needed
            </p>
          )}
      </div>

      {state.error && (
        <div className="bg-error-container text-on-error-container font-body text-sm px-4 py-3">
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
        <div className="flex items-center gap-5">
          <span className="font-label text-xs tracking-widest uppercase text-secondary">
            ✓ PDF UPLOADED
          </span>
          <button
            onClick={onGenerateDraft}
            disabled={(state.jobDescription ?? "").trim().length < 10}
            className="mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-6 py-2.5 rounded-md disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            GENERATE DRAFT
          </button>
        </div>
      )}
    </div>
  );
}
