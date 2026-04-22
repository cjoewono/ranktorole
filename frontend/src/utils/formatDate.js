/**
 * Format an ISO date string as "Mon DD, YYYY".
 * @param {string} isoString - ISO 8601 date string
 * @param {{ uppercase?: boolean }} options
 * @returns {string}
 */
export function formatDate(isoString, { uppercase = false } = {}) {
  const formatted = new Date(isoString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  return uppercase ? formatted.toUpperCase() : formatted;
}
