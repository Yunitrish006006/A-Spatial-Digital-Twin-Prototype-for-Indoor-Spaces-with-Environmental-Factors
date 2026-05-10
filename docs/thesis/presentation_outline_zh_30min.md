# 論文報告投影片大綱（30min 版）

## Slide 1: 封面
- 題目、姓名、雙指導教授、研究定位

## Slide 2: 報告流程
- 背景、文獻、方法、實作、驗證、結論、公式與指標整理

## Slide 3: 研究主軸與輸入輸出
- 研究主軸：少量角落感測 + 非連網家電 + 單房間幾何配置 → 三因子空間場估計與決策支援
- 輸入：房間、8 點感測、baseline、外部邊界、時間與設備狀態
- 模型：三因子 nominal model、power calibration、trilinear correction、hybrid residual
- 輸出：任意點/區域估計、3D 視覺化、影響學習、推薦排序與 MCP 查詢

## Slide 4: 研究背景與問題
- 非連網裝置造成空間影響但無法直接讀取
- 有限感測器仍需估全室環境

## Slide 5: 研究問題與貢獻
- RQ1-RQ4、主要技術貢獻、task-aligned benchmark 策略

## Slide 6: 文獻定位、研究缺口與比較原則
- IEQ 實驗、場重建、hybrid model、digital twin 平台之差異
- 公開資料集只比較相容子任務

## Slide 7: 整體系統架構
- 人機互動層與 AI 工具呼叫層共用服務編排入口

## Slide 8: 主要執行資料流
- runtime request 到 dashboard / MCP response 的流程

## Slide 9: 房間拓樸、感測器與目標區域
- 8 顆角落感測器與三個區域

## Slide 10: 模組化裝置與家具阻擋
- 裝置模組化、家具自適應阻擋

## Slide 11: 數學模型
- 變數專屬 nominal model + residual correction
- 早期純插值與 local-only 模型失敗後的調整
- 避免把同一套公式套用到溫度、濕度、照度

## Slide 12: 方法選擇：為什麼不是純插值、純物理或純黑盒
- IDW 適合作 baseline 但缺設備與方向資訊
- 完整 CFD/ray tracing 對低成本即時服務太重
- hybrid residual 只學剩餘誤差，不取代可解釋主模型

## Slide 13: 模型學習、推論與推薦資料流
- 學習資料流：raw data → 對齊 → scenario state → labels → coefficients/checkpoint
- 推論資料流：runtime input → nominal field → correction/hybrid → 溫濕照度
- 推薦資料流：sample / cluster + T/H/L 目標 → 反事實重跑 → penalty reduction 排序

## Slide 14: 系統實作與介面
- MCP 是工具化介面，不是預測模型本身
- initialize：設定 scenario、baseline、外部邊界、設備/家具、時間與 estimator
- sample point：註冊環境後查指定座標三因子估計
- learn impacts：以 before/after observations 建立可學習資料
- window direct / rank actions：直接輸入窗戶外部資料；rank actions 需指定 sample 與 T/H/L 目標
- Gemma/Ollama 透過 bridge 呼叫 tools；Web demo 負責人機互動展示

## Slide 15: 驗證設計
- E1-E3：truth-adjusted simulation、IDW、synthetic ablation
- E4-E6：裝置影響學習、window matrix、hybrid no-Fourier/LOO
- E7：bedroom_01 7 天真實快照與 pillow 位置比較
- E8：推薦動作 before/after intervention protocol
- E9：public datasets 僅作 task-aligned benchmark
- Web demo 與 3D 展示是呈現層，不列為量化實驗

## Slide 16: 證據鏈與 Claim Boundary
- Synthetic full-field 支援完整 3D 場比較，但不等同長期真實場
- Real-bedroom snapshot 支援稀疏校正的 held-out 點位檢查，但不是 dense truth
- Public datasets 僅支援相容子任務，不是單房間 8 點拓樸驗證
- Recommendation 目前是反事實排序，仍需 before/after 介入驗證

## Slide 17: 情境設計與輸入模式
- 8 組 scenario、48 組窗戶矩陣、direct input、timeline

## Slide 18: 主要量化結果
- 平均 MAE、IDW/Base/LOO Hybrid 誤差圖
- 真實臥室 raw vs corrected pillow MAE
- 推薦有效性以 actual comfort-penalty reduction 驗證
- 實驗 E1-E7 與 E9 已有數值輸出；E8 僅為介入 protocol

