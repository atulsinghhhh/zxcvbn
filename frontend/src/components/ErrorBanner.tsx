import { AlertCircle } from 'lucide-react';

interface Props {
  message: string;
  label?: string;
}

export function ErrorBanner({ message, label = 'Error' }: Props) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-300"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        <span className="font-semibold">{label}: </span>
        {message}
      </span>
    </div>
  );
}
