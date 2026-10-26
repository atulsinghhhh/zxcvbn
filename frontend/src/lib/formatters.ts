import { format, parseISO, addDays } from 'date-fns';

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
