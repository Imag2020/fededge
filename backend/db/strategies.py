# strategies.py
STRATEGIES = {
    "Conservative": {
        "edge_safety_margin_bps": 25,
        "risk_budget_pct": 0.10,
        "max_trades_per_interval": 1,
        "min_holding_min": 120,
        "cooldown_min": 120,
    },
    "Balanced": {
        "edge_safety_margin_bps": 18,
        "risk_budget_pct": 0.18,
        "max_trades_per_interval": 1,
        "min_holding_min": 60,
        "cooldown_min": 60,
    },
    "Aggressive": {
        "edge_safety_margin_bps": 12,
        "risk_budget_pct": 0.28,
        "max_trades_per_interval": 2,
        "min_holding_min": 30,
        "cooldown_min": 30,
    },
    "Scalping": {
        "edge_safety_margin_bps": 20,
        "risk_budget_pct": 0.08,
        "max_trades_per_interval": 1,
        "min_holding_min": 5,
        "cooldown_min": 10,
    },
}
