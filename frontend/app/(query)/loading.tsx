export default function Loading(): JSX.Element {
	return (
		<div className="space-y-3 rounded-2xl border border-cyan-300/30 bg-white/10 p-6 backdrop-blur">
			<div className="h-4 w-40 animate-pulse rounded bg-cyan-100/30" />
			<div className="h-20 animate-pulse rounded bg-cyan-100/20" />
			<div className="h-10 w-32 animate-pulse rounded bg-cyan-100/30" />
		</div>
	);
}
