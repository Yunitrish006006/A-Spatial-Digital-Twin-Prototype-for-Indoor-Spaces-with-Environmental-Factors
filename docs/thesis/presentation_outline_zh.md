# 論文報告投影片大綱

## Slide 1: 封面
- 題目、姓名、指導教授、研究定位

## Slide 2: 研究問題與動機
- 非連網裝置無法直接回報狀態
- 有限感測器下仍需估計全室環境
- 早期純插值與 local-only 模型都不合理

## Slide 3: 系統架構
- Web / MCP / Gemma 共用 service layer
- 主模型與 hybrid residual 的分工

## Slide 4: 房間拓樸、感測器與目標區域
- 8 顆角落感測器
- 三個主要區域與三個核心裝置

## Slide 5: 數學模型
- bulk + local field
- trilinear correction
- 裝置與家具模組化

## Slide 6: 感測器校正與影響學習
- power calibration
- least-squares impact learning

## Slide 7: 系統實作與介面
- MCP tools
- Gemma bridge
- Web demo

## Slide 8: 驗證流程與比較原則
- truth-adjusted simulation
- IDW baseline 比較
- task-aligned public benchmark
- 48 組窗戶矩陣

## Slide 9: 主要結果
- 平均 field MAE
- 3D 視覺化案例

## Slide 10: Hybrid Residual 結果
- held-out MAE 降幅
- 研究定位不是黑盒替代

## Slide 11: 研究貢獻與資料策略
- 三因子、有限感測器、非連網裝置、服務化
- canonical synthetic benchmark + task-aligned public datasets

## Slide 12: 結論與未來工作
- 真實資料、更多因子、multi-zone、task-aligned benchmark、閉環控制
