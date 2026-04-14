# 公開資料 Shared-Task Benchmark 結果摘要

本文件整理兩份公開資料 benchmark 輸出：

- `outputs/data/public_benchmarks/cu_bems_benchmark_summary.json`
- `outputs/data/public_benchmarks/sml2010_benchmark_summary.json`

此處結果屬於第二層 `public task-aligned benchmark`，用途是建立外部可重現的 shared-task baseline。它不是用來取代本研究在標準模擬場景中的完整空間場評估，而是補充說明：在真實公開資料上，哪些簡單 baseline 容易或不容易被超越。

## 資料規模

| Dataset | 時間尺度 | 主要觀測形式 | Benchmark 樣本規模 |
| --- | --- | --- | ---: |
| CU-BEMS | 1 分鐘 | 33 個 zone 的用電與部分環境感測 | `C1/C2` 約 1140 萬筆，`C3` 約 16.7 萬筆 |
| SML2010 | 15 分鐘 | 2 個室內點位 + 戶外/日照/通風輔助變數 | `S1/S2` 約 4130 筆，`S3` 約 1290 筆 |

CU-BEMS 的 benchmark 使用 `15` 與 `60` 分鐘 horizon；SML2010 亦同。CU-BEMS 原始資料中發現至少一筆異常時間值 `Date=2`，目前流程已在正規化與 benchmark 階段自動跳過該類髒資料列，不再讓整體執行失敗。

## 結果總結

### 1. CU-BEMS：persistence baseline 全面優於線性回歸

在 CU-BEMS 的 `C1`、`C2`、`C3` 三類任務中，不論是 `15` 分鐘還是 `60` 分鐘 horizon，`persistence` 的 MAE 都全面低於 `linear regression`。代表這份多區域建築資料具有很強的短中期時間延續性，單純把外生變數與當前狀態送進線性模型，仍不足以穩定超越「直接延用最近一次觀測值」這個簡單 baseline。

| Horizon | Task | 代表 target | Persistence MAE | Linear Regression MAE | 較佳 baseline |
| --- | --- | --- | ---: | ---: | --- |
| 15 min | `C1` | temperature | 0.261973 | 0.288409 | Persistence |
| 15 min | `C1` | humidity | 0.713036 | 0.777978 | Persistence |
| 15 min | `C2` | illuminance | 1.363127 | 1.793783 | Persistence |
| 15 min | `C3` | temperature delta | 0.571121 | 0.691739 | Persistence |
| 15 min | `C3` | humidity delta | 0.991996 | 1.258929 | Persistence |
| 15 min | `C3` | illuminance delta | 2.184304 | 3.382856 | Persistence |
| 60 min | `C1` | temperature | 0.747704 | 0.834086 | Persistence |
| 60 min | `C1` | humidity | 1.504325 | 1.562054 | Persistence |
| 60 min | `C2` | illuminance | 4.011693 | 5.646140 | Persistence |
| 60 min | `C3` | temperature delta | 1.195808 | 1.364022 | Persistence |
| 60 min | `C3` | humidity delta | 1.763551 | 1.964076 | Persistence |
| 60 min | `C3` | illuminance delta | 4.508905 | 7.093012 | Persistence |

解讀上，CU-BEMS 比較像是「大規模 zone-level building operation forecasting」問題，而不是「局部設備顯著改變單一房間場分布」問題。因此這份資料更適合用來說明 shared-task baseline 的難度與時間慣性，不宜被誤解為本研究完整空間孿生模型的直接替代評測場域。

### 2. SML2010：線性回歸明顯改善溫度預測，但不擅長照度

SML2010 的結果呈現出與 CU-BEMS 不同的結構。對 `temperature` 類任務，`linear regression` 在 `S2` 與 `S3` 任務上穩定優於 `persistence`；但對 `illuminance` 類任務，`persistence` 仍普遍較強。`humidity` 則是混合結果，改善幅度明顯小於溫度。

#### 溫度任務

