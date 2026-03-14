"""Tests for validation result dataclasses."""
import numpy as np
import pandas as pd
import pytest

from validation.results import (
    OOSResult,
    MonteCarloResult,
    WalkForwardWindow,
    WalkForwardResult,
    ValidationReport,
)


class TestOOSResult:
    def test_instantiation(self):
        result = OOSResult(
            in_sample_metrics={'sharpe_ratio': 1.5, 'ROI': 10.0},
            out_of_sample_metrics={'sharpe_ratio': 0.8, 'ROI': 5.0},
            split_date=pd.Timestamp('2024-06-01'),
            is_size=700,
            oos_size=300,
            degradation={
                'sharpe_ratio': {'is': 1.5, 'oos': 0.8, 'pct_change': -46.7},
            },
        )
        assert result.is_size == 700
        assert result.oos_size == 300
        assert result.split_date == pd.Timestamp('2024-06-01')

    def test_degradation_values(self):
        result = OOSResult(
            in_sample_metrics={}, out_of_sample_metrics={},
            split_date=pd.Timestamp('2024-06-01'),
            is_size=700, oos_size=300,
            degradation={
                'sharpe_ratio': {'is': 2.0, 'oos': 1.0, 'pct_change': -50.0},
            },
        )
        assert result.degradation['sharpe_ratio']['pct_change'] == -50.0


class TestMonteCarloResult:
    def test_instantiation(self):
        n_sim, n_trades = 100, 20
        result = MonteCarloResult(
            original_final_equity=1200.0,
            simulated_equities=np.ones((n_sim, n_trades)) * 1200,
            percentiles={5: 1100, 25: 1150, 50: 1200, 75: 1250, 95: 1300},
            p_value=0.55,
            max_drawdowns=np.ones(n_sim) * 0.05,
            confidence_intervals={
                'final_equity': (1100, 1300),
                'max_drawdown': (0.03, 0.08),
            },
        )
        assert result.original_final_equity == 1200.0
        assert result.simulated_equities.shape == (n_sim, n_trades)
        assert result.p_value == 0.55


class TestWalkForwardResult:
    def test_instantiation(self):
        window = WalkForwardWindow(
            window_id=0,
            is_start=pd.Timestamp('2024-01-01'),
            is_end=pd.Timestamp('2024-04-01'),
            oos_start=pd.Timestamp('2024-04-01'),
            oos_end=pd.Timestamp('2024-06-01'),
            best_params={'lookback': 20},
            is_metrics={'sharpe_ratio': 1.5},
            oos_metrics={'sharpe_ratio': 1.0},
        )
        assert window.window_id == 0
        assert window.best_params == {'lookback': 20}

        result = WalkForwardResult(
            windows=[window],
            oos_combined_metrics={'sharpe_ratio': 1.0},
            efficiency_ratio=0.67,
            param_stability={'lookback': {'values': [20], 'mean': 20, 'std': 0, 'cv': 0}},
        )
        assert result.efficiency_ratio == 0.67
        assert len(result.windows) == 1


class TestValidationReport:
    def test_all_none(self):
        report = ValidationReport(
            oos=None,
            monte_carlo=None,
            walk_forward=None,
            summary={'is_robust': True, 'issues': [], 'scores': {}},
        )
        assert report.oos is None
        assert report.monte_carlo is None
        assert report.walk_forward is None
        assert report.summary['is_robust'] is True

    def test_with_results(self):
        oos = OOSResult(
            in_sample_metrics={}, out_of_sample_metrics={},
            split_date=pd.Timestamp('2024-06-01'),
            is_size=700, oos_size=300, degradation={},
        )
        report = ValidationReport(
            oos=oos, monte_carlo=None, walk_forward=None,
            summary={'is_robust': True, 'issues': [], 'scores': {}},
        )
        assert report.oos is not None
        assert report.monte_carlo is None
