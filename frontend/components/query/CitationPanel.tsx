import type { SourceCitation } from "../../types/source";
import { sourceFileName, truncateSnippet } from "../../types/source";

interface CitationPanelProps {
	sources: SourceCitation[];
}

export function CitationPanel({ sources }: CitationPanelProps): JSX.Element {
	if (!sources.length) {
		return (
			<div className="rounded-xl border border-slate-200 bg-white/80 p-4 text-sm text-slate-500">
				No sources were returned for this response.
			</div>
		);
	}

	return (
		<aside className="space-y-3 rounded-xl border border-slate-300 bg-white/80 p-4 shadow-sm">
			<h3 className="text-sm font-semibold text-slate-900">Sources</h3>
			<ul className="space-y-3">
				{sources.map((source) => (
					<li key={`${source.file_path}:${source.start_line}-${source.end_line}`} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
						<div className="flex flex-wrap items-center justify-between gap-2">
							<p className="text-sm font-medium text-slate-900">{sourceFileName(source.file_path)}</p>
							<p className="text-xs text-slate-600">
								Lines {source.start_line}-{source.end_line}
							</p>
						</div>

						<p className="mt-2 text-xs text-slate-700">{truncateSnippet(source.text)}</p>

						{source.source_url ? (
							<a
								href={source.source_url}
								target="_blank"
								rel="noreferrer"
								className="mt-2 inline-block text-xs font-medium text-cyan-700 underline decoration-cyan-400 hover:text-cyan-900"
							>
								Open source
							</a>
						) : (
							<span className="mt-2 inline-block text-xs text-slate-400">Source URL unavailable</span>
						)}
					</li>
				))}
			</ul>
		</aside>
	);
}
