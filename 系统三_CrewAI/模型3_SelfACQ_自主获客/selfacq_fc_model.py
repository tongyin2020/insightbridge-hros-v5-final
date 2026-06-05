# 系统三 | 模型3 | SELFACQ_ALL_FC 自主获客

            except Exception as e:
                hour_results.append(("CRM", 0, [f"ERR:{e}"]))

        for h_idx, hotel in enumerate(ALL_HOTELS):
            scenario = get_scenario(h_idx, hour)
            _ota_in = _ota_ref_45 if hotel["star"] >= 4 else _ota_ref_23
            hotel = dict(hotel)
            hotel["base_price"] = compute_dynamic_base_price(
                hotel["hotel_id"], hotel["star"], _ota_in, _cur_month
            )
            try:
                r = run_45star_test(hotel, signal, real_data, scenario)
                anom = detect_anomalies(hotel, r, signal, "SELFACQ_ALL")
                dp = r.get("direct_offer_price", 0)
                if r.get("direct_wins_vs_ota"): acq_wins += 1
                conn.execute(
                    "INSERT INTO hourly_runs VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_at, hour, hotel["hotel_id"], hotel["name"], "SELFACQ_ALL_FC",
                     signal["season"],
                     json.dumps({"scenario": scenario.name,
                                 "competitor_mult": scenario.competitor_price_multiplier}),
                     json.dumps({"direct_offer_price": dp,
                                 "ota_standard_price": r.get("ota_standard_price"),
                                 "direct_wins_vs_ota": r.get("direct_wins_vs_ota")}),
                     # 修正(2026-06-01): confidence列错误写入loyalty_tier，改为直销胜出置信度
                     dp, "HIGH" if r.get("demand_high") else "NORMAL",
                     ("High"   if r.get("direct_wins_vs_ota") and
                                  r.get("direct_net_revenue", 0) > r.get("ota_net_revenue", 0) * 1.05
                      else "Medium" if r.get("direct_wins_vs_ota")
                      else "Low"),
                     f"+{r.get('revpar_lift_vs_market', '0%')}", "; ".join(anom),
                     weather_c, int(signal["is_holiday"]), int(signal["is_weekend"]))
                )
                hour_results.append(("ACQ", dp, anom))
            except Exception as e:
                hour_results.append(("ACQ", 0, [f"ERR:{e}"]))

        conn.commit()

        # ── 步骤5：与Playwright基线对比 ──────────────────────────────
        baseline = read_playwright_baseline(hour)
        avg_mare = sum(mare_prices) / len(mare_prices) if mare_prices else 0
        avg_crm  = sum(crm_scores) / len(crm_scores) if crm_scores else 0
        mare_diff = ((avg_mare - baseline.get("avg_mare", avg_mare)) /
                     max(1, baseline.get("avg_mare", avg_mare)) * 100) if baseline else 0

        # 计算Firecrawl真实抓取覆盖率（scenario_*和simulated均算fallback，不计入✓）
        _bad = ("simulated", "fallback", "failed", "unavailable")
        fc_real_count = sum([
