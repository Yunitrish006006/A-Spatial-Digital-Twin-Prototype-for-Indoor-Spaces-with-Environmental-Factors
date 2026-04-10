# A Lightweight Spatial Digital Twin Prototype for Single-Room Temperature, Humidity, and Illuminance Estimation Using Corner Sensor Calibration

中文暫定題目：基於角落感測器校正之單房間溫度、濕度與照度輕量化空間數位孿生原型

建議 GitHub repository 名稱：

`single-room-spatial-digital-twin`

這個專案實作了一個可直接執行的 Python 研究原型，用來模擬單一房間中的三個環境參數：

- 溫度 `T(x, y, z, t)`
- 濕度 `H(x, y, z, t)`
- 亮度 `L(x, y, z, t)`

英文題目中的三個環境因素明確定義為：

- Temperature
- Humidity
- Illuminance

模型採用「連續影響場 + 離散採樣網格」的混合方式，並固定使用 8 顆角落感測器進行觀測與校正。

## 內容

- `digital_twin/`
  核心模型、情境定義、決策排序與輸出工具。
- `scripts/run_demo.py`
  執行完整模擬、校正、情境評估與 SVG/JSON/CSV 匯出。
- `tests/`
  基本單元測試與行為驗證。
- `docs/thesis_guide_zh.md`
  將此原型對應到碩士論文撰寫的章節與方法說明。

## 快速開始

執行完整示範：

```bash
python3 scripts/run_demo.py
```

執行測試：

```bash
python3 -m unittest discover -s tests
```

## 輸出結果

執行後會在 `outputs/` 產生：

- `validation_summary.json`
  各情境的場重建誤差、區域平均值、感測器校正結果與動作排序。
- `*.svg`
  每個情境在中間高度切片的溫度、濕度、亮度熱圖。
- `*.csv`
  每個情境的 3D 採樣網格資料，可直接拿去做論文圖表。

## 模型摘要

模型將房間狀態視為三個連續場，並對每類設備建立簡化影響函數：

- 冷氣：局部降溫、弱除濕、具方向性與時間響應
- 窗戶：引入日照並使溫濕度向外部環境漂移
- 照明：增加照度並帶來少量熱效應

感測器校正使用 8 顆角落節點對模型殘差擬合 affine 修正面：

```text
delta(x, y, z) = a0 + a1*x + a2*y + a3*z
```

這讓有限量測可以反映整體場的偏移與梯度變化。
