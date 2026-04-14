# 公開資料集一對一模型比較結果

本文件整理「本研究模型映射到 shared-task benchmark 後」與兩個外部 baseline 的直接比較結果。目前已完成：

- `SML2010` 一對一比較
- `CU-BEMS` 一對一比較

對應輸出檔：

- `outputs/data/public_benchmarks/sml2010_hybrid_twin_comparison.json`
- `outputs/data/public_benchmarks/cu_bems_hybrid_twin_comparison.json`

## 比較方式

本次比較不是把本研究模型硬套成純時間序列模型，也不是直接拿 physics 模型 zero-shot 輸出與 persistence 比。實際流程是：

1. 先把本研究的 `DigitalTwinModel + hybrid residual checkpoint` 映射成公開資料可用的 `structured prior`。
2. 對每個 public task 建立對應的 pseudo room、pseudo device 與 boundary-response 特徵。
3. 在與 baseline 完全相同的 chronological `70/30` split 上，再 fit 一個小型 linear readout head。
4. 最後將 `hybrid_digital_twin_readout` 與 `persistence`、`linear regression` 在相同 target 上逐一比較。

因此這份結果可視為「本研究模型在 public task benchmark 上的正式 head-to-head 比較」，但仍需注意：它比較的是 shared observable tasks，而不是完整 3D 空間場重建。

## SML2010 總結

整體看起來，本研究模型映射後的表現呈現明確的 task 差異：

1. 在 `temperature` 與部分 `humidity delta` 任務上表現強，尤其是 `S3` 事件型任務。
2. 在 `illuminance` 任務上仍不穩，短 horizon 下明顯落後。
3. 在 `60` 分鐘的 `S3` 任務上，本研究模型全面優於兩個 baseline。

## 任務別結果

### S1: daylight-response benchmark

| Horizon | Target | 本研究模型 MAE | Linear Regression MAE | Persistence MAE | 結論 |
| --- | --- | ---: | ---: | ---: | --- |
| 15 min | dining illuminance | 5.274763 | 4.022864 | 3.418143 | 本研究模型落後 |
| 15 min | room illuminance | 8.464513 | 5.399408 | 4.311997 | 本研究模型落後 |
| 60 min | dining illuminance | 7.494116 | 9.089619 | 7.524185 | 本研究模型勝過兩者 |
| 60 min | room illuminance | 15.114360 | 14.886315 | 11.095341 | 本研究模型落後 |

解讀：S1 類 daylight-response 任務仍然是本研究映射後模型的弱點。短 horizon 的照度預測無法超越傳統 baseline，只有 `60` 分鐘的 dining illuminance 略優於兩者。這表示目前 pseudo geometry 與 boundary-response mapping 對採光傳輸的描述仍偏粗糙。

### S2: thermal-humidity benchmark

| Horizon | Target 群 | 與 Linear Regression 比 | 與 Persistence 比 | 結論 |
| --- | --- | --- | --- | --- |
| 15 min | temperature | 兩個點位都落後 | 兩個點位都領先 | 中等 |
| 15 min | humidity | 兩個點位都落後 | 兩個點位都落後 | 弱 |
| 60 min | temperature | 兩個點位都領先 | 兩個點位都領先 | 強 |
| 60 min | humidity | 兩個點位都落後 | 兩個點位都落後 | 弱 |

代表性數值如下：

| Horizon | Target | 本研究模型 MAE | Linear Regression MAE | Persistence MAE |
| --- | --- | ---: | ---: | ---: |
| 15 min | dining temperature | 0.072801 | 0.042593 | 0.118236 |
| 15 min | room temperature | 0.095048 | 0.051943 | 0.115293 |
| 60 min | dining temperature | 0.156035 | 0.192471 | 0.469776 |
| 60 min | room temperature | 0.216465 | 0.229682 | 0.458005 |

解讀：在 `S2` 上，本研究模型對溫度的優勢主要出現在較長 horizon。這與前面的 baseline 分析一致，表示本研究模型中的結構化邊界響應先驗，確實能在較長時間尺度上提供額外資訊。但濕度仍然是目前映射版本的弱項。

