import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import App from '../App';

vi.mock('../api/client', () => ({
  api: {
    forecast: vi.fn(),
    intervals: vi.fn(),
    health: vi.fn(),
    accuracy: vi.fn(),
    overview: vi.fn(),
  },
}));

import { api } from '../api/client';
import { type Mock } from 'vitest';

// ── Fixtures ────────────────────────────────────────────────────────────────

const mockForecast = {
  delivery_date: '2026-01-15',
  decision_cutoff_utc: '2026-01-14T11:00:00+00:00',
  selected_vintage_utc: '2026-01-14T09:00:00+00:00',
  metrics: {
    total_hours: 48,
    evaluation_hours: 48,
    missing_forecast_hours: 0,
    missing_actual_hours: 0,
    invalid_hours: 0,
    mae_mw: 120.5,
    rmse_mw: 155.2,
    bias_mw: -30.1,
    max_abs_error_mw: 400.0,
    min_abs_error_mw: 5.0,
    p90_abs_error_mw: 300.0,
    max_signed_error_mw: 200.0,
    min_signed_error_mw: -400.0,
  },
  hours: [
    {
      start_utc: '2026-01-15T00:00:00+00:00',
      start_uk: '2026-01-15T00:00:00+00:00',
      forecast_mw: 2000,
      actual_mw: 1800,
      signed_error_mw: 200,
      abs_error_mw: 200,
    },
    {
      start_utc: '2026-01-15T00:30:00+00:00',
      start_uk: '2026-01-15T00:30:00+00:00',
      forecast_mw: 2100,
      actual_mw: null,
      signed_error_mw: null,
      abs_error_mw: null,
    },
  ],
};

const mockIntervals = {
  delivery_date: '2026-01-15',
  decision_cutoff_utc: '2026-01-14T11:00:00+00:00',
  selected_vintage_utc: '2026-01-14T09:00:00+00:00',
  total: 2,
  offset: 0,
  limit: 50,
  hours: mockForecast.hours,
};

const mockOverview = {
  from_date: '2026-01-01',
  to_date: '2026-01-31',
  cutoff_hour: 11,
  total_days: 31,
  days_with_data: 30,
  failed_dates: ['2026-01-05'],
  aggregate_metrics: {
    total_hours: 720,
    evaluation_hours: 690,
    missing_forecast_hours: 0,
    missing_actual_hours: 30,
    invalid_hours: 0,
    mae_mw: 850.0,
    rmse_mw: 950.0,
    bias_mw: 750.0,
    max_abs_error_mw: 2100.0,
    min_abs_error_mw: 50.0,
    p90_abs_error_mw: 1600.0,
    max_signed_error_mw: 2100.0,
    min_signed_error_mw: -200.0,
  },
  days: [
    {
      delivery_date: '2026-01-15',
      decision_cutoff_utc: '2026-01-14T11:00:00+00:00',
      selected_vintage_utc: '2026-01-14T09:00:00+00:00',
      metrics: {
        total_hours: 24,
        evaluation_hours: 24,
        missing_forecast_hours: 0,
        missing_actual_hours: 0,
        invalid_hours: 0,
        mae_mw: 120.5,
        rmse_mw: 155.2,
        bias_mw: -30.1,
        max_abs_error_mw: 400.0,
        min_abs_error_mw: 5.0,
        p90_abs_error_mw: 300.0,
        max_signed_error_mw: 200.0,
        min_signed_error_mw: -400.0,
      },
    },
  ],
};

const mockAccuracy = {
  from_date: '2026-01-01',
  to_date: '2026-01-31',
  cutoff_hour: 11,
  total_days: 31,
  days_with_data: 30,
  failed_dates: ['2026-01-05'],
  days: mockOverview.days,
};

const mockForecastNoActuals = {
  ...mockForecast,
  metrics: {
    ...mockForecast.metrics,
    mae_mw: null,
    bias_mw: null,
    evaluation_hours: 0,
    missing_actual_hours: 2,
  },
  hours: [
    {
      start_utc: '2026-01-15T00:00:00+00:00',
      start_uk: '2026-01-15T00:00:00+00:00',
      forecast_mw: 2000,
      actual_mw: null,
      signed_error_mw: null,
      abs_error_mw: null,
    },
  ],
};

