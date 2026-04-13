# Hybrid Residual Neural Network 說明

## 定位

本模組不是用神經網路取代目前的環境數位孿生主模型，而是建立一個第二層殘差修正器：

```text
F_final(p, t) = F_physics(p, t) + f_theta(features(p, t))
```

- `F_physics(p, t)`：目前已實作的 `bulk + local field` 參數化數位孿生模型
- `f_theta(...)`：小型多層感知器（MLP），學習主模型尚未捕捉到的殘差

這種設計適合目前題目，因為：

- 主模型仍保留冷氣、窗戶、照明的可解釋影響函數
- 感測器校正、power scale calibration、時間常數等物理啟發式結構不會被黑盒吃掉
- 神經網路只負責修正殘差，較容易在論文中說明其角色與限制

## 目前實作

核心檔案：

- `digital_twin/hybrid_residual.py`
- `scripts/run_hybrid_residual_experiment.py`

主要流程：

1. 對每個 scenario 先跑主模型，得到 `estimated field`
2. 以 `truth adjustments` 建立對照的 `truth field`
3. 取每個採樣點的 `truth - estimated` 作為訓練目標
4. 將座標、環境條件、主模型估計值、設備啟用狀態與 influence envelope 組成 feature
5. 訓練三個小型 MLP，分別學習 temperature、humidity、illuminance 的 residual
6. 在測試 scenario 上套用：

```text
corrected_value = estimated_value + predicted_residual
```

## 目前 feature 組成

每個採樣點的 feature 包含：

- 正規化座標 `x / y / z`
- 時間 `elapsed_minutes`
- 室內基準條件：`base_temperature / base_humidity / base_illuminance`
- 室外條件：`outdoor_temperature / outdoor_humidity / sunlight_illuminance / daylight_factor`
- 主模型估計值：`estimated_temperature / estimated_humidity / estimated_illuminance`
- 三個設備的 `activation / power / influence_envelope`
- 冷氣模式 one-hot：`cool / dry / heat / fan`

## 建議論文寫法

若你要把這部分寫進論文，建議定位為：

`A hybrid residual learning extension built on top of the reduced-order spatial digital twin`

而不是：

`A pure neural-network digital twin`

原因是目前資料條件仍偏少量感測器、單房間、模擬為主。若直接宣稱純 neural digital twin，說服力會比 hybrid residual 弱。

## 建議數學式

主模型：

```text
F_m(p, t) = B_m^bulk(t) + B_m^local(p, t) + Σ I_j,m^local(p, t) + C_m(p)
```

殘差修正後：

```text
F_m^hybrid(p, t) = F_m(p, t) + r_m(p, t; theta_m)
```

其中 `r_m` 由神經網路近似，訓練目標為：

```text
r_m^*(p, t) = F_m^truth(p, t) - F_m(p, t)
```

損失函數可寫為：

```text
L(theta_m) = (1 / N) Σ_i || r_m^*(p_i, t_i) - r_m(p_i, t_i; theta_m) ||^2 + lambda || theta_m ||^2
```

## 執行方式

```bash
python3 scripts/run_hybrid_residual_experiment.py
```

輸出：

- `outputs/data/hybrid_residual_summary.json`
- `outputs/data/hybrid_residual_checkpoint.json`

`summary` 會包含：

- train/test scenario split
- baseline field MAE
- hybrid field MAE
- target-zone MAE
- 每個 metric 的 residual learning 成效

## 我對這個方向的建議

推薦做，前提是把它定位成：

- 主模型：`reduced-order bulk + local field`
- 神經網路：`residual correction layer`

不推薦目前直接全面改成純神經網路，因為：

- 現有資料量有限
- 你需要保留對非連網裝置影響的可解釋性
- 題目核心仍是有限感測器下的空間數位孿生與控制推薦，不是追求純黑盒預測分數
