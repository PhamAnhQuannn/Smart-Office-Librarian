/**
 * Merge Tailwind / plain CSS class strings, filtering out falsy values.
 * Drop-in compatible with the shadcn/ui `cn()` convention.
 */
export function cn(...inputs: (string | undefined | null | false)[]): string {
  return inputs.filter(Boolean).join(" ");
}

/** Format an ISO date string to a human-readable short form. */
export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

/** Truncate a string to `max` characters, appending … if needed. */
export function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1)}…`;
}

/** Sleep for `ms` milliseconds (useful in tests / retry helpers). */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