const mockIntervalsNoActuals = {
  ...mockIntervals,
  hours: mockForecastNoActuals.hours,
  total: 1,
};

const emptyForecast = {
  ...mockForecast,
  metrics: {
    ...mockForecast.metrics,
    evaluation_hours: 0,
    mae_mw: null,
    bias_mw: null,
  },
  hours: [],
};

const emptyIntervals = {
  ...mockIntervals,
  hours: [],
  total: 0,
};

// ── Helpers ─────────────────────────────────────────────────────────────────

describe('WindSight Dashboard', () => {
  const mockApi = api as unknown as {
    forecast: Mock;
    intervals: Mock;
    overview: Mock;
    accuracy: Mock;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Monthly data endpoints: return a never-resolving promise by default so
    // they don't interfere with single-day test assertions.
    mockApi.overview.mockReturnValue(new Promise(() => {}));
    mockApi.accuracy.mockReturnValue(new Promise(() => {}));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Single-day forecast tests ──────────────────────────────────────────────

  it('shows loading state on initial render', async () => {
    mockApi.forecast.mockReturnValue(new Promise(() => {}));
    mockApi.intervals.mockReturnValue(new Promise(() => {}));

    render(<App />);

    const spinners = document.querySelectorAll('svg.animate-spin');
    expect(spinners.length).toBeGreaterThan(0);
  });

  it('renders forecast and actual values when data loads', async () => {
    mockApi.forecast.mockResolvedValue(mockForecast);
    mockApi.intervals.mockResolvedValue(mockIntervals);

    render(<App />);

    // (2000+2100)/2 = 2050
    await waitFor(() => {
      expect(screen.getByTestId('kpi-forecast')).toHaveTextContent('2050');
    });

    // Avg Actual: only 1 non-null = 1800
    expect(screen.getByTestId('kpi-actual')).toHaveTextContent('1800');

    // MAE and Bias from backend metrics
    expect(screen.getByTestId('kpi-mae')).toHaveTextContent('120.5');
    expect(screen.getByTestId('kpi-bias')).toHaveTextContent('-30.1');
  });

  it('shows em-dash for null actual_mw, never zero', async () => {
    mockApi.forecast.mockResolvedValue(mockForecastNoActuals);
    mockApi.intervals.mockResolvedValue(mockIntervalsNoActuals);

    render(<App />);

    await waitFor(() => {
      const actualKpi = screen.getByTestId('kpi-actual');
      expect(actualKpi).toHaveTextContent('—');
      expect(actualKpi).not.toHaveTextContent('0');
    });

    await waitFor(() => {
      expect(screen.getByTestId('kpi-mae')).toHaveTextContent('—');
      expect(screen.getByTestId('kpi-bias')).toHaveTextContent('—');
    });
  });

  it('shows empty state when hours array is empty', async () => {
    mockApi.forecast.mockResolvedValue(emptyForecast);
    mockApi.intervals.mockResolvedValue(emptyIntervals);

    render(<App />);

    // Navigate to Forecast Analysis section to see chart/table empty states
    fireEvent.click(screen.getByRole('button', { name: /forecast analysis/i }));

    await waitFor(() => {
      expect(screen.getByText(/no forecast data available/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/no interval data available/i)).toBeInTheDocument();
  });

  it('shows error banner when API returns an error', async () => {
    mockApi.forecast.mockRejectedValue(new Error('No forecast vintage available'));
    mockApi.intervals.mockRejectedValue(new Error('No forecast vintage available'));

    render(<App />);

    await waitFor(() => {
      const alerts = screen.getAllByRole('alert');
      expect(alerts.length).toBeGreaterThan(0);
      const hasMessage = alerts.some((el) =>
        el.textContent?.includes('No forecast vintage available'),
      );
      expect(hasMessage).toBe(true);
    });
  });

  it('refetches data when decision date changes', async () => {
    mockApi.forecast.mockResolvedValue(mockForecast);
    mockApi.intervals.mockResolvedValue(mockIntervals);

    render(<App />);

    await waitFor(() => {
      expect(mockApi.forecast).toHaveBeenCalledTimes(1);
    });

    const dateInput = screen.getByLabelText(/select decision date/i);
    fireEvent.change(dateInput, { target: { value: '2026-01-15' } });

    await waitFor(() => {
      expect(mockApi.forecast).toHaveBeenCalledTimes(2);
    });

    expect(mockApi.forecast).toHaveBeenLastCalledWith(
      '2026-01-16', // deliveryDate = decisionDate + 1
      11,
      expect.any(AbortSignal),
    );
  });

  it('refetches data when refresh button is clicked', async () => {
    mockApi.forecast.mockResolvedValue(mockForecast);
    mockApi.intervals.mockResolvedValue(mockIntervals);

    render(<App />);

    await waitFor(() => {
      expect(mockApi.forecast).toHaveBeenCalledTimes(1);
    });

    const refreshBtn = screen.getByRole('button', { name: /refresh/i });
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(mockApi.forecast).toHaveBeenCalledTimes(2);
    });
  });

  it('does not overwrite current result with stale request response', async () => {
    let resolveForecast1!: (v: typeof mockForecast) => void;
    let resolveForecast2!: (v: typeof mockForecast) => void;
    let resolveIntervals1!: (v: typeof mockIntervals) => void;
    let resolveIntervals2!: (v: typeof mockIntervals) => void;

    const stale = {
      ...mockForecast,
      delivery_date: '2026-01-15',
      metrics: { ...mockForecast.metrics, mae_mw: 999.9 },
    };
    const fresh = {
      ...mockForecast,
      delivery_date: '2026-01-16',
      metrics: { ...mockForecast.metrics, mae_mw: 50.0 },
    };

    mockApi.forecast
      .mockReturnValueOnce(new Promise((res) => { resolveForecast1 = res; }))
      .mockReturnValueOnce(new Promise((res) => { resolveForecast2 = res; }));
    mockApi.intervals
      .mockReturnValueOnce(new Promise((res) => { resolveIntervals1 = res; }))
      .mockReturnValueOnce(new Promise((res) => { resolveIntervals2 = res; }));

    render(<App />);

    const dateInput = screen.getByLabelText(/select decision date/i);
    fireEvent.change(dateInput, { target: { value: '2026-01-15' } });

    await act(async () => {
      resolveForecast2(fresh);
      resolveIntervals2(mockIntervals);
    });

    await waitFor(() => {
      expect(screen.getByTestId('kpi-mae')).toHaveTextContent('50.0');
    });

    await act(async () => {
      resolveForecast1(stale);
      resolveIntervals1(mockIntervals);
    });

    expect(screen.getByTestId('kpi-mae')).toHaveTextContent('50.0');
    expect(screen.getByTestId('kpi-mae')).not.toHaveTextContent('999.9');
  });

  it('shows correct signed error with negative values', async () => {
    const withNegError = {
      ...mockForecast,
      hours: [
        {
          start_utc: '2026-01-15T00:00:00+00:00',
          start_uk: '2026-01-15T00:00:00+00:00',
          forecast_mw: 1500,
          actual_mw: 2000,
          signed_error_mw: -500,
          abs_error_mw: 500,
        },
      ],
    };
    mockApi.forecast.mockResolvedValue(withNegError);
    mockApi.intervals.mockResolvedValue({
      ...mockIntervals,
      hours: withNegError.hours,
      total: 1,
    });

    render(<App />);

    // Navigate to Forecast Analysis to see the interval table
    fireEvent.click(screen.getByRole('button', { name: /forecast analysis/i }));

    await waitFor(() => {
      const cells = screen.getAllByRole('cell');
      const errorCell = cells.find((c) => c.textContent === '-500');
      expect(errorCell).toBeInTheDocument();
    });
  });

  it('refresh button is accessible and shows loading indicator', async () => {
    mockApi.forecast.mockReturnValue(new Promise(() => {}));
    mockApi.intervals.mockReturnValue(new Promise(() => {}));

    render(<App />);

    const refreshBtn = screen.getByRole('button', { name: /refresh/i });
    expect(refreshBtn).toBeInTheDocument();
    expect(refreshBtn).toBeDisabled();
  });

  it('decision date input is accessible with label', () => {
    mockApi.forecast.mockReturnValue(new Promise(() => {}));
    mockApi.intervals.mockReturnValue(new Promise(() => {}));

    render(<App />);

    const dateInput = screen.getByLabelText(/select decision date/i);
    expect(dateInput).toBeInTheDocument();
    expect(dateInput).toHaveAttribute('type', 'date');
  });

  // ── Historical Accuracy section tests ──────────────────────────────────────

  it('renders January aggregate metrics from /api/overview', async () => {
    mockApi.forecast.mockResolvedValue(mockForecast);
    mockApi.intervals.mockResolvedValue(mockIntervals);
    mockApi.overview.mockResolvedValue(mockOverview);
    mockApi.accuracy.mockResolvedValue(mockAccuracy);

    render(<App />);

    // Navigate to Historical Accuracy section
    fireEvent.click(screen.getByRole('button', { name: /historical accuracy/i }));

    // Aggregate MAE from overview.aggregate_metrics (850 → displayed as "850")
    await waitFor(() => {
      expect(screen.getByText('850')).toBeInTheDocument();
    });

    expect(screen.getByText(/30 of 31 days with data/i)).toBeInTheDocument();
  });

  it('renders day-by-day accuracy table from /api/accuracy', async () => {
    mockApi.forecast.mockResolvedValue(mockForecast);
    mockApi.intervals.mockResolvedValue(mockIntervals);
    mockApi.overview.mockResolvedValue(mockOverview);
    mockApi.accuracy.mockResolvedValue(mockAccuracy);

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /historical accuracy/i }));

    await waitFor(() => {
      expect(screen.getByText(/day-by-day accuracy/i)).toBeInTheDocument();
    });

    expect(screen.getAllByText(/15 Jan 2026/i).length).toBeGreaterThan(0);
  });

  it('highlights the selected delivery date row in the accuracy table', async () => {
    mockApi.forecast.mockResolvedValue(mockForecast);
    mockApi.intervals.mockResolvedValue(mockIntervals);
    mockApi.overview.mockResolvedValue(mockOverview);
    mockApi.accuracy.mockResolvedValue(mockAccuracy);

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /historical accuracy/i }));

    await waitFor(() => {
      expect(screen.getByText('selected')).toBeInTheDocument();
    });
  });

  it('shows accuracy error banner when /api/accuracy fails', async () => {
    mockApi.forecast.mockResolvedValue(mockForecast);
    mockApi.intervals.mockResolvedValue(mockIntervals);
    mockApi.overview.mockResolvedValue(mockOverview);
    mockApi.accuracy.mockRejectedValue(new Error('Accuracy unavailable'));

    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /historical accuracy/i }));

    await waitFor(() => {
      const alerts = screen.getAllByRole('alert');
      const hasMessage = alerts.some((el) =>
        el.textContent?.includes('Accuracy unavailable'),
      );
      expect(hasMessage).toBe(true);
    });
  });

  // ── Sidebar navigation tests ───────────────────────────────────────────────

  it('sidebar contains navigation buttons for all four sections', () => {
    mockApi.forecast.mockReturnValue(new Promise(() => {}));
    mockApi.intervals.mockReturnValue(new Promise(() => {}));

    render(<App />);

    expect(screen.getByRole('button', { name: /overview/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /forecast analysis/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /historical accuracy/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /data sources/i })).toBeInTheDocument();
  });

  it('only the active section renders; switching shows the correct section', () => {
    mockApi.forecast.mockReturnValue(new Promise(() => {}));
    mockApi.intervals.mockReturnValue(new Promise(() => {}));

    render(<App />);

    // Default: Overview is visible, others are not
    expect(document.getElementById('section-overview')).toBeInTheDocument();
    expect(document.getElementById('section-forecast')).not.toBeInTheDocument();

    // Click Forecast Analysis
    fireEvent.click(screen.getByRole('button', { name: /forecast analysis/i }));
    expect(document.getElementById('section-forecast')).toBeInTheDocument();
    expect(document.getElementById('section-overview')).not.toBeInTheDocument();

    // Click Data Sources
    fireEvent.click(screen.getByRole('button', { name: /data sources/i }));
    expect(document.getElementById('section-data-sources')).toBeInTheDocument();
    expect(document.getElementById('section-forecast')).not.toBeInTheDocument();
  });
});
