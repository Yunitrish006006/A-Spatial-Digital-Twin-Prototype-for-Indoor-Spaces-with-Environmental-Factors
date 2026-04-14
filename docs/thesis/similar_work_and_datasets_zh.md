# 相似研究與資料集比對筆記

本筆記用於支援論文第二章與第五章的研究定位，目標不是證明「完全沒有類似研究」，而是清楚界定目前公開研究與本系統之間的重疊範圍與差異。

## 一、最相近的論文

| 論文 | 相近原因 | 與本研究的主要差異 | 連結 |
| --- | --- | --- | --- |
| Qian et al., 2025, *Building and Environment* | 使用有限觀測重建住宅房間中的溫濕度分布 | 未納入照度、非連網家電影響學習、MCP 工具化 | https://doi.org/10.1016/j.buildenv.2024.112495 |
| Huljak et al., 2025, *Frontiers in Built Environment* | 使用 hybrid 方法模擬空調空間的溫度分布 | 主體偏溫度場 surrogate，未整合三因子與控制排序 | https://doi.org/10.3389/fbuil.2025.1690062 |
| Megri et al., 2022, *Indoor and Built Environment* | 強調動態 zonal 模型與 transient thermal comfort | 不處理照度與非連網裝置學習，也非 MCP 化原型 | https://doi.org/10.1177/1420326X211060486 |
| Chen and Wen, 2007, *SPIE* | 討論 zonal model 與感測器配置 | 偏感測器網路設計，不是單房間數位孿生服務 | https://doi.org/10.1117/12.716356 |
| Gokhale et al., 2022, *Applied Energy* | 物理導向與神經網路混合建模思路接近 hybrid residual | 問題設定偏 building thermal prediction，不含空間照度與家具阻擋 | https://doi.org/10.1016/j.apenergy.2022.118852 |

## 二、本研究的差異定位

本研究不是一般性的智慧建築平台論文，也不是純熱模型或純資料驅動預測模型。較準確的定位是：

`single-room, control-oriented, reduced-order spatial digital twin with limited corner sensors, non-networked appliance impact learning, and MCP-accessible tools`

和現有研究相比，本研究同時結合了下列條件：

- 單房間而非整棟建築
- 溫度、濕度、照度三因子，而不只熱場
- 固定 8 顆角落感測器
- 非連網冷氣、窗戶、照明的影響學習
- 家具阻擋與可模組化裝置
- 候選控制動作排序
- MCP / Web / Gemma 橋接式服務化

目前查到的公開研究大多只覆蓋其中一部分，尚未看到和本系統完全等價的公開論文。

## 三、可用來比對的公開資料集

| 資料集 | 內容 | 可拿來做什麼 | 不適合直接做什麼 | 連結 |
| --- | --- | --- | --- | --- |
| CU-BEMS | 多區商辦的用電、溫度、濕度、照度、設備功率資料 | 驗證裝置狀態與室內三因子時序關聯，模擬 service 層輸入輸出格式 | 不能直接當單房間 8 角落空間場真值 | https://doi.org/10.1038/s41597-020-00582-3 |
| Appliances Energy Prediction | 多房間溫溼度、氣象、燈光用電 | 驗證室內外條件與用電之間的統計相關 | 不含明確房間幾何、裝置位置與空間場 | https://doi.org/10.24432/C5VC8G |
| SML2010 | 室內兩組溫度/濕度/照度，加上日照與室外條件 | 驗證窗戶日照、外氣條件與室內響應的時序關聯 | 量測點太少，不能直接做 3D 場重建 | https://doi.org/10.24432/C5RS3S |
| Occupancy Detection | 溫度、濕度、照度、CO2 與占用 | 驗證感測器前處理與環境事件偵測 | 不含冷氣/窗戶/照明設備狀態與空間幾何 | https://doi.org/10.24432/C5X01N |
| Denmark room-level IEQ dataset | 住宅房間的 operative temperature、RH、CO2、occupancy ground truth | 驗證住宅真實 IEQ 波動與 occupancy 關係 | 缺照度與裝置狀態，不是空間場資料 | https://doi.org/10.5281/zenodo.10761326 |
| ASHRAE Global Thermal Comfort Database II | 大量環境量測與熱舒適主觀資料 | 調整舒適目標設定與控制評分權重 | 不適合做單房間幾何場重建 | https://doi.org/10.1016/j.buildenv.2018.06.022 |

## 四、對 hybrid residual 模型最有價值的資料

如果目標是讓目前的 hybrid residual neural network 從公開資料得到外部驗證，資料價值排序可先這樣看：

1. `CU-BEMS`
原因：同時有設備操作痕跡與室內環境量測，最接近 service 層與裝置學習層的需求。

2. `SML2010`
原因：有溫度、濕度、照度與外部日照，可拿來驗證窗戶與日照相關響應。

3. `Denmark room-level IEQ dataset`
原因：較接近住宅場景，可用來檢查溫溼度動態是否落在合理範圍。

4. `ASHRAE Global Thermal Comfort Database II`
原因：比較適合舒適度目標與控制評分，不是直接拿來訓練空間場。

## 五、目前最誠實的說法

就目前公開資料來看，沒有一套資料能直接對應本研究這個完整問題：

- 單房間幾何
- 8 顆角落感測器
- 溫度/濕度/照度三因子
- 冷氣/窗戶/照明狀態
- 可移動家具阻擋
- 空間場真值

因此，目前最合理的研究說法不是「已用公開資料完整訓練」，而是：

- 主要方法以可控制的模擬情境驗證
- 公開資料集用於外部合理性比對
- 未來以真實 ESP32 量測資料接上模型校正與 hybrid residual 再訓練

