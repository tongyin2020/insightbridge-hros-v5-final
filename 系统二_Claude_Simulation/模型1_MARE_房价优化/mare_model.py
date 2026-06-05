# 系统二 | 模型1 | MARE_ALL 房价优化
# 依赖: 共用_HROS_V5引擎/hros/ + app/services/pricing_engine.py
# HROS V5: apply_hros_v5_fields() 已集成进 pricing_engine.py

# ============================================================
# compute_dynamic_base_price
# ============================================================

def compute_dynamic_base_price(hotel_id: str, star: int,
                                ota_snapshot_price: float,
                                month: int = None) -> float:
    """
    动态计算 base_price，替代随机数方式：
      Step A — 历史参考价（四层优先级，MakCorps已停用）：
               层1 Shifter真实BAR(85%) + DSEC(15%) → 混合OTA权重
               层2 Shifter OTA折算BAR(85%) + DSEC(15%) → 混合OTA权重
               层3 冷启动：DSEC统计局(100%)，不与MakCorps fallback混合
               层4 完全冷启动兜底：OTA估算×0.97
      Step B — 星级范围截断
      Step C — 声誉情感修正 rep_adj ∈ [-0.17, +0.17]
      Step D — 库存紧张溢价（avail_level: critical/low/moderate）

    OTA权重按需求档位差异化（淡季不跟价格战，旺季锚定自身BAR）：
      大众(3-4★): LOW=0.40 / NORMAL=0.50 / HIGH=0.25
      豪华(5★):   LOW=0.15 / NORMAL=0.30 / HIGH=0.20
    """
    if month is None:
        month = datetime.now().month

    tier = {3: "3_star", 4: "4_star", 5: "5_star"}.get(star, "3_star")
    ratio = _OTA_TO_BAR_LUXURY if star == 5 else _OTA_TO_BAR_MASS
    ota_estimate = max(ota_snapshot_price * ratio, 100.0)
    # 静态基础权重（后续按需求档位覆盖）
    w_bar = _BAR_WEIGHT.get(star, 0.55)
    w_ota = _OTA_WEIGHT.get(star, 0.45)

    real_bar_avg  = None   # 来自hotel_real_data.db price_snapshots（轨道A：官网BAR）
    real_ota_avg  = None   # 来自hotel_real_data.db price_snapshots（轨道B：OTA竞对）
    dsec_adr_ref  = 0.0
    shared_conn   = None

    if _REAL_DB_PATH.exists():
        try:
            shared_conn = sqlite3.connect(str(_REAL_DB_PATH), timeout=5)

            # ── 层1：Shifter采集的真实官网BAR（最近7天快照，同月份入住日期）
            row = shared_conn.execute("""
                SELECT AVG(official_bar), COUNT(*)
                FROM price_snapshots
                WHERE hotel_id = ?
                  AND official_bar > 200
                  AND source_ok = 1
                  AND CAST(strftime('%m', checkin_date) AS INTEGER) = ?
                  AND snapshot_time >= datetime('now', '-7 days')
            """, (hotel_id, month)).fetchone()
            if row and row[1] and row[1] >= 1:
                real_bar_avg = float(row[0])

            # ── 层2备用：Booking.com OTA竞对价（最近7天）
            row_ota = shared_conn.execute("""
                SELECT AVG(booking_rate), COUNT(*)
                FROM price_snapshots
                WHERE hotel_id = ?
                  AND booking_rate > 200
                  AND CAST(strftime('%m', checkin_date) AS INTEGER) = ?
                  AND snapshot_time >= datetime('now', '-7 days')
            """, (hotel_id, month)).fetchone()
            if row_ota and row_ota[1] and row_ota[1] >= 1:
                real_ota_avg = float(row_ota[0])

        except Exception:
            pass

    if _DSEC_OK and _REAL_DB_PATH.exists():
        try:
            _dc = shared_conn or sqlite3.connect(str(_REAL_DB_PATH), timeout=5)
            dsec_adr_ref = _dsec_market_adr(month, star, _dc)
            if not shared_conn:
                _dc.close()
        except Exception:
            pass

    # ── 需求档位差异化OTA权重（覆盖静态权重）────────────────────────────────
    # 淡季不跟随OTA价格战；旺季自身BAR主导，OTA权重反而降低
    # 大众(3-4★): LOW→0.40, NORMAL→0.50, HIGH→0.25
    # 豪华(5★):   LOW→0.15, NORMAL→0.30, HIGH→0.20
    _DEMAND_OTA_W = {
        ("mass",   "LOW"):    0.40, ("mass",   "NORMAL"): 0.40, ("mass",   "HIGH"): 0.25,

# ============================================================
# run_3star_test (MARE主函数)
# ============================================================

def run_3star_test(hotel: dict, signal: dict, real_data: dict,
                    scenario: HotelScenario) -> dict:
    """
    MARE 房价优化模型测试。
    外部因子来自实时抓取数据（Booking.com/天气/渡轮）。
    内部因子来自 scenario（入住率/客户画像/预订节奏），
    确保极端场景被系统性测试。
    """
    occupancy = scenario.occupancy

    # 竞对价格：Booking.com实时价格 × 场景调整系数
    real_prices = real_data.get("booking_prices_3", [])
    if real_prices:
        base_comp = float(sum(real_prices) / len(real_prices))
        competitor_price = max(200.0, base_comp * scenario.competitor_price_multiplier
                               * random.uniform(0.97, 1.03))
        competitor_availability = real_data.get("competitor_availability_real", 0.5)
    else:
        competitor_price = hotel["base_price"] * scenario.competitor_price_multiplier
        competitor_availability = max(0.05, 1.0 - occupancy - 0.10)

    upper_tier = real_data.get("upper_tier_adr_real") or None
    remaining = max(1, int(hotel["total_rooms"] * scenario.remaining_inventory_ratio))

    req = RecommendationRequest(
        hotel_id=hotel["hotel_id"],
        hotel_star=hotel.get("star", 3),   # 竞对权重差异化：3-4★ vs 5★
        season=signal["season"],
        base_price=hotel["base_price"],
        # 外部实时信号
        holiday=signal["holiday"],
        weekend=signal["weekend"],
        border_flow=signal["border_flow"],
        visitors_stats=signal["visitors_stats"],
        flight_ferry=signal["flight_ferry"],
        zhuhai_saturation=signal["zhuhai_saturation"],
        ota_booking_pace=signal["ota_booking_pace"],
        weather=signal["weather_signal"],
        event_ticket_sales=signal["event_ticket_sales"],
        # 竞对（实时+场景调整）
        competitor_price=competitor_price,
        competitor_availability=competitor_availability,
        upper_tier_adr=upper_tier,
        # 内部数据（来自scenario，非随机）
        current_occupancy=occupancy,
        remaining_inventory=remaining,
        total_rooms=hotel["total_rooms"],
        booking_velocity_24h=scenario.booking_velocity_24h,
        days_to_arrival=scenario.days_to_arrival,
        cancellation_rate=scenario.cancellation_rate,
        # DSEC 澳门统计局月度需求信号
        dsec_market_occ=signal.get("dsec_market_occ", 0.0),
    )
    result = pe.recommend(req, hotel_settings=_hotel_settings(hotel))

    # ── Phase 2：价格弹性 RevPAR 最优化 ──────────────────────────────────────
    if _ELASTICITY_OK and result.get("recommended_price", 0) > 0:
        mkt_price = (float(sum(real_prices) / len(real_prices))
                     if real_prices else hotel["base_price"])
        # 修复(2026-06-02 P3-A): 防止OTA淡季低价(≤500 MOP)将搜索基准拉至不合理水平
        # DSEC后疫情3★年均ADR≈950 MOP；低季节最低合理参考 = 950×0.70 = 665，取整680
        _mkt_floor = {3: 680, 4: 900, 5: 1400}
        mkt_price = max(mkt_price, _mkt_floor.get(hotel.get("star", 3), 680))
        er = _elasticity_optimize(
            candidate_price = result["recommended_price"],
            market_price    = mkt_price,
            star            = hotel.get("star", 3),
            district        = hotel.get("district", "NAPE"),
            demand_level    = signal.get("demand_state", "NORMAL"),
            season          = signal.get("season", "normal"),
            hotel_id        = hotel.get("hotel_id"),
        )
        result["recommended_price"]   = er.optimal_price
        result["predicted_occupancy"] = er.predicted_occupancy
        result["predicted_revpar"]    = er.predicted_revpar
        result["baseline_revpar"]     = er.baseline_revpar
        result["expected_revenue_lift"] = f"+{er.true_lift_pct:.1f}%"
        result["elasticity_used"]     = er.elasticity_used
        result["elasticity_source"]   = er.data_source

    return result


# ── 4-5星自主获客模型测试 ──────────────────────────────────────────────────────