### S3: facade event delta benchmark

這一組是目前對本研究模型最有利的任務。

| Horizon | 勝過 Linear Regression | 勝過 Persistence | 結論 |
| --- | ---: | ---: | --- |
| 15 min | 5 / 6 | 4 / 6 | 強 |
| 60 min | 6 / 6 | 6 / 6 | 最強 |

代表性數值如下：

| Horizon | Target | 本研究模型 MAE | Linear Regression MAE | Persistence MAE |
| --- | --- | ---: | ---: | ---: |
| 15 min | dining temperature delta | 0.071084 | 0.092903 | 0.233167 |
| 15 min | room temperature delta | 0.076448 | 0.095708 | 0.220143 |
| 15 min | dining humidity delta | 0.335185 | 0.393154 | 0.385770 |
| 60 min | dining temperature delta | 0.189357 | 0.211799 | 0.563401 |
| 60 min | room temperature delta | 0.215591 | 0.243147 | 0.532738 |
| 60 min | dining illuminance delta | 14.480169 | 17.169939 | 15.208888 |
| 60 min | room illuminance delta | 20.498463 | 25.616869 | 23.248001 |

解讀：`S3` 本質上是在比較邊界條件突變後的響應量，這類任務和本研究的裝置影響場、方向性、時間響應建模邏輯最接近。因此在這組任務上，本研究模型映射後能穩定發揮優勢，尤其 `60` 分鐘 horizon 已經對全部 target 都取得最佳 MAE。

## CU-BEMS 總結

CU-BEMS 的一對一比較結果和 SML2010 很不一樣。這份資料上，本研究模型映射後雖然經常能勝過 `linear regression`，但仍然無法超越 `persistence`。換句話說，在這種大規模 zone-level building operation forecasting 任務裡，最強 baseline 仍然是「直接延用最近一次觀測值」。

## 任務別結果

### C1: AC response benchmark

| Horizon | Target | 本研究模型 MAE | Linear Regression MAE | Persistence MAE | 結論 |
| --- | --- | ---: | ---: | ---: | --- |
| 15 min | temperature | 0.282049 | 0.288409 | 0.261973 | 勝過線性回歸，但輸給 persistence |
| 15 min | humidity | 0.756199 | 0.777978 | 0.713036 | 勝過線性回歸，但輸給 persistence |
| 60 min | temperature | 0.824116 | 0.834086 | 0.747704 | 勝過線性回歸，但輸給 persistence |
| 60 min | humidity | 1.566125 | 1.562054 | 1.504325 | 同時輸給兩者 |

解讀：在溫濕度絕對值預測上，本研究模型的結構化先驗可以帶來一些訊號，因此通常比純線性回歸更穩。但 CU-BEMS 的時間延續性太強，最終仍然很難打敗 persistence。

### C2: lighting response benchmark


| Horizon | Target | 本研究模型 MAE | Linear Regression MAE | Persistence MAE | 結論 |
| --- | --- | ---: | ---: | ---: | --- |
| 15 min | illuminance | 7.699824 | 1.793783 | 1.363127 | 明顯落後（已用多燈+照度角mapping） |
| 60 min | illuminance | 9.565866 | 5.646140 | 4.011693 | 明顯落後（已用多燈+照度角mapping） |

> 補充說明：本次已將 zone 內所有 lighting_power 欄位自動對應為多個光源，並為每個光源加入照度角（direction_angle_deg，預設120度），使照度模型能同時考慮多燈疊加與方向性分布。然而，CU-BEMS 的 zone-level ambient light 仍與單房間多燈物理模型存在結構性落差，導致本研究模型在此任務上 MAE 仍高於 baseline。這顯示公開資料集的照度欄位與本研究模型假設的空間分布、遮蔽、反射等物理條件不完全對應。

解讀：CU-BEMS 的照度任務對目前這個 pseudo single-room 映射非常不利。因為真實資料中的 zone ambient light 並不對應到本研究單房間光照傳輸的幾何假設，所以映射後模型在 `C2` 上顯著弱於兩個時間序列 baseline。這一點在論文裡應該明確承認，而不是硬解釋成模型普遍失敗。

