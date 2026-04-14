# 公開資料集 Shared-Task Benchmark 設計

本文件將 CU-BEMS 與 SML2010 對齊到本 repo 目前的資料模板與實驗流程，目標不是把公開資料集硬轉成完整單房間 3D 空間場，而是建立可公平比較的 shared-task benchmark。

使用前仍需依原始資料集頁面的授權與引用規範辦理。依目前可查資訊，SML2010 在 UCI 頁面標示為 CC BY 4.0；CU-BEMS 則應以 figshare 與論文頁面的授權與引用要求為準。

目前 repo 已提供正規化腳本，可直接把原始資料轉成 benchmark 用的中介格式：

```text
python3 scripts/normalize_public_benchmark_data.py --dataset cu-bems
python3 scripts/normalize_public_benchmark_data.py --dataset sml2010
python3 scripts/run_public_dataset_benchmark.py --dataset cu-bems --horizons 15,60
python3 scripts/run_public_dataset_benchmark.py --dataset sml2010 --horizons 15,60
```

## 目標

1. 讓本研究模型、IDW baseline、未來純資料驅動 baseline 可以在相同公開資料集上比較共同子任務。
2. 把公開資料集欄位對應到本 repo 既有的輸入模板，降低未來接入真實資料的摩擦。
3. 明確界定哪些任務能比，哪些任務不能比，避免把 zone-level 或 point-level 資料誤當成完整空間場真值。

## 與本 Repo 模板的對齊

本 repo 已有的模板檔案位於 outputs/data_templates，可作為公開資料集正規化後的中介格式。

| 本 repo 模板 | 用途 | CU-BEMS 對應方式 | SML2010 對應方式 | 備註 |
| --- | --- | --- | --- | --- |
| corner_sensor_timeseries_template.csv | 儲存感測器時間序列 | 每個有感測器的 floor-zone 轉成一個 pseudo sensor | dining room 與 room 轉成兩個 pseudo sensors | 公開資料集 benchmark 主要用 point-level 或 zone-level，比較時不宣稱 8 角落配置 |
| device_event_log_template.csv | 儲存裝置事件與出力 | 同一 zone 內所有 AC 欄位加總成 ac_main，lighting 欄位對應 light_main，plug load 作為輔助特徵 | 不建議強行映射為 window_main；enthalpic motor 只作為輔助特徵或 ventilation proxy | SML2010 沒有明確冷氣/窗戶/照明事件，應以 boundary-response 任務為主 |
| outdoor_environment_template.csv | 儲存外部邊界條件 | 原始資料通常沒有 outdoor 欄位，可留空或以外部氣象來源補齊 | outdoor temperature、outdoor humidity、sunlight facade、sun irradiance、rain、wind 可直接填入 | CU-BEMS 若無外部氣象，不做窗戶 direct input benchmark |
| scenario_metadata_template.json | 儲存 pseudo room 與 split 設定 | 每個 zone 可視為一個 single-zone pseudo room | 兩點量測可視為一個 two-point pseudo room | 用來聲明 benchmark mode、資料切分與 pseudo geometry |
| public_benchmark_auxiliary_features_template.csv | 儲存 benchmark 輔助特徵 | 存放 plug load、樓層與 zone 輔助資訊 | 存放 facade sunlight、rain、wind、enthalpic motor、CO2 等欄位 | 補足現有模板未直接涵蓋的公開資料集欄位 |
| spatial_probe_ground_truth_template.csv | 儲存稠密空間真值 | 無法直接取得 | 無法直接取得 | 因此公開資料集不回報 full field MAE |

## Benchmark 原則

1. 只比較共同可觀測、共同可輸出的任務。
2. 只有 synthetic benchmark 報告完整空間場誤差；公開資料集只報 point-level、zone-level 或 comfort-level 指標。
3. 公開資料集若缺少裝置狀態，就不宣稱做裝置影響學習，只做 boundary-response 或 environmental response benchmark。
4. 若公開資料集缺少幾何資訊，則使用 pseudo geometry 只為了統一資料介面，不作為真實空間拓樸宣稱。

## CU-BEMS 對齊方案

CU-BEMS 是多區商辦資料，最適合拿來比較 AC 與照明事件後的 zone-level 響應。其資料以 floor 為單位拆成 CSV，欄位數依樓層與 zone 中的 AC、lighting、plug、sensor 數量而變化。根據資料描述，每個樓層檔案都有 timestamp，並包含 zone 前綴的 AC 用電、lighting 用電、plug load、temperature、humidity 與 ambient light 欄位。

