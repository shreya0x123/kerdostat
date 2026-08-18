import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="min-h-screen bg-[#0d1520] text-slate-100 flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-3xl rounded-3xl border border-slate-800 bg-slate-950/80 p-10 shadow-2xl text-center">
        <h2 className="text-3xl font-bold text-white mb-4">
          404 — Page not found
        </h2>
        <p className="text-slate-400 mb-6">
          The page you are looking for does not exist. Use the navigation below
          to return home.
        </p>
        <Link
          className="inline-flex rounded-full bg-[#22d3ee] px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-[#2dd4bf] transition"
          to="/"
        >
          Go back home
        </Link>
      </div>
    </main>
  );
}