| Horizon | Task | Target | Persistence MAE | Linear Regression MAE | MAE 改善 |
| --- | --- | --- | ---: | ---: | ---: |
| 15 min | `S2` | dining temperature | 0.118236 | 0.042593 | 0.075643 |
| 15 min | `S2` | room temperature | 0.115293 | 0.051943 | 0.063350 |
| 15 min | `S3` | dining temperature delta | 0.233167 | 0.092903 | 0.140264 |
| 15 min | `S3` | room temperature delta | 0.220143 | 0.095708 | 0.124435 |
| 60 min | `S2` | dining temperature | 0.469776 | 0.192471 | 0.277305 |
| 60 min | `S2` | room temperature | 0.458005 | 0.229682 | 0.228323 |
| 60 min | `S3` | dining temperature delta | 0.563401 | 0.211799 | 0.351602 |
| 60 min | `S3` | room temperature delta | 0.532738 | 0.243147 | 0.289591 |

這代表 SML2010 中的戶外溫度、戶外濕度、日照與通風相關輔助變數，對熱環境短中期預測有明顯幫助。尤其在 `60` 分鐘 horizon 下，線性回歸相對 persistence 的 MAE 改善更明顯，表示外部邊界條件對較長時間尺度的熱反應預測確實提供了額外資訊。

#### 濕度與照度任務

| Horizon | Task | Target 群 | 主要結果 |
| --- | --- | --- | --- |
| 15 min | `S1` | illuminance | 兩個點位皆為 Persistence 較佳 |
| 15 min | `S2` | humidity | `room humidity` 線性回歸極小幅勝出；`dining humidity` Persistence 較佳 |
| 15 min | `S3` | humidity + illuminance delta | humidity 混合；兩個 illuminance delta 皆為 Persistence 較佳 |
| 60 min | `S1` | illuminance | 兩個點位皆為 Persistence 較佳 |
| 60 min | `S2` | humidity | 兩個點位皆為 Persistence 較佳 |
| 60 min | `S3` | humidity + illuminance delta | humidity 兩個點位皆為線性回歸較佳；兩個 illuminance delta 皆為 Persistence 較佳 |

這說明：

1. 溫度是最容易從外部特徵中獲益的目標變數。
2. 濕度可被部分輔助變數改善，但效果不穩定。
3. 照度的時間結構與日照傳輸關係更複雜，簡單線性模型仍不足以穩定超越 persistence。

## 論文可直接使用的結論文字

可直接改寫為第五章的結果描述：

> 在公開資料 shared-task benchmark 層，我們觀察到不同資料集呈現兩種不同的 baseline 結構。第一，對 CU-BEMS 這類大規模 multi-zone building operation dataset 而言，persistence baseline 在 15 與 60 分鐘 horizon 的所有 zone-level response 任務上皆優於線性回歸，顯示其短中期狀態具有強烈的 temporal inertia。第二，對 SML2010 這類 two-point boundary-response dataset 而言，線性回歸可穩定降低溫度預測 MAE，例如 60 分鐘 horizon 下 dining/room temperature 的 MAE 分別由 0.4698/0.4580 降至 0.1925/0.2297，表示外氣與日照等邊界條件特徵對熱反應預測具明顯貢獻；然而在 illuminance 任務上 persistence 仍較強，說明簡單線性模型尚不足以捕捉光照變化的非線性傳輸。整體而言，公開資料 benchmark 更適合作為 shared-task external baseline，而完整空間場重建能力仍應以本研究的 canonical synthetic benchmark 為主要評估依據。

## 建議在論文中的定位方式

建議把這份結果放在「外部 benchmark 補充」而不是「主結果」的位置，理由如下：

1. 這兩份公開資料都無法提供本研究所需的完整 3D 空間真值場。
2. 它們適合評估的是 point-level 或 zone-level 的 shared observable tasks。
3. 因此它們最有價值的角色，是提供一組外部、可重現、與文獻常見時間序列 baseline 可對齊的比較層。

## 下一步

如果要再往前走一步，最有價值的是把本研究模型的輸出再映射到 `C1/C2/C3` 與 `S1/S2/S3` 這些 shared targets，讓本研究方法也能在同一份 public benchmark summary 中與 `persistence`、`linear regression` 並列比較。