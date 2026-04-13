# 單房間三因子數位孿生文獻閱讀筆記

## 閱讀範圍說明

本筆記以期刊官方頁面、摘要、開放全文頁面為主，整理出對本研究最直接有用的內容：

- 研究問題是什麼
- 方法怎麼做
- 你可以借什麼
- 你不應該直接照搬什麼
- 和你題目的差異在哪裡

## 1. Cespedes-Cubides and Jradi (2024)

題目：
`A review of building digital twins to improve energy efficiency in the building operational stage`

來源：
https://doi.org/10.1186/s42162-024-00313-7

我讀到的重點：

- 它的核心不是做一個新模型，而是整理 building digital twin 在 operation stage 的應用方式。
- 文中反覆強調 digital twin 不只是 BIM 視覺化，而是需要和感測器資料、資料管線、分析模型有持續交換。
- 它也指出很多案例會提到節能與舒適度改善，但真正提供嚴格量化成效的研究不多。

你可以借的部分：

- 用來定義你論文裡的「digital twin」不是單純 3D 畫面，而是包含感測、模型更新、預測與決策。
- 可支撐你把系統定位在 building operation / indoor environment optimization。
- 可引用它對研究缺口的描述：很多數位孿生論文偏平台、架構或 BIM 整合，較少聚焦「少量感測器下的空間場估測」。

不要直接照搬的部分：

- 它是 review，不會替你提供可直接落地的室內溫濕度數學模型。
- 不能只引用這篇就說明你的模型合理，模型合理性還是要靠 thermal / zonal / estimation 類論文。

和你題目的差異：

- 它是 building-level review。
- 你是 single-room、limited sensors、temperature/humidity/illuminance、可做 action ranking 的原型。

## 2. Bacher and Madsen (2011)

題目：
`Identifying suitable models for the heat dynamics of buildings`

來源：
https://doi.org/10.1016/j.enbuild.2011.02.005

我讀到的重點：

- 這篇在講如何辨識「適合控制與預測」的建築熱動態模型。
- 它的價值在於 model identification procedure，而不是追求超細空間解析。
- 它明確把模型用途連到 control、forecasting、energy performance description。

你可以借的部分：

- 把你的系統定義成 `control-oriented reduced-order model` 很合理。
- 你現在的 `bulk + local field` 可以被描述成：在平均狀態上建立低階動態，再疊加局部空間擾動。
- 感測器資料可用來做模型參數校正，這和它強調的 identification 思路一致。

不要直接照搬的部分：

- 它偏 building thermal dynamics，不是為了空間場分布設計。
- 如果你只做單一平均溫度模型，會失去你題目最重要的空間性。

和你題目的差異：

- 它是熱動態辨識。
- 你要再多加一層 spatial field estimation。

## 3. Hietaharju et al. (2018)

題目：
`A Dynamic Model for Indoor Temperature Prediction in Buildings`

來源：
https://doi.org/10.3390/en11061477

我讀到的重點：

- 這篇很重視「容易參數化、容易部署、跨不同建築也能用」。
- 它認為許多模型過度依賴詳細建築參數或大量量測，因此不利實務部署。
- 研究重心是 indoor temperature prediction 與控制用途。

你可以借的部分：

- 支撐你選擇簡化模型而不是 CFD。
- 支撐你用少量、容易取得的感測資料去做模型更新。
- 可以幫你強化論文裡的工程論述：你要的是可部署、可校正、可控制，不是最高精度。

不要直接照搬的部分：

- 它主要是單一溫度預測，不是三因子空間分布。
- 不能直接回答你的窗邊、中央、角落差異。

和你題目的差異：

- 它提供「簡化動態」的合理性。
- 你的創新點是把簡化動態擴展到 spatial twin。

## 4. Megri et al. (2022)

題目：
`A new dynamic zOnal model with air-diffuser (DOMA) - Application to thermal comfort prediction`

來源：
https://doi.org/10.1177/1420326X211060486

我讀到的重點：

- 它明確把 zonal model 定位在 CFD 和 mono-zone / multi-room model 之間。
- 它強調 zonal model 可以描述室內溫度分布、分層與 HVAC 造成的非均勻性，但計算比 CFD 輕。
- 它做的是瞬態模型，而且和建築熱模型耦合，重點是時間演化與 thermal comfort。

你可以借的部分：

- 這篇是你方法論最重要的支撐之一。
- 你可以說你的模型不是 full CFD，也不是 well-mixed single-zone，而是更接近 reduced-order spatial / zonal thinking。
- 你現在改成 `bulk + local field`，其實就很適合被描述成「借鑑 zonal thinking 的控制導向空間 surrogate」。

不要直接照搬的部分：

- DOMA 比你現在的原型更偏向嚴格的 zonal conservation equation。
- 你的系統目前仍是 influence-field surrogate，不是完整 pressure-based zonal solver。

和你題目的差異：

