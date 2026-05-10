# 30 分鐘論文簡報逐頁講稿

本檔是 `thesis_presentation_zh_30min.pptx` 的講稿，不放入投影片畫面。投影片維持正式內容；這份 Markdown 用於練習口頭說明與答辯準備。

## Slide 1: 封面

各位老師好，我是林昀佑。今天報告的題目是「單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型」。這個題目聚焦在一般房間中常見但不一定連網的冷氣、窗戶與照明，以及少量感測器下如何估計完整室內環境分布。

整體研究不是要做完整 CFD 或精密光學模擬，而是建立一個控制導向、可解釋、可校正、也能被工具介面查詢的三因子空間數位孿生原型。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **控制導向**：模型重點在支援查詢、比較與推薦排序，而不是取代高精度物理模擬器。
- **CFD**：Computational Fluid Dynamics，計算流體力學；可模擬細緻氣流，但邊界條件與計算成本高。

## Slide 2: 報告流程

接下來會先從研究背景與問題開始，說明為什麼非連網家電與有限感測器會造成空間感知困難。

再來會說明文獻定位、系統架構、數學模型、感測器校正與影響學習，然後進入系統實作、驗證設計與實驗結果。

最後整理結論、限制與未來工作；後半段的公式與指標整理可以用來補充每個模型元件的細節。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。

## Slide 3: 研究主軸與輸入輸出

這頁先把整個研究壓縮成輸入、模型與輸出三個部分。輸入端包含房間幾何、8 顆角落感測器、室內 baseline、外部環境邊界、時間與設備狀態。

模型端的核心是三因子 nominal model，再加上 power calibration、trilinear residual correction，以及 optional 的 hybrid residual 修正。

輸出端則包含任意點或區域的溫度、濕度、照度估計，3D 視覺化，非連網裝置影響係數，以及後續可以提供 MCP 或 Web demo 使用的反事實推薦排序。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **Web demo**：人機互動展示介面，用於查看 3D 場、時間軸、設備狀態與查詢結果。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。

## Slide 4: 研究背景與問題

一般智慧居家或智慧建築需要知道室內環境狀態，才能支援舒適度評估、能源管理與設備控制。但實際房間中，冷氣、窗戶和照明常常沒有可讀取的 API 或遙測資料。

另一個限制是感測器數量。使用者關心的是整個房間不同位置的舒適狀態，但實際上通常只會放少數幾顆感測器。

因此本研究的問題是：在非連網裝置狀態不完整、感測器稀疏的情況下，如何估計整個房間的環境分布，並學習這些裝置對環境的影響。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **API**：Application Programming Interface，讓系統讀取或控制設備狀態的程式介面。
- **遙測**：設備主動回報狀態或感測資料；非連網裝置通常缺少這類資料。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。

## Slide 5: 研究問題與貢獻

本研究可以拆成四個研究問題。第一，8 顆角落感測器能不能支援單房間三因子空間場估計。第二，能不能從環境變化中學習非連網裝置影響。

第三，當使用者指定 sample 或 zone 以及溫濕照度目標時，能不能排序可能的控制動作。第四，這個模型能不能封裝成 Web 與 MCP 可查詢服務。

主要貢獻是把三因子 nominal model、8 點 residual correction、非連網裝置影響學習、hybrid residual，以及 task-aligned public benchmark 放在同一個可執行原型中。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Sample**：指定房間中的查詢點，用來取得該座標的三因子估計。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。

## Slide 6: 文獻定位、研究缺口與比較原則

相關研究大致可以分成 IEQ 實驗、有限感測器場重建、hybrid thermal model 與 digital twin 平台。但很多研究只處理單一或雙因子，或依賴較完整的設備遙測。

本研究的差異在於把單房間、低成本角落感測、非連網裝置，以及溫度、濕度、照度三因子放在同一個控制導向模型中。

公開資料集的比較採取 task-aligned 原則，因為 SML2010 和 CU-BEMS 沒有本研究需要的單房間幾何、8 點拓樸和 dense 3D 場真值，所以只能比較相容子任務。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **控制導向**：模型重點在支援查詢、比較與推薦排序，而不是取代高精度物理模擬器。
- **遙測**：設備主動回報狀態或感測資料；非連網裝置通常缺少這類資料。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **IEQ**：Indoor Environmental Quality，室內環境品質，通常涵蓋熱舒適、空氣品質、照明等因素。
- **Hybrid thermal model**：結合物理結構與資料驅動方法的熱環境模型。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。
- **SML2010**：公開智慧建築資料集；本研究用於 two-point boundary-response 類任務。
- **CU-BEMS**：商辦建築能源管理資料集；本研究用於 zone-level device-response 類任務。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Dense ground truth**：房間內大量點位的真實環境場資料，是更嚴格但較難取得的驗證基準。

## Slide 7: 整體系統架構

整體架構分為前端互動、AI 工具呼叫、服務編排、數位孿生核心、校正學習與視覺化輸出幾層。

Web demo 與 MCP tools 都不直接做模型推論，而是呼叫同一個服務編排入口，由核心模型負責場估計、校正、學習與推薦排序。

這樣設計的好處是展示介面、AI tool calling 與後端模型可以分工，未來也比較容易替換 estimator 或新增裝置與環境因子。

### 名詞註釋
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **Web demo**：人機互動展示介面，用於查看 3D 場、時間軸、設備狀態與查詢結果。
- **Tool calling**：語言模型不是直接計算答案，而是呼叫外部工具取得模型查詢或操作結果。
- **服務編排**：把 scenario、模型估計、校正、推薦與輸出流程串接起來的中介層。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。

## Slide 8: 主要執行資料流

執行時，系統先取得 scenario 或 direct input，包含房間狀態、baseline、外部邊界、家具和設備設定。

