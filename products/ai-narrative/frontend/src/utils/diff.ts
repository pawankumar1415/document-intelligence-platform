export type DiffPart = { value: string; added?: boolean; removed?: boolean };

export function wordDiff(oldText: string, newText: string): DiffPart[] {
  if (!oldText && !newText) return [];
  if (!oldText) return [{ value: newText, added: true }];
  if (!newText) return [{ value: oldText, removed: true }];

  const tokenize = (t: string): string[] => {
    const parts: string[] = [];
    let i = 0;
    while (i < t.length) {
      const isWs = /\s/.test(t[i]);
      let j = i + 1;
      while (j < t.length && /\s/.test(t[j]) === isWs) j++;
      parts.push(t.slice(i, j));
      i = j;
    }
    return parts;
  };

  const ot = tokenize(oldText);
  const nt = tokenize(newText);
  const m = ot.length;
  const n = nt.length;

  // Fall back to side-by-side for very large texts
  if (m * n > 200_000) {
    return [
      { value: oldText, removed: true },
      { value: " → ", },
      { value: newText, added: true },
    ];
  }

  // LCS dynamic programming
  const dp = Array.from({ length: m + 1 }, () => new Int32Array(n + 1));
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        ot[i - 1] === nt[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);
    }
  }

  // Backtrack to build diff parts
  const parts: DiffPart[] = [];
  let i = m;
  let j = n;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && ot[i - 1] === nt[j - 1]) {
      parts.unshift({ value: ot[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      parts.unshift({ value: nt[j - 1], added: true });
      j--;
    } else {
      parts.unshift({ value: ot[i - 1], removed: true });
      i--;
    }
  }

  // Merge consecutive same-type parts
  const merged: DiffPart[] = [];
  for (const part of parts) {
    const last = merged[merged.length - 1];
    if (
      last &&
      !!last.added === !!part.added &&
      !!last.removed === !!part.removed
    ) {
      last.value += part.value;
    } else {
      merged.push({ ...part });
    }
  }

  return merged;
}