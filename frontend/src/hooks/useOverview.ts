import { useEffect, useState } from 'react';
import { api } from '../api/client';
import type { OverviewResponse } from '../api/types';
import { daysAgoIso, todayIso } from '../lib/formatters';

export function useOverview(cutoffHour: number) {
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    api
      .overview(daysAgoIso(30), todayIso(), cutoffHour, controller.signal)
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
