// src/components/Layout.tsx
import Header from "./Header";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <main className="mx-auto max-w-6xl p-4">{children}</main>
    </div>
  );
}
