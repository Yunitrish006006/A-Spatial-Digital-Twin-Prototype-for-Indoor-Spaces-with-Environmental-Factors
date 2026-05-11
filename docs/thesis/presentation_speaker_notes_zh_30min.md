# 30 分鐘論文簡報逐頁講稿

本檔是 `thesis_presentation_zh_30min.pptx` 的講稿，不放入投影片畫面。投影片維持正式內容；這份 Markdown 用於練習口頭說明與答辯準備。

## Slide 1: 封面

各位老師好，我是林昀佑。今天報告的題目是「單房間非連網家電環境影響學習之稀疏感測空間數位孿生原型」。題目中的「單房間」代表研究範圍先限制在一個可明確定義幾何邊界的室內空間；「非連網家電」指的是冷氣、窗戶、燈具這類會影響環境，但通常沒有穩定 API 可以讀取狀態的設備；「稀疏感測」則表示系統只依賴少量感測點，而不是完整佈滿房間的感測陣列。

這個研究要解決的核心問題是：使用者真正關心的是床邊、桌面、窗邊或其他位置的舒適狀態，但系統通常只能看到少數感測器讀值，而且很多設備狀態還要靠使用者或介面輸入。因此我建立一個可以把房間幾何、設備狀態與少量感測資料結合起來的空間數位孿生原型。

整體研究不是要取代完整 CFD 或精密光學模擬，也不是把所有問題交給黑盒模型處理。我的定位是控制導向與決策支援：模型需要足夠可解釋、可以被感測資料校正，也能輸出任意位置或區域的溫度、濕度與照度估計。

後面報告會先說明為什麼這個問題重要，再說明模型與系統怎麼設計，最後用 synthetic full-field、真實臥室快照與公開資料相容子任務說明目前的驗證範圍。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **控制導向**：模型重點在支援查詢、比較與推薦排序，而不是取代高精度物理模擬器。
- **CFD**：Computational Fluid Dynamics，計算流體力學；可模擬細緻氣流，但邊界條件與計算成本高。
- **API**：Application Programming Interface，讓系統讀取或控制設備狀態的程式介面。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **黑盒模型**：主要依資料學習輸入輸出關係、但內部物理意義較不明確的模型。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Synthetic full-field**：可取得完整場 truth 的受控驗證資料，用於完整 3D 場誤差比較。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。

## Slide 2: 報告流程

整份報告會依照「問題、方法、實作、驗證、限制」的順序走。前半段先建立研究動機，說明為什麼非連網設備與有限感測器會讓室內環境估計變困難。

接著會進入文獻定位與研究缺口。這裡的重點不是逐篇列文獻，而是說明既有 IEQ、場重建、hybrid model 與 digital twin 研究，和本研究的單房間、三因子、低成本角落感測設定有什麼差異。

方法部分會先看整體系統架構，再拆成數學模型、校正流程、影響學習與推薦排序。這樣安排是因為本研究不是只有一個公式，而是一個從輸入資料到可查詢服務的完整 pipeline。

驗證部分會分成受控完整場、真實臥室快照、hybrid residual、公開資料集與推薦驗證狀態。每一類資料能支持的結論不同，所以我會特別區分哪些結果可以證明 field reconstruction，哪些只能作為 sparse calibration 或 task-aligned benchmark。

最後會整理目前已完成的貢獻、尚未完成的真實介入驗證，以及後續要補強的硬體、資料量與泛化能力。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **IEQ**：Indoor Environmental Quality，室內環境品質，通常涵蓋熱舒適、空氣品質、照明等因素。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Synthetic full-field**：可取得完整場 truth 的受控驗證資料，用於完整 3D 場誤差比較。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 3: 研究主軸與輸入輸出

這頁把研究整理成三段：輸入、模型與輸出。輸入端不是只有感測值，還包含房間尺寸、座標系、8 顆角落感測器、室內 baseline、室外邊界條件、時間，以及冷氣、窗戶、燈具等設備狀態。

這些輸入之所以都需要，是因為室內環境不是均勻的。冷氣出風方向、窗戶日照位置、燈具距離、家具遮蔽，都會讓同一個房間中的不同位置出現不同溫度、濕度或照度。

模型端先用變數專屬 nominal model 建立可解釋的主要趨勢，再用 power calibration 調整設備作用強度，最後用 trilinear residual correction 把 8 個角落觀測到的誤差補到整個房間。Hybrid residual 是額外的第二層修正，用來學習 base model 還沒有捕捉到的剩餘誤差。

輸出端包含兩種層級。第一種是估計結果，例如任意 sample point 或 zone 的溫度、濕度、照度，以及 3D 視覺化。第二種是決策支援，例如學習到的非連網裝置影響係數，和針對目標舒適度的反事實推薦排序。

因此這頁的主軸可以理解成：少量感測資料本身不夠，但如果結合房間幾何、設備先驗與校正機制，就能把 sparse observations 轉成可查詢的 spatial field。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Sample**：指定房間中的查詢點，用來取得該座標的三因子估計。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **影響係數 β_m**：描述裝置操作對第 m 個環境因子的方向與大小；m 可為溫度、濕度或照度。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **座標系**：用 x/y/z 公尺座標描述房間內位置；本研究原點在地面西南角。

## Slide 4: 研究背景與問題

一般智慧居家或智慧建築如果要做舒適度評估、能源管理或設備控制，必須先知道室內環境狀態。但實際房間裡的很多設備並不會主動回報狀態，例如傳統冷氣、手動窗戶或一般燈具。

這造成第一個問題：設備有影響，但系統看不到完整狀態。冷氣可能正在冷房、窗戶可能正在引入外氣或日照、燈具可能改變桌面照度，但如果沒有 API 或遙測，就不能直接把這些資訊當成可靠輸入。

第二個問題是感測器很少。即使有 1 到 8 顆感測器，它們也只能代表少數位置。以臥室為例，床頭、書桌、窗邊和門側的狀態可能不同，但使用者通常不會在每個位置都放一顆感測器。

所以本研究要處理的是一個資訊不完整的空間估計問題：在設備狀態需要被描述或推定、感測點又有限的情況下，如何估計整個房間的三因子分布。

這裡的目標不是只預測單一平均溫度，而是要能回答「某個位置現在大概是多少」、「某個區域是否偏離目標」、「如果調整冷氣或窗戶，哪個動作比較可能改善」這類空間化問題。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **API**：Application Programming Interface，讓系統讀取或控制設備狀態的程式介面。
- **遙測**：設備主動回報狀態或感測資料；非連網裝置通常缺少這類資料。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。

## Slide 5: 研究問題與貢獻

