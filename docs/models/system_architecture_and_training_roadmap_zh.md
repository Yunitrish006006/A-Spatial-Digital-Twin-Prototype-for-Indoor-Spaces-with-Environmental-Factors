# 系統架構與資料訓練路線整理

本文件的目標不是再重畫一次架構圖，而是回答兩個更實際的問題：

1. 目前整個系統到底分成哪些層？
2. 在現有架構下，能不能先用資料訓練出一個模型？

結論先寫在前面：

- **可以訓練模型，而且其實你現在已經有一條可運作的訓練路線。**
- 但要分清楚你要訓練的是哪一層：
  - `physics 主模型`
  - `裝置影響係數`
  - `感測器校正模型`
  - `hybrid residual neural network`
- 如果你只有 `8 顆角落感測器` 的真實資料，而沒有全室高密度 ground truth，**不適合一開始就直接訓練一個純黑盒 3D 空間場模型**。
- 最穩的做法是：**先保留 physics twin，讓資料去學參數、校正與 residual**。

---

## 一、目前系統架構

### 1. `core/`：資料與流程編排層

主要檔案：

- [entities.py](/Volumes/DataExtended/school/digital_twin/core/entities.py)
- [scenarios.py](/Volumes/DataExtended/school/digital_twin/core/scenarios.py)
- [service.py](/Volumes/DataExtended/school/digital_twin/core/service.py)
- [demo.py](/Volumes/DataExtended/school/digital_twin/core/demo.py)

責任：

- 定義房間、感測器、設備、家具、區域等資料結構
- 建立標準情境與窗戶矩陣情境
- 接收 Web / MCP / CLI 的輸入
- 組合 scenario、執行模型、回傳 dashboard 結果

這一層是 orchestration，不是數學模型本體。

---

### 2. `physics/`：可解釋主模型

主要檔案：

- [model.py](/Volumes/DataExtended/school/digital_twin/physics/model.py)
- [learning.py](/Volumes/DataExtended/school/digital_twin/physics/learning.py)
- [baselines.py](/Volumes/DataExtended/school/digital_twin/physics/baselines.py)
- [recommendations.py](/Volumes/DataExtended/school/digital_twin/physics/recommendations.py)

責任：

- 建立 `bulk + local field` 空間場
- 模擬冷氣、窗戶、燈、家具阻擋
- 用角落感測器做 power calibration
- 擬合 trilinear residual correction
- 建立 IDW baseline
- 對候選動作做 ranking

這一層是現在系統的主心臟。

---

### 3. `neural/`：資料驅動殘差修正層

主要檔案：

- [hybrid_residual.py](/Volumes/DataExtended/school/digital_twin/neural/hybrid_residual.py)

責任：

- 以主模型輸出為 baseline
- 學習 `truth - estimated` 的 residual
- 產生 hybrid corrected field

這一層不是取代 physics model，而是加在後面做第二層修正。

---

### 4. `mcp/`：工具化介面層

主要檔案：

- [mcp_server.py](/Volumes/DataExtended/school/digital_twin/mcp/mcp_server.py)
- [gemma_bridge.py](/Volumes/DataExtended/school/digital_twin/mcp/gemma_bridge.py)

責任：

- 把 service 功能包成工具
- 讓 VS Code、MCP client、Gemma/Ollama bridge 可以呼叫

這一層不是模型，不負責訓練。

---

### 5. `web/`：展示與互動層

主要檔案：

- [web_demo.py](/Volumes/DataExtended/school/digital_twin/web/web_demo.py)
- [render.py](/Volumes/DataExtended/school/digital_twin/web/render.py)

責任：

- 3D 預覽
- 時間軸
- 裝置與家具互動
- 匯出 SVG / CSV / JSON

這一層是 UI，不是訓練核心。

---

## 二、目前已經能訓練什麼

### 1. 已經能訓練：hybrid residual neural network

現在已經有完整流程：

- build training scenarios
- 生成 truth field
- 生成 estimated field
- 將 `truth - estimated` 當成 target
- 對每個採樣點建立 feature
- 訓練三個小型 residual network

核心在：

- [build_residual_dataset()](/Volumes/DataExtended/school/digital_twin/neural/hybrid_residual.py)
- [build_point_features()](/Volumes/DataExtended/school/digital_twin/neural/hybrid_residual.py)
- [train_hybrid_residual_model()](/Volumes/DataExtended/school/digital_twin/neural/hybrid_residual.py)

所以如果你問的是：

> 「我能不能先用數據訓練出一個模型？」

答案是：

**可以，現在最自然的就是先訓練 hybrid residual model。**

---

### 2. 已經能學：裝置影響係數

[learning.py](/Volumes/DataExtended/school/digital_twin/physics/learning.py) 已經有兩條路：

- 單一裝置 impact coefficient learning
- 多裝置 ridge least squares learning

這表示你即使沒有 dense ground truth field，只要有：

- 裝置開之前的感測器資料
- 裝置開之後的感測器資料

就能先學：

- 冷氣大概對溫度/濕度造成多少變化
- 窗戶大概對溫度/濕度/照度造成多少變化
- 燈對照度與熱效應的相對強度

這一塊其實很適合先接真實資料。

---

### 3. 已經能校正：主模型參數

主模型現在已經支援：

- active device power calibration
- trilinear residual correction

這代表你就算還沒有要訓練神經網路，也可以先用資料讓模型變準。

這是最實用、最穩的第一步。

---

## 三、如果只有 8 顆角落感測器，能不能直接訓練整個空間模型？

