# 系统一 | 模型2 | DirectorAI CRM

def run_director(repo_path: Path, payload: dict[str, Any], objective_mode: str) -> tuple[bool, dict[str, Any]]:
    script = r"""
import json, sys
from types import SimpleNamespace
from app.core.pricing_engine import recommend
payload = json.loads(sys.argv[1])
objective_mode = payload.pop("_objective_mode", "maximize_revenue")
hotel_settings = SimpleNamespace(
    floor_price=float(payload.get("floor_price", 750)),
    ceiling_price=float(payload.get("ceiling_price", 1015)),
)
result = recommend(payload, hotel_settings, objective_mode=objective_mode)
print(json.dumps(result))
"""
    payload = dict(payload)
    payload["_objective_mode"] = objective_mode
    return run_python_snippet(repo_path / "backend", repo_path / "backend", script, payload)