接著服務層把這些資料交給 estimator，先建立 nominal field，再套用感測器校正或 hybrid residual，最後輸出 dashboard、point sample、zone summary 或 MCP response。

所以 Web 和 MCP 只是不同入口，核心資料流是共用的，避免展示結果和工具查詢結果不一致。

### 名詞註釋
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **Web demo**：人機互動展示介面，用於查看 3D 場、時間軸、設備狀態與查詢結果。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Direct input**：不使用預設矩陣情境，直接輸入外部溫濕度、日照與開窗比例。

## Slide 9: 房間拓樸、感測器與目標區域

本研究使用單一矩形房間作為主要研究場景，尺寸為 6 m × 4 m × 3 m。座標系使用公尺，原點在房間地面西南角。

感測器放在地面四角與天花板四角，共 8 顆。這 8 點不是直接量到全室，而是提供 sparse observation，用來對 nominal model 的 residual 做三線性補間。

目標區域分成窗邊、中心與門側等 zone，方便後續做區域平均、舒適度評估和推薦排序。

### 名詞註釋
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **座標系**：用 x/y/z 公尺座標描述房間內位置；本研究原點在地面西南角。

## Slide 10: 模組化裝置與家具阻擋

冷氣、窗戶與燈具都被視為模組化裝置，每個裝置都有位置、方向、作用尺度與啟動狀態。這讓模型可以支援新增或移動裝置。

家具則被視為空間中的阻擋物，會影響冷氣、窗戶日照或燈具光源的局部作用權重。

這個設計的目的不是做非常精細的流場或光線追蹤，而是用低成本幾何資訊修正單純距離衰減太粗略的問題。

### 名詞註釋
- **Ray tracing**：依光線路徑追蹤照明傳播的精密光學方法；本研究只採輕量照度幾何與一次漫反射近似。
- **Distance decay**：距離設備越遠，局部作用越弱的權重函數。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。

## Slide 11: 數學模型

核心估計式是 F_hat_v(p,t)=N_v(p,t)+C_v(p,t)。N_v 是變數專屬 nominal model，C_v 是由角落感測 residual 建立的校正場。

溫度模型處理熱交換、熱源和垂直分層；濕度模型處理除濕與外氣水氣交換；照度模型處理光源幾何、遮蔽與一次漫反射。

這裡最重要的是三個環境變數不共用同一套物理公式。它們共用座標、裝置框架與校正流程，但 nominal model 根據物理意義分開設計。

### 名詞註釋
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **一次漫反射**：只計算一次表面反射對照度的回填效果，是輕量近似而非完整 radiosity。

## Slide 12: 方法選擇：為什麼不是純插值、純物理或純黑盒

純插值，例如 IDW，只知道感測器位置與距離，不知道冷氣出風、窗戶日照或燈具位置，因此在局部熱區和照度場會比較吃虧。

完整物理模擬像 CFD 或 ray tracing，需要大量邊界條件、材料與計算成本，不符合低成本房間原型與即時查詢的需求。

純黑盒模型在資料量有限時也容易過擬合，而且不容易解釋設備與空間結構的作用。因此本研究採用可解釋 base model，再用 residual correction 和 hybrid residual 補足誤差。

### 名詞註釋
- **CFD**：Computational Fluid Dynamics，計算流體力學；可模擬細緻氣流，但邊界條件與計算成本高。
- **Ray tracing**：依光線路徑追蹤照明傳播的精密光學方法；本研究只採輕量照度幾何與一次漫反射近似。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **黑盒模型**：主要依資料學習輸入輸出關係、但內部物理意義較不明確的模型。

## Slide 13: 模型學習、推論與推薦資料流

學習端會把 raw records 對齊成 scenario state，產生訓練 labels，再更新裝置影響係數或 hybrid checkpoint。

推論端從 runtime input 開始，先建立 nominal field，再做 correction 或 hybrid 修正，最後輸出 point 或 zone 的三因子估計。

推薦端不是直接控制設備，而是把候選動作做反事實重跑，計算採取動作前後的 comfort penalty reduction，再依改善幅度排序。

### 名詞註釋
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **標籤 yᵢ**：監督式學習中的目標值；本研究常用 true field 與 base estimator 的差作 residual label。

## Slide 14: 系統實作與介面

MCP 的全名是 Model Context Protocol。它不是我的預測模型，也不是一個新的神經網路架構，而是一個讓 LLM application 用標準化方式連接外部資料與工具的 open protocol。

如果老師問 std 或 standard，我會回答：MCP 本身是標準化的 protocol；官方規格用 JSON-RPC 2.0 表示 request、response 與 notification。它的標準 transport 包含 stdio 和 Streamable HTTP。

stdio 是 standard input/output 的意思，適合本機工具。client 會啟動 MCP server subprocess，server 從 stdin 讀 newline-delimited JSON-RPC message，再把 response 寫到 stdout；stderr 只用於 log。

在我的系統裡，數位孿生核心服務被包成本地 MCP server，主要暴露 tools/list 與 tools/call。工具包含 initialize_environment、sample_point、learn_impacts、run_window_direct 和 rank_actions。

initialize 負責註冊 scenario、baseline、外部邊界、設備、家具、時間與 estimator。冷氣設備狀態不是只有模式，也包含目標溫度、風速或 fan strength、水平與垂直出風角度，以及 fixed/swing 擺動設定。sample_point 查詢指定座標的溫濕照度估計；rank_actions 則在給定 sample 與三因子目標後，用包含這些 AC 操作參數的候選動作做反事實排序。

所以本研究對 MCP 的定位是系統整合與工具化封裝：證明這個數位孿生模型可以被 AI client 操作。我的研究貢獻不是提出新的 MCP protocol，也不是宣稱模型權重原生支援 MCP。

