// Shared normalisation for persisted older answers and current API responses.
export function normaliseCitations(text = '') {
  return String(text).replace(/\[SOURCE\s+\d+(?:\s*,\s*(?:SOURCE\s+)?\d+)+\]/gi, (group) =>
    [...group.matchAll(/\d+/g)].map((m) => `[SOURCE ${m[0]}]`).join(' '),
  );
}
export function citedNumbers(text) {
  return new Set(
    [...normaliseCitations(text).matchAll(/\[SOURCE\s+(\d+)\]/gi)].map((m) => Number(m[1])),
  );
}
export function sourceAnchor(scope, number) {
  return `${scope}-source-${number}`;
}
