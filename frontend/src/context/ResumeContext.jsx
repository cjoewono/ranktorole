import { createContext, useContext, useState, useEffect } from "react";
import { listResumes } from "../api/resumes";

const ResumeContext = createContext(null);

export function ResumeProvider({ children }) {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);

  async function refreshResumes() {
    setLoading(true);
    try {
      const data = await listResumes();
      setResumes(data);
    } catch {
      // silently ignore — consumers can handle empty state
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshResumes();
  }, []);

  return (
    <ResumeContext.Provider value={{ resumes, loading, refreshResumes }}>
      {children}
    </ResumeContext.Provider>
  );
}

// Exposes: { resumes, loading, refreshResumes }
// resumes: the array returned by listTranslations()
// loading: boolean
// refreshResumes: async function that re-fetches and updates resumes
export function useResumes() {
  return useContext(ResumeContext);
}
