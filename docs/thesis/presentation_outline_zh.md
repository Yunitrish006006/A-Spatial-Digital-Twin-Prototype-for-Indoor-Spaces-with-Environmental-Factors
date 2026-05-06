# 論文報告投影片大綱

## Slide 1: 封面
- 題目、姓名、雙指導教授、研究定位

## Slide 2: 研究問題與動機
- 非連網裝置無法直接回報狀態
- 有限感測器下仍需估計全室環境
- 早期純插值與 local-only 模型都不合理

## Slide 3: 系統架構
- 入口分成使用者互動層與 AI 工具呼叫層
- 服務編排、主模型與 residual 修正的分工

## Slide 4: 房間拓樸、感測器與目標區域
- 8 顆角落感測器
- 三個主要區域與三個核心裝置

## Slide 5: 數學模型
- 變數專屬 nominal model
- trilinear correction
- 裝置與家具模組化
- 溫度、濕度、照度分別使用不同公式

## Slide 6: 感測器校正與影響學習
- power calibration
- least-squares impact learning

## Slide 7: 系統實作與介面
- MCP 是工具化介面，不是預測模型本身
- initialize：註冊環境、設備、家具與 baseline
- sample point：查指定座標在特定時間或穩定態的溫濕照度
- learn impacts：start/finish before-after record
- window direct / rank actions：輸入外部窗戶資料，並針對指定座標排序註冊設備操作
- Gemma bridge 與 Web demo 分別負責 AI tool calling 與人機展示

## Slide 8: 驗證流程與比較原則
- E1-E3：synthetic full-field、IDW baseline、ablation
- E4：非連網裝置影響學習與推薦排序
- E5：48 組窗戶矩陣與 direct input
- E6：hybrid residual no-Fourier 與 LOO cross-validation
- E7：bedroom_01 7 天真實快照與 pillow hold-out
- E8 protocol、E9 public task-aligned benchmark；demo 不是量化實驗

## Slide 9: 主要結果
- 平均 field MAE
- IDW / Base / LOO Hybrid 誤差比較
- 真實臥室 pillow MAE 比較
- 推薦排序目前為 counterfactual simulation
- 3D 視覺化案例

## Slide 10: Hybrid Residual 結果
- default held-out、no-Fourier、LOO MAE
- train/test sample count
- 研究定位不是黑盒替代
- LOO 結果限標準情境 family

## Slide 11: 研究貢獻與資料策略
- 三因子、有限感測器、非連網裝置、服務化
- canonical synthetic benchmark + real-bedroom snapshots + task-aligned public datasets
- 明確列出每種資料支援的 claim boundary

## Slide 12: 結論與未來工作
- 長期真實資料、dense real-room ground truth、更多因子、multi-zone、推薦動作介入驗證、閉環控制

## Slide 13: 公式說明 1：三因子場與查詢點
- 場的定義：逐項解釋公式用途與符號
- 要跟教授說的重點：逐項解釋公式用途、限制與可主張範圍

## Slide 14: 公式說明 2：總估計式
- 主公式：逐項解釋公式用途與符號
- 為什麼這樣拆：逐項解釋公式用途、限制與可主張範圍

## Slide 15: 公式說明 3：Indoor baseline
- baseline 定義：逐項解釋公式用途與符號
- 跟 baseline 比較法的差別：逐項解釋公式用途、限制與可主張範圍

## Slide 16: 公式說明 4：baseline 的取得方式
- 有啟動前觀測時：逐項解釋公式用途與符號
- 沒有啟動前觀測時：逐項解釋公式用途、限制與可主張範圍

## Slide 17: 公式說明 5：高度正規化
- 垂直座標：逐項解釋公式用途與符號
- 為什麼需要：逐項解釋公式用途、限制與可主張範圍

## Slide 18: 公式說明 6：設備 activation
- 時間響應：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 19: 公式說明 7：influence envelope
- 空間作用範圍：逐項解釋公式用途與符號
- 距離衰減：逐項解釋公式用途、限制與可主張範圍

