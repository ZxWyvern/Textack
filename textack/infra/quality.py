QLEVELS = [{"name": "HIGH", "fps": 60, "maxp": 180, "stars_div": 45, "boom": 1.0}, {"name": "MED", "fps": 40, "maxp": 120, "stars_div": 70, "boom": 0.7}, {"name": "LOW", "fps": 30, "maxp": 70, "stars_div": 110, "boom": 0.45}]
def from_env(argv=None, env=None) -> int:
    a = list(argv or []) + [((env or {}).get("TEXTACK_Q", ""))]
    if "--low" in a or "low" in a: return 2
    if "--med" in a or "med" in a: return 1
    if "--high" in a or "high" in a: return 0
    return 1
def effective_interval(base: float, slow: float) -> float:
    return max(2.4, base * (1.0 + slow))
