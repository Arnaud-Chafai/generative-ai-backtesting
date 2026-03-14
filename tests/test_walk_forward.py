"""Tests for WalkForwardValidator."""
import numpy as np
import pandas as pd
import pytest

from validation.walk_forward import WalkForwardValidator


@pytest.fixture
def tiny_market_data():
    """30-bar dataset too small for 5 windows."""
    np.random.seed(99)
    dates = pd.date_range('2024-01-01', periods=30, freq='5min')
    close = np.linspace(100, 105, 30)
    df = pd.DataFrame({
        'Open': close - 0.1, 'High': close + 0.3,
        'Low': close - 0.3, 'Close': close,
        'Volume': np.ones(30) * 100,
    }, index=dates)
    df.index.name = 'Time'
    return df


class TestWalkForwardInstantiation:
    def test_rejects_one_window(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="n_windows"):
            WalkForwardValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                n_windows=1,
            )

    def test_rejects_zero_windows(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="n_windows"):
            WalkForwardValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                n_windows=0,
            )

    def test_rejects_insufficient_data(self, dummy_strategy_class, tiny_market_data):
        with pytest.raises(ValueError, match="[Ii]nsufficient"):
            WalkForwardValidator(
                strategy_class=dummy_strategy_class,
                market_data=tiny_market_data,
                n_windows=5,
            )

    def test_rejects_invalid_optimization_metric(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=2,
        )
        with pytest.raises(ValueError, match="optimization_metric"):
            wf.run(
                param_ranges={'buy_every': [15, 20]},
                optimization_metric='invalid_metric',
                verbose=False,
            )


class TestWalkForwardRolling:
    def test_rolling_fixed_mode(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
            anchored=False,
        )
        result = wf.run(verbose=False)
        assert len(result.windows) == 3
        assert result.param_stability is None  # fixed mode

    def test_rolling_windows_cover_dataset(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
            anchored=False,
        )
        result = wf.run(verbose=False)
        # First window starts at first bar
        assert result.windows[0].is_start == synthetic_market_data.index[0]
        # Last window ends at last bar
        assert result.windows[-1].oos_end == synthetic_market_data.index[-1]
        # No gaps: each window's IS start == previous window's OOS end (next bar)
        for i in range(len(result.windows) - 1):
            curr_oos_end = result.windows[i].oos_end
            next_is_start = result.windows[i + 1].is_start
            # next window starts right after current window ends (1 bar gap max)
            gap = abs((next_is_start - curr_oos_end).total_seconds())
            assert gap <= 600, f"Gap between window {i} and {i+1}: {gap}s (max 600s for 5min bars)"

    def test_efficiency_ratio_calculated(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
        )
        result = wf.run(verbose=False)
        assert isinstance(result.efficiency_ratio, float)

    def test_oos_combined_metrics_populated(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
        )
        result = wf.run(verbose=False)
        assert len(result.oos_combined_metrics) > 0


class TestWalkForwardAnchored:
    def test_anchored_is_always_starts_at_zero(self, dummy_strategy_class, synthetic_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            n_windows=3,
            oos_ratio=0.25,
            anchored=True,
        )
        result = wf.run(verbose=False)
        first_ts = synthetic_market_data.index[0]
        for w in result.windows:
            assert w.is_start == first_ts


class TestWalkForwardOptimization:
    def test_optimization_mode(self, dummy_strategy_class, small_market_data):
        """Test WF with re-optimization. Uses small data + tiny grid for speed."""
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=small_market_data,
            n_windows=2,
            oos_ratio=0.3,
        )
        result = wf.run(
            param_ranges={'buy_every': [15, 20]},
            optimization_metric='sharpe_ratio',
            min_trades=1,
            verbose=False,
        )
        assert len(result.windows) == 2
        # In optimization mode, best_params should be filled
        for w in result.windows:
            assert w.best_params is not None
        # param_stability should be calculated
        assert result.param_stability is not None
        assert 'buy_every' in result.param_stability

    def test_param_stability_has_cv(self, dummy_strategy_class, small_market_data):
        wf = WalkForwardValidator(
            strategy_class=dummy_strategy_class,
            market_data=small_market_data,
            n_windows=2,
            oos_ratio=0.3,
        )
        result = wf.run(
            param_ranges={'buy_every': [15, 20]},
            min_trades=1,
            verbose=False,
        )
        if result.param_stability:
            for param, stats in result.param_stability.items():
                assert 'values' in stats
                assert 'mean' in stats
                assert 'std' in stats
                assert 'cv' in stats
