import { format, parseISO, addDays, subDays } from 'date-fns';

/** Today's date as yyyy-MM-dd (local time). */
export function todayIso(): string {
  return format(new Date(), 'yyyy-MM-dd');
}

/** Yesterday's date as yyyy-MM-dd — the default decision date (latest complete delivery day). */
export function yesterdayIso(): string {
  return format(subDays(new Date(), 1), 'yyyy-MM-dd');
}

/** The date `n` days before today as yyyy-MM-dd. */
export function daysAgoIso(n: number): string {
  return format(subDays(new Date(), n), 'yyyy-MM-dd');
}

export function formatTime(isoString: string): string {
  return format(parseISO(isoString), 'HH:mm');
}

export function formatDateTime(isoString: string): string {
  return format(parseISO(isoString), 'dd MMM yyyy HH:mm');
}

export function formatDateTimeUtc(isoString: string): string {
  return format(parseISO(isoString), "dd MMM yyyy HH:mm 'UTC'");
}

export function formatDate(isoString: string): string {
  return format(parseISO(isoString), 'dd MMM yyyy');
}

export function addOneDay(dateStr: string): string {
  return format(addDays(parseISO(dateStr), 1), 'yyyy-MM-dd');
}

export function formatMw(value: number | null, decimals = 0): string {
  if (value === null) return '—';
  return `${value.toFixed(decimals)} MW`;
}

export function formatNumber(value: number | null, decimals = 1): string {
  if (value === null) return '—';
  return value.toFixed(decimals);
}
