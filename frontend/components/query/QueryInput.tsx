"use client";

import { useMemo, useState, type FormEvent } from "react";

interface QueryInputProps {
	isStreaming: boolean;
	queriesRemaining: number;
	showRateWarning: boolean;
	onSubmit: (query: string, options: { retrievalOnly: boolean }) => Promise<void>;
}

const USD_PER_1K_TOKENS_ESTIMATE = 0.0003;

export function QueryInput({
	isStreaming,
	queriesRemaining,
	showRateWarning,
	onSubmit,
}: QueryInputProps): JSX.Element {
	const [query, setQuery] = useState("");
	const [retrievalOnly, setRetrievalOnly] = useState(false);
	const [inputError, setInputError] = useState<string | null>(null);

	const estimatedTokens = useMemo(() => Math.ceil(query.trim().length / 4), [query]);
	const estimatedCost = useMemo(() => ((estimatedTokens / 1000) * USD_PER_1K_TOKENS_ESTIMATE).toFixed(4), [estimatedTokens]);

	const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
		event.preventDefault();

		if (!query.trim()) {
			setInputError("Please enter a question before submitting.");
			return;
		}

		setInputError(null);
		await onSubmit(query, { retrievalOnly });
	};

	return (
		<form onSubmit={handleSubmit} className="space-y-3 rounded-2xl border border-slate-300 bg-white/90 p-5 shadow-sm">
			<label htmlFor="query-input" className="block text-sm font-semibold text-slate-900">
				Ask the Librarian
			</label>

			<textarea
				id="query-input"
				value={query}
				onChange={(event) => setQuery(event.target.value)}
				rows={5}
				disabled={isStreaming}
				placeholder="Example: Where is the official process for restoring the database after a failed deploy?"
				className="w-full rounded-xl border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-900 shadow-inner outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-200 disabled:cursor-not-allowed disabled:opacity-70"
			/>

			<div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
				<label className="inline-flex items-center gap-2">
					<input
						type="checkbox"
						checked={retrievalOnly}
						onChange={(event) => setRetrievalOnly(event.target.checked)}
						disabled={isStreaming}
						className="h-4 w-4 rounded border-slate-400 text-cyan-700"
					/>
					Retrieval-only mode
				</label>

				<div className="flex items-center gap-3">
					<span>Estimated tokens: {estimatedTokens}</span>
					<span>Estimated cost: ${estimatedCost}</span>
				</div>
			</div>

			{showRateWarning ? (
				<p className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1 text-xs text-amber-900">
					Rate warning: only {queriesRemaining} request(s) remain in the current local hour window.
				</p>
			) : null}

			{inputError ? (
				<p className="rounded-md border border-rose-300 bg-rose-50 px-2 py-1 text-xs text-rose-800">{inputError}</p>
			) : null}

			<button
				type="submit"
				disabled={isStreaming}
				className="inline-flex items-center rounded-lg bg-cyan-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-cyan-800 disabled:cursor-not-allowed disabled:bg-slate-400"
			>
				{isStreaming ? "Streaming..." : "Send Query"}
			</button>
		</form>
	);
}