本研究拆成四個研究問題。第一是場估計問題：在單房間中，只使用 8 顆角落感測器與房間幾何，能不能估計溫度、濕度與照度的 3D 空間場。

第二是裝置影響學習問題：對於沒有 API 的冷氣、窗戶與燈具，能不能透過 before/after observations，把實際操作轉成可學習的影響係數，而不是只依賴人工設定。

第三是決策支援問題：當使用者指定 sample point 或 zone，以及三因子的目標值時，系統能不能用反事實模擬比較候選動作，並依 comfort penalty reduction 排序。

第四是系統封裝問題：這個模型能不能不是只停留在離線程式，而是封裝成 Web demo 與 MCP tools，讓人機介面或 AI client 都能查詢同一個核心服務。

對應的貢獻包含：變數專屬三因子 nominal model、8 點 residual correction、非連網裝置影響學習、hybrid residual 修正，以及公開資料集上的 task-aligned benchmark。

同時也要先界定範圍：本研究不宣稱已完成多房間建築級模型，也不宣稱公開資料集能驗證完整 3D 場；公開資料只用來測相容子任務，完整場驗證主要來自受控 synthetic full-field。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **API**：Application Programming Interface，讓系統讀取或控制設備狀態的程式介面。
- **Sample**：指定房間中的查詢點，用來取得該座標的三因子估計。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **影響係數 β_m**：描述裝置操作對第 m 個環境因子的方向與大小；m 可為溫度、濕度或照度。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **Web demo**：人機互動展示介面，用於查看 3D 場、時間軸、設備狀態與查詢結果。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Synthetic full-field**：可取得完整場 truth 的受控驗證資料，用於完整 3D 場誤差比較。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 6: 文獻定位、研究缺口與比較原則

文獻可以先分成幾類。IEQ 研究通常關心熱舒適、空氣品質與照明品質；有限感測器場重建研究關心如何從少量點推估空間分布；hybrid thermal model 結合物理結構與資料驅動；digital twin 平台則強調系統整合與可視化。

這些研究各自提供重要基礎，但和我的設定仍有落差。有些研究依賴比較完整的 BMS 或設備遙測，有些只處理溫度或照度單一因子，有些不處理房間內任意位置的 3D 場估計。

本研究的缺口定位是把幾個限制同時放在一起：單房間、低成本角落感測、非連網裝置、三因子環境量，以及可被查詢和推薦使用的控制導向模型。

公開資料集比較也要小心。SML2010 和 CU-BEMS 很有價值，但它們不是為本研究的 8 點單房間拓樸設計，也沒有 dense 3D ground truth。因此我不把它們說成完整替代驗證，而是拆成 task-aligned 子任務。

這樣做的原因是避免過度宣稱。能直接比較的地方就比較，例如 boundary response 或 device-response；不能比較的地方就明確說明限制，維持論文結論和資料支撐一致。

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
- **Device-response benchmark**：以設備用電或啟動訊號對 zone 環境變化的響應作為比較任務。

## Slide 7: 整體系統架構

這頁說明系統不是單一模型函式，而是一個分層架構。最上層是使用者介面與 AI 工具呼叫，中間是服務編排，底層才是數位孿生核心、校正學習與視覺化輸出。

Web demo 和 MCP tools 都是入口層。Web demo 讓使用者在畫面上設定房間、設備與查詢點；MCP tools 則讓 AI client 用結構化 arguments 呼叫 initialize、sample、learn 或 rank actions。

服務編排層負責把不同入口的資料整理成同一種內部格式，例如 scenario、device_specs、baseline、outdoor boundary 和 estimator configuration。這一層可以避免 Web 顯示和 MCP 查詢走不同邏輯。

核心模型層負責真正的場估計、校正、裝置影響學習與推薦排序。也就是說，介面不直接決定結果，結果都來自同一套 estimator 和 correction pipeline。

這樣設計的好處是可替換性。未來如果要換更好的 residual model、新增 CO2 或 PM2.5，或加入新的設備類型，不需要重寫 Web 或 MCP，只要在核心模型與服務編排補上對應欄位。

### 名詞註釋
- **空間數位孿生**：以房間幾何、裝置、感測器與模型維持一個可查詢的室內環境狀態估計。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **device_specs**：系統把 device_state 合併進目前註冊設備後形成的完整設備清單，是後續 sample、learning 與 ranking 使用的 runtime 裝置狀態。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **Web demo**：人機互動展示介面，用於查看 3D 場、時間軸、設備狀態與查詢結果。
- **Tool calling**：語言模型不是直接計算答案，而是呼叫外部工具取得模型查詢或操作結果。
- **服務編排**：把 scenario、模型估計、校正、推薦與輸出流程串接起來的中介層。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **CO2**：二氧化碳濃度，可作為未來室內空氣品質因子。
- **PM2.5**：細懸浮微粒濃度，可作為未來室內空氣品質因子。

## Slide 8: 主要執行資料流

執行資料流可以分成四步。第一步是取得 runtime request，來源可能是 Web dashboard，也可能是 MCP tool call。兩者都會提供或引用一個 scenario，包含房間、設備、外部邊界與時間。

第二步是資料正規化。系統會把 baseline、device state、furniture obstruction、direct input 和 sensor observations 整理成 estimator 可讀的狀態，而不是讓每個入口各自解讀。

第三步是估計流程。Estimator 先建立 nominal field，這是由設備、幾何與物理先驗產生的主要趨勢；接著用角落感測 residual 做 trilinear correction，必要時再加上 hybrid residual。

第四步是輸出。Dashboard 會拿到 3D 場與視覺化資料，sample_point 會回傳指定座標的 T/H/L，zone summary 會回傳區域平均，rank_actions 則回傳候選動作的預期改善排序。

這頁要強調的是一致性：Web 和 MCP 只是不同使用方式，不是兩套模型。因此同一個 scenario 下，畫面展示、工具查詢和推薦排序應該對齊。

### 名詞註釋
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **Web demo**：人機互動展示介面，用於查看 3D 場、時間軸、設備狀態與查詢結果。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Direct input**：不使用預設矩陣情境，直接輸入外部溫濕度、日照與開窗比例。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。

## Slide 9: 房間拓樸、感測器與目標區域

本研究使用單一矩形房間作為主要研究場景，尺寸為 6 m × 4 m × 3 m。座標系以公尺表示，原點設在房間地面西南角，x、y、z 分別對應房間的水平與高度方向。

使用座標系的原因是模型需要回答任意位置的查詢，而不是只回答感測器所在位置。例如桌面、床邊或窗邊都可以被表示成 p=(x,y,z)，再查詢該點的三因子估計。

8 顆感測器放在地面四角與天花板四角。這樣的配置讓模型至少能觀察房間邊界的低處與高處 residual，對 3D 空間補間比只放同一平面更合理。