### CU-BEMS 原始欄位到本研究格式

| CU-BEMS 原始訊號 | 正規化欄位 | 目標模板 | 處理方式 |
| --- | --- | --- | --- |
| timestamp | timestamp | 全部模板 | 直接保留一分鐘解析度 |
| floor + zone | sensor_name / scenario id | corner_sensor_timeseries / scenario_metadata | 命名為 floor{f}_zone{z}_sensor |
| zone temperature | temperature_c | corner_sensor_timeseries | 每個有感測器的 zone 轉成一個 pseudo sensor |
| zone humidity | humidity_pct | corner_sensor_timeseries | 同上 |
| zone ambient light | illuminance_lux | corner_sensor_timeseries | 同上 |
| zone AC1..ACn power | power / activation | device_event_log | 同一 zone 內所有 AC 欄位加總成 ac_main_power_kw；非零視為 activation>0 |
| zone lighting power | power / activation | device_event_log | 對應 light_main_power_kw |
| zone plug load power | plug_load_kw 或輔助欄位 | device_event_log 或外部特徵檔 | 建議保留為輔助特徵，不作主要控制裝置 |
| outdoor variables | outdoor_temperature_c 等 | outdoor_environment | 原始資料通常沒有，若缺少則整個任務不使用 outdoor benchmark |

### CU-BEMS 建議 pseudo geometry

| 元件 | 建議座標 | 用途 |
| --- | --- | --- |
| zone sensor | (3.0, 2.0, 2.8) | 單一 zone ceiling sensor placeholder |
| ac_main | (0.3, 2.0, 2.7) | 牆上冷氣 placeholder |
| light_main | (3.0, 2.0, 2.8) | 天花板照明 placeholder |
| target_zone | center_zone | 只報 zone-level 響應，不報空間場 |

以上座標只是為了對齊本 repo 的資料介面，不是對 CU-BEMS 真實房間幾何的宣稱。

### CU-BEMS 建議 benchmark 任務

| 任務 ID | 任務 | 輸入 | 預測目標 | 比較方法 | 指標 |
| --- | --- | --- | --- | --- | --- |
| C1 | AC 響應 benchmark | 前一段溫濕度、AC power、plug load | 下一步或 15/60 分鐘後的 zone temperature、humidity | 本研究模型 vs 純 persistence vs 純回歸 baseline | MAE、RMSE |
| C2 | 照明響應 benchmark | 前一段 illuminance、lighting power、plug load | 下一步或 15/60 分鐘後的 zone illuminance | 本研究模型 vs persistence vs 線性回歸 | MAE、RMSE |
| C3 | 事件後 delta benchmark | AC 或 lighting 開啟/關閉事件 | 事件後 5/15/30 分鐘的變化量 | 比較事件前後的變化量擬合 | delta MAE、Pearson correlation |

### CU-BEMS 切分建議

1. 訓練集：2018 全年可用資料。
2. 驗證集：2019 年前 3 個月。
3. 測試集：2019 年其餘月份。
4. 只保留有完整感測器資料的 zone，排除沒有 sensor 的樓層或樓梯區。

## SML2010 對齊方案

SML2010 最適合用來比較兩個室內點位在外氣與日照條件下的響應。依 UCI 說明，欄位包含 Date、Time、兩個室內點位的 temperature、humidity、lighting、weather forecast temperature、rain、wind、三個 facade sunlight、sun irradiance、三個 enthalpic motor 狀態、outdoor temperature、outdoor humidity，以及 day of week。原始檔前幾行為西班牙文註解標頭，因此實作時應以欄位順序或自定命名表解析，而不要假設資料檔一定已是英文欄名。

### SML2010 原始欄位到本研究格式

