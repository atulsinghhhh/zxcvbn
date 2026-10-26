import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { OverviewResponse } from '../api/types';

export function useOverview(cutoffHour: number) {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    api
      .overview('2026-01-01', '2026-01-31', cutoffHour, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setOverview(data);
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

  return { overview, loading, error };
}
