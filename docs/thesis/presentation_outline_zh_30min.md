# 論文報告投影片大綱（公式詳解完整版）

## Slide 1: 封面
- 題目、姓名、雙指導教授、公式詳解完整版

## Slide 2: 報告流程
- 背景、文獻、方法、實作、驗證、結論

## Slide 3: 研究背景與問題
- 非連網裝置造成空間影響但無法直接讀取
- 有限感測器仍需估全室環境

## Slide 4: 研究問題與貢獻
- RQ1-RQ4、主要技術貢獻、task-aligned benchmark 策略

## Slide 5: 文獻定位、研究缺口與比較原則
- IEQ 實驗、場重建、hybrid model、digital twin 平台之差異
- 公開資料集只比較相容子任務

## Slide 6: 整體系統架構
- 人機互動層與 AI 工具呼叫層共用服務編排入口

## Slide 7: 主要執行資料流
- scenario 到 dashboard / MCP response 的流程

## Slide 8: 房間拓樸、感測器與目標區域
- 8 顆角落感測器與三個區域

## Slide 9: 模組化裝置與家具阻擋
- 裝置模組化、家具自適應阻擋

## Slide 10: 數學模型
- 變數專屬 nominal model + residual correction
- 早期純插值與 local-only 模型失敗後的調整
- 避免把同一套公式套用到溫度、濕度、照度

## Slide 11: 感測器校正與裝置影響學習
- power calibration 與 least squares

## Slide 12: 系統實作與介面
- MCP、Gemma/Ollama、Web Demo

## Slide 13: 驗證設計
- E1-E3：truth-adjusted simulation、IDW、synthetic ablation
- E4-E6：裝置影響學習、window matrix、hybrid no-Fourier/LOO
- E7：bedroom_01 7 天真實快照與 pillow 位置比較
- E8：推薦動作 before/after intervention protocol
- E9：public datasets 僅作 task-aligned benchmark
- Web demo 與 3D 展示是呈現層，不列為量化實驗

## Slide 14: 情境設計與輸入模式
- 8 組 scenario、48 組窗戶矩陣、direct input、timeline

## Slide 15: 主要量化結果
- 平均 MAE、IDW/Base/LOO Hybrid 誤差圖
- 真實臥室 raw vs corrected pillow MAE
- 推薦有效性以 actual comfort-penalty reduction 驗證
- 實驗 E1-E7 與 E9 已有數值輸出；E8 僅為介入 protocol

## Slide 16: 3D 視覺化結果
- 溫度與照度熱區案例

## Slide 17: Hybrid Residual 結果
- default held-out、no-Fourier、LOO robustness checks
- train/test sample count 與 synthetic benchmark 限制
- LOO 結果限標準情境 family
- 真實快照作為 sparse calibration 驗證

## Slide 18: 結論、限制與未來工作
- 目前完成度、真實快照限制、hybrid 泛化限制、推薦動作尚需介入驗證、task-aligned benchmark 與後續方向

## Slide 19: 公式說明 1：三因子場與查詢點
- 場的定義：逐項解釋公式用途與符號
- 要跟教授說的重點：逐項解釋公式用途、限制與可主張範圍

## Slide 20: 公式說明 2：總估計式
- 主公式：逐項解釋公式用途與符號
- 為什麼這樣拆：逐項解釋公式用途、限制與可主張範圍

## Slide 21: 公式說明 3：Indoor baseline
- baseline 定義：逐項解釋公式用途與符號
- 跟 baseline 比較法的差別：逐項解釋公式用途、限制與可主張範圍

## Slide 22: 公式說明 4：baseline 的取得方式
- 有啟動前觀測時：逐項解釋公式用途與符號
- 沒有啟動前觀測時：逐項解釋公式用途、限制與可主張範圍

## Slide 23: 公式說明 5：高度正規化
- 垂直座標：逐項解釋公式用途與符號
- 為什麼需要：逐項解釋公式用途、限制與可主張範圍