| SML2010 原始欄位 | 正規化欄位 | 目標模板 | 處理方式 |
| --- | --- | --- | --- |
| Date + Time | timestamp | 全部模板 | 合併成 UTC timestamp |
| Indoor temperature (dinning-room) | temperature_c | corner_sensor_timeseries | sensor_name 設為 dining_room |
| Indoor temperature (room) | temperature_c | corner_sensor_timeseries | sensor_name 設為 room |
| Relative humidity (dinning-room) | humidity_pct | corner_sensor_timeseries | 與 dining_room 對應 |
| Relative humidity (room) | humidity_pct | corner_sensor_timeseries | 與 room 對應 |
| Lighting (dinning-room) | illuminance_lux | corner_sensor_timeseries | 與 dining_room 對應 |
| Lighting (room) | illuminance_lux | corner_sensor_timeseries | 與 room 對應 |
| Outdoor temperature | outdoor_temperature_c | outdoor_environment | 直接填入 |
| Outdoor relative humidity | outdoor_humidity_pct | outdoor_environment | 直接填入 |
| Sun light west/east/south facade | sunlight_illuminance_lux 或 facade features | outdoor_environment | 建議保留三個 facade 欄位，並額外計算合成 sunlight |
| Sun irradiance | sun_irradiance_w_m2 | outdoor_environment | 作為 boundary forcing |
| Rain | rain_ratio | outdoor_environment | 保留為外部條件 |
| Wind | wind_speed_m_s | outdoor_environment | 保留為外部條件 |
| Weather forecast temperature | forecast_temperature_c | outdoor_environment 或輔助特徵 | 可作為基準 forecast feature |
| Enthalpic motor 1/2/turbo | auxiliary hvac/ventilation feature | 輔助特徵 | 不建議直接映射為 window_main |
| CO2 欄位 | optional feature | 輔助特徵 | 本研究主模型目前未直接使用 |

### SML2010 建議 pseudo geometry

| 元件 | 建議座標 | 用途 |
| --- | --- | --- |
| dining_room sensor | (1.8, 2.0, 1.2) | 點位一 |
| room sensor | (4.2, 2.0, 1.2) | 點位二 |
| west/east/south facade sunlight | 西、東、南牆外部邊界 | 對應 facade sunlight feature |
| target outputs | 兩點時間序列 | 不宣稱完整空間場 |

### SML2010 建議 benchmark 任務

| 任務 ID | 任務 | 輸入 | 預測目標 | 比較方法 | 指標 |
| --- | --- | --- | --- | --- | --- |
| S1 | daylight-response benchmark | outdoor temperature、outdoor humidity、facade sunlight、sun irradiance、rain、wind | 下一步或 15/60 分鐘後的兩點 illuminance | 本研究 boundary-response 模式 vs persistence vs 線性回歸 | MAE、RMSE |
| S2 | thermal-humidity benchmark | 前一段兩點 temperature、humidity 與 outdoor variables | 下一步或 15/60 分鐘後的兩點 temperature、humidity | 本研究簡化動態模式 vs persistence vs 線性回歸 | MAE、RMSE |
| S3 | facade event delta benchmark | 日照突增、降雨或外氣明顯變化事件 | 事件後的兩點變化量 | 比較事件響應斜率與變化量 | delta MAE |

## 執行步驟

1. 先執行下列命令產生本 repo 的模板：

```text
python3 scripts/build_training_templates.py
python3 scripts/build_public_dataset_benchmark_templates.py
```

2. 下載公開資料集原始檔，建議存放於下列路徑：

```text
outputs/data/raw_public/cu-bems/
outputs/data/raw_public/sml2010/
```

3. 依 outputs/data_templates/public_dataset_alignment_template.json 的規則，把原始資料轉成下列正規化檔案：

```text
outputs/data/normalized_public/cu_bems/corner_sensor_timeseries.csv
outputs/data/normalized_public/cu_bems/device_event_log.csv
outputs/data/normalized_public/cu_bems/auxiliary_features.csv
outputs/data/normalized_public/cu_bems/scenario_metadata.json
outputs/data/normalized_public/sml2010/corner_sensor_timeseries.csv
outputs/data/normalized_public/sml2010/outdoor_environment.csv
outputs/data/normalized_public/sml2010/auxiliary_features.csv
outputs/data/normalized_public/sml2010/scenario_metadata.json
```

4. 對 CU-BEMS，只執行 C1-C3 這類 zone-response benchmark，不報 full field MAE。

5. 對 SML2010，只執行 S1-S3 這類 two-point boundary-response benchmark，不把 enthalpic motor 直接宣稱為 window 開關。

6. 論文中報告時，明確區分：

- synthetic benchmark：完整空間場、區域平均、IDW、hybrid residual。
- public benchmark：zone-level 或 point-level 響應，以及 comfort-level 驗證。

7. benchmark 結果會輸出至下列目錄：

```text
outputs/data/public_benchmarks/
```

## 建議在論文中的表述方式

最穩妥的說法是：本研究已建立公開資料集 shared-task benchmark 設計，使不同方法可在 CU-BEMS 與 SML2010 上比較共同子任務；然而，由於公開資料集不具備完整單房間空間 ground truth，因此完整 3D 場重建與 8 角落感測器校正的主要 benchmark 仍採用本研究自建的 canonical synthetic dataset。