### 短答案

**不建議直接做純黑盒 full 3D field model。**

### 原因

如果只有 8 顆角落感測器，你真正拿到的 supervision 只有：

- 8 個位置
- 每個時間點的三個值

但你想預測的是：

- 全房間 `16 × 12 × 6 = 1152` 個點的三因子值

這會出現 supervision 極稀疏的問題。  
也就是說：

- 你知道角落
- 但你不知道房間中央、窗邊中段、冷氣前方、家具後面的真實值

因此如果直接用 sparse sensor truth 去監督 full field network，模型很容易：

- 過擬合角落點
- 對中間區域亂補
- 看起來 loss 很低，但空間場其實不可信

---

## 四、你現在最可行的訓練路線

### 路線 A：先做 physics-aware training

這是我最推薦的。

#### 第一步：學裝置影響係數

資料需求最低：

- 裝置事件時間
- 8 顆感測器時序資料

你可以先學：

- 冷氣開啟後溫度下降速度與影響幅度
- 窗戶開啟後溫濕度與照度漂移量
- 燈對照度與弱熱效應的實際係數

這一步不需要 dense field truth。

#### 第二步：學 bulk dynamics

你可以把全室平均狀態改成由資料估參的動態模型，例如：

- `bulk temperature`
- `bulk humidity`
- `mixing factor`
- `response time`

這一步一樣只需要 sparse sensor time series。

#### 第三步：學 residual correction

保留 physics 主模型，再用資料去學 residual：

```text
F_final = F_physics + r_theta
```

這就是你現在的 hybrid residual 路線。

---

### 路線 B：先用模擬資料 pretrain，再用真實資料 fine-tune

這是第二推薦。

適合你的原因：

- 你現在已經有大量可控情境模擬器
- 可生成 truth / estimated 對照
- 可先把網路預訓練好

然後之後再用真實資料做：

- feature normalization update
- residual bias fine-tune
- device-specific domain adaptation

這比一開始完全拿真實 sparse data 直接訓練穩很多。

---

### 路線 C：等有更密集量測後，再做 full spatial model

如果你之後真的想訓練一個比較完整的空間模型，至少要補其中一種：

- 移動式量測
  例如手持感測器或滑軌在房間內掃描
- 增加中間區域感測器
- 做多輪不同家具/裝置配置下的 dense sampling
- 用 CFD 或高精模擬生成 teacher field

有了比較像樣的空間 supervision，再考慮：

- MLP spatial regressor
- graph neural network
- 3D voxel residual model
- PINN / operator learning

才有意義。

---

## 五、你現在手上的資料，最適合訓練哪個模型？

### 如果你只有這些：

- ESP32 角落感測器時序
- 冷氣 / 窗戶 / 燈的手動記錄
- 室外溫度 / 濕度 / 日照

那我建議的優先順序是：

1. **裝置影響係數模型**
2. **bulk dynamics 參數模型**
3. **hybrid residual correction**
4. **最後才考慮 full spatial neural model**

### 如果你有這些：

- 多位置移動式量測
- 家具配置記錄
- 多種裝置設定與時間軸
- 同一房間多次 repeat experiments

那就可以開始考慮：

- 訓練更強的 residual field model
- 或訓練一個弱監督的 spatial predictor

---

## 六、最小可用資料格式

你至少要有三種表：

### 1. 角落感測器時序

用途：

- 學 bulk dynamics
- 學 device impact
- 做 residual correction

### 2. 裝置事件紀錄

用途：

- 知道哪個時間點有冷氣、窗戶、燈變化
- 對齊 before/after observations

### 3. 外部環境時序

用途：

- 窗戶模式需要 outdoor temperature / humidity / sunlight

如果你之後要做更完整的空間模型，還需要：

### 4. 額外空間量測或移動式 ground truth

用途：

- 真正監督全室 field

---

## 七、對你題目的最佳訓練策略

如果你現在要開始做，而且希望風險最低、論文最穩，我的建議是：

### 方案 1：最穩版本

- physics twin 當主模型
- 8 角落感測器資料學 device coefficients
- 再用同一批資料學 bulk parameter calibration
- 最後再掛 hybrid residual model

這個版本最符合你現在的論文定位。

### 方案 2：進階版本

- 先用模擬資料 pretrain hybrid residual
- 再用真實資料做 fine-tune
- 保持主模型不變

這個版本是現在最有機會做出漂亮結果的。

### 方案 3：高風險版本

- 直接訓練 end-to-end neural field model

我不推薦現在做，因為資料監督太稀疏。

---

## 八、我對你的直接判斷

### 你現在就能做的

- 用現有模擬資料訓練 hybrid residual
- 用真實 8 角落時序資料去學裝置影響係數
- 用真實時序去校正 bulk dynamics 與 response time

### 你現在不該急著做的

- 跳過 physics twin，直接做黑盒 full 3D predictor
- 用只有角落點的資料宣稱重建出真實全室高精度場

---

## 九、最實際的下一步

如果你要開始收資料，我建議立刻做這三件事：

1. 建立固定格式的 `sensor_timeseries.csv`
2. 建立 `device_event_log.csv`
3. 每次實驗都保留 `scenario metadata`

只要這三件事先固定，你後面不管是：

- 重新估 physics 參數
- 學 impact coefficients
- 訓練 hybrid residual

都能接得起來。

本專案已另外提供資料模板輸出腳本：

- [build_training_templates.py](/Volumes/DataExtended/school/scripts/build_training_templates.py)