Web demo 負責人機互動展示，Gemma/Ollama bridge 負責把自然語言轉成 tool calling。兩者底層都呼叫同一個模型服務，因此結果可以保持一致。

### 名詞註釋
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Sample**：指定房間中的查詢點，用來取得該座標的三因子估計。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **AC operating state**：冷氣操作狀態包含模式、設定溫度、風速/風量、水平與垂直出風角度，以及 fixed/swing 擺動設定。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **MCP host/client/server**：MCP 採 client-server 概念；host/client 是使用工具的 AI 應用端，server 則暴露工具、資源或 prompt。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **JSON-RPC**：MCP 使用 JSON-RPC 2.0 編碼 request、response 與 notification。
- **stdio transport**：MCP 的本地 transport 之一；client 啟動 server subprocess，透過 stdin/stdout 傳送 UTF-8 JSON-RPC 訊息。
- **Streamable HTTP**：MCP 的另一種標準 transport，適合遠端或網路化部署。
- **Web demo**：人機互動展示介面，用於查看 3D 場、時間軸、設備狀態與查詢結果。
- **Gemma/Ollama bridge**：讓本地語言模型透過工具呼叫流程存取模型服務的橋接層。
- **Tool calling**：語言模型不是直接計算答案，而是呼叫外部工具取得模型查詢或操作結果。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。

## Slide 15: learn_impacts：動作如何成為資料記錄

這一頁回答「學習時記錄的動作是什麼」。系統不是只記錄一個開關，也不是記錄 rank_actions 的推薦名稱，而是把實際要套用到裝置上的 device_state 記錄下來。

在 start 階段，client 會送 device_name 與 device_state。以冷氣為例，device_state 可以包含 activation、kind、power、ac_mode、target_temperature、fan_speed、fan_strength、horizontal_mode、horizontal_angle_deg、vertical_mode、vertical_angle_deg，以及 swing 相關欄位。系統會把這些欄位合併到目前註冊設備，形成新的 device_specs，並更新 runtime state。

同一筆 learning record 會得到 learning_record_id，狀態先是 RECORDING。紀錄裡會保存 device_name、device_state、合併後的 device_specs、當時的室內 baseline、外部邊界、家具遮蔽、elapsed time、sampling mode、before_observations，以及 optional note。before_observations 的格式是 sensor name 對應 temperature、humidity、illuminance，例如 floor_sw 對應一組 T/H/L。

finish 階段必須提供同一批感測器的 after_observations。系統用 after minus before 得到每顆感測器的 ΔT、ΔH、ΔL，再用模型中的 influence envelope 當作 X 矩陣，對每個 metric 解 least-squares 係數。輸出 learned_device_impacts 裡會包含 metric_coefficients、sensor_mae 與 sensor_observation_delta。

所以口試時可以說：學習資料是「操作狀態 + 環境快照 + 前後感測讀值」形成的事件紀錄；只有 before 和 after 都存在時才會計算係數。若想追蹤這筆資料來自哪一個推薦動作，目前可寫在 note，或未來新增 action_name 欄位。

### 名詞註釋
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **AC operating state**：冷氣操作狀態包含模式、設定溫度、風速/風量、水平與垂直出風角度，以及 fixed/swing 擺動設定。
- **device_state**：learn_impacts start 階段輸入的裝置操作狀態，包含 activation、kind、power 與冷氣模式、設定溫度、風速、風向等欄位。
- **device_specs**：系統把 device_state 合併進目前註冊設備後形成的完整設備清單，是後續 sample、learning 與 ranking 使用的 runtime 裝置狀態。
- **learning_record_id**：每一次 learn_impacts start 產生的唯一紀錄編號，用來在 finish 階段把 after observations 接回同一筆事件。
- **before_observations / after_observations**：同一批感測器在裝置操作前後的真實讀值，格式通常是 sensor name 對應 temperature、humidity 與 illuminance。
- **learned_device_impacts**：由 before/after 差值與設備 influence envelope 解出的裝置影響係數，描述該操作對三因子的方向與大小。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **Activation**：設備啟動強度隨時間接近穩態的函數。
- **Influence envelope**：設備對某位置的空間作用權重，通常含時間強度、距離、方向與遮蔽。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **LOO**：Leave-one-scenario-out，輪流留下一個情境作測試，檢查模型是否只對單一切分有效。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。

## Slide 16: 驗證設計

驗證採分層設計。E1 到 E3 是受控完整場重建、IDW baseline 與 ablation，主要檢查完整 3D 場估計。

E4 到 E6 包含非連網裝置影響學習、48 組窗戶矩陣，以及 hybrid no-Fourier 和 leave-one-scenario-out 檢查。

E7 使用 bedroom_01 的 28 筆真實快照做 pillow hold-out 檢查。E8 是推薦動作介入驗證 protocol，E9 是公開資料集 task-aligned benchmark。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Window matrix**：依季節、天氣、時段等組合建立的窗戶外部邊界情境集合。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Synthetic full-field**：可取得完整場 truth 的受控驗證資料，用於完整 3D 場誤差比較。
- **Ablation**：移除或替換模型元件後比較性能，用來檢查各元件貢獻。
- **LOO**：Leave-one-scenario-out，輪流留下一個情境作測試，檢查模型是否只對單一切分有效。
- **No-Fourier**：去除或比較 Fourier 相關處理的對照設定，用於確認改善不是單一頻域技巧造成。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **Pillow hold-out**：將 pillow 位置作為未參與校正 fitting 的參考點，用於測試非感測點估計效果。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 17: 證據鏈與 Claim Boundary