### C3: event delta benchmark

| Horizon | 勝過 Linear Regression | 勝過 Persistence | 結論 |
| --- | ---: | ---: | --- |
| 15 min | 3 / 3 | 0 / 3 | 中等 |
| 60 min | 3 / 3 | 0 / 3 | 中等 |

代表性數值如下：

| Horizon | Target | 本研究模型 MAE | Linear Regression MAE | Persistence MAE |
| --- | --- | ---: | ---: | ---: |
| 15 min | temperature delta | 0.625709 | 0.691739 | 0.571121 |
| 15 min | humidity delta | 1.139949 | 1.258929 | 0.991996 |
| 15 min | illuminance delta | 2.749931 | 3.382856 | 2.184304 |
| 60 min | temperature delta | 1.275066 | 1.364022 | 1.195808 |
| 60 min | humidity delta | 1.876073 | 1.964076 | 1.763551 |
| 60 min | illuminance delta | 5.725854 | 7.093012 | 4.508905 |

解讀：在事件後變化量任務上，本研究模型能穩定勝過純線性回歸，表示 geometry-aware structured prior 對事件型響應仍有幫助。但 CU-BEMS 的事件後短中期變化仍然保有很高的時間慣性，因此 persistence 依然最強。

## 目前可下的結論
### Mapping 限制與修正策略補充

在本次 mapping 過程中，我們發現若僅以單一光源對應 zone 照明，模型表現會嚴重低估多燈疊加效果。因此已修正為自動偵測所有 lighting_power 欄位，並為每個非零功率產生獨立光源，均勻分布於天花板，並預設照度角（direction_angle_deg）為120度。若資料集未提供照度角，則自動填入預設值。此修正能讓模型更合理反映 zone 多燈情境，但由於公開資料集缺乏燈具空間分布、遮蔽、反射等細節，模型在 zone-level ambient light 任務上仍有結構性限制。

因此，照度任務的主要誤差來源並非單純模型設計，而是公開資料集與物理模型假設間的 mapping gap。未來若有更細緻的 zone geometry、燈具分布或遮蔽資料，模型可進一步優化。
把 `SML2010` 與 `CU-BEMS` 合起來看，可以得到更完整的說法：

1. 本研究模型不是通用的最佳時間序列預測器。
2. 在與本研究物理結構最接近的 `event-response`、`boundary-response`、`longer-horizon thermal response` 任務上，本研究模型可以量化地勝過傳統 baseline。
3. 在強時間慣性的大規模 building operation forecasting 任務上，`persistence` 仍然很難被打敗。
4. 在目前的 public mapping 設定下，照度任務是最弱的一環，尤其是 CU-BEMS 的 `C2` 與 SML2010 的 short-horizon `S1`。
5. 因此論文最合理的主張不是「本研究模型在所有公開資料任務上全面優於 baseline」，而是「本研究模型在具有幾何與事件結構的 shared tasks 上具明顯優勢，但在純時間延續型 forecasting 任務上未必優於 persistence」。

## 論文可直接使用的結論文字

可直接改寫為第五章的一段結果描述：

> 在已完成的一對一 public-task comparison 中，本研究將 physics-based digital twin 與 hybrid residual correction 映射為可在公開資料上評估的 structured prior，並在與 baseline 相同的 chronological split 上 fit 線性 readout。結果顯示，本研究模型在 SML2010 的 facade event delta benchmark (`S3`) 上表現最佳，特別是 60 分鐘 horizon 時對所有 target 皆優於 persistence 與 linear regression；例如 dining/room temperature delta 的 MAE 分別為 0.1894/0.2156，皆低於 linear regression 的 0.2118/0.2431 與 persistence 的 0.5634/0.5327。相對地，在 CU-BEMS 這類大規模 zone-level building operation forecasting 資料上，本研究模型雖常優於 linear regression，但仍未超越 persistence，顯示其優勢主要體現在具有明確幾何與事件結構的空間或邊界響應任務，而非一般高時間慣性的建築時間序列 forecasting。