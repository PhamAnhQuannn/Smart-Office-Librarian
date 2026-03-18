import Link from "next/link";
import { APP_NAME, NAV_LINKS } from "../../lib/constants";

export function Header(): JSX.Element {
  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-8">
        <Link href="/" className="text-sm font-bold tracking-widest text-cyan-400 uppercase">
          {APP_NAME}
        </Link>
        <nav className="flex items-center gap-6">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-slate-300 transition-colors hover:text-white"
            >
              {link.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
