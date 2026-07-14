# 变电所扩建方案设计

**日期**: 2026-07-14  
**状态**: 已确认  
**关联**: PWR-02 供电潮流计算

## 背景

当前供电系统仅配置 2 座变电所（SUB01 @ 0m, SUB02 @ 3200m），覆盖 18.6km 线路。车辆运行方向为上行（18600m → 0m），南段列车距最近变电所最远达 15.4km，单列车最大压降达 1025V，导致受电弓端电压被钳位至 1000V 底线。

## 方案选择

采用**三站一变电所**方案，在线路全程设置 8 座变电所，覆盖全部 24 站。

### 配置详情

| 变电所 | chainage | 覆盖站点 | 间距 |
|:---|:---|:---|:---|
| SUB01 | 0m | ST01~ST03 (安河桥北→西苑) | — |
| SUB02 | 2800m | ST04~ST06 (圆明园→中关村) | 2.8km |
| SUB03 | 5100m | ST07~ST09 (海淀黄庄→魏公村) | 2.3km |
| SUB04 | 7300m | ST10~ST12 (国家图书馆→西直门) | 2.2km |
| SUB05 | 10000m | ST13~ST15 (新街口→西四) | 2.7km |
| SUB06 | 12000m | ST16~ST18 (灵境胡同→宣武门) | 2.0km |
| SUB07 | 14300m | ST19~ST21 (菜市口→北京南站) | 2.3km |
| SUB08 | 18600m | ST22~ST24 (马家堡→公益西桥) | 4.3km |

### 电压分析

- 回路电阻：0.03 Ω/km
- 单列车最大取流：~2220 A（3.33MW @ 1500V）

最差场景为 SUB04-SUB05 之间（8650m），距最近变电所 ~1.35km：

```
ΔV = 2220A × 0.03Ω/km × 1.35km ≈ 90V
V_panto = 1500 - 90 = 1410V > 1000V 底线 ✅
```

### 负载分析

3 列车发车间隔 120s，典型间距约 2.7km。变电所间距 2.0~4.3km，正常情况下每列车分布在独立变电所上，单站负载 ≤ 3.3MW，在 5MW 额定容量内。

### SUB07→SUB08 间距说明

SUB07（14300m）到 SUB08（18600m）间距 4.3km，是最大跨距。中间点（16450m）距最近变电所 ~2.15km，压降约 143V → V=1357V，仍在安全范围内。选择 18600m 而非中间点设置 SUB08 是因为线路端头必须有变电所保障折返供电。

## 影响范围

- **修改文件**：仅 `backend/sim_engine/config/power.yaml`
- **代码逻辑**：无需变更（现有 `load_flow.py` 的多列车独立分配逻辑已支持任意数量变电所）
- **测试**：现有 `test_power.py` 使用 `_make_network()` 自定义网络，不受配置变更影响
- **前端**：API 返回的 `substationStates` 数组自动扩展，显示面板无需修改

## 变更内容

```yaml
# power.yaml — substations 段替换
substations:
  - { chainage: 0,     id: SUB01, name: 安河桥北变电所,   rated_power: 5000, rated_voltage: 1500 }
  - { chainage: 2800,  id: SUB02, name: 圆明园变电所,     rated_power: 5000, rated_voltage: 1500 }
  - { chainage: 5100,  id: SUB03, name: 海淀黄庄变电所,   rated_power: 5000, rated_voltage: 1500 }
  - { chainage: 7300,  id: SUB04, name: 国家图书馆变电所,  rated_power: 5000, rated_voltage: 1500 }
  - { chainage: 10000, id: SUB05, name: 新街口变电所,     rated_power: 5000, rated_voltage: 1500 }
  - { chainage: 12000, id: SUB06, name: 灵境胡同变电所,   rated_power: 5000, rated_voltage: 1500 }
  - { chainage: 14300, id: SUB07, name: 菜市口变电所,     rated_power: 5000, rated_voltage: 1500 }
  - { chainage: 18600, id: SUB08, name: 公益西桥变电所,   rated_power: 5000, rated_voltage: 1500 }
```
