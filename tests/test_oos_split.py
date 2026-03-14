"""Tests for OOSSplitValidator."""
import pandas as pd
import pytest

from validation.oos_split import OOSSplitValidator


class TestOOSSplitInstantiation:
    def test_rejects_zero_ratio(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="oos_ratio"):
            OOSSplitValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                oos_ratio=0.0,
            )

    def test_rejects_ratio_one(self, dummy_strategy_class, synthetic_market_data):
        with pytest.raises(ValueError, match="oos_ratio"):
            OOSSplitValidator(
                strategy_class=dummy_strategy_class,
                market_data=synthetic_market_data,
                oos_ratio=1.0,
            )

    def test_rejects_insufficient_data(self, dummy_strategy_class):
        tiny_data = pd.DataFrame(
            {'Open': [1]*10, 'High': [2]*10, 'Low': [0.5]*10, 'Close': [1.5]*10, 'Volume': [100]*10},
            index=pd.date_range('2024-01-01', periods=10, freq='5min'),
        )
        tiny_data.index.name = 'Time'
        with pytest.raises(ValueError, match="at least 20"):
            OOSSplitValidator(
                strategy_class=dummy_strategy_class,
                market_data=tiny_data,
                oos_ratio=0.3,
            )


class TestOOSSplitRun:
    def test_split_sizes(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        assert result.is_size + result.oos_size == len(synthetic_market_data)
        assert result.is_size == int(len(synthetic_market_data) * 0.7)

    def test_split_date_in_range(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        assert result.split_date >= synthetic_market_data.index[0]
        assert result.split_date <= synthetic_market_data.index[-1]

    def test_metrics_populated(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        assert 'sharpe_ratio' in result.in_sample_metrics
        assert 'sharpe_ratio' in result.out_of_sample_metrics

    def test_degradation_has_key_metrics(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        expected_keys = {'sharpe_ratio', 'ROI', 'profit_factor', 'percent_profitable', 'max_drawdown_pct'}
        assert expected_keys.issubset(result.degradation.keys())

    def test_degradation_pct_change_calculation(self, dummy_strategy_class, synthetic_market_data):
        oos = OOSSplitValidator(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
            oos_ratio=0.3,
        )
        result = oos.run(verbose=False)
        for metric, vals in result.degradation.items():
            assert 'is' in vals
            assert 'oos' in vals
            assert 'pct_change' in vals