這 8 點不等於完整量到全室。它們的角色是提供 sparse observation，用來修正 nominal model 的 residual。Nominal model 提供主要趨勢，角點 residual 則用 trilinear correction 補足模型偏差。

目標區域分成窗邊、中心與門側等 zone，目的是讓後續推薦不只看單一點，也能看一個區域的平均舒適度。這對實際使用比較合理，因為使用者通常關心床區、工作區或窗邊區域，而不是單一座標點。

### 名詞註釋
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **座標系**：用 x/y/z 公尺座標描述房間內位置；本研究原點在地面西南角。

## Slide 10: 模組化裝置與家具阻擋

這頁說明為什麼要把設備和家具都放進模型。冷氣、窗戶與燈具不只是 on/off 狀態，它們在房間中有位置、方向、作用距離、啟動強度和時間響應。

以冷氣為例，除了模式之外，目標溫度、風量、水平與垂直出風角度，以及是否固定或擺動，都會影響哪個位置先變冷。窗戶則和開窗比例、外部溫濕度、日照方向有關；燈具則和光源位置、光束方向與距離衰減有關。

家具在這裡被建模成 bounding box obstruction。它不需要做到精密流體或光學遮擋，但至少可以讓模型知道某些位置和設備之間可能被床、桌子或櫃子阻擋。

因此每個裝置的影響可以被拆成 activation、distance decay、directionality 與 visibility/obstruction 幾個權重。這些權重再組合成 influence envelope，描述裝置對空間中某一點的作用強弱。

這樣做的目的不是追求 CFD 或 ray tracing 等級的細節，而是在低成本資料下保留最重要的幾何資訊，避免模型退化成只看距離或全室平均的粗略估計。

### 名詞註釋
- **CFD**：Computational Fluid Dynamics，計算流體力學；可模擬細緻氣流，但邊界條件與計算成本高。
- **Ray tracing**：依光線路徑追蹤照明傳播的精密光學方法；本研究只採輕量照度幾何與一次漫反射近似。
- **AC operating state**：冷氣操作狀態包含模式、設定溫度、風速/風量、水平與垂直出風角度，以及 fixed/swing 擺動設定。
- **Activation**：設備啟動強度隨時間接近穩態的函數。
- **Influence envelope**：設備對某位置的空間作用權重，通常含時間強度、距離、方向與遮蔽。
- **Distance decay**：距離設備越遠，局部作用越弱的權重函數。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。

## Slide 11: 數學模型

核心估計式是 F_hat_v(p,t)=N_v(p,t)+C_v(p,t)。v 代表環境變數，可以是 temperature、humidity 或 illuminance；p 是房間內位置；t 是時間或 elapsed time。

N_v 是 nominal model，也就是模型在沒有感測器校正前，根據房間、設備、外部邊界和時間所估出的主要趨勢。它負責把物理與幾何先驗放進估計中，例如冷氣方向、窗戶日照或燈具距離。

C_v 是 correction field，也就是用感測器 residual 建立的校正項。Residual 是觀測值減掉 nominal prediction，如果角落感測器發現模型偏高或偏低，C_v 會把這個偏差用三線性補間延伸到房間內部。

三個因子的 nominal model 不能共用同一套公式。溫度主要處理熱交換、熱源與垂直分層；濕度要處理除濕與外氣水氣交換；照度則要處理光源幾何、遮蔽和一次漫反射。

所以這頁的重點是兩層設計：第一層是變數專屬的可解釋 base estimator，第二層是由稀疏感測器提供的 residual correction。後面的 hybrid residual 則是在這兩層之後再學剩餘誤差。

### 名詞註釋
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **一次漫反射**：只計算一次表面反射對照度的回填效果，是輕量近似而非完整 radiosity。

## Slide 12: 方法選擇：為什麼不是純插值、純物理或純黑盒

這頁是在說明方法選擇。第一個可能方法是純插值，例如 IDW。IDW 的優點是簡單，也適合作為 baseline；但它只知道感測器位置與讀值，不知道冷氣出風、窗戶日照、燈具位置或家具遮蔽。

因此在設備造成局部影響時，純插值會吃虧。例如窗邊強光或冷氣出風口附近的局部冷區，不一定能從距離最近的角落感測器直接推回來。

第二個可能方法是完整物理模擬，例如 CFD 或 ray tracing。這類方法精度潛力高，但需要材料、邊界條件、氣流、反射率等大量資訊，計算成本也比較高，和本研究的低成本即時服務目標不一致。

第三個可能方法是純黑盒模型。問題是本研究目前資料量有限，而且需要解釋設備與空間結構如何影響結果；如果完全黑盒，口徑上比較難說明為什麼某個動作會被推薦。

因此本研究採取折衷：先用可解釋 base model 表達主要物理與幾何趨勢，再用 residual correction 貼近感測器，最後用 hybrid residual 學 base model 尚未捕捉到的剩餘誤差。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **CFD**：Computational Fluid Dynamics，計算流體力學；可模擬細緻氣流，但邊界條件與計算成本高。
- **Ray tracing**：依光線路徑追蹤照明傳播的精密光學方法；本研究只採輕量照度幾何與一次漫反射近似。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **黑盒模型**：主要依資料學習輸入輸出關係、但內部物理意義較不明確的模型。

## Slide 13: 模型學習、推論與推薦資料流

這頁把系統分成三條資料流：學習、推論與推薦。三條資料流共用同一個房間與設備表示，但目的不同。

學習資料流從 raw records 開始。系統會把 before/after observations、device_state、baseline、外部邊界和時間對齊成 scenario state，再產生訓練 labels。對 learn_impacts 來說，label 是裝置操作前後的感測變化；對 hybrid residual 來說，label 是 truth field 和 base estimator 之間的 residual。

推論資料流處理的是使用者當下查詢。輸入 runtime state 後，模型先產生 nominal field，再套用 correction 或 hybrid residual，最後得到某個 sample point、zone 或整個 3D grid 的三因子估計。

推薦資料流則是建立在推論之上。系統會列出候選動作，例如調整冷氣、開窗或改變照明，對每個候選動作重新跑一次 counterfactual simulation，再計算 comfort penalty 是否下降。

因此推薦結果目前是模型反事實排序，不等於系統已經真的控制設備並量到改善。這個區分很重要，因為後面 E8 會把實際 before/after intervention 列為未來需要完成的驗證。

### 名詞註釋
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Sample**：指定房間中的查詢點，用來取得該座標的三因子估計。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **device_state**：learn_impacts start 階段輸入的裝置操作狀態，包含 activation、kind、power 與冷氣模式、設定溫度、風速、風向等欄位。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。
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