- 它更偏熱舒適與 HVAC 分布。
- 你多了有限角落感測器、設備影響學習、MCP service 化、三因子整合。

## 5. Qian et al. (2025)

題目：
`Estimating indoor air temperature and humidity distributions by data assimilation with finite observations: Validation using an actual residential room`

來源：
https://doi.org/10.1016/j.buildenv.2024.112495

我讀到的重點：

- 這篇直接打中你的核心問題：室內溫濕度場是非均勻的，但感測器數量有限。
- 他們用 data assimilation 改進 finite observations 下的場估測。
- 不只是數值模擬，還有 actual residential room 驗證，並討論 sensor placement。

你可以借的部分：

- 這篇非常適合放在文獻探討第二章核心段落。
- 可支撐你論文中的研究動機：有限感測器下仍要估測全室分布。
- 也能支持你之後談 sensor placement、corner sensors 限制與可行性。

不要直接照搬的部分：

- 它比較偏 data assimilation。
- 你的模型不是 EnKF / DA 主導，而是 parameterized influence field + sensor correction。

和你題目的差異：

- 它是「有限觀測 + 溫濕度場估測」。
- 你多加了 illuminance、設備影響函數、動作排序、MCP service。

## 6. Huljak et al. (2025)

題目：
`Hybrid models for simulating indoor temperature distribution in air-conditioned spaces`

來源：
https://doi.org/10.3389/fbuil.2025.1690062

我讀到的重點：

- 它處理 air-conditioned space 的室內溫度分布。
- 重點是 hybrid model，以及 real-time interface 對空間溫控分析和設計優化的價值。
- 它把較高保真度模型和較輕的推估方式結合，目標不是只做靜態圖，而是支援分析。

你可以借的部分：

- 這篇是你最接近的對照文獻之一。
- 可以用來支持你把系統稱為 `hybrid spatial digital twin` 或 `hybrid surrogate twin`。
- 也很適合放在 related work 裡，對照你為何選 simplified spatial field 而不是 full CFD。

不要直接照搬的部分：

- 它仍比你目前原型更偏高保真或與物理邊界條件緊耦合。
- 你現在的系統更強調有限感測器與低計算量。

和你題目的差異：

- 它主要是溫度分布。
- 你是 temperature + humidity + illuminance，還有 device action recommendation。

## 7. Teshome and Haghighat (2004)

題目：
`Zonal Models for Indoor Air Flow - A Critical Review`

來源：
https://doi.org/10.1080/14733315.2004.11683908

我讀到的重點：

- 這篇很適合拿來當 zonal model 的定義來源。
- 它清楚指出 zonal model 是 CFD 和 single-zone model 的中間選擇。
- 也提醒 zonal model 在強制對流與 recirculation loop 上仍有侷限。

你可以借的部分：

- 幫你在論文裡誠實界定方法邊界。
- 可以用來說明：你現在不是要做 CFD 等級的回流細節，而是做控制導向的近似。

## 8. Chen and Wen (2007)

題目：
`Application of zonal model on indoor air sensor network design`

來源：
https://pure.psu.edu/en/publications/application-of-zonal-model-on-indoor-air-sensor-network-design/

我讀到的重點：

- 這篇直接把 zonal model 和 sensor network design 連在一起。
- 雖然年代較早，但它對你的感測器配置論述很有幫助。

你可以借的部分：

- 支撐你在論文中討論「有限感測器不是隨便放，而是需要和空間模型一起思考」。
- 很適合放在感測器配置與觀測模型那一節。

## 9. Feng et al. (2019)

題目：
`Fast prediction for indoor environment: Models assessment`

來源：
https://doi.org/10.1177/1420326X19852450

我讀到的重點：

- 這篇不是單做建築熱模型，而是從 indoor environment fast prediction 的角度看各種快速模型。
- 它很明確指出 online control 需要 real-time 或 faster-than-real-time simulation。
- 並且提到 fast model 和 machine learning / POD 的耦合是可行方向。

你可以借的部分：

- 可支撐你不用 CFD 的理由。
- 也能支撐之後你若把 Gemma 或其他學習模型接進來，作為 hybrid twin 的延伸。

## 你現在題目的最佳定位

把上面幾篇綜合起來，你的系統最適合這樣定位：

- `single-room`
- `control-oriented`
- `reduced-order spatial digital twin`
- `limited-corner-sensor calibrated`
- `bulk + local influence field`
- `temperature, humidity, and illuminance estimation with action ranking`

## 目前和現有論文的差異化建議

如果你要避免看起來像在重做別人的版本，你的論文最好強調這幾點：

1. 不是 CFD 重建，而是有限感測器下的可控制空間 surrogate。
2. 不是只做溫度，而是三因子，其中濕度次核心、照度明確納入。
3. 不是只做估測，而是要輸出 candidate action ranking。
4. 不是只做 dashboard，而是做成可服務化的 MCP interface。
5. 不是追求一般建築尺度，而是固定在單房間、角落感測器配置下的方法論。
