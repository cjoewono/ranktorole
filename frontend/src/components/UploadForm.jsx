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
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-4">
      <h2 className="font-semibold text-gray-800 text-lg">
        Upload Your Resume
      </h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Resume PDF
        </label>
        <input
          type="file"
          accept=".pdf"
          disabled={isUploaded}
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="block w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Job Description
        </label>
        <textarea
          rows={6}
          value={state.jobDescription}
          onChange={(e) =>
            dispatch({ type: "JD_CHANGED", value: e.target.value })
          }
          placeholder="Paste the job description here..."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      {state.error && <p className="text-red-600 text-sm">{state.error}</p>}

      {!isUploaded ? (
        <button
          onClick={handleUpload}
          disabled={!file || uploading}
          className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
        >
          {uploading ? "Uploading..." : "Upload PDF"}
        </button>
      ) : (
        <div className="flex items-center gap-4">
          <span className="text-green-700 text-sm font-medium">
            ✓ PDF uploaded
          </span>
          <button
            onClick={onGenerateDraft}
            disabled={!(state.jobDescription ?? "").trim()}
            className="bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
          >
            Generate Draft
          </button>
        </div>
      )}
    </div>
  );
}