Synthetic full-field 支援完整 3D 場誤差比較，因此可以用來比較 base model、IDW、ablation 與 hybrid residual。

Real-bedroom snapshot 支援真實稀疏校正檢查，尤其是 pillow hold-out 點，但它不是 dense real-room ground truth。

Public datasets 只支援相容子任務，不能被解讀為單房間 8 點拓樸或完整 3D 場驗證。Recommendation 目前也只是反事實排序，尚需真實 before/after intervention 證明因果改善。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Synthetic full-field**：可取得完整場 truth 的受控驗證資料，用於完整 3D 場誤差比較。
- **Ablation**：移除或替換模型元件後比較性能，用來檢查各元件貢獻。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **Pillow hold-out**：將 pillow 位置作為未參與校正 fitting 的參考點，用於測試非感測點估計效果。
- **Dense ground truth**：房間內大量點位的真實環境場資料，是更嚴格但較難取得的驗證基準。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 18: 情境設計與輸入模式

標準情境包含 idle、單裝置啟動、雙裝置組合與 all_active，用來觀察不同裝置組合對三因子場的影響。

窗戶部分除了 48 組季節、天氣與時段矩陣，也支援 direct input，讓使用者直接指定外部溫度、濕度、日照與開窗比例。

所有 scenario 都有時間軸設定，設備影響採一階收斂近似，因此可以看啟動後逐步接近 quasi-steady state 的過程。

### 名詞註釋
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Direct input**：不使用預設矩陣情境，直接輸入外部溫濕度、日照與開窗比例。
- **Quasi-steady state**：近似達到穩定但非嚴格物理穩態的狀態，用於簡化時間響應解讀。

## Slide 19: 主要量化結果

8 組標準情境中，base model 平均 field MAE 為 temperature 0.0474、humidity 0.1765、illuminance 2.0835。

圖中比較 IDW、base model 與 leave-one-scenario-out hybrid residual。IDW 因缺少裝置位置、方向與物理先驗，在照度與局部場上特別不利。

真實臥室 pillow 點的 raw MAE 為 T=0.8967, H=4.1286, L=358.6392，校正後 MAE 為 T=0.1676, H=0.3939, L=21.3753，顯示稀疏校正在此設定下有明顯改善。

### 名詞註釋
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **LOO**：Leave-one-scenario-out，輪流留下一個情境作測試，檢查模型是否只對單一切分有效。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **Pillow hold-out**：將 pillow 位置作為未參與校正 fitting 的參考點，用於測試非感測點估計效果。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。

## Slide 20: 真實臥室快照與推薦驗證狀態

E7 的重點是 pillow 參考點沒有參與 8 個角點 residual fitting，因此它可以用來檢查校正場是否改善非感測點估計。

結果上，校正後 pillow MAE 從 raw 的 T=0.8967, H=4.1286, L=358.6392 降到 T=0.1676, H=0.3939, L=21.3753。

E8 目前是推薦動作驗證 protocol。也就是說，本研究已能做模型反事實排序，但實際控制行為是否真的改善舒適度，仍需要 before/after intervention 來驗證。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **Pillow hold-out**：將 pillow 位置作為未參與校正 fitting 的參考點，用於測試非感測點估計效果。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 21: 3D 視覺化結果

這頁展示不同情境下的 3D 場分布，例如 all_active 的溫度場、window_only 的照度場，以及 ac_only 的溫度場。

3D 圖的功能是幫助理解空間分布，不直接作為新的量化實驗。量化結果仍以前面提到的 field MAE、baseline comparison 和 hold-out 檢查為主。

可以看到裝置位置與作用方向會造成局部差異，這也是為什麼模型不能只用單一平均值或純距離插值處理。

### 名詞註釋
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Pillow hold-out**：將 pillow 位置作為未參與校正 fitting 的參考點，用於測試非感測點估計效果。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。

## Slide 22: Hybrid Residual 結果

Default held-out 的 train/test samples 為 576 / 192，hybrid test MAE 為 T=0.0023, H=0.0041, L=0.1675。

No-Fourier 對照的 MAE 為 T=0.0022, H=0.0045, L=0.1675，LOO 平均 hybrid MAE 為 T=0.0017, H=0.0055, L=0.1581。

這些結果表示標準情境 family 內的 residual 有可學習性，但不能直接擴大解讀為任意房間、任意裝置配置都能泛化。

### 名詞註釋
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **LOO**：Leave-one-scenario-out，輪流留下一個情境作測試，檢查模型是否只對單一切分有效。
- **No-Fourier**：去除或比較 Fourier 相關處理的對照設定，用於確認改善不是單一頻域技巧造成。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。

## Slide 23: 公開資料任務拆解：SML2010

SML2010 被映射成 two-point boundary-response benchmark。它適合檢查外氣、日照與室內兩點響應，但沒有完整 3D 場真值。

S1 純照度短視窗是主要劣勢，因為 persistence 在短時間照度高度自相關時很強。S2 長視窗溫度有部分優勢，但濕度有尺度對齊問題。

S3 facade event delta 是主要優勢，因為事件後變化方向和長視窗響應更能受益於 structured prior。

### 名詞註釋
- **SML2010**：公開智慧建築資料集；本研究用於 two-point boundary-response 類任務。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Dense ground truth**：房間內大量點位的真實環境場資料，是更嚴格但較難取得的驗證基準。
- **Persistence**：直接沿用上一時步值作預測的時間序列 baseline，在高慣性短視窗資料中通常很強。
- **Structured prior**：模型內建的設備、邊界與物理結構先驗。
- **Facade event delta**：檢查外部邊界或事件造成的變化量，而非只預測下一時步絕對值。

## Slide 24: 公開資料任務拆解：CU-BEMS

