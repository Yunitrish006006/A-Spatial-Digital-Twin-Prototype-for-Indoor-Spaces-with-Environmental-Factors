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

- `digital_twin/neural/hybrid_residual.py`
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

## Fourier 頻域去噪延伸

目前版本另外支援一個可選的 Fourier low-pass denoising 前處理。它不是把頻譜當成新的主模型，而是在 hybrid residual 訓練前，先對 residual target 的短時間軌跡做頻域低通濾波：

```text
residual trace over elapsed time
    ↓
DFT / spectrum
    ↓
low-pass mask
    ↓
inverse DFT
    ↓
denoised residual target
```

這個設計的目的，是讓 residual MLP 更專注於低頻、較平滑的 thermal / humidity 結構性誤差，而不是追逐短時擾動。根據目前實驗，這個頻域去噪對 `temperature` 幾乎不改變結果，對 `humidity` 有小幅改善，但若直接套用到 `illuminance` 反而會抹掉有用訊號，因此目前預設只對：

- `temperature`
- `humidity`

啟用 Fourier 低通，不對 `illuminance` 啟用。

### 為什麼不是固定時間窗積分或區間平均

一個更接近直覺的替代方式，是對 residual trace 做固定時間窗積分或區間平均，讓局部坡度不要上下晃動太多。這種方法確實能平滑訊號，但它在目前題目下仍有幾個限制：

- 它本質上是時間域中的固定 box filter，視窗大小需要先指定。
- 視窗太小時，短時振盪還是會保留下來；視窗太大時，瞬態響應和局部轉折又容易被一起抹平。
- 這種平滑常會帶來較明顯的 lag，尤其在 residual trace 有快速轉折時更明顯。

Fourier low-pass denoising 比較適合，因為它不是把時間軸整段壓扁，而是：

1. 先轉到頻域。
2. 去掉高頻成分。
3. 再轉回時間域。

這樣做的結果是：

- 保留低頻主趨勢。
- 抑制高頻震盪。
- 最後仍能取得對應目前時間點的 denoised endpoint，保留 time-aligned supervision。

所以在你的題目裡，FFT 低通的價值不是「比平均更炫」，而是它比固定時間窗積分／區間平均更直接地針對高頻振盪下手，並在保留慢變主趨勢與當前時間位置語意的前提下完成去噪。

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

若要啟用 Fourier 頻域去噪，可使用：

```bash
python3 scripts/run_hybrid_residual_experiment.py \
  --fourier-denoise \
  --spectral-metrics temperature,humidity
```

輸出：

- `outputs/data/hybrid_residual_summary.json`
- `outputs/data/hybrid_residual_checkpoint.json`

`summary` 會包含：

- train/test scenario split
- baseline field MAE
- hybrid field MAE
- target-zone MAE
- Fourier 去噪設定
- 每個 metric 的 residual learning 成效

## 我對這個方向的建議

推薦做，前提是把它定位成：

- 主模型：`reduced-order bulk + local field`
- 神經網路：`residual correction layer`

不推薦目前直接全面改成純神經網路，因為：

- 現有資料量有限
- 你需要保留對非連網裝置影響的可解釋性
- 題目核心仍是有限感測器下的空間數位孿生與控制推薦，不是追求純黑盒預測分數
