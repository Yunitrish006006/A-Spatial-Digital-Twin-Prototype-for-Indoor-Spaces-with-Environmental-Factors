# 論文報告投影片大綱

## Slide 1: 封面
- 題目、姓名、雙指導教授、研究定位

## Slide 2: 研究問題與動機
- 非連網裝置無法直接回報狀態
- 有限感測器下仍需估計全室環境
- 早期純插值與 local-only 模型都不合理

## Slide 3: 系統架構
- top-down tree 區分情境觀測、估測學習、服務決策三個責任域
- MCP/Gemma bridge 屬於工具介面層，不是主模型核心

## Slide 4: 房間拓樸、感測器與目標區域
- 8 顆角落感測器
- 三個主要區域與三個核心裝置

## Slide 5: 數學模型
- 變數專屬 nominal model
- trilinear correction
- 裝置與家具模組化
- 溫度、濕度、照度分別使用不同公式

## Slide 6: 模型學習、推論與推薦資料流
- 學習端：raw records → 對齊 → scenario state → labels → coefficients/checkpoint
- 推論端：runtime input → nominal field → correction / hybrid → point or zone prediction
- 推薦端：sample / cluster + T/H/L 目標 → 反事實重跑 → penalty reduction 排序

## Slide 7: 系統實作與介面
- MCP 是工具化介面，不是預測模型本身
- initialize：設定 scenario、室內 baseline、外部邊界、設備/家具、預設時間與 estimator
- AC state：模式、目標溫度、風量、水平/垂直角度與固定/擺動
- sample point：查指定座標在特定時間或穩定態的溫濕照度
- learn impacts：start/finish before-after record
- window direct / rank actions：輸入外部窗戶資料；rank actions 需指定 sample 與 T/H/L 目標
- Gemma bridge 與 Web demo 分別負責 AI tool calling 與人機展示

## Slide 8: learn_impacts：動作如何成為資料記錄
- start：device_name + device_state 記錄實際操作狀態
- record：儲存 learning_record_id、baseline、外部邊界、家具、elapsed time 與 before observations
- finish：用同一批感測器 after observations 計算 after-before delta
- least squares：由 influence envelope 與 delta 求 learned_device_impacts

## Slide 9: 驗證流程與比較原則
- E1-E3：synthetic full-field、IDW baseline、ablation
- E4：非連網裝置影響學習與推薦排序
- E5：48 組窗戶矩陣與 direct input
- E6：hybrid residual no-Fourier 與 LOO cross-validation
- E7：bedroom_01 7 天真實快照與 pillow hold-out
- E8 protocol、E9 public task-aligned benchmark；demo 不是量化實驗

## Slide 10: 主要結果
- 平均 field MAE
- IDW / Base / LOO Hybrid 誤差比較
- 真實臥室 pillow MAE 比較
- 推薦排序目前為 counterfactual simulation
- 3D 視覺化案例

## Slide 11: Hybrid Residual 結果
- default held-out、no-Fourier、LOO MAE
- train/test sample count
- 研究定位不是黑盒替代
- LOO 結果限標準情境 family

## Slide 12: 公開資料任務拆解
- SML2010：S1 純照度劣勢、S2 長視窗溫度部分優勢、S3 事件 delta 主要優勢
- CU-BEMS：C1/C3 勝 linear regression 但不勝 persistence，C2 照度劣勢
- 明確說明 public benchmark 不是 full 3D 場驗證

## Slide 13: 研究貢獻與資料策略
- 三因子、有限感測器、非連網裝置、服務化
- canonical synthetic benchmark + real-bedroom snapshots + task-aligned public datasets
- 明確列出每種資料支援的驗證範圍

## Slide 14: 結論與未來工作
- 長期真實資料、dense real-room ground truth、更多因子、multi-zone、推薦動作介入驗證、閉環控制

## Slide 15: 公式說明 1：三因子場與查詢點
- 場的定義
- 適用範圍

## Slide 16: 公式說明 2：總估計式
- 主公式
- 為什麼這樣拆

## Slide 17: 公式說明 3：Indoor baseline
- baseline 定義
- 跟 baseline 比較法的差別

## Slide 18: 公式說明 4：baseline 的取得方式
- 有啟動前觀測時
- 沒有啟動前觀測時

## Slide 19: 公式說明 5：高度正規化
- 垂直座標
- 為什麼需要

## Slide 20: 公式說明 6：設備 activation
- 時間響應
- 使用原因

## Slide 21: 公式說明 7：influence envelope
- 空間作用範圍
- 距離衰減

## Slide 22: 公式說明 8：溫度場主式
- 溫度 nominal model
- 使用原因

## Slide 23: 公式說明 9：溫度的全室與局部項
- 分解式
- 三類來源

## Slide 24: 公式說明 10：冷氣溫度項
- 冷氣全室項
- 冷氣局部項

## Slide 25: 公式說明 11：窗戶與燈具溫度項
- 窗戶熱交換
- 燈具熱源

## Slide 26: 公式說明 12：濕度場主式
- 濕度 nominal model
- 使用原因

## Slide 27: 公式說明 13：濕度來源項
- 全室濕度項
- 局部濕度項

## Slide 28: 公式說明 14：照度場主式
- 照度 nominal model
- 為什麼不同於溫濕度

## Slide 29: 公式說明 15：直射光與環境光
- 窗戶直射光
- 燈具與環境光

## Slide 30: 公式說明 16：一次漫反射
- 反射公式
- 模型限制

## Slide 31: 公式說明 17：8 參數校正多項式
- 三線性形式
- 為什麼剛好 8 點

## Slide 32: 公式說明 18：角點 residual
- residual 定義
- 直覺意義

## Slide 33: 公式說明 19：三線性校正式
- 校正公式
- 重要性質

## Slide 34: 公式說明 20：校正後估計值
- 回到主公式
- 適用範圍

## Slide 35: 公式說明 21：可完全表示的 residual 空間
- 函數空間
- 適用範圍

## Slide 36: 公式說明 22：平滑 residual 的誤差界
- 這個上界在衡量什麼
- 為什麼會這樣

## Slide 37: 公式說明 23：非連網裝置影響學習
- before/after delta
- least-squares 估計

## Slide 38: 公式說明 24：Hybrid residual
- 第二層修正
- 定位

## Slide 39: 公式說明 25：Hybrid 訓練目標
- residual label
- 損失函數

## Slide 40: 公式說明 26：MAE、RMSE 與 Correlation
- 誤差指標
- 使用原因

## Slide 41: 公式說明 27：IDW baseline
- IDW 插值
- 比較基準理由

## Slide 42: 公式說明 28：推薦排序與驗證
- 推薦分數
- 驗證限制
