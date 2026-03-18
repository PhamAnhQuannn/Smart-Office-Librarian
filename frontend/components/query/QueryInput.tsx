"use client";

import { useState, type FormEvent } from "react";

interface QueryInputProps {
  isStreaming: boolean;
  queriesRemaining: number;
  showRateWarning: boolean;
  onSubmit: (query: string, options: { retrievalOnly: boolean }) => Promise<void>;
}

export function QueryInput({
  isStreaming,
  queriesRemaining,
  showRateWarning,
  onSubmit,
}: QueryInputProps): JSX.Element {
  const [query, setQuery] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    if (!query.trim()) {
      setInputError("Please enter a question before submitting.");
      return;
    }
    setInputError(null);
    await onSubmit(query, { retrievalOnly: false });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="relative">
        <textarea
          id="query-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={5}
          disabled={isStreaming}
          placeholder='e.g. "How do we onboard a new engineer?"'
          className="w-full p-6 bg-slate-50 border-2 border-transparent rounded-2xl outline-none focus:bg-white focus:border-teal-500 focus:shadow-xl focus:shadow-teal-500/10 transition-all text-base font-medium resize-none shadow-sm text-slate-900 placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-40"
        />
        <button
          type="submit"
          disabled={isStreaming || !query.trim()}
          className="absolute right-4 bottom-4 px-6 py-2.5 bg-teal-500 text-white font-bold rounded-xl hover:bg-teal-600 transition-all shadow-lg shadow-teal-500/20 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed text-sm"
        >
          {isStreaming ? "Streaming…" : "Ask"}
        </button>
      </div>

      {showRateWarning && (
        <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">
          Rate limit: {queriesRemaining} request{queriesRemaining !== 1 ? "s" : ""} remaining this hour.
        </p>
      )}

      {inputError && (
        <p className="rounded-lg border border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-800" role="alert">
          {inputError}
        </p>
      )}
    </form>
  );
}

