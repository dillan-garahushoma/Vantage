import { Link } from "react-router";
import { useDocumentMeta } from "@/hooks/useDocumentMeta";

export default function NotFound() {
  useDocumentMeta({ title: "Page not found | FibreHood" });
  return (
    <div className="container-site flex min-h-[50vh] flex-col items-center justify-center py-20 text-center">
      <p className="text-6xl font-extrabold text-gold">404</p>
      <h1 className="mt-4 text-2xl font-extrabold text-navy">Page not found</h1>
      <p className="mt-2 text-ink/60">The page you're looking for doesn't exist.</p>
      <Link
        to="/"
        className="mt-6 inline-flex h-11 items-center rounded-lg bg-navy px-6 text-sm font-bold text-white hover:bg-navy-600"
      >
        Back to home
      </Link>
    </div>
  );
}
