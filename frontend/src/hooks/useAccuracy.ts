import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { AccuracyResponse } from '../api/types';
import { daysAgoIso, todayIso } from '../lib/formatters';

export function useAccuracy(cutoffHour: number) {
  const [accuracy, setAccuracy] = useState<AccuracyResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    api
      .accuracy(daysAgoIso(30), todayIso(), cutoffHour, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setAccuracy(data);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [cutoffHour]);

  return { accuracy, loading, error };
}
