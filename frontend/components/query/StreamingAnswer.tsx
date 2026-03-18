import { ChevronDown, ShieldCheck } from "lucide-react";
import { useState } from "react";
import type { ConfidenceLevel, QueryMode, RefusalReason } from "../../types/api";
import type { SourceCitation } from "../../types/source";
import { CitationPanel } from "./CitationPanel";

interface StreamingAnswerProps {
  answer: string;
  mode: QueryMode | null;
  confidence: ConfidenceLevel | null;
  refusalReason: RefusalReason | null;
  sources: SourceCitation[];
  isStreaming: boolean;
  errorMessage: string | null;
}

function refusalCopy(reason: RefusalReason | null): string {
  if (reason === "LOW_SIMILARITY")  return "The retrieved context is not similar enough to provide a reliable answer.";
  if (reason === "BUDGET_EXCEEDED") return "Monthly token budget exhausted. Showing top sources without generation.";
  if (reason === "LLM_UNAVAILABLE") return "The language model is temporarily unavailable. Showing retrieved sources only.";
  return "No answer could be generated for this request.";
}

function ConfidenceBanner({ confidence }: { confidence: ConfidenceLevel }): JSX.Element {
  const styles: Record<ConfidenceLevel, { bg: string; label: string; hint: string }> = {
    HIGH:   { bg: "bg-green-500",  label: "CONFIDENT",  hint: "Strong evidence found." },
    MEDIUM: { bg: "bg-amber-500",  label: "UNCERTAIN",  hint: "Moderate evidence — verify sources." },
    LOW:    { bg: "bg-rose-500",   label: "LOW CONFIDENCE", hint: "Weak evidence — treat with caution." },
  };
  const s = styles[confidence];
  return (
    <div className={`w-full py-3 px-6 rounded-t-2xl text-xs font-black uppercase tracking-[0.2em] flex items-center justify-between ${s.bg} text-white`}>
      <div className="flex items-center gap-2">
        <ShieldCheck size={14} />
        {s.label}
      </div>
      <span className="opacity-80">{s.hint}</span>
    </div>
  );
}

function SkeletonLoader(): JSX.Element {
  return (
    <div className="space-y-4 pt-2">
      <div className="h-5 bg-slate-100 rounded-md w-1/4 animate-pulse" />
      <div className="space-y-3">
        <div className="h-4 bg-slate-50 rounded-md w-full animate-pulse" />
        <div className="h-4 bg-slate-50 rounded-md w-5/6 animate-pulse" />
        <div className="h-4 bg-slate-50 rounded-md w-4/6 animate-pulse" />
        <div className="h-4 bg-slate-50 rounded-md w-full animate-pulse" />
      </div>
    </div>
  );
}

function CitationsSection({ sources }: { sources: SourceCitation[] }): JSX.Element {
  const [open, setOpen] = useState(true);
  return (
    <div className="pt-6 border-t border-slate-200">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center justify-between w-full mb-5 group"
      >
        <p className="text-xs font-black text-slate-400 uppercase tracking-widest">
          Citations &amp; Evidence ({sources.length})
        </p>
        <ChevronDown
          size={14}
          className={`text-slate-400 transition-transform group-hover:text-slate-600 ${open ? "" : "-rotate-90"}`}
        />
      </button>
      {open && <CitationPanel sources={sources} />}
    </div>
  );
}

export function StreamingAnswer({
  answer,
  mode,
  confidence,
  refusalReason,
  sources,
  isStreaming,
  errorMessage,
}: StreamingAnswerProps): JSX.Element {
  if (errorMessage) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-800">
        {errorMessage}
      </div>
    );
  }

  if (isStreaming && !answer) {
    return <SkeletonLoader />;
  }

  const isRefusal = mode === "refusal" || mode === "retrieval_only";

  return (
    <div className="space-y-0 rounded-2xl overflow-hidden border border-slate-100 shadow-sm">
      {/* Confidence banner */}
      {confidence && !isRefusal && <ConfidenceBanner confidence={confidence} />}

      {/* Refusal banner */}
      {isRefusal && (
        <div className="w-full py-3 px-6 bg-slate-500 text-white text-xs font-black uppercase tracking-[0.2em] flex items-center gap-2">
          <ShieldCheck size={14} />
          {mode === "refusal" ? "REFUSAL" : "RETRIEVAL ONLY"}
        </div>
      )}

      <div className="bg-slate-50 p-8 space-y-8">
        {/* Refusal message */}
        {isRefusal && (
          <p className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
            {refusalCopy(refusalReason)}
          </p>
        )}

        {/* Answer text */}
        {(mode === "answer" || (!mode && answer)) && (
          <div className="text-base leading-relaxed text-slate-800 font-normal whitespace-pre-wrap">
            {answer}
            {isStreaming && (
              <span className="ml-1 inline-block h-4 w-0.5 bg-teal-500 animate-pulse align-middle" />
            )}
          </div>
        )}

        {sources.length > 0 && <CitationsSection sources={sources} />}
      </div>
    </div>
  );
}