例如一次冷氣學習事件可以記錄為：冷氣模式 cool、target_temperature 24°C、fan_strength high、horizontal_angle 30°、vertical_angle -15°、swing disabled。系統先保存操作前 8 顆感測器的 T/H/L，再等待操作後同一批感測器的 T/H/L。

整理來說，學習資料是「操作狀態 + 環境快照 + 前後感測讀值」形成的事件紀錄；只有 before 和 after 都存在時才會計算係數。若想追蹤這筆資料來自哪一個推薦動作，目前可寫在 note，或未來新增 action_name 欄位。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
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

驗證採分層設計，因為不同資料能支持的結論不同。E1 到 E3 使用受控完整場資料，重點是直接比較整個 3D field 的估計誤差，並和 IDW baseline 及 ablation variants 比較。

E4 到 E6 驗證模型的其他元件。E4 檢查非連網裝置影響學習是否能從 before/after observations 解出合理係數；E5 檢查 48 組窗戶矩陣與 direct input 對外部邊界的支援；E6 檢查 hybrid no-Fourier 和 leave-one-scenario-out，確認改善不是單一切分造成。

E7 使用 bedroom_01 的 28 筆真實快照做 pillow hold-out 檢查。這裡能支持的是 sparse real-room calibration，也就是校正後對未參與 fitting 的 pillow 點有改善，但它不是 dense 3D truth。

E8 是推薦動作的 before/after intervention protocol。也就是說，現在系統可以做 counterfactual ranking，但實際採取推薦後是否真的降低 comfort penalty，仍需要用介入實驗補上因果驗證。

E9 使用公開資料集做 task-aligned benchmark。這部分不是單房間完整場驗證，而是把公開資料中相容的 boundary-response 或 device-response 子任務拿來壓力測試模型概念。

### 名詞註釋
- **單房間**：本研究限定在單一矩形房間，不處理多房間或整棟建築的氣流與能量交換。
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Direct input**：不使用預設矩陣情境，直接輸入外部溫濕度、日照與開窗比例。
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
- **Dense ground truth**：房間內大量點位的真實環境場資料，是更嚴格但較難取得的驗證基準。
- **Device-response benchmark**：以設備用電或啟動訊號對 zone 環境變化的響應作為比較任務。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Comfort penalty**：偏離目標溫濕照度時的懲罰值，推薦排序用它衡量改善幅度。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 17: 證據鏈與驗證範圍

這頁是把證據鏈和結論邊界講清楚。第一類證據是 synthetic full-field，因為它有完整 3D truth，所以可以真正計算整個房間的 field MAE，並比較 base model、IDW、ablation 和 hybrid residual。

第二類證據是 real-bedroom snapshot。它來自真實臥室，因此比 synthetic 更貼近實際環境；但它只有稀疏量測與 pillow hold-out，不是整個房間每個位置都有 truth。因此它支援的是校正效果檢查，不是完整真實 3D 場驗證。

第三類證據是 public datasets。SML2010 和 CU-BEMS 可以測某些相容子任務，例如外部邊界響應或設備響應，但它們沒有本研究的房間幾何、8 角點感測拓樸與 dense field truth。

第四類是 recommendation。現階段推薦排序是 counterfactual simulation，也就是模型假設採取某動作後重新估計結果；它可以說明系統具備排序能力，但還不能宣稱推薦已被真實介入證明有效。

因此我的結論會分層表述：受控完整場支援主要模型有效性，真實臥室支援 sparse calibration 的可行性，公開資料支援相容任務上的外部壓力測試，推薦則是已完成 protocol 與系統流程、仍待實測介入驗證。

### 名詞註釋
- **稀疏感測**：感測點數量少於完整空間場需求，需靠模型與校正推估未量測位置。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **外部邊界**：室外溫度、濕度、日照等會透過窗戶或邊界條件影響室內的輸入。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **Task-aligned benchmark**：只比較公開資料集中與本研究觀測型態相容的子任務，不宣稱完整場驗證。
- **SML2010**：公開智慧建築資料集；本研究用於 two-point boundary-response 類任務。
- **CU-BEMS**：商辦建築能源管理資料集；本研究用於 zone-level device-response 類任務。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Synthetic full-field**：可取得完整場 truth 的受控驗證資料，用於完整 3D 場誤差比較。
- **Ablation**：移除或替換模型元件後比較性能，用來檢查各元件貢獻。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **Pillow hold-out**：將 pillow 位置作為未參與校正 fitting 的參考點，用於測試非感測點估計效果。
- **Dense ground truth**：房間內大量點位的真實環境場資料，是更嚴格但較難取得的驗證基準。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 18: 情境設計與輸入模式

標準情境共有 8 組，包含 idle、ac_only、window_only、light_only、ac_window、window_light、ac_light 和 all_active。這些情境讓模型可以分別觀察單一設備、兩兩組合，以及全部設備同時作用時的三因子場變化。

這種設計的目的不是列出所有可能生活情境，而是建立可控的 benchmark family。單裝置情境可以看每個裝置的基本影響，雙裝置情境可以看交互作用，all_active 則檢查多來源影響疊加時模型是否仍穩定。

窗戶相關輸入除了標準情境，也包含 48 組 window matrix。矩陣會組合季節、天氣、時段等條件，用來測試外部溫度、濕度與日照輸入變化時，模型是否能產生合理反應。

系統也支援 direct input，讓使用者不一定要選預設矩陣，而可以直接輸入外部溫度、濕度、日照與開窗比例。這對 demo 和 MCP tools 很重要，因為使用者可能會問一個當下的自訂條件。

所有 scenario 都有 elapsed time，設備影響用一階收斂近似描述從剛啟動到接近 quasi-steady state 的過程。這讓系統不只看靜態開關，也能呈現時間推進後的環境變化。

### 名詞註釋
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **MCP**：Model Context Protocol，是讓 LLM application 以標準化方式連接外部資料與工具的 open protocol；本研究用它封裝數位孿生工具。
- **MCP Tools**：MCP server 可暴露可執行工具；client 可列出工具並以結構化 arguments 呼叫。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Direct input**：不使用預設矩陣情境，直接輸入外部溫濕度、日照與開窗比例。
- **Window matrix**：依季節、天氣、時段等組合建立的窗戶外部邊界情境集合。
- **Quasi-steady state**：近似達到穩定但非嚴格物理穩態的狀態，用於簡化時間響應解讀。

## Slide 19: 主要量化結果

這頁上方的柱狀圖是 field_mae_comparison，資料來自 8 組 canonical scenarios 的完整 3D grid 評估。每一個 scenario 都會在整個房間網格上比較估計值與 truth，再把 temperature、humidity、illuminance 各自的 field MAE 平均起來。