CU-BEMS 被映射成商辦 zone-level device-response benchmark。它有 AC power 和 lighting power 等欄位，但不是本研究的單房間 8 點拓樸。

C1 中 AC 溫濕度可補強 linear regression，但不勝 persistence。C2 商辦照度與單房間光學假設差距大，是明確劣勢。

C3 compound event 可勝 linear regression，但仍不勝 persistence。這表示本研究特徵對事件讀出有幫助，但不能宣稱在商辦時序任務全面勝出。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **CU-BEMS**：商辦建築能源管理資料集；本研究用於 zone-level device-response 類任務。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Persistence**：直接沿用上一時步值作預測的時間序列 baseline，在高慣性短視窗資料中通常很強。
- **Linear regression**：線性回歸 baseline，用線性權重將輸入特徵映射到目標值。
- **Device-response benchmark**：以設備用電或啟動訊號對 zone 環境變化的響應作為比較任務。
- **Zone-level**：以建築區域平均值為資料粒度，不含房間內細緻 3D 幾何。

## Slide 25: 結論、限制與未來工作

本研究完成一個單房間三因子空間數位孿生原型，能在少量角落感測器下估計溫度、濕度與照度分布，並支援非連網裝置影響學習。

限制方面，目前仍缺長期 dense real-room ground truth，hybrid residual 的泛化也主要限於標準情境 family。

未來工作包括擴大 ESP32 長期資料、加入 CO2/PM2.5、發展 multi-zone model、執行推薦動作介入驗證，以及往閉環控制與遠端 MCP 延伸。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Dense ground truth**：房間內大量點位的真實環境場資料，是更嚴格但較難取得的驗證基準。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。
- **ESP32**：低成本微控制器平台，可用於後續長期真實感測資料蒐集。
- **CO2**：二氧化碳濃度，可作為未來室內空氣品質因子。
- **PM2.5**：細懸浮微粒濃度，可作為未來室內空氣品質因子。
- **Multi-zone model**：將房間或建築切成多個區域處理交換與隔間效應的模型。
- **閉環控制**：模型輸出進一步驅動控制動作，並用後續感測結果回饋修正決策。

## Slide 26: 公式與指標整理

後半段整理公式與指標。第一組是場模型，包括三因子場、總估計式、baseline、activation 與 influence envelope。

第二組是三因子 nominal model，分別說明溫度、濕度與照度為什麼要採用不同的物理近似。

第三組是校正與評估，包括 8 點三線性 residual correction、非連網裝置影響學習、hybrid residual、MAE/RMSE/correlation、IDW baseline 與推薦排序。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Activation**：設備啟動強度隨時間接近穩態的函數。
- **Influence envelope**：設備對某位置的空間作用權重，通常含時間強度、距離、方向與遮蔽。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。
- **RMSE**：Root Mean Squared Error，均方根誤差；比 MAE 更放大尖峰或離群誤差。
- **Correlation**：衡量預測與真值趨勢方向一致性的指標。

## Slide 27: 公式說明 1：三因子場與查詢點

這頁說明「場的定義」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：T(p,t)：位置 p、時間 t 的溫度；H(p,t)：位置 p、時間 t 的相對濕度；L(p,t)：位置 p、時間 t 的照度。

接著說明「主張邊界」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：本研究不是只估單一平均值；輸出是三維空間中任意點的三個環境量；8 顆角落感測器只提供稀疏觀測。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **H(p,t)**：位置 p、時間 t 的相對濕度場值。
- **L(p,t)**：位置 p、時間 t 的照度場值。

## Slide 28: 公式說明 2：總估計式

這頁說明「主公式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：F̂ᵥ(p,t) = Nᵥ(p,t) + Cᵥ(p,t)；v ∈ {T,H,L}；T：temperature；H：relative humidity；L：illuminance。

接著說明「為什麼這樣拆」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：Nᵥ 讓模型先有設備、邊界與空間結構；Cᵥ 讓模型對齊真實角落感測器；三個變數共用此估計框架。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **H(p,t)**：位置 p、時間 t 的相對濕度場值。
- **L(p,t)**：位置 p、時間 t 的照度場值。

## Slide 29: 公式說明 3：Indoor baseline

這頁說明「baseline 定義」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：b₀ = (T₀, H₀, L₀)；T₀：設備作用前的室內基準溫度；H₀：設備作用前的室內基準相對濕度。

接著說明「跟 baseline 比較法的差別」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：這裡的 baseline 是模型起始狀態；不是第 5 章的 IDW baseline；也不是公開資料集的 persistence 或 linear regression。

### 名詞註釋
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Persistence**：直接沿用上一時步值作預測的時間序列 baseline，在高慣性短視窗資料中通常很強。
- **Linear regression**：線性回歸 baseline，用線性權重將輸入特徵映射到目標值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。

## Slide 30: 公式說明 4：baseline 的取得方式

這頁說明「有啟動前觀測時」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：T₀ = (1/|S|) ∑ₛ∈S Oₜ(pₛ, t_{ref})；H₀ = (1/|S|) ∑ₛ∈S Oₕ(pₛ, t_{ref})；L₀ = (1/|S|) ∑ₛ∈S Oₗ(pₛ, t_{ref})。

接著說明「沒有啟動前觀測時」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：改由房間設計檔、情境設定或 demo 輸入提供；例如標準房間預設 T₀=29°C、H₀=67%、L₀=90 lux；因此 baseline 不是模型學出來的黑盒值。

### 名詞註釋
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **黑盒模型**：主要依資料學習輸入輸出關係、但內部物理意義較不明確的模型。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。

## Slide 31: 公式說明 5：高度正規化

這頁說明「垂直座標」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：ζ = z / Hᵣ - 1/2；Hᵣ：房間高度；z：查詢點高度。

