# 可參考模型整理

本文整理可作為本論文第二章文獻探討與第三章方法設計的模型。建議本研究採用「輕量化混合模型」作為主軸：用物理啟發的簡化模型描述設備影響，用有限感測器做校正，不直接使用 CFD 或大型深度學習模型。

## 建議採用的核心模型

### 1. 空間數位孿生總模型

本研究可將單房間狀態定義為三個環境場：

```text
T(x, y, z, t): temperature field
H(x, y, z, t): humidity field
L(x, y, z, t): illuminance field
```

任一變數 `v` 可表示為：

```text
F_v(x, y, z, t) = B_v(x, y, z) + Σ I_j,v(x, y, z, t) + C_v(x, y, z)
```

其中：

- `B_v` 是背景場。
- `I_j,v` 是第 `j` 個設備對變數 `v` 的影響函數。
- `C_v` 是由 8 顆角落感測器殘差建立的校正場。

這個形式可以連接 digital twin、空間場估計與設備影響推估三個研究重點。

### 2. 一階動態響應模型

設備啟動後，環境不會瞬間達到穩態，因此可用一階響應描述設備影響強度：

```text
u_j(t) = a_j · (1 - exp(-t / τ_j))
```

其中：

- `a_j` 是設備啟用程度或出力。
- `τ_j` 是設備時間常數。
- `u_j(t)` 是時間 `t` 時的有效作用強度。

此模型適合冷氣降溫、窗戶換氣與照明開啟後的簡化動態。

### 3. 設備空間影響函數

每個設備對空間某點的影響可用距離衰減與方向性權重描述：

```text
I_j,v(x, y, z, t) = β_j,v · u_j(t) · exp(-d_j / λ_j) · D_j(x, y, z)
```

其中：

- `β_j,v` 是設備對環境變數 `v` 的影響強度。
- `d_j` 是設備到目標點的距離。
- `λ_j` 是影響半徑或衰減尺度。
- `D_j` 是方向性權重。

這比完整 CFD 簡單，但能保留「設備位置」、「作用方向」與「距離衰減」三個重要因素。

### 4. 角落感測器校正模型

本研究固定使用 8 顆角落感測器，因此建議先採用 affine correction：

```text
C_v(x, y, z) = θ_0 + θ_x x + θ_y y + θ_z z
```

用 8 個感測器的觀測殘差估計 `θ`：

```text
r_i,v = y_i,v - F_v(x_i, y_i, z_i)
```

此模型優點是：

- 參數少，8 顆感測器足夠估計。
- 可解釋為整體偏移與一階空間梯度校正。
- 比 Kriging 或 Gaussian Process 更適合論文初版原型。

## 各環境因素可參考模型

### Temperature: RC / Grey-Box Thermal Model

建築熱模型常用 thermal resistance-capacitance network，簡稱 RC model。概念是把牆、窗、室內空氣與熱容量用類似電路的熱阻與熱容表示。

簡化成單房間一階模型：

```text
dT_in/dt = (T_out - T_in) / τ_env + Q_ac + Q_light + Q_solar
```

本研究不需要完整建立牆體 RC 網路，但可以引用 RC model 作為冷氣與外氣交換的理論基礎。

適合本研究的用法：

- 將冷氣視為負熱源。
- 將照明視為小型正熱源。
- 將窗戶視為室外溫度與室內溫度的交換項。
- 使用一階時間常數表示動態。

### Humidity: Zone Moisture Balance

濕度可參考 zone air moisture balance。完整模型通常使用 humidity ratio，而不是直接使用 relative humidity。

簡化形式：

```text
dH_in/dt = α_window · (H_out - H_in) + α_ac · H_ac + S_h
```

其中：

- `α_window` 表示窗戶或通風造成的濕度交換。
- `H_out` 是室外濕度條件。
- `α_ac · H_ac` 表示冷氣除濕影響。
- `S_h` 是室內濕氣來源，本研究初版可先設為 0 或固定常數。

論文中應說明：濕度是次核心變數，因此採一階簡化，不做完整吸放濕與牆體濕傳。

### Illuminance: Point-Source / Inverse-Square / Cosine Model

照度可用點光源近似模型：

```text
E = I · cos(θ) / d²
```

其中：

- `E` 是照度。
- `I` 是光源發光強度。
- `d` 是光源到目標點距離。
- `θ` 是入射方向與受光面法線的夾角。

本研究可以將室內照明和窗戶日照都視為簡化光源：

- 燈具：以天花板點光源或面光源近似。
- 窗戶：以方向性外部光源或入射邊界近似。

若論文不想處理反射與材質，應明確說明本研究只處理直接光與簡化衰減，不做 radiosity 或 ray tracing。

## 空間場估計可參考模型

### IDW

Inverse Distance Weighting 是最簡單的空間插值方法：

```text
F(x) = Σ w_i(x) y_i / Σ w_i(x)
w_i(x) = 1 / d_i^p
```

優點是簡單、可解釋；缺點是無法自然表示不確定性。

適合用途：

- 當作 baseline。
- 與本研究的 affine correction 比較。

### RBF

Radial Basis Function interpolation 可用徑向基底函數建立較平滑的空間場。