圖表的三個群組分別代表溫度、濕度與照度。Y 軸是 log-scale，原因是照度 MAE 的量級比溫度與濕度大很多；因此這張圖要看柱上數字與相對排序，不能只用柱高做線性比例解讀。

每個群組內有三根柱。IDW 使用同一批 8 個角落觀測值做反距離插值，只知道距離與感測值；Base 是本研究的可解釋主模型，包含變數專屬 nominal model、裝置與幾何先驗、power calibration 與 trilinear residual correction；LOO Hybrid 是 leave-one-scenario-out 的 residual model 平均結果，用來檢查第二層 residual 是否只對單一切分有效。

具體數字上，IDW 的平均 field MAE 是 T=0.1723, H=0.4633, L=54.9052；Base 是 T=0.0474, H=0.1765, L=2.0269；LOO Hybrid 是 T=0.0017, H=0.0059, L=0.1407。Base 相對 IDW 的降幅約為 temperature 72.5%、humidity 61.9%、illuminance 96.3%。

解讀重點是：IDW 在照度特別差，因為它不知道窗戶日照方向、燈具位置、家具遮蔽或反射；只靠距離很難重建局部光照分布。溫度與濕度也有改善，表示設備狀態、方向性與房間幾何先驗確實提供了純幾何插值沒有的資訊。

右下角的真實臥室校正檢查不是同一張柱狀圖的資料，而是 E7 bedroom_01 的 28 筆真實快照，房間網格解析度為 12 x 12 x 6。Pillow 參考點沒有參與 8 角點 residual fitting，所以可當 held-out point 檢查非感測點估計。

真實臥室 pillow 點的 raw MAE 為 T=0.8967, H=4.1286, L=309.0142，校正後 MAE 為 T=0.1676, H=0.3939, L=16.6450。相對 raw，校正後降幅約為 temperature 81.3%、humidity 90.5%、illuminance 94.6%。這支持稀疏校正在此真實快照設定下有改善，但仍不能宣稱已具備 dense real-room ground truth 驗證。

### 名詞註釋
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **空間場**：不是單一平均值，而是在房間 3D 座標中任意位置可查詢的環境量分布。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **Directionality**：冷氣出風方向、窗戶日照方向或光源方向造成的非均向影響。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **LOO**：Leave-one-scenario-out，輪流留下一個情境作測試，檢查模型是否只對單一切分有效。
- **Real-bedroom snapshot**：真實臥室中的稀疏量測快照，用於檢查校正對未參與 fitting 點位的改善。
- **Pillow hold-out**：將 pillow 位置作為未參與校正 fitting 的參考點，用於測試非感測點估計效果。
- **Dense ground truth**：房間內大量點位的真實環境場資料，是更嚴格但較難取得的驗證基準。
- **Log-scale**：對數刻度；適合把量級差很多的誤差放在同一張圖，但柱高不能用線性比例直接比較。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。

## Slide 20: 真實臥室快照與推薦驗證狀態

E7 的重點是 pillow 參考點沒有參與 8 個角點 residual fitting，因此它可以用來檢查校正場是否改善非感測點估計。

結果上，校正後 pillow MAE 從 raw 的 T=0.8967, H=4.1286, L=309.0142 降到 T=0.1676, H=0.3939, L=16.6450。

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

Default held-out 的 train/test samples 為 576 / 192，hybrid test MAE 為 T=0.0020, H=0.0051, L=0.1370。

No-Fourier 對照的 MAE 為 T=0.0021, H=0.0057, L=0.1370，LOO 平均 hybrid MAE 為 T=0.0017, H=0.0059, L=0.1407。

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

接著說明「適用範圍」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：本研究不是只估單一平均值；輸出是三維空間中任意點的三個環境量；8 顆角落感測器只提供稀疏觀測。

數字範例：若查詢點 p=(2,1,1.2)，時間 t=10 min，模型輸出 T=27.4°C、H=60%、L=280 lux，表示同一個座標與時間可同時取得三個環境量。

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

數字範例：以溫度為例，若 nominal model 得到 N_T=27.0°C，角點 residual correction 給 C_T=-0.4°C，則校正後 F̂_T=27.0-0.4=26.6°C。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **三因子**：本研究同時估計溫度、相對濕度與照度三種室內環境量。
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Residual correction**：利用感測器 residual 修正 nominal model，使估計更貼近觀測。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **H(p,t)**：位置 p、時間 t 的相對濕度場值。
- **L(p,t)**：位置 p、時間 t 的照度場值。

## Slide 29: 公式說明 3：Indoor baseline

這頁說明「baseline 定義」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：b₀ = (T₀, H₀, L₀)；T₀：設備作用前的室內基準溫度；H₀：設備作用前的室內基準相對濕度。

接著說明「跟 baseline 比較法的差別」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：這裡的 baseline 是模型起始狀態；不是第 5 章的 IDW baseline；也不是公開資料集的 persistence 或 linear regression。

數字範例：一個房間的初始狀態可寫成 b₀=(T₀,H₀,L₀)=(29°C,67%,90 lux)，後續裝置影響都以這組基準值作為起點。

### 名詞註釋
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **Persistence**：直接沿用上一時步值作預測的時間序列 baseline，在高慣性短視窗資料中通常很強。
- **Linear regression**：線性回歸 baseline，用線性權重將輸入特徵映射到目標值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。

## Slide 30: 公式說明 4：baseline 的取得方式

這頁說明「有啟動前觀測時」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：T₀ = (1/|S|) ∑ₛ∈S O_{T}(pₛ, t_{ref})；H₀ = (1/|S|) ∑ₛ∈S O_{H}(pₛ, t_{ref})；L₀ = (1/|S|) ∑ₛ∈S O_{L}(pₛ, t_{ref})。

接著說明「沒有啟動前觀測時」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：改由房間設計檔、情境設定或 demo 輸入提供；例如標準房間預設 T₀=29°C、H₀=67%、L₀=90 lux；因此 baseline 不是模型學出來的黑盒值。

數字範例：若 8 顆角落感測器在 t_{ref} 的溫度總和為 232°C，則 T₀=232/8=29°C；濕度與照度可用相同平均方式取得。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **Scenario**：一組房間、設備、外部邊界與時間設定，用於模擬或驗證。
- **黑盒模型**：主要依資料學習輸入輸出關係、但內部物理意義較不明確的模型。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。

## Slide 31: 公式說明 5：高度正規化

這頁說明「垂直座標」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：ζ = z / Hᵣ - 1/2；Hᵣ：房間高度；z：查詢點高度。

接著說明「為什麼需要」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：室內溫度與濕度可能存在垂直分層；冷空氣、熱源與混合程度會讓上下層不同；ζ 提供低成本的高度修正項。