## Slide 24: 公式說明 6：設備 activation
- 時間響應：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 25: 公式說明 7：influence envelope
- 空間作用範圍：逐項解釋公式用途與符號
- 距離衰減：逐項解釋公式用途、限制與可主張範圍

## Slide 26: 公式說明 8：溫度場主式
- 溫度 nominal model：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 27: 公式說明 9：溫度的全室與局部項
- 分解式：逐項解釋公式用途與符號
- 三類來源：逐項解釋公式用途、限制與可主張範圍

## Slide 28: 公式說明 10：冷氣溫度項
- 冷氣全室項：逐項解釋公式用途與符號
- 冷氣局部項：逐項解釋公式用途、限制與可主張範圍

## Slide 29: 公式說明 11：窗戶與燈具溫度項
- 窗戶熱交換：逐項解釋公式用途與符號
- 燈具熱源：逐項解釋公式用途、限制與可主張範圍

## Slide 30: 公式說明 12：濕度場主式
- 濕度 nominal model：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 31: 公式說明 13：濕度來源項
- 全室濕度項：逐項解釋公式用途與符號
- 局部濕度項：逐項解釋公式用途、限制與可主張範圍

## Slide 32: 公式說明 14：照度場主式
- 照度 nominal model：逐項解釋公式用途與符號
- 為什麼不同於溫濕度：逐項解釋公式用途、限制與可主張範圍

## Slide 33: 公式說明 15：直射光與環境光
- 窗戶直射光：逐項解釋公式用途與符號
- 燈具與環境光：逐項解釋公式用途、限制與可主張範圍

## Slide 34: 公式說明 16：一次漫反射
- 反射公式：逐項解釋公式用途與符號
- 限制與說法：逐項解釋公式用途、限制與可主張範圍

## Slide 35: 公式說明 17：8 參數校正多項式
- 三線性形式：逐項解釋公式用途與符號
- 為什麼剛好 8 點：逐項解釋公式用途、限制與可主張範圍

## Slide 36: 公式說明 18：角點 residual
- residual 定義：逐項解釋公式用途與符號
- 直覺意義：逐項解釋公式用途、限制與可主張範圍

## Slide 37: 公式說明 19：三線性校正式
- 校正公式：逐項解釋公式用途與符號
- 重要性質：逐項解釋公式用途、限制與可主張範圍

## Slide 38: 公式說明 20：校正後估計值
- 回到主公式：逐項解釋公式用途與符號
- 教授追問時的說法：逐項解釋公式用途、限制與可主張範圍

## Slide 39: 公式說明 21：可完全表示的 residual 空間
- 函數空間：逐項解釋公式用途與符號
- 嚴謹主張：逐項解釋公式用途、限制與可主張範圍

## Slide 40: 公式說明 22：平滑 residual 的誤差界
- 誤差上界：逐項解釋公式用途與符號
- 如何解釋「接近」：逐項解釋公式用途、限制與可主張範圍

## Slide 41: 公式說明 23：非連網裝置影響學習
- 特徵向量：逐項解釋公式用途與符號
- 標籤定義：逐項解釋公式用途、限制與可主張範圍

## Slide 42: 公式說明 24：Hybrid residual
- 第二層修正：逐項解釋公式用途與符號
- 定位：逐項解釋公式用途、限制與可主張範圍

## Slide 43: 公式說明 25：Hybrid 訓練目標
- residual label：逐項解釋公式用途與符號
- 損失函數：逐項解釋公式用途、限制與可主張範圍

## Slide 44: 公式說明 26：MAE、RMSE 與 Correlation
- 誤差指標：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 45: 公式說明 27：IDW baseline
- IDW 插值：逐項解釋公式用途與符號
- 為什麼拿它比較：逐項解釋公式用途、限制與可主張範圍

## Slide 46: 公式說明 28：推薦排序與驗證
- 推薦分數：逐項解釋公式用途與符號
- 必須說清楚的限制：逐項解釋公式用途、限制與可主張範圍
