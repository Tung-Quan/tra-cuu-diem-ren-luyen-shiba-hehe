export default function ErrorBanner({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700">
      {message}
    </div>
  );
}