數字範例：若房高 Hᵣ=3 m、查詢點高度 z=1.2 m，則 ζ=1.2/3-0.5=-0.1，代表位置略低於房間中高。

### 名詞註釋
- **ζ**：高度正規化座標，用於描述查詢點相對於房間高度的位置。

## Slide 32: 公式說明 6：設備 activation

這頁說明「時間響應」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Aⱼ(t) = aⱼ(1 - exp(-t/τⱼ))；j 代表某個設備，例如冷氣、窗戶或燈具；aⱼ：設備影響的穩態比例或強度尺度。

接著說明「使用原因」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：設備不會在啟動瞬間把全室改變到穩態；冷氣降溫、除濕與窗戶交換都需要時間；這是一階收斂近似，計算成本低且可解釋。

數字範例：若穩態強度 a=1、時間常數 τ=10 min、啟動後 t=10 min，則 A(t)=1-exp(-10/10)=1-e^-1≈0.632。

### 名詞註釋
- **Activation**：設備啟動強度隨時間接近穩態的函數。
- **τⱼ**：設備時間響應常數，控制 activation 接近穩態的速度。

## Slide 33: 公式說明 7：influence envelope

這頁說明「空間作用範圍」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Eⱼ(p,t) = Aⱼ(t) Rⱼ(p) Dⱼ(p,t) Vⱼ(p)；Aⱼ(t)：設備目前啟動強度；Rⱼ(p)：距離衰減。

接著說明「距離衰減」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：Rⱼ(p) = exp(-||p - pⱼ|| / rⱼ)；pⱼ：設備位置；rⱼ：設備作用半徑或衰減尺度。

數字範例：若某點的時間強度 A=0.8、距離權重 R=0.5、方向權重 D=0.9、無遮蔽 V=1，則 E=0.8×0.5×0.9×1=0.36。

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

數字範例：若 T₀=29°C、B_T=-1.2°C、S_T=-0.5°C、γ_T M(t)=0.2、ζ=-0.1，則 N_T=29-1.2-0.5+0.2×(-0.1)=27.28°C。

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

數字範例：若冷氣全室項 -1.0°C、窗戶全室項 +0.2°C、燈具熱源 +0.1°C，則 B_T=-1.0+0.2+0.1=-0.7°C。

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

數字範例：冷房模式 s_m=-1，若 k_ac,Tᵍ=0.8、d_T=3、P_ac=1、A_ac=0.5，則 B_ac,T=-1×0.8×3×1×0.5=-1.2°C。

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

數字範例：若窗戶熱交換係數 k_win,Tᵍ=0.05，室外與室內基準溫差 T_out-T₀=4°C，且 P_win=A_win=1，則 B_win,T=0.05×4=+0.20°C。

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

數字範例：若 H₀=67%、B_H=-5%、S_H=+1%、γ_HMζ=0.2，則 N_H=clip[0,100](67-5+1-0.2)=62.8%。

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

數字範例：若冷氣除濕項為 -0.4×10×0.5=-2.0%，窗戶項因 H_out-H₀=8 而為 0.02×8=+0.16%，則全室濕度項合計 -1.84%。

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

數字範例：若 L₀=90 lux、窗戶直射 250 lux、燈具直射 120 lux、環境光 40 lux、一次反射 30 lux，則 N_L=max(0,90+250+120+40+30)=530 lux。

### 名詞註釋
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **L(p,t)**：位置 p、時間 t 的照度場值。
- **b₀**：室內基準狀態，包含基準溫度、相對濕度與照度。
- **max{0}**：把照度限制為非負值，避免模型輸出不合理的負照度。
- **直射光**：直接由窗戶或燈具到達查詢點的照度貢獻。
- **環境光**：非單一路徑直射、較均勻分布的背景照度貢獻。
- **一次漫反射**：只計算一次表面反射對照度的回填效果，是輕量近似而非完整 radiosity。

## Slide 41: 公式說明 15：直射光與環境光

這頁說明「窗戶直射光」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：L_winᵈⁱʳ(p,t) = S_out d_f k_sol P_win E_win(p,t)；S_out：室外日照強度；d_f：與時間、季節或日照方向相關的折減。

接著說明「燈具與環境光」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：L_lightᵈⁱʳ(p,t) = G_light P_light A_light(t) Φ_light(p) Q_light(p) V_light(p)；Φ_light：由光束角推得的 cosine 方向權重；Q_light：參考距離正規化後的距離衰減；V_light：遮蔽或可見性。

數字範例：若燈具增益 G_light=500、P_light=1、A_light=0.8、方向權重 Φ=0.5、距離衰減 Q=0.4、可見性 V=1，則 L_lightᵈⁱʳ=80 lux。

### 名詞註釋
- **Power calibration**：依觀測差異調整設備影響強度，避免裝置作用尺度只依預設值決定。
- **Distance decay**：距離設備越遠，局部作用越弱的權重函數。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **燈具光束權重**：照度模型中用方向權重、距離衰減與可見性近似燈具直射光，而非完整光線追蹤。
- **T(p,t)**：位置 p、時間 t 的溫度場值。
- **直射光**：直接由窗戶或燈具到達查詢點的照度貢獻。
- **環境光**：非單一路徑直射、較均勻分布的背景照度貢獻。

## Slide 42: 公式說明 16：一次漫反射

這頁說明「反射公式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Iʳᵉᶠˡ(p,t) = Σ_s ρ_s Ī_s A_sʳᵉˡ exp(-||p-c_s||/ℓ_s)；× max(0, n_s·r̂_s→p) V_s(p)；s：牆、地板、天花板或家具表面。

接著說明「模型限制」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：一次漫反射用來補足非直射區域的回填亮度；它不是完整 ray tracing 或 radiosity；只計算一次反射，因此成本較低。

數字範例：若某牆面 ρ=0.6、接收平均照度 200 lux、相對面積 0.5、距離衰減 0.4、方向 cosine 0.8、可見性 1，則一次反射貢獻約 19.2 lux。

### 名詞註釋
- **Ray tracing**：依光線路徑追蹤照明傳播的精密光學方法；本研究只採輕量照度幾何與一次漫反射近似。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Distance decay**：距離設備越遠，局部作用越弱的權重函數。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **燈具光束權重**：照度模型中用方向權重、距離衰減與可見性近似燈具直射光，而非完整光線追蹤。
- **一次漫反射**：只計算一次表面反射對照度的回填效果，是輕量近似而非完整 radiosity。
- **反射率 ρ**：表面反射率，描述牆面、地板或家具把入射光反射出去的比例。

## Slide 43: 公式說明 17：8 參數校正多項式

