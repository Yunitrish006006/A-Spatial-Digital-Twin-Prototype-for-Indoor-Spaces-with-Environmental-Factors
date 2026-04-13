# Baseline 與非連網裝置影響學習結果

本文件整理新增的兩項研究強化功能：

1. `IDW baseline comparison`
2. `non-networked appliance impact learning`

## IDW Baseline

IDW（Inverse Distance Weighting）是本研究加入的 baseline。它只使用 8 顆角落感測器的觀測值，依距離權重插值整個房間，不使用裝置位置、裝置方向或設備影響函數。

本研究模型則使用：

```text
background field + appliance influence function + active-device power calibration + trilinear sensor correction
```

因此比較 IDW baseline 可以說明：只做空間插值與加入設備影響模型之間的差異。

## 範例結果

以 `light_only` 情境為例：

| 指標 | 本研究模型 MAE | IDW MAE | MAE 降低比例 |
| --- | ---: | ---: | ---: |
| Temperature | 0.0470 | 0.1523 | 69.14% |
| Humidity | 0.1762 | 0.4656 | 62.16% |
| Illuminance | 2.7090 | 119.5279 | 97.73% |

此結果表示，對照明情境而言，只靠角落感測器做 IDW 插值難以重建中央照明影響；加入設備位置與影響函數後，照度場重建誤差明顯下降。

以 `ac_only` 情境為例：

| 指標 | 本研究模型 MAE | IDW MAE | MAE 降低比例 |
| --- | ---: | ---: | ---: |
| Temperature | 0.0502 | 0.8306 | 93.96% |
| Humidity | 0.1772 | 0.7076 | 74.96% |
| Illuminance | 1.7625 | 1.3210 | -33.42% |

其中照度在 `ac_only` 情境沒有實際設備影響，因此 IDW 可能略優；這可在論文中作為誠實限制說明：當某個變數沒有明顯設備影響時，簡單插值可能已足夠。

## 非連網裝置影響學習

新增的 `learn_impacts` 流程將裝置視為沒有 API、沒有狀態回報的非連網裝置。系統使用裝置啟用前後的感測器觀測差異，估計該裝置的影響係數。

流程如下：

```text
before sensor observations
    ↓
after sensor observations
    ↓
sensor delta
    ↓
device spatial basis
    ↓
least-squares impact coefficient learning
```

對單一 active device，模型估計：

```text
delta_v(sensor_i) ≈ coefficient_v · envelope(device, sensor_i)
```

對多個 active devices，模型使用多變量最小平方法分解不同裝置的影響。

## 範例學習結果

### `ac_only`

| 裝置 | Temperature coefficient | Humidity coefficient | Illuminance coefficient |
| --- | ---: | ---: | ---: |
| `ac_main` | -9.1798 | -5.3999 | 0.0000 |

解讀：

- 冷氣對溫度是負影響，符合降溫效果。
- 冷氣對濕度是負影響，符合弱除濕效果。
- 冷氣對照度無影響，符合模型設定。

### `light_only`

| 裝置 | Temperature coefficient | Humidity coefficient | Illuminance coefficient |
| --- | ---: | ---: | ---: |
| `light_main` | 0.8400 | 0.0000 | 1102.4793 |

解讀：

- 照明主要提升照度。
- 照明帶來少量熱效應。
- 照明對濕度無直接影響。

## 論文可用結論

加入 IDW baseline 後，本研究可以說明設備影響模型並非只是一般空間插值。加入非連網裝置影響學習後，本研究可以回應核心問題：即使裝置本身沒有連網能力，系統仍可透過有限環境感測資料估計其對溫度、濕度與照度的影響，並將該影響模型用於控制動作排序。
