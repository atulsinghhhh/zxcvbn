import { AlertCircle } from 'lucide-react';

interface Props {
  message: string;
  label?: string;
}

export function ErrorBanner({ message, label = 'Error' }: Props) {
  return (
    <div
      role="alert"
      style={{ border: '1px solid rgba(209,29,69,0.2)', background: '#fff0f3', borderRadius: 8, color: '#d11d45' }}
      className="flex items-start gap-3 px-4 py-3 text-sm"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      <span>
        <span className="font-semibold">{label}: </span>
        {message}
      </span>
    </div>
  );
}
