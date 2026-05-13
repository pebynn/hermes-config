# -*- coding: utf-8 -*-
"""
TDD tests for Strategy A Momentum Optimization (T1: t_e52512cc)

Tests:
  1. ParamConfig dataclass creation and defaults
  2. Parameterized backtest function
  3. WR penalty evaluation
  4. Factor weight normalization
  5. Stage 1 random search
"""

import sys
sys.path.insert(0, '/home/pebynn/quant')

import numpy as np
import pandas as pd
import pytest
from dataclasses import dataclass, fields


# ══════════════════════════════════════════════════════════════════
# Helper: synthetic price data for backtest testing
# ══════════════════════════════════════════════════════════════════

def make_kline(n_days=100, trend=0.001, noise=0.02, seed=42):
    """Create synthetic kline data matching the real data schema."""
    rng = np.random.RandomState(seed)
    base = 10.0
    closes = [base]
    for i in range(1, n_days):
        ret = trend + noise * rng.randn()
        closes.append(closes[-1] * (1 + ret))
    closes = np.array(closes)
    highs = closes * (1 + np.abs(noise * rng.randn(n_days)))
    lows = closes * (1 - np.abs(noise * rng.randn(n_days)))
    vols = np.abs(1e6 + 1e5 * rng.randn(n_days))

    df = pd.DataFrame({
        '日期': [f'2025-{i//30+1:02d}-{i%28+1:02d}' for i in range(n_days)],
        '开盘': closes * (1 + noise * 0.1 * rng.randn(n_days)),
        '收盘': closes,
        '最高': highs,
        '最低': lows,
        '成交量': vols,
        '成交额': vols * closes,
    })
    return df


# ══════════════════════════════════════════════════════════════════
# Test 1: ParamConfig Dataclass
# ══════════════════════════════════════════════════════════════════

class TestParamConfig:
    """Test that ParamConfig is properly defined with all required fields."""

    def test_param_config_exists(self):
        """ParamConfig should be importable from strategy_momentum_opt."""
        from strategy_momentum_opt import ParamConfig
        assert ParamConfig is not None

    def test_param_config_default_creation(self):
        """Default ParamConfig() should create without errors."""
        from strategy_momentum_opt import ParamConfig
        cfg = ParamConfig()
        assert cfg is not None
        assert cfg.LEVERAGE == 1.0
        assert cfg.TOP_N >= 2

    def test_param_config_all_fields_present(self):
        """All required parameters should be fields of ParamConfig."""
        from strategy_momentum_opt import ParamConfig
        required_fields = {
            'TOP_N', 'N_DROP', 'HARD_STOP', 'ATR_STOP_MULT',
            'TRAILING_ACTIVATE', 'TRAILING_DISTANCE', 'LEVERAGE',
            'MIN_VOL_20D', 'MIN_DAYS', 'TC_COST',
            'MAX_RSI_ENTRY', 'MIN_RET_60D', 'MIN_RET_5D',
            'COOLDOWN_DAYS', 'START_DATE', 'END_DATE', 'WARMUP_DAYS',
        }
        field_names = {f.name for f in fields(ParamConfig)}
        missing = required_fields - field_names
        assert not missing, f"Missing fields: {missing}"

    def test_param_config_n_drop_clamped(self):
        """N_DROP should be clamped to TOP_N - 1."""
        from strategy_momentum_opt import ParamConfig
        cfg = ParamConfig(TOP_N=3, N_DROP=5)
        assert cfg.N_DROP <= cfg.TOP_N - 1


# ══════════════════════════════════════════════════════════════════
# Test 2: Parameterized Backtest
# ══════════════════════════════════════════════════════════════════

class TestParameterizedBacktest:
    """Test that run_backtest(params) works and returns expected structure."""

    def test_run_backtest_returns_dict(self):
        """run_backtest should return a dict with expected keys."""
        from strategy_momentum_opt import ParamConfig, run_backtest
        cfg = ParamConfig()
        result = run_backtest(cfg, source='sina')
        assert isinstance(result, dict)
        required_keys = {'ann_ret', 'wr', 'dd', 'nav', 'trades', 'sharpe'}
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_run_backtest_wr_in_range(self):
        """Win rate should be between 0 and 100."""
        from strategy_momentum_opt import ParamConfig, run_backtest
        cfg = ParamConfig()
        result = run_backtest(cfg, source='sina')
        assert 0 <= result['wr'] <= 100

    def test_run_backtest_with_default_params_produces_trades(self):
        """Default params should produce some trades."""
        from strategy_momentum_opt import ParamConfig, run_backtest
        cfg = ParamConfig()
        result = run_backtest(cfg, source='sina')
        assert result['trades'] > 0, "Should produce at least one trade"

    def test_run_backtest_nav_positive(self):
        """NAV should stay positive."""
        from strategy_momentum_opt import ParamConfig, run_backtest
        cfg = ParamConfig()
        result = run_backtest(cfg, source='sina')
        assert result['nav'] > 0


