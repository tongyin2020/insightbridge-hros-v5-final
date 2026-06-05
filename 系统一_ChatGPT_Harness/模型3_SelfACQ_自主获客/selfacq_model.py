# 系统一 | 模型3 | SelfACQ 自主获客

def evaluate_result(name: str, result: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    price = result.get("recommended_price")
    if not isinstance(price, (int, float)):
        issues.append("missing_recommended_price")
        return issues
    if price <= 0:
        issues.append("non_positive_price")
    if price > 100000:
        issues.append("implausibly_high_price")
    report = result.get("guardrail_report") or {}
    final_price = report.get("final_price")
    if isinstance(final_price, (int, float)) and final_price <= 0:
        issues.append("invalid_guardrail_final_price")
    if name == "director":
        cp = result.get("channel_pricing") or {}
        ota = cp.get("ota_price")
        direct = cp.get("direct_price")
        vip = cp.get("vip_price")
        if all(isinstance(x, (int, float)) for x in (ota, direct, vip)):
            if not (ota > direct >= vip):
                issues.append("channel_hierarchy_broken")
    return issues




# ── SelfACQ 关键逻辑 ──
    from run_simulation import run_45star_test as _run_selfacq
    _SELFACQ_OK = True
    _SELFACQ_OK = False
    def _run_selfacq(hotel, signal, real_data, scenario):
        return {"direct_offer_price": 0, "direct_wins_vs_ota": False, "error": str(_e)}
        "selfacq_runs": 0,
        "selfacq_failures": 0,
        # ── 自主获客集成模型（SELFACQ）：全部76家酒店 × 14标准场景 ────────────
        if _SELFACQ_OK and _SIM_SCENARIOS:
                        result = _run_selfacq(hotel_with_base, _signal, _real_data, sc)
                        if result.get("direct_offer_price", 0) <= 0:
                            issues.append("selfacq_error")
                        issues = ["selfacq_exception"]
                    global_counts["selfacq_runs"] += 1
                        global_counts["selfacq_failures"] += 1
                        "model": "selfacq",
                record.get("result", {}).get("direct_offer_price", 0)
        if "direct_offer_price" in result and result["direct_offer_price"]:
            ltv_dec = DirectLTVEngine().evaluate_direct_offer(
                direct_price=float(result["direct_offer_price"]),
