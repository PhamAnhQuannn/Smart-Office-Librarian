import { ExternalLink } from "lucide-react";
import type { SourceCitation } from "../../types/source";
import { sourceFileName } from "../../types/source";

interface CitationPanelProps {
  sources: SourceCitation[];
}

export function CitationPanel({ sources }: CitationPanelProps): JSX.Element {
  if (!sources.length) return <></>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {sources.map((source) => (
        <div
          key={`${source.file_path}:${source.start_line}-${source.end_line}`}
          className="bg-white border border-slate-100 p-5 rounded-xl shadow-sm hover:shadow-md transition-all border-l-4 border-l-teal-500 group"
        >
          <div className="flex items-start justify-between gap-2 mb-2">
            <p className="font-bold text-slate-900 text-sm truncate">
              {sourceFileName(source.file_path)}
            </p>
            <span className="text-xs font-bold text-slate-400 shrink-0">
              L{source.start_line}–{source.end_line}
            </span>
          </div>

          <p className="text-xs text-slate-500 italic mb-4 line-clamp-2">
            &ldquo;{source.text.slice(0, 140)}{source.text.length > 140 ? "…" : ""}&rdquo;
          </p>

          {source.source_url ? (
            <a
              href={source.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-teal-600 text-xs font-black uppercase tracking-wide hover:underline group-hover:text-teal-700"
            >
              Open source <ExternalLink size={11} />
            </a>
          ) : (
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(source.file_path)}
              className="text-slate-400 text-xs font-black uppercase tracking-wide hover:text-slate-600 transition-colors"
            >
              Copy path
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

