# 系统三 | 模型1 | MARE_ALL_FC
# Firecrawl 真实信号增强：border_flow/zhuhai/ota_booking_pace

        _ota_ref_45 = float(real_data["upper_tier_adr_real"]) \
            if real_data.get("upper_tier_adr_real") else 2000.0

        for h_idx, hotel in enumerate(ALL_HOTELS):
            scenario = get_scenario(h_idx, hour)
            # 动态计算base_price：DSEC×85% + MakCorps×15%（替代随机数）
            _ota_in = _ota_ref_45 if hotel["star"] >= 4 else _ota_ref_23
            hotel = dict(hotel)
            hotel["base_price"] = compute_dynamic_base_price(
                hotel["hotel_id"], hotel["star"], _ota_in, _cur_month
            )
            # 4-5星酒店MARE用高端竞对价格
            if hotel["star"] >= 4 and real_data.get("upper_tier_adr_real"):
                rd = dict(real_data); rd["booking_prices_3"] = [real_data["upper_tier_adr_real"]]
            else:
                rd = real_data
            try:
                r = run_23star_test(hotel, signal, rd, scenario)
                # ── Phase 2：弹性引擎 RevPAR 最优化 ──────────────────────
                if _ELASTICITY_OK_CREWAI and r.get("recommended_price", 0) > 0:
                    mkt_price = float(_ota_ref_45 if hotel["star"] >= 4 else _ota_ref_23)
                    # 修复(2026-06-02 P3-A): 防止OTA淡季低价将弹性搜索基准拉至不合理水平
                    _mkt_floor = {3: 680, 4: 900, 5: 1400}
                    mkt_price = max(mkt_price, _mkt_floor.get(hotel.get("star", 3), 680))
                    er = _elasticity_optimize(
                        candidate_price = r["recommended_price"],
                        market_price    = mkt_price,
                        star            = hotel["star"],
                        district        = hotel.get("district", "NAPE"),
                        demand_level    = signal.get("demand_state", "NORMAL"),
                        season          = signal.get("season", "normal"),
                        hotel_id        = hotel.get("hotel_id"),
                    )
                    r["recommended_price"]   = er.optimal_price
                    r["predicted_occupancy"] = er.predicted_occupancy
                    r["predicted_revpar"]    = er.predicted_revpar
                    r["expected_revenue_lift"] = f"+{er.true_lift_pct:.1f}%"
                    r["elasticity_used"]     = er.elasticity_used
                anom = detect_anomalies(hotel, r, signal, "MARE_ALL")
                rp = r.get("recommended_price", 0)
                mare_prices.append(rp)
                conn.execute(
                    "INSERT INTO hourly_runs VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_at, hour, hotel["hotel_id"], hotel["name"], "MARE_ALL_FC",
                     signal["season"],
                     json.dumps({"scenario": scenario.name,
                                 "border_source": signal["border_flow_source"],
                                 "zhuhai_source": signal["zhuhai_source"],
                                 "ota_source": signal["ota_pace_source"]}),
                     json.dumps({"recommended_price": rp,
                                 "demand_state": r.get("demand_state"),
                                 "confidence": r.get("confidence"),
                                 "predicted_occupancy": r.get("predicted_occupancy"),
                                 "predicted_revpar": r.get("predicted_revpar"),
                                 "elasticity_used": r.get("elasticity_used")}),
                     rp, r.get("demand_state"), r.get("confidence"),
                     r.get("expected_revenue_lift"), "; ".join(anom),
                     weather_c, int(signal["is_holiday"]), int(signal["is_weekend"]))
                )
                hour_results.append(("MARE", rp, anom))
            except Exception as e:
                hour_results.append(("MARE", 0, [f"ERR:{e}"]))

        for h_idx, hotel in enumerate(ALL_HOTELS):
