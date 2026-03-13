import type { ConfidenceLevel } from "../../types/api";

interface ConfidenceBadgeProps {
	confidence: ConfidenceLevel;
}

const CONFIDENCE_STYLES: Record<ConfidenceLevel, string> = {
	HIGH: "border-emerald-600/50 bg-emerald-100 text-emerald-900",
	MEDIUM: "border-amber-500/50 bg-amber-100 text-amber-900",
	LOW: "border-rose-500/50 bg-rose-100 text-rose-900",
};

const CONFIDENCE_HINT: Record<ConfidenceLevel, string> = {
	HIGH: "High confidence based on strong retrieval similarity.",
	MEDIUM: "Medium confidence based on moderate retrieval similarity.",
	LOW: "Low confidence based on weak retrieval similarity or refusal mode.",
};

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps): JSX.Element {
	return (
		<span
			className={`inline-flex items-center rounded-full border px-2 py-1 text-xs font-semibold ${CONFIDENCE_STYLES[confidence]}`}
			title={CONFIDENCE_HINT[confidence]}
			aria-label={`Confidence ${confidence}`}
		>
			{confidence}
		</span>
	);
}
