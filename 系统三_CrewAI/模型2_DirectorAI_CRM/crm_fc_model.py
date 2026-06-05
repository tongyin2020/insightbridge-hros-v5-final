# 系统三 | 模型2 | DIRECTOR_CRM_ALL_FC

            except Exception as e:
                hour_results.append(("MARE", 0, [f"ERR:{e}"]))

        for h_idx, hotel in enumerate(ALL_HOTELS):
            scenario = get_scenario(h_idx, hour)
            _ota_in = _ota_ref_45 if hotel["star"] >= 4 else _ota_ref_23
            hotel = dict(hotel)
            hotel["base_price"] = compute_dynamic_base_price(
                hotel["hotel_id"], hotel["star"], _ota_in, _cur_month
            )
            try:
                r = run_director_crm_test(hotel, signal, real_data, scenario)
                anom = detect_anomalies(hotel, r, signal, "DIRECTOR_CRM_ALL")
                cp = r.get("crm_adjusted_price", 0)
                crm_scores.append(r.get("integration_score", 0))
                conn.execute(
                    "INSERT INTO hourly_runs VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_at, hour, hotel["hotel_id"], hotel["name"], "DIRECTOR_CRM_ALL_FC",
                     signal["season"],
                     json.dumps({"scenario": scenario.name, "psrs_health": scenario.psrs_health}),
                     json.dumps({"crm_adjusted_price": cp,
                                 "psrs_status": r.get("psrs_status"),
                                 "integration_score": r.get("integration_score"),
                                 "channel": r.get("channel")}),
                     # 修正(2026-06-01): confidence列错误写入loyalty_tier，改为integration_score分级
                     cp, r.get("psrs_status"),
                     ("High"   if r.get("integration_score", 0) >= 0.60 else
                      "Medium" if r.get("integration_score", 0) >= 0.35 else "Low"),
                     str(r.get("upsell_revenue", 0)), "; ".join(anom),
                     weather_c, int(signal["is_holiday"]), int(signal["is_weekend"]))
                )
                hour_results.append(("CRM", cp, anom))
            except Exception as e:
                hour_results.append(("CRM", 0, [f"ERR:{e}"]))

        for h_idx, hotel in enumerate(ALL_HOTELS):