適合用途：

- 當作較平滑的插值 baseline。
- 未來如果要提高空間解析度，可取代 affine correction。

### Kriging / Gaussian Process Regression

Kriging 與 Gaussian Process Regression 適合處理空間相關性，且能輸出不確定性。

適合用途：

- 作為文獻探討的重要模型。
- 作為未來改進版本。
- 若論文後期需要更強的方法論，可將 affine correction 升級為 Gaussian Process correction。

目前不建議一開始就採用 GPR，原因是 8 顆感測器點位太少，kernel 與超參數估計容易不穩，反而會增加論文風險。

## 舒適度與決策模型

### Simple Comfort Score

本研究目前最適合使用加權偏差分數：

```text
Score = w_T · e_T + w_H · e_H + w_L · e_L
```

其中：

- `e_T` 是溫度偏離目標的懲罰。
- `e_H` 是濕度偏離目標的懲罰。
- `e_L` 是照度偏離目標的懲罰。

候選動作的改善分數：

```text
Improvement(a) = Score_before - Score_after(a)
```

然後依 improvement 由高到低排序。

### PMV / PPD

PMV/PPD 是熱舒適研究常見模型，並與 ASHRAE 55、ISO 7730 相關。但 PMV 需要更多參數：

- air temperature
- mean radiant temperature
- air speed
- relative humidity
- metabolic rate
- clothing insulation

本研究目前沒有完整量測 mean radiant temperature、air speed、metabolic rate 和 clothing insulation，因此不建議把 PMV 作為核心模型。較適合的寫法是：

- 第二章介紹 PMV/PPD 作為熱舒適基準。
- 第三章說明本研究使用較簡化的三因子舒適度分數。
- 未來工作可加入 PMV/PPD。

### MPC

Model Predictive Control 適合未來擴充為閉環控制。它的基本想法是預測未來一段時間內不同控制動作的效果，選擇成本最低的動作。

本研究目前只做候選動作排序，不做閉環控制。因此 MPC 可以放在文獻探討或未來工作，不必作為主方法。

## 建議論文模型架構

最適合本研究初版的架構如下：

```text
Room geometry
    ↓
Background field
    ↓
Appliance influence functions
    ↓
Predicted temperature / humidity / illuminance fields
    ↓
8 corner sensor residuals
    ↓
Affine correction field
    ↓
Corrected spatial digital twin
    ↓
Zone average estimation
    ↓
Action ranking by comfort improvement
```

## 可放入論文的模型比較表

| 模型 | 可用位置 | 優點 | 缺點 | 本研究建議 |
| --- | --- | --- | --- | --- |
| BIM-IoT Digital Twin | 第二章 | 系統完整、視覺化強 | 建置成本高，偏平台 | 參考，不採為核心 |
| RC Thermal Model | 第二章、第三章 | 可解釋、適合溫度動態 | 對空間分布解析度有限 | 採用簡化版 |
| Zone Moisture Balance | 第二章、第三章 | 可描述濕度來源與交換 | 完整模型較複雜 | 採用一階簡化版 |
| Inverse-Square Lighting Model | 第三章 | 簡單、符合照度衰減 | 不含反射與材質 | 採用簡化版 |
| IDW | 第二章、第五章 | baseline 簡單 | 易受距離影響，無物理設備項 | 可作比較基準 |
| Kriging / GPR | 第二章、未來工作 | 可建模空間相關與不確定性 | 感測器少時不穩 | 先不採用 |
| PMV / PPD | 第二章、未來工作 | 熱舒適標準常用 | 需要更多人體與環境參數 | 不作核心 |
| MPC | 第二章、未來工作 | 適合閉環控制 | 實作與驗證成本高 | 保留為延伸 |

## 目前原型與模型對應

目前程式已實作：

- 一階設備動態響應
- 距離衰減與方向性設備影響
- 三因子場估計
- 8 角落感測器 affine correction
- 目標區域平均值
- 候選設備動作排序

下一步若要加強研究深度，建議優先加入：

1. IDW baseline，與 affine correction 比較。
2. 不同外部環境條件的敏感度分析。
3. 不同感測器誤差幅度下的校正穩定性分析。
4. 將照度模型從指數衰減改為 inverse-square/cosine 形式。

## 參考來源

- Digital twin indoor condition monitoring case study: https://vuir.vu.edu.au/48190/1/1-s2.0-S092658052300448X-main.pdf
- ASHRAE Standard 55 overview: https://www.ashrae.org/technical-resources/bookstore/standard-55-thermal-environmental-conditions-for-human-occupancy
- CBE Thermal Comfort Tool: https://ashrae55.berkeley.edu/
- Modelica Buildings Reduced-Order RC thermal zone models: https://simulationresearch.lbl.gov/modelica/releases/v9.1.0/help/Buildings_ThermalZones_ReducedOrder_RC.html
- EnergyPlus moisture predictor-corrector reference: https://bigladdersoftware.com/epx/docs/8-5/engineering-reference/moisture-predictor-corrector.html
- Indoor spatial interpolation for IAQ: https://www.mdpi.com/2220-9964/12/8/347
- IES inverse-square law definition: https://ies.org/definitions/inverse-square-law/
