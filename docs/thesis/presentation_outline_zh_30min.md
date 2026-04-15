# 論文報告投影片大綱（30 分鐘版）

## Slide 1: 封面
- 題目、姓名、指導教授、30 分鐘口試版

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
- 多入口共用 service layer

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
- truth-adjusted simulation、IDW、window matrix
- public datasets 僅作 task-aligned benchmark

## Slide 14: 情境設計與輸入模式
- 8 組 scenario、48 組窗戶矩陣、direct input、timeline

## Slide 15: 主要量化結果
- 平均 MAE 與推薦示例

## Slide 16: 3D 視覺化結果
- 溫度與照度熱區案例

## Slide 17: Hybrid Residual 結果
- held-out MAE 降幅與研究定位

## Slide 18: 結論、限制與未來工作
- 目前完成度、限制、task-aligned benchmark 與後續方向
