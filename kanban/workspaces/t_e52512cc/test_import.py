#!/home/pebynn/tools/quant_env/bin/python3
"""Quick import test for new strategy_momentum_opt."""
import sys
sys.path.insert(0, '/home/pebynn/.hermes/kanban/workspaces/t_e52512cc')

# Import module-like
import importlib.util
spec = importlib.util.spec_from_file_location("smo", "strategy_momentum_opt_new.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

print('ParamConfig:', mod.ParamConfig())
print('run_backtest:', callable(mod.run_backtest))
print('evaluate_result:', callable(mod.evaluate_result))
print('normalize_weights:', callable(mod.normalize_weights))
print('optimize_stage1:', callable(mod.optimize_stage1))
print('All imports OK')
