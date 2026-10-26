import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import type { ForecastResponse, IntervalsResponse } from '../api/types';
import { addOneDay } from '../lib/formatters';

interface WindSightState {
  decisionDate: string;
  deliveryDate: string;
  cutoffHour: number;
  forecast: ForecastResponse | null;
  intervals: IntervalsResponse | null;
  forecastLoading: boolean;
  intervalsLoading: boolean;
  forecastError: string | null;
  intervalsError: string | null;
  intervalsOffset: number;
  setDecisionDate: (date: string) => void;
  setIntervalsOffset: (offset: number) => void;
  refresh: () => void;
}

export function useWindSight(): WindSightState {
  const [decisionDate, setDecisionDate] = useState('2026-01-14');
  const cutoffHour = 11;
  const [refreshKey, setRefreshKey] = useState(0);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [intervals, setIntervals] = useState<IntervalsResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [intervalsLoading, setIntervalsLoading] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [intervalsError, setIntervalsError] = useState<string | null>(null);
  const [intervalsOffset, setIntervalsOffset] = useState(0);

  const deliveryDate = addOneDay(decisionDate);

  // Track the "current" request so stale responses are discarded
  const requestIdRef = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const currentId = ++requestIdRef.current;

    setForecastLoading(true);
    setIntervalsLoading(true);
    setForecastError(null);
    setIntervalsError(null);

    api
      .forecast(deliveryDate, cutoffHour, controller.signal)
      .then((data) => {
        if (requestIdRef.current !== currentId) return;
        setForecast(data);
        setForecastError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        if (requestIdRef.current !== currentId) return;
        setForecast(null);
        setForecastError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => {
        if (requestIdRef.current !== currentId) return;
        setForecastLoading(false);
      });

    api
      .intervals(deliveryDate, cutoffHour, 50, intervalsOffset, controller.signal)
      .then((data) => {
        if (requestIdRef.current !== currentId) return;
        setIntervals(data);
        setIntervalsError(null);
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        if (requestIdRef.current !== currentId) return;
        setIntervals(null);
        setIntervalsError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => {
        if (requestIdRef.current !== currentId) return;
        setIntervalsLoading(false);
      });

    return () => {
      controller.abort();
    };
  }, [decisionDate, cutoffHour, refreshKey, intervalsOffset, deliveryDate]);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return {
    decisionDate,
    deliveryDate,
    cutoffHour,
    forecast,
    intervals,
    forecastLoading,
    intervalsLoading,
    forecastError,
    intervalsError,
    intervalsOffset,
    setDecisionDate,
    setIntervalsOffset,
    refresh,
  };
}
