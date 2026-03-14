"""Tests for ValidationSuite orchestrator."""
import pytest

from validation.validation_suite import ValidationSuite


class TestValidationSuiteRunAll:
    def test_full_run(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=50,
            mc_seed=42,
            wf_windows=2,
            wf_oos_ratio=0.25,
            verbose=False,
        )
        assert report.oos is not None
        assert report.monte_carlo is not None
        assert report.walk_forward is not None
        assert 'is_robust' in report.summary
        assert 'issues' in report.summary
        assert 'scores' in report.summary

    def test_skip_oos(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0,  # skip
            mc_simulations=50,
            mc_seed=42,
            wf_windows=2,
            verbose=False,
        )
        assert report.oos is None
        assert report.monte_carlo is not None
        assert report.walk_forward is not None

    def test_skip_monte_carlo(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=0,  # skip
            wf_windows=2,
            verbose=False,
        )
        assert report.monte_carlo is None
        assert report.oos is not None

    def test_skip_walk_forward(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=50,
            mc_seed=42,
            wf_windows=0,  # skip
            verbose=False,
        )
        assert report.walk_forward is None
        assert report.oos is not None
        assert report.monte_carlo is not None

    def test_only_monte_carlo(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0,
            mc_simulations=100,
            mc_seed=42,
            wf_windows=0,
            verbose=False,
        )
        assert report.oos is None
        assert report.monte_carlo is not None
        assert report.walk_forward is None


class TestValidationSuiteSummary:
    def test_summary_has_scores(self, dummy_strategy_class, synthetic_market_data):
        suite = ValidationSuite(
            strategy_class=dummy_strategy_class,
            market_data=synthetic_market_data,
        )
        report = suite.run_all(
            oos_ratio=0.3,
            mc_simulations=50,
            mc_seed=42,
            wf_windows=2,
            verbose=False,
        )
        scores = report.summary['scores']
        assert 'oos_degradation' in scores or report.oos is None
        assert 'mc_p_value' in scores or report.monte_carlo is None
        assert 'wf_efficiency' in scores or report.walk_forward is None