## Slide 19: 真實臥室快照與推薦驗證狀態
- E7：pillow hold-out 不參與 8 角點 residual fitting，呈現 raw vs corrected MAE
- E8：rank actions 目前是模型反事實排序，需實測介入驗證因果效果

## Slide 20: 3D 視覺化結果
- 溫度與照度熱區案例

## Slide 21: Hybrid Residual 結果
- default held-out、no-Fourier、LOO robustness checks
- train/test sample count 與 synthetic benchmark 限制
- LOO 結果限標準情境 family
- 真實快照作為 sparse calibration 驗證

## Slide 22: 公開資料任務拆解：SML2010
- S1：純照度短視窗是劣勢
- S2：長視窗溫度有優勢但濕度有尺度對齊問題
- S3：事件 delta response 是主要優勢

## Slide 23: 公開資料任務拆解：CU-BEMS
- C1：AC 溫濕度可補強 linear regression
- C2：商辦照度與單房間假設差距大
- C3：compound event 可勝 linear regression 但不勝 persistence

## Slide 24: 結論、限制與未來工作
- 目前完成度、真實快照限制、hybrid 泛化限制、推薦動作尚需介入驗證、task-aligned benchmark 與後續方向

## Slide 25: 公式與指標整理
- 場模型：三因子場、總估計式、baseline、activation、envelope
- 三因子公式：溫度、濕度、照度分別說明
- 校正與評估：8 點三線性校正、影響學習、hybrid residual、metrics、IDW、推薦排序

## Slide 26: 公式說明 1：三因子場與查詢點
- 場的定義
- 主張邊界

## Slide 27: 公式說明 2：總估計式
- 主公式
- 為什麼這樣拆

## Slide 28: 公式說明 3：Indoor baseline
- baseline 定義
- 跟 baseline 比較法的差別

## Slide 29: 公式說明 4：baseline 的取得方式
- 有啟動前觀測時
- 沒有啟動前觀測時

## Slide 30: 公式說明 5：高度正規化
- 垂直座標
- 為什麼需要

## Slide 31: 公式說明 6：設備 activation
- 時間響應
- 使用原因

## Slide 32: 公式說明 7：influence envelope
- 空間作用範圍
- 距離衰減

## Slide 33: 公式說明 8：溫度場主式
- 溫度 nominal model
- 使用原因

## Slide 34: 公式說明 9：溫度的全室與局部項
- 分解式
- 三類來源

## Slide 35: 公式說明 10：冷氣溫度項
- 冷氣全室項
- 冷氣局部項

## Slide 36: 公式說明 11：窗戶與燈具溫度項
- 窗戶熱交換
- 燈具熱源

## Slide 37: 公式說明 12：濕度場主式
- 濕度 nominal model
- 使用原因

## Slide 38: 公式說明 13：濕度來源項
- 全室濕度項
- 局部濕度項

## Slide 39: 公式說明 14：照度場主式
- 照度 nominal model
- 為什麼不同於溫濕度

## Slide 40: 公式說明 15：直射光與環境光
- 窗戶直射光
- 燈具與環境光

## Slide 41: 公式說明 16：一次漫反射
- 反射公式
- 限制與說法

## Slide 42: 公式說明 17：8 參數校正多項式
- 三線性形式
- 為什麼剛好 8 點

## Slide 43: 公式說明 18：角點 residual
- residual 定義
- 直覺意義

## Slide 44: 公式說明 19：三線性校正式
- 校正公式
- 重要性質

## Slide 45: 公式說明 20：校正後估計值
- 回到主公式
- 主張邊界

## Slide 46: 公式說明 21：可完全表示的 residual 空間
- 函數空間
- 嚴謹主張

## Slide 47: 公式說明 22：平滑 residual 的誤差界
- 誤差上界
- 如何解釋「接近」

## Slide 48: 公式說明 23：非連網裝置影響學習
- 特徵向量
- 標籤定義

## Slide 49: 公式說明 24：Hybrid residual
- 第二層修正
- 定位

## Slide 50: 公式說明 25：Hybrid 訓練目標
- residual label
- 損失函數

## Slide 51: 公式說明 26：MAE、RMSE 與 Correlation
- 誤差指標
- 使用原因

## Slide 52: 公式說明 27：IDW baseline
- IDW 插值
- 為什麼拿它比較

## Slide 53: 公式說明 28：推薦排序與驗證
- 推薦分數
- 必須說清楚的限制
