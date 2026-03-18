import { APP_NAME } from "../../lib/constants";

export function Footer(): JSX.Element {
  return (
    <footer className="border-t border-white/10 bg-slate-950/60 py-4 text-center text-xs text-slate-500">
      &copy; {new Date().getFullYear()} {APP_NAME}. Internal use only.
    </footer>
  );
}