## Slide 20: 公式說明 8：溫度場主式
- 溫度 nominal model：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 21: 公式說明 9：溫度的全室與局部項
- 分解式：逐項解釋公式用途與符號
- 三類來源：逐項解釋公式用途、限制與可主張範圍

## Slide 22: 公式說明 10：冷氣溫度項
- 冷氣全室項：逐項解釋公式用途與符號
- 冷氣局部項：逐項解釋公式用途、限制與可主張範圍

## Slide 23: 公式說明 11：窗戶與燈具溫度項
- 窗戶熱交換：逐項解釋公式用途與符號
- 燈具熱源：逐項解釋公式用途、限制與可主張範圍

## Slide 24: 公式說明 12：濕度場主式
- 濕度 nominal model：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 25: 公式說明 13：濕度來源項
- 全室濕度項：逐項解釋公式用途與符號
- 局部濕度項：逐項解釋公式用途、限制與可主張範圍

## Slide 26: 公式說明 14：照度場主式
- 照度 nominal model：逐項解釋公式用途與符號
- 為什麼不同於溫濕度：逐項解釋公式用途、限制與可主張範圍

## Slide 27: 公式說明 15：直射光與環境光
- 窗戶直射光：逐項解釋公式用途與符號
- 燈具與環境光：逐項解釋公式用途、限制與可主張範圍

## Slide 28: 公式說明 16：一次漫反射
- 反射公式：逐項解釋公式用途與符號
- 限制與說法：逐項解釋公式用途、限制與可主張範圍

## Slide 29: 公式說明 17：8 參數校正多項式
- 三線性形式：逐項解釋公式用途與符號
- 為什麼剛好 8 點：逐項解釋公式用途、限制與可主張範圍

## Slide 30: 公式說明 18：角點 residual
- residual 定義：逐項解釋公式用途與符號
- 直覺意義：逐項解釋公式用途、限制與可主張範圍

## Slide 31: 公式說明 19：三線性校正式
- 校正公式：逐項解釋公式用途與符號
- 重要性質：逐項解釋公式用途、限制與可主張範圍

## Slide 32: 公式說明 20：校正後估計值
- 回到主公式：逐項解釋公式用途與符號
- 教授追問時的說法：逐項解釋公式用途、限制與可主張範圍

## Slide 33: 公式說明 21：可完全表示的 residual 空間
- 函數空間：逐項解釋公式用途與符號
- 嚴謹主張：逐項解釋公式用途、限制與可主張範圍

## Slide 34: 公式說明 22：平滑 residual 的誤差界
- 誤差上界：逐項解釋公式用途與符號
- 如何解釋「接近」：逐項解釋公式用途、限制與可主張範圍

## Slide 35: 公式說明 23：非連網裝置影響學習
- 特徵向量：逐項解釋公式用途與符號
- 標籤定義：逐項解釋公式用途、限制與可主張範圍

## Slide 36: 公式說明 24：Hybrid residual
- 第二層修正：逐項解釋公式用途與符號
- 定位：逐項解釋公式用途、限制與可主張範圍

## Slide 37: 公式說明 25：Hybrid 訓練目標
- residual label：逐項解釋公式用途與符號
- 損失函數：逐項解釋公式用途、限制與可主張範圍

## Slide 38: 公式說明 26：MAE、RMSE 與 Correlation
- 誤差指標：逐項解釋公式用途與符號
- 使用原因：逐項解釋公式用途、限制與可主張範圍

## Slide 39: 公式說明 27：IDW baseline
- IDW 插值：逐項解釋公式用途與符號
- 為什麼拿它比較：逐項解釋公式用途、限制與可主張範圍

## Slide 40: 公式說明 28：推薦排序與驗證
- 推薦分數：逐項解釋公式用途與符號
- 必須說清楚的限制：逐項解釋公式用途、限制與可主張範圍