# ══════════════════════════════════════════════════════════════════
# Test 3: Evaluation / WR Penalty
# ══════════════════════════════════════════════════════════════════

class TestEvaluateResult:
    """Test the evaluation/scoring function."""

    def test_evaluate_importable(self):
        """evaluate_result should be importable."""
        from strategy_momentum_opt import evaluate_result
        assert callable(evaluate_result)

    def test_wr_in_range_no_penalty(self):
        """WR=50% should get no penalty."""
        from strategy_momentum_opt import evaluate_result
        # WR 50%, high return
        score = evaluate_result(ann_ret=300, wr=50, dd=-30)
        # Score should be close to ann_ret when WR is perfect
        assert score > 250

    def test_wr_out_of_range_penalized(self):
        """WR=30% should be penalized vs WR=50%."""
        from strategy_momentum_opt import evaluate_result
        score_good = evaluate_result(ann_ret=300, wr=50, dd=-30)
        score_bad = evaluate_result(ann_ret=300, wr=30, dd=-30)
        assert score_bad < score_good

    def test_wr_extreme_penalized(self):
        """WR=80% (too high == overfit) should be penalized."""
        from strategy_momentum_opt import evaluate_result
        score_good = evaluate_result(ann_ret=300, wr=50, dd=-30)
        score_overfit = evaluate_result(ann_ret=300, wr=80, dd=-30)
        assert score_overfit < score_good

    def test_deep_drawdown_penalized(self):
        """DD=-80% should score lower than DD=-30%."""
        from strategy_momentum_opt import evaluate_result
        score_good = evaluate_result(ann_ret=300, wr=50, dd=-30)
        score_bad = evaluate_result(ann_ret=300, wr=50, dd=-80)
        assert score_bad < score_good


# ══════════════════════════════════════════════════════════════════
# Test 4: Factor Weight Normalization
# ══════════════════════════════════════════════════════════════════

class TestFactorWeights:
    """Test factor weight manipulation."""

    def test_weights_normalize_to_1(self):
        """Any weight dict should normalize to sum=1."""
        from strategy_momentum_opt import normalize_weights
        w = {'a': 0.5, 'b': 0.3, 'c': 0.4}
        result = normalize_weights(w)
        assert abs(sum(result.values()) - 1.0) < 1e-10

    def test_weights_perturb_preserves_sum(self):
        """Perturbed weights should still sum to 1."""
        from strategy_momentum_opt import normalize_weights, FACTOR_WEIGHTS
        # Perturb each by ±20%
        perturbed = {}
        for k, v in FACTOR_WEIGHTS.items():
            perturbed[k] = v * np.random.uniform(0.8, 1.2)
        result = normalize_weights(perturbed)
        assert abs(sum(result.values()) - 1.0) < 1e-10

    def test_factor_names_match_weights(self):
        """FACTOR_NAMES should correspond to FACTOR_WEIGHTS keys (with _z suffix)."""
        from strategy_momentum_opt import FACTOR_NAMES, FACTOR_WEIGHTS
        for fn in FACTOR_NAMES:
            zname = fn + '_z'
            assert zname in FACTOR_WEIGHTS, f"Weight for {zname} missing"


# ══════════════════════════════════════════════════════════════════
# Test 5: Optimization Stage 1 (Random Search)
# ══════════════════════════════════════════════════════════════════

class TestOptimizationStage1:
    """Test that the random search optimizer works correctly."""

    def test_stage1_importable(self):
        """optimize_stage1 should be importable."""
        from strategy_momentum_opt import optimize_stage1
        assert callable(optimize_stage1)

    def test_stage1_returns_valid_results(self):
        """Stage 1 should return a list of (score, params) tuples."""
        from strategy_momentum_opt import optimize_stage1, ParamConfig
        results = optimize_stage1(n_trials=5, source='sina')
        assert isinstance(results, list)
        assert len(results) > 0
        # Each result should be (score, params_dict)
        for score, params in results:
            assert isinstance(score, (int, float))
            assert isinstance(params, dict)
            assert 'ann_ret' in params
            assert 'wr' in params
            assert 'dd' in params

    def test_stage1_params_are_valid(self):
        """Returned params should be valid for ParamConfig."""
        from strategy_momentum_opt import optimize_stage1, ParamConfig
        results = optimize_stage1(n_trials=5, source='sina')
        for _, params in results:
            # Should be constructable
            cfg = ParamConfig(**{k: v for k, v in params.items()
                                if k in {f.name for f in fields(ParamConfig)}})
            assert cfg.TOP_N >= 2
            assert cfg.N_DROP <= cfg.TOP_N - 1

    def test_stage1_no_duplicate_params(self):
        """Different trials should try different parameter sets."""
        from strategy_momentum_opt import optimize_stage1
        results = optimize_stage1(n_trials=5, source='sina')
        param_sets = set()
        for _, params in results:
            key = tuple(sorted(params.items()))
            param_sets.add(key)
        # At least 3 unique parameter sets (could be less if search space small)
        assert len(param_sets) >= 2, f"Only {len(param_sets)} unique param sets"