接著說明「為什麼需要」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：室內溫度與濕度可能存在垂直分層；冷空氣、熱源與混合程度會讓上下層不同；ζ 提供低成本的高度修正項。

### 名詞註釋
- **ζ**：高度正規化座標，用於描述查詢點相對於房間高度的位置。

## Slide 32: 公式說明 6：設備 activation

這頁說明「時間響應」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Aⱼ(t) = aⱼ(1 - exp(-t/τⱼ))；j 代表某個設備，例如冷氣、窗戶或燈具；aⱼ：設備影響的穩態比例或強度尺度。

接著說明「使用原因」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：設備不會在啟動瞬間把全室改變到穩態；冷氣降溫、除濕與窗戶交換都需要時間；這是一階收斂近似，計算成本低且可解釋。

### 名詞註釋
- **Activation**：設備啟動強度隨時間接近穩態的函數。
- **τⱼ**：設備時間響應常數，控制 activation 接近穩態的速度。

## Slide 33: 公式說明 7：influence envelope

這頁說明「空間作用範圍」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Eⱼ(p,t) = Aⱼ(t) Rⱼ(p) Dⱼ(p,t) Vⱼ(p)；Aⱼ(t)：設備目前啟動強度；Rⱼ(p)：距離衰減。

接著說明「距離衰減」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：Rⱼ(p) = exp(-||p - pⱼ|| / rⱼ)；pⱼ：設備位置；rⱼ：設備作用半徑或衰減尺度。

### 名詞註釋
- **Activation**：設備啟動強度隨時間接近穩態的函數。
- **Influence envelope**：設備對某位置的空間作用權重，通常含時間強度、距離、方向與遮蔽。
- **Distance decay**：距離設備越遠，局部作用越弱的權重函數。
- **Directionality**：冷氣出風方向、窗戶日照方向或光源方向造成的非均向影響。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。

## Slide 34: 公式說明 8：溫度場主式

這頁說明「溫度 nominal model」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：N_T(p,t) = T₀ + B_T(t) + S_T(p,t) + γ_T M(t) ζ；T₀：室內基準溫度；B_T(t)：全室平均熱響應。

接著說明「使用原因」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：溫度受熱交換、熱源與空氣混合影響；只做局部衰減會低估冷氣的全室降溫；所以保留 B_T 表示整體室溫移動。

### 名詞註釋
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。
- **ζ**：高度正規化座標，用於描述查詢點相對於房間高度的位置。
- **B 項**：表示全室平均狀態偏移的 bulk/global effect。
- **S 項**：表示設備附近、窗邊或光源附近的局部空間差異。

## Slide 35: 公式說明 9：溫度的全室與局部項

這頁說明「分解式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：B_T(t) = B_ac,T(t) + B_win,T(t) + B_light,T(t)；S_T(p,t) = S_ac,T(p,t) + S_win,T(p,t) + S_light,T(p,t)；B_T 負責全室平均狀態改變。

接著說明「三類來源」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：冷氣：依模式與設定溫差讓室內趨冷或趨暖；窗戶：依 T_out - T₀ 表示外氣熱交換方向；燈具：在溫度路徑中視為小型熱源。

### 名詞註釋
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。
- **B 項**：表示全室平均狀態偏移的 bulk/global effect。
- **S 項**：表示設備附近、窗邊或光源附近的局部空間差異。

## Slide 36: 公式說明 10：冷氣溫度項

這頁說明「冷氣全室項」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：B_ac,T(t) = s_m k_ac,Tᵍ d_T P_ac A_ac(t)；s_m：冷房或暖房模式符號；k_ac,Tᵍ：冷氣對全室溫度的增益係數。

接著說明「冷氣局部項」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：S_ac,T(p,t) = s_m k_ac,Tˢ d_T P_ac E_ac(p,t)；k_ac,Tˢ：冷氣局部空間增益；E_ac(p,t)：出風口附近、方向與遮蔽造成的空間權重。

### 名詞註釋
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **B 項**：表示全室平均狀態偏移的 bulk/global effect。
- **S 項**：表示設備附近、窗邊或光源附近的局部空間差異。

## Slide 37: 公式說明 11：窗戶與燈具溫度項

這頁說明「窗戶熱交換」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：B_win,T(t) = k_win,Tᵍ (T_out - T₀) P_win A_win(t)；S_win,T(p,t) = k_win,Tˢ (T_out - T₀) P_win E_win(p,t)；T_out > T₀ 時偏升溫。

接著說明「燈具熱源」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：B_light,T(t) = k_light,Tᵍ P_light A_light(t)；S_light,T(p,t) = k_light,Tˢ P_light E_light(p,t)；燈具在溫度模型裡只代表發熱。

### 名詞註釋
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。
- **B 項**：表示全室平均狀態偏移的 bulk/global effect。
- **S 項**：表示設備附近、窗邊或光源附近的局部空間差異。

## Slide 38: 公式說明 12：濕度場主式

這頁說明「濕度 nominal model」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：N_H(p,t) = clip[0,100]{H₀ + B_H(t) + S_H(p,t) - γ_H M(t) ζ}；H₀：室內基準相對濕度；B_H(t)：全室平均水氣或除濕響應。

接著說明「使用原因」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：相對濕度有明確物理範圍；冷氣常見效果是除濕，所以符號方向不同於溫度；窗戶則由室外濕度與室內基準濕度差決定。

### 名詞註釋
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **H(p,t)**：位置 p、時間 t 的相對濕度場值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。
- **ζ**：高度正規化座標，用於描述查詢點相對於房間高度的位置。
- **B 項**：表示全室平均狀態偏移的 bulk/global effect。
- **S 項**：表示設備附近、窗邊或光源附近的局部空間差異。
- **clip[0,100]**：把相對濕度限制在 0% 到 100% 的合理物理範圍內。

