import type { ReactNode } from "react";

interface QueryLayoutProps {
	children: ReactNode;
}

export default function QueryLayout({ children }: QueryLayoutProps): JSX.Element {
	return (
		<main className="min-h-screen bg-gradient-to-br from-slate-950 via-cyan-950 to-emerald-900 px-4 py-8 text-slate-100 sm:px-8">
			<div className="mx-auto max-w-5xl">{children}</div>
		</main>
	);
}
