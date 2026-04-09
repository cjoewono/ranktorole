/**
 * Word-level LCS diff.
 * Returns [{type: 'equal'|'removed'|'added', value: string}]
 * 'removed' = in original only  → render strikethrough red
 * 'added'   = in current only   → render amber
 */
function computeLCS(a, b) {
  const m = a.length,
    n = b.length;
  const dp = Array.from({ length: m + 1 }, () => new Int32Array(n + 1));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }
  const result = [];
  let i = m,
    j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && a[i - 1] === b[j - 1]) {
      result.unshift({ type: "equal", value: a[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ type: "added", value: b[j - 1] });
      j--;
    } else {
      result.unshift({ type: "removed", value: a[i - 1] });
      i--;
    }
  }
  return result;
}

export function diffWords(original, current) {
  const a = original.trim().split(/\s+/).filter(Boolean);
  const b = current.trim().split(/\s+/).filter(Boolean);
  return computeLCS(a, b);
}