## Slide 39: 公式說明 13：濕度來源項

這頁說明「全室濕度項」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：B_H(t) = -k_ac,Hᵍ d_H P_ac A_ac(t)；+ k_win,Hᵍ (H_out - H₀) P_win A_win(t)；冷氣項為負：表示除濕。

接著說明「局部濕度項」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：S_H(p,t) = -k_ac,Hˢ d_H P_ac E_ac(p,t)；+ k_win,Hˢ (H_out - H₀) P_win E_win(p,t)；E_ac 讓除濕效果在冷氣影響區附近更強。

### 名詞註釋
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **H(p,t)**：位置 p、時間 t 的相對濕度場值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。
- **B 項**：表示全室平均狀態偏移的 bulk/global effect。
- **S 項**：表示設備附近、窗邊或光源附近的局部空間差異。

## Slide 40: 公式說明 14：照度場主式

這頁說明「照度 nominal model」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：N_L(p,t) = max{0, L₀ + L_winᵈⁱʳ(p,t)；+ L_lightᵈⁱʳ(p,t) + L_winᵃᵐᵇ(p,t) + Iʳᵉᶠˡ(p,t)}；L₀：室內基準照度。

接著說明「為什麼不同於溫濕度」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：照度不是空氣混合或水氣交換問題；它更接近光線幾何與可視性問題；燈具與窗戶可造成局部高照度峰值。

### 名詞註釋
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **L(p,t)**：位置 p、時間 t 的照度場值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。
- **max{0}**：把照度限制為非負值，避免模型輸出不合理的負照度。
- **直射光**：直接由窗戶或燈具到達查詢點的照度貢獻。
- **一次漫反射**：只計算一次表面反射對照度的回填效果，是輕量近似而非完整 radiosity。

## Slide 41: 公式說明 15：直射光與環境光

這頁說明「窗戶直射光」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：L_winᵈⁱʳ(p,t) = S_out d_f k_sol P_win E_win(p,t)；S_out：室外日照強度；d_f：與時間、季節或日照方向相關的折減。

接著說明「燈具與環境光」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：L_lightᵈⁱʳ(p,t) = G_light P_light E_light(p,t)；L_winᵃᵐᵇ(p,t)：窗戶帶來的擴散環境光；G_light：燈具光通量尺度。

### 名詞註釋
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **直射光**：直接由窗戶或燈具到達查詢點的照度貢獻。
- **環境光**：非單一路徑直射、較均勻分布的背景照度貢獻。

## Slide 42: 公式說明 16：一次漫反射

這頁說明「反射公式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Iʳᵉᶠˡ(p,t) = Σ_s ρ_s Ī_s A_sʳᵉˡ exp(-||p-c_s||/ℓ_s)；× max(0, n_s·r̂_s→p) V_s(p)；s：牆、地板、天花板或家具表面。

接著說明「限制與說法」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：一次漫反射用來補足非直射區域的回填亮度；它不是完整 ray tracing 或 radiosity；只計算一次反射，因此成本較低。

### 名詞註釋
- **Ray tracing**：依光線路徑追蹤照明傳播的精密光學方法；本研究只採輕量照度幾何與一次漫反射近似。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **一次漫反射**：只計算一次表面反射對照度的回填效果，是輕量近似而非完整 radiosity。
- **反射率 ρ**：表面反射率，描述牆面、地板或家具把入射光反射出去的比例。

## Slide 43: 公式說明 17：8 參數校正多項式

這頁說明「三線性形式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：C(p) = c₀ + c₁X + c₂Y + c₃Z；+ c₄XY + c₅XZ + c₆YZ + c₇XYZ；X,Y,Z 是正規化房間座標。

接著說明「為什麼剛好 8 點」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：房間有地面四角與天花板四角；每個變數在同一時間有 8 個 residual；三線性校正場也有 8 個自由度。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **三線性函數空間**：由 1、X、Y、Z 與交互項組成的 8 維 residual 表示空間。

## Slide 44: 公式說明 18：角點 residual

這頁說明「residual 定義」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：rᵛ_{abc}(t) = Oᵥ(p_{abc},t) - Nᵥ(p_{abc},t)；a,b,c ∈ {0,1}；p_{abc}：其中一個房間角點。

接著說明「直覺意義」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：rᵛ 是主模型在感測點的誤差；如果 rᵛ 為正，代表模型低估該角點；如果 rᵛ 為負，代表模型高估該角點。

### 名詞註釋
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **角點 residual**：角落感測器觀測值與 nominal model 預測值的差。

## Slide 45: 公式說明 19：三線性校正式

這頁說明「校正公式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Cᵥ(X,Y,Z,t) = Σ_{a,b,c∈{0,1}} rᵛ_{abc}(t)；× ℓ_a(X) ℓ_b(Y) ℓ_c(Z)；ℓ₀(u)=1-u，ℓ₁(u)=u。

接著說明「重要性質」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：所有權重非負且總和為 1；所以這是房間內部補間，不是無限制外插；在任一角點上，對應權重為 1，其餘為 0。

### 名詞註釋
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **角點 residual**：角落感測器觀測值與 nominal model 預測值的差。
- **補間權重 ℓ**：三線性補間中每個角點 residual 對內部點的權重函數。

## Slide 46: 公式說明 20：校正後估計值

這頁說明「回到主公式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：F̂ᵥ(p,t) = Nᵥ(p,t) + Cᵥ(p,t)；在角點：Cᵥ 等於觀測 residual；所以 F̂ᵥ(p_{abc},t) = Oᵥ(p_{abc},t)。