這頁說明「三線性形式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：C(p) = c₀ + c₁X + c₂Y + c₃Z；+ c₄XY + c₅XZ + c₆YZ + c₇XYZ；X,Y,Z 是正規化房間座標。

接著說明「為什麼剛好 8 點」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：房間有地面四角與天花板四角；每個變數在同一時間有 8 個 residual；三線性校正場也有 8 個自由度。

數字範例：若 c₀=0.2、c₁=0.4、c₂=-0.2、c₃=0.1、c₄=0.1，其餘係數為 0，且 X=Y=Z=0.5，則 C=0.2+0.4×0.5-0.2×0.5+0.1×0.5+0.1×0.25=0.375。

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

數字範例：若某角點感測器觀測溫度 O_T=27.2°C，而 nominal model 在同一點預測 N_T=26.8°C，則 residual r_T=27.2-26.8=+0.4°C。

### 名詞註釋
- **Nominal model**：主模型的可解釋估計部分，描述設備、邊界與空間結構造成的主要趨勢。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **角點 residual**：角落感測器觀測值與 nominal model 預測值的差。

## Slide 45: 公式說明 19：三線性校正式

這頁說明「校正公式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Cᵥ(X,Y,Z,t) = Σ_{a,b,c∈B} rᵛ_{abc}(t)；× ℓ_a(X) ℓ_b(Y) ℓ_c(Z), B={0,1}；ℓ₀(u)=1-u，ℓ₁(u)=u。

接著說明「重要性質」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：所有權重非負且總和為 1；所以這是房間內部補間，不是無限制外插；在任一角點上，對應權重為 1，其餘為 0。

數字範例：在房間中心 X=Y=Z=0.5 時，8 個角點權重各為 1/8；若 8 個角點 residual 總和為 1.6，則 C=1.6/8=0.2。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **角點 residual**：角落感測器觀測值與 nominal model 預測值的差。
- **補間權重 ℓ**：三線性補間中每個角點 residual 對內部點的權重函數。

## Slide 46: 公式說明 20：校正後估計值

這頁說明「回到主公式」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：F̂ᵥ(p,t) = Nᵥ(p,t) + Cᵥ(p,t)；在角點：Cᵥ 等於觀測 residual；所以 F̂ᵥ(p_{abc},t) = Oᵥ(p_{abc},t)。

接著說明「適用範圍」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：8 顆感測器不能直接量到所有點；三線性 residual correction 在角點與觀測一致；其他點是 nominal model 加上低階 residual 補間的估計。

數字範例：若 nominal model 在某點給 N_T=26.8°C，校正場給 C_T=+0.4°C，則校正後 F̂_T=26.8+0.4=27.2°C。

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

接著說明「適用範圍」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：並非所有室內場都必然三線性；三線性 residual 假設下可完全重建；平滑但非三線性的 residual 可由誤差界描述接近程度。

數字範例：若 residual 函數 R=0.2+0.3X+0.1Y，屬於三線性函數空間；在 X=0.5、Y=0.5、Z=0 時，R=0.2+0.15+0.05=0.40。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **三線性函數空間**：由 1、X、Y、Z 與交互項組成的 8 維 residual 表示空間。

## Slide 48: 公式說明 22：平滑 residual 的誤差界

這頁可以用很白話的方式說：我們只有 8 個角落點有真實 residual，房間中間很多點沒有直接量到，所以 Cᵥ 是用 8 個角點補出來的 residual。公式左邊 |Rᵥ-Cᵥ| 就是在問：某個沒量到的點，這個補出來的 residual 最多可能和真實 residual 差多少。

M_xx、M_yy、M_zz 的名字來自二階偏導數記號。M_xx 不是 x 乘 x，而是對 x 方向微分兩次後的最大絕對值上界，也就是 M_xx ≥ max|∂²Rᵥ/∂x²|。M_yy 和 M_zz 同理，分別代表 y 與 z 方向 residual 的最大彎曲程度。

右邊分成三個方向：W²M_xx/8 是 x 方向造成的最壞誤差，L²M_yy/8 是 y 方向，H²M_zz/8 是 z 方向。W、L、H 越大，代表角點之間隔得越遠，中間靠補間猜的距離越長；M_xx、M_yy、M_zz 越大，代表 residual 在該方向彎得越厲害，也越難用直線補準。

原因可以用「用直線補曲線」來理解。線性補間等於拿兩端點連成一條直線去估中間值；如果 residual 是直線，即使斜率很大，二階導數仍然是 0，線性補間可以補對；真正造成補間誤差的是曲線彎曲，也就是二階導數。這就是為什麼這裡用 M_xx、M_yy、M_zz，而不是用一階斜率。

三線性補間只是把這件事放到 3D 房間裡：先沿 x 方向補，再沿 y 方向補，再沿 z 方向補。因此三個方向各自有一個可能誤差，合起來就是 W²M_xx/8 + L²M_yy/8 + H²M_zz/8。這也說明為什麼主模型要先把冷氣、窗戶、燈具等主要效果吃掉；剩下的 residual 越平滑，這個上界才越有意義。若 residual 是局部尖峰、光斑或遮蔽邊界，曲率會變大，單靠 8 點就不夠，需要更多感測點或 hybrid residual 補強。

數字範例：若 W=6、L=4、H=3，且 M_xx=0.01、M_yy=0.02、M_zz=0.01，則上界為 36×0.01/8 + 16×0.02/8 + 9×0.01/8 = 0.09625，約 0.096。

### 名詞註釋
- **角落感測器**：配置在房間地面四角與天花板四角的 8 個感測點，用於建立 sparse observation 與 residual correction。
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Trilinear correction**：用 X/Y/Z 三個座標方向的一階補間，由 8 個角點 residual 推估室內 residual 場。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Visibility/obstruction**：家具或幾何遮擋造成設備影響變弱的因素。
- **誤差上界**：用 residual 二階曲率限制三線性補間與真實 residual 的最大偏差。

## Slide 49: 公式說明 23：非連網裝置影響學習

這頁說明「before/after delta」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Δy_m = y_mᵃᶠᵗᵉʳ - y_mᵇᵉᶠᵒʳᵉ；m ∈ {T,H,L}；X_{i,k}：第 i 個感測點對第 k 個裝置 envelope。

接著說明「least-squares 估計」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：β_m = argmin_{β} ||Δy_m - Xβ||²₂；β_m：裝置對第 m 個因子的影響係數；X：由 influence envelope 組成的設計矩陣。

數字範例：若兩個感測點的 envelope 為 X=[1,0.5]，觀測變化 Δy=[-0.8,-0.4]，單一係數 least squares 為 β=(XᵀΔy)/(XᵀX)=(-0.8-0.2)/(1+0.25)=-0.8。

