# 論文報告投影片大綱（30 分鐘版）

## Slide 1: 封面
- 題目、姓名、雙指導教授、30 分鐘口試版

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
- bulk + local field + correction
- 早期純插值與 local-only 模型失敗後的調整

## Slide 11: 感測器校正與裝置影響學習
- power calibration 與 least squares

## Slide 12: 系統實作與介面
- MCP、Gemma/Ollama、Web Demo

## Slide 13: 驗證設計
- truth-adjusted simulation、IDW、synthetic ablation、window matrix
- 證據層級：synthetic full-field、real sparse calibration、public task-aligned、intervention validation
- bedroom_01 7 天真實快照與 pillow 位置比較
- 推薦動作 before/after intervention protocol
- no-Fourier 與 LOO cross-validation
- public datasets 僅作 task-aligned benchmark

## Slide 14: 情境設計與輸入模式
- 8 組 scenario、48 組窗戶矩陣、direct input、timeline

## Slide 15: 主要量化結果
- 平均 MAE、IDW/Base/LOO Hybrid 誤差圖
- 真實臥室 raw vs corrected pillow MAE
- 推薦有效性以 actual comfort-penalty reduction 驗證

## Slide 16: 3D 視覺化結果
- 溫度與照度熱區案例

## Slide 17: Hybrid Residual 結果
- default held-out、no-Fourier、LOO robustness checks
- train/test sample count 與 synthetic benchmark 限制
- LOO 結果限標準情境 family
- 真實快照作為 sparse calibration 驗證

## Slide 18: 結論、限制與未來工作
- 目前完成度、真實快照限制、hybrid 泛化限制、推薦動作尚需介入驗證、task-aligned benchmark 與後續方向
