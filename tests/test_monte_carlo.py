"""Tests for MonteCarloValidator."""
import numpy as np
import pandas as pd
import pytest

from validation.monte_carlo import MonteCarloValidator


class TestMonteCarloInstantiation:
    def test_basic_creation(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df, initial_capital=1000.0)
        assert mc.initial_capital == 1000.0

    def test_rejects_empty_dataframe(self):
        with pytest.raises(ValueError, match="at least 2 trades"):
            MonteCarloValidator(pd.DataFrame({'net_pnl': []}))

    def test_rejects_single_trade(self):
        with pytest.raises(ValueError, match="at least 2 trades"):
            MonteCarloValidator(pd.DataFrame({'net_pnl': [10]}))

    def test_rejects_missing_pnl_column(self):
        with pytest.raises(ValueError, match="net_pnl.*net_profit_loss"):
            MonteCarloValidator(pd.DataFrame({'other_col': [1, 2, 3]}))

    def test_detects_net_profit_loss_column(self):
        df = pd.DataFrame({'net_profit_loss': [10, -5, 15]})
        mc = MonteCarloValidator(df, initial_capital=1000.0)
        assert mc.initial_capital == 1000.0


class TestMonteCarloRun:
    def test_deterministic_with_seed(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        r1 = mc.run(n_simulations=100, seed=42, verbose=False)
        mc2 = MonteCarloValidator(synthetic_trades_df)
        r2 = mc2.run(n_simulations=100, seed=42, verbose=False)
        np.testing.assert_array_equal(r1.simulated_equities, r2.simulated_equities)

    def test_result_shapes(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=50, seed=42, verbose=False)
        assert result.simulated_equities.shape == (50, 20)
        assert result.max_drawdowns.shape == (50,)

    def test_percentile_ordering(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=500, seed=42, verbose=False)
        assert result.percentiles[5] <= result.percentiles[25]
        assert result.percentiles[25] <= result.percentiles[50]
        assert result.percentiles[50] <= result.percentiles[75]
        assert result.percentiles[75] <= result.percentiles[95]

    def test_p_value_range(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=100, seed=42, verbose=False)
        assert 0.0 <= result.p_value <= 1.0

    def test_confidence_intervals_structure(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=100, confidence_level=0.95, seed=42, verbose=False)
        assert 'final_equity' in result.confidence_intervals
        assert 'max_drawdown' in result.confidence_intervals
        lo, hi = result.confidence_intervals['final_equity']
        assert lo <= hi

    def test_uniform_trades_all_same_equity(self):
        """All trades +$10: every permutation produces identical equity curve."""
        df = pd.DataFrame({'net_pnl': [10.0] * 20})
        mc = MonteCarloValidator(df, initial_capital=1000.0)
        result = mc.run(n_simulations=100, seed=42, verbose=False)
        expected = 1000.0 + 20 * 10.0
        np.testing.assert_allclose(
            result.simulated_equities[:, -1], expected, atol=1e-10
        )

    def test_original_final_equity(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df, initial_capital=1000.0)
        result = mc.run(n_simulations=50, seed=42, verbose=False)
        expected = 1000.0 + synthetic_trades_df['net_pnl'].sum()
        assert abs(result.original_final_equity - expected) < 1e-10

    def test_max_drawdowns_non_negative(self, synthetic_trades_df):
        mc = MonteCarloValidator(synthetic_trades_df)
        result = mc.run(n_simulations=100, seed=42, verbose=False)
        assert (result.max_drawdowns >= 0).all()
