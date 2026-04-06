import { useState } from "react";
import NavBar from "../components/NavBar";
import TranslateForm from "../components/TranslateForm";
import ResumeOutput from "../components/ResumeOutput";

export default function Translator() {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar />
      <main className="max-w-2xl mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">
          Military-to-Civilian Translator
        </h1>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3 mb-6">
            {error}
          </div>
        )}

        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <TranslateForm onResult={setResult} onError={setError} />
        </div>

        <ResumeOutput result={result} />
      </main>
    </div>
  );
}