接著說明「主張邊界」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：8 顆感測器不能直接量到所有點；我們證明的是三線性 residual correction 的一致性與可表示範圍；其他點是 nominal model 加上低階 residual 補間的估計。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **角點 residual**：角落感測器觀測值與 nominal model 預測值的差。

## Slide 47: 公式說明 21：可完全表示的 residual 空間

這頁說明「函數空間」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：𝒱 = span{1, X, Y, Z, XY, XZ, YZ, XYZ}；這個空間的維度是 8；三線性函數可由 8 個角點取值唯一決定。

接著說明「嚴謹主張」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：這不是說所有室內場都一定是三線性；而是說在三線性 residual 假設下可完全重建；對平滑但非三線性的 residual，則用誤差界描述接近程度。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **三線性函數空間**：由 1、X、Y、Z 與交互項組成的 8 維 residual 表示空間。

## Slide 48: 公式說明 22：平滑 residual 的誤差界

這頁說明「誤差上界」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：|Rᵥ(p,t) - Cᵥ(p,t)| ≤ W²M_xx/8 + L²M_yy/8；+ H²M_zz/8；Rᵥ：真實 residual。

接著說明「如何解釋「接近」」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：M_xx/M_yy/M_zz 是 residual 二階曲率上界；曲率越小，代表 residual 越平滑；平滑時，8 點三線性補間誤差可被上界限制。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **誤差上界**：用 residual 二階曲率限制三線性補間與真實 residual 的最大偏差。

## Slide 49: 公式說明 23：非連網裝置影響學習

這頁說明「特徵向量」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：φᵢ = [xᵢ,yᵢ,zᵢ,tᵢ, baseline, outdoor, F_temp,；F_hum, F_illum, activations, powers, envelopes]；φᵢ 是模型已知的情境特徵。

接著說明「標籤定義」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：yᵢᵛ = F_trueᵛ(pᵢ,tᵢ) - Fᵥ(pᵢ,tᵢ)；yᵢᵛ 是主模型尚未吸收的 residual target；before/after 觀測提供設備啟用造成的差異訊號。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Activation**：設備啟動強度隨時間接近穩態的函數。
- **Influence envelope**：設備對某位置的空間作用權重，通常含時間強度、距離、方向與遮蔽。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。
- **特徵向量 φᵢ**：模型訓練時輸入的情境特徵，例如座標、時間、baseline、外部條件與設備作用。
- **標籤 yᵢ**：監督式學習中的目標值；本研究常用 true field 與 base estimator 的差作 residual label。

## Slide 50: 公式說明 24：Hybrid residual

這頁說明「第二層修正」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：F_hybridᵛ(p,t) = Fᵥ(p,t) + Rᵥ(p,t; θᵥ)；Fᵥ：前面可解釋的 base estimator；Rᵥ：小型 neural network 預測的 residual。

接著說明「定位」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：hybrid 不是取代物理模型；它只修正主模型剩下的系統性誤差；這樣可保留可解釋結構。

### 名詞註釋
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。

## Slide 51: 公式說明 25：Hybrid 訓練目標

這頁說明「residual label」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Rᵥ*(p,t) = F_trueᵛ(p,t) - Fᵥ(p,t)；F_trueᵛ：訓練或合成 truth 場；Fᵥ：base estimator 輸出。

接著說明「損失函數」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：ℒ(θᵥ) = (1/N)Σᵢ ||Rᵥ* - Rᵥ(pᵢ,tᵢ;θᵥ)||²；+ λ||θᵥ||²；第一項是 residual 預測誤差。

### 名詞註釋
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **標籤 yᵢ**：監督式學習中的目標值；本研究常用 true field 與 base estimator 的差作 residual label。
- **損失函數 ℒ**：訓練 neural network 時要最小化的目標函數。
- **正則化 λ**：限制模型參數大小以降低過擬合的項。

## Slide 52: 公式說明 26：MAE、RMSE 與 Correlation

這頁說明「誤差指標」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：MAE = (1/n) Σᵢ |ŷᵢ - yᵢ|；RMSE = √[(1/n) Σᵢ (ŷᵢ - yᵢ)²]；ŷᵢ：模型估計值。

接著說明「使用原因」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：MAE 代表平均偏差，最直觀；RMSE 會放大尖峰或離群誤差；Correlation 用於公開資料時序任務，檢查趨勢是否同向。

### 名詞註釋
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。
- **RMSE**：Root Mean Squared Error，均方根誤差；比 MAE 更放大尖峰或離群誤差。
- **Correlation**：衡量預測與真值趨勢方向一致性的指標。
- **標籤 yᵢ**：監督式學習中的目標值；本研究常用 true field 與 base estimator 的差作 residual label。

## Slide 53: 公式說明 27：IDW baseline

這頁說明「IDW 插值」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：IDW(p) = Σ_s w_s O_s / Σ_s w_s；w_s = 1 / (dist(p,s) + ε)^q；s：感測器索引。

接著說明「為什麼拿它比較」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：IDW 是無設備物理先驗的幾何插值 baseline；它只知道感測器位置與距離；不知道冷氣出風、窗戶日照或燈具位置。

### 名詞註釋
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **IDW 權重**：IDW 中由距離決定的感測器權重，距離越近權重越高。

## Slide 54: 公式說明 28：推薦排序與驗證

這頁說明「推薦分數」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Score(a) = P_before - P_after；Penalty 越大代表越偏離舒適目標；P_before：採取動作前的目標區域懲罰。

接著說明「必須說清楚的限制」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：目前推薦排序是 counterfactual simulation；它是模型預測下的改善，不等於已證明因果效果；真正驗證需做 before/after intervention。

### 名詞註釋
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。
- **Score(a)**：候選動作 a 的推薦分數，通常由採取前後 comfort penalty 的下降量決定。
