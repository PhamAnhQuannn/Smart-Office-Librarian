export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}): JSX.Element {
  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-6">
      {children}
    </div>
  );
}