### 名詞註釋
- **非連網家電/裝置**：沒有穩定 API 或遙測資料可讀取狀態的冷氣、窗戶、照明等設備。
- **After-before delta Δy**：裝置操作後觀測值減去操作前觀測值，用來把實際動作轉成可學習的數值變化。
- **設計矩陣 X**：每一列對應一個感測點或樣本，每一欄對應一個裝置 influence envelope，用於 least-squares 估計。
- **影響係數 β_m**：描述裝置操作對第 m 個環境因子的方向與大小；m 可為溫度、濕度或照度。
- **Influence envelope**：設備對某位置的空間作用權重，通常含時間強度、距離、方向與遮蔽。
- **Before/after intervention**：實際採取動作前後量測環境變化，用於驗證推薦是否有因果改善效果。

## Slide 50: 公式說明 24：Hybrid residual

這頁說明「第二層修正」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：F_hybridᵛ(p,t) = Fᵥ(p,t) + Rᵥ(p,t; θᵥ)；Fᵥ：前面可解釋的 base estimator；Rᵥ：小型 neural network 預測的 residual。

接著說明「定位」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：hybrid 不是取代物理模型；它只修正主模型剩下的系統性誤差；這樣可保留可解釋結構。

數字範例：若 base estimator 輸出 F=27.0°C，hybrid residual model 預測 R=-0.3°C，則 F_hybrid=27.0-0.3=26.7°C。

### 名詞註釋
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。

## Slide 51: 公式說明 25：Hybrid 訓練目標

這頁說明「residual label」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：Rᵥ*(p,t) = F_trueᵛ(p,t) - Fᵥ(p,t)；F_trueᵛ：訓練或合成 truth 場；Fᵥ：base estimator 輸出。

接著說明「損失函數」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：ℒ(θᵥ) = (1/N)Σᵢ ||Rᵥ*(pᵢ,tᵢ)；- Rᵥ(pᵢ,tᵢ;θᵥ)||² + λ||θᵥ||²；第一項是 residual 預測誤差。

數字範例：若兩筆 residual 預測誤差為 0.2 與 -0.1，平方平均為 (0.04+0.01)/2=0.025，再加上正則化 0.01，則 ℒ=0.035。

### 名詞註釋
- **Residual**：觀測或 truth 與模型預測之間的差，用於校正或第二層學習。
- **Hybrid residual**：在可解釋 base estimator 後面再加一個資料驅動 residual 模型，不直接取代主模型。
- **Estimator**：實際負責產生場估計的模型物件，可切換 base、corrected 或 hybrid 版本。
- **標籤 yᵢ**：監督式學習中的目標值；本研究常用 true field 與 base estimator 的差作 residual label。
- **損失函數 ℒ**：訓練 neural network 時要最小化的目標函數。
- **正則化 λ**：限制模型參數大小以降低過擬合的項。

## Slide 52: 公式說明 26：MAE、RMSE 與 Correlation

這頁說明「誤差指標」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：MAE = (1/n) Σᵢ |ŷᵢ - yᵢ|；RMSE = √[(1/n) Σᵢ (ŷᵢ - yᵢ)²]；Corr = cov(ŷ,y)/(σ_{ŷ} σ_{y})。

接著說明「使用原因」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：MAE 代表平均偏差，最直觀；RMSE 會放大尖峰或離群誤差；Correlation 用於公開資料時序任務，檢查趨勢是否同向。

數字範例：若 ŷ=[1,2,3]、y=[1,2,4]，絕對誤差平均為 (0+0+1)/3=0.33，RMSE=sqrt(1/3)=0.58，相關係數約 0.98。

### 名詞註釋
- **Public dataset**：外部公開資料來源；本研究只用於相容任務壓力測試，不作完整 3D truth。
- **MAE**：Mean Absolute Error，平均絕對誤差；數值越低代表平均偏差越小。
- **RMSE**：Root Mean Squared Error，均方根誤差；比 MAE 更放大尖峰或離群誤差。
- **Correlation**：衡量預測與真值趨勢方向一致性的指標。
- **標籤 yᵢ**：監督式學習中的目標值；本研究常用 true field 與 base estimator 的差作 residual label。

## Slide 53: 公式說明 27：IDW baseline

這頁說明「IDW 插值」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：IDW(p) = Σ_s w_s O_s / Σ_s w_s；w_s = 1 / (dist(p,s) + ε)^q；s：感測器索引。

接著說明「比較基準理由」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：IDW 是無設備物理先驗的幾何插值 baseline；它只知道感測器位置與距離；不知道冷氣出風、窗戶日照或燈具位置。

數字範例：若兩個感測器讀值為 26°C 與 30°C，距離為 1 m 與 3 m，q=2，則權重為 1 與 1/9，IDW=(26+30/9)/(1+1/9)≈26.4°C。

### 名詞註釋
- **Baseline**：泛指比較或模型參考基準；在模型脈絡中常指未加入設備作用前的室內溫濕照度基準。
- **IDW**：Inverse Distance Weighting，反距離加權插值；只使用距離與感測值，不含設備物理先驗。
- **IDW 權重**：IDW 中由距離決定的感測器權重，距離越近權重越高。

## Slide 54: 公式說明 28：推薦排序與驗證

這頁說明「推薦分數」。可以先從公式或定義開始，指出它在整體模型中負責哪一部分。

左側重點包含：q_m(S)= (1/K)Σ_k F_m(p_{k},t)；P(q)=Σ_m w_m max(0,(|q_m-g_m|-δ_m)/δ_m)；Score(a)=P(q_base)-P(q_a)。

接著說明「驗證限制」。這一部分通常用來補上模型設計理由、限制或可主張範圍。

右側重點包含：S 是推薦評估的 sample scope 或目標區域；g_m 是目標值，δ_m 是容許範圍；目前推薦排序是 counterfactual simulation。

數字範例：若只看溫度，目標 g=26°C、容許 δ=2°C；動作前 q_base=30°C 時 P=(|30-26|-2)/2=1，候選動作後 q_a=27°C 時 P=0，因此 Score=1-0=1。

### 名詞註釋
- **Sample**：指定房間中的查詢點，用來取得該座標的三因子估計。
- **Zone**：房間內的目標區域，用於彙整多個點的平均狀態或舒適度評估。
- **Counterfactual simulation**：假設某候選動作發生後重新估計結果，用來比較預期改善。
- **區域平均 q_m(S)**：在指定 sample scope 或目標區域 S 內，彙整第 m 個環境因子的平均狀態。
- **目標值與容許範圍**：g_m 是舒適目標，δ_m 是允許偏離範圍；超出範圍才累積 penalty。
- **Score(a)**：候選動作 a 的推薦分數，通常由採取前後 comfort penalty 的下降量決定。
