# InsightBridge HROS V5 — 九大AI模型最终版本

**版本**: V5.0 Final | **日期**: 2026-06-05  
**状态**: ✅ 生产就绪（7/7 测试通过）

---

## 架构概览

```
InsightBridge_HROS_V5_Final/
│
├── 共用_HROS_V5引擎/          ← 三大系统共用的核心算法
│   └── hros/                  ← HROS V5 Package（P0/P1已修复）
│
├── 系统一_ChatGPT_Harness/
│   ├── 模型1_MARE_房价优化/
│   ├── 模型2_DirectorAI_CRM/
│   └── 模型3_SelfACQ_自主获客/
│
├── 系统二_Claude_Simulation/
│   ├── 模型1_MARE_房价优化/   ← 含 pricing_engine.py + HROS V5集成
│   ├── 模型2_DirectorAI_CRM/
│   └── 模型3_SelfACQ_自主获客/
│
└── 系统三_CrewAI/
    ├── 模型1_MARE_房价优化/   ← Firecrawl 真实数据增强
    ├── 模型2_DirectorAI_CRM/
    └── 模型3_SelfACQ_自主获客/
```

---

## HROS V5 修复内容

| 优先级 | 模块 | 修复内容 |
|--------|------|---------|
| **P0** | `direct_ltv_engine.py` | 添加折现因子（discount_rate=10%），修复直销LTV系统性高估 |
| **P1** | `risk_engine.py` | 风险分归一化（/3.0），解决极端场景全部压缩为100的问题 |
| **P1** | `opportunity_engine.py` | 权重重构（基础最高91分），避免机会分过早满分 |
| **P1** | `crm_value_engine.py` | margin_rate 默认从0.65降至0.60，可配置 |

---

## 快速使用

```python
from hros.direct_ltv_engine import DirectLTVEngine
from hros.risk_engine import calculate_price_risk
from hros.opportunity_engine import calculate_opportunity_score

# 直销LTV（P0修复版，含折现）
decision = DirectLTVEngine().evaluate_direct_offer(
    direct_price=1100, ota_gross_price=1200,
    ota_commission_rate=0.15, repeat_probability=0.20,
    future_margin=700, discount_rate=0.10
)
print(f"直销LTV: {decision.direct_ltv} | 折现后复购: {decision.discounted_future_value}")
```

---

## 测试

```bash
cd 共用_HROS_V5引擎
python -m pytest tests/ -v
# 预期：7/7 PASSED
```

---

*InsightBridge Global | HROS V5 | 2026-06-05*
