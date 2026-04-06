import { useState } from "react";

export default function TranslateForm({ onResult, onError }) {
  const [militaryText, setMilitaryText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    onError(null);
    setLoading(true);
    try {
      const { createTranslation } = await import("../api/translations");
      const result = await createTranslation(militaryText, jobDescription);
      onResult(result);
    } catch (err) {
      onError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const charCount = (val) => (
    <span className="text-xs text-gray-400 text-right block mt-1">
      {val.length} / 5000
    </span>
  );

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Military Experience
        </label>
        <textarea
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y min-h-[140px]"
          placeholder="Paste your military job description, duties, or resume text here..."
          value={militaryText}
          onChange={(e) => setMilitaryText(e.target.value)}
          maxLength={5000}
          required
          minLength={10}
        />
        {charCount(militaryText)}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Target Job Description
        </label>
        <textarea
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y min-h-[140px]"
          placeholder="Paste the civilian job posting you are targeting..."
          value={jobDescription}
          onChange={(e) => setJobDescription(e.target.value)}
          maxLength={5000}
          required
          minLength={10}
        />
        {charCount(jobDescription)}
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-700 hover:bg-blue-800 disabled:opacity-50 text-white font-semibold py-2.5 rounded-lg transition-colors"
      >
        {loading ? "Translating..." : "Translate to Civilian"}
      </button>
    </form>
  );
}
