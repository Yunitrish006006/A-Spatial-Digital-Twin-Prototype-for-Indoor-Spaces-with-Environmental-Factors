# 論文實驗資料驗證流程

本文件說明如何確認中文論文、PDF/Docx 產生腳本與 IEEE paper 中的實驗數字，是否有對應的本地輸出資料支撐。驗證重點不是讓數字看起來通過，而是把每個數字標成可重現、缺資料或僅存在於文件中。

## 一、資料類型與 claim boundary

本研究目前的實驗證據分成三層：

| 類型 | 對應資料 | 可支持的主張 | 不能過度宣稱 |
|---|---|---|---|
| controlled simulation | `outputs/data/validation_summary.json`、`window_matrix_summary.json`、`hybrid_residual_summary.json`、`submission_readiness_summary.json` | 8 組標準情境、IDW baseline、hybrid residual、LOO 在受控真值下的 field MAE | 不能直接宣稱任意真實房間都達到相同 dense-field 誤差 |
| real-bedroom snapshot | `outputs/data/bedroom_01_weekly/weekly_simulation_summary.json` | 7 天、28 筆快照中，8 角落感測校正改善未參與校正的 pillow 參考點 | 不能宣稱已完成真實房間完整 3D dense ground truth 驗證 |
| public task-aligned benchmark | `outputs/data/public_benchmarks/*_hybrid_twin_comparison.json` | SML2010、CU-BEMS 上與 persistence / linear regression 的 shared-task 比較 | 不能宣稱公開資料支援本研究的 full 3D field MAE、8-corner calibration 或完整非連網裝置係數學習 |

推薦排序目前屬於 counterfactual simulation。若要宣稱推薦動作具有實際因果改善效果，仍需額外做 before/after intervention 實測。

## 二、目前論文中的實驗標記

中文論文第五章已將實驗或驗證項目標成 E1--E9。Web demo、MCP 與可旋轉 3D 展示只負責呈現或服務化同一批輸出，不列為獨立量化實驗。

| 標記 | 名稱 | 類型 | 主要 evidence file | 驗證狀態定位 |
|---|---|---|---|---|
| 實驗 E1 | 標準情境 full-field 重建 | controlled simulation | `outputs/data/validation_summary.json` | `REPRODUCIBLE` |
| 實驗 E2 | IDW baseline 比較 | controlled simulation baseline | `outputs/data/validation_summary.json` | `REPRODUCIBLE` |
| 實驗 E3 | 消融與可重現性 | robustness / ablation | `outputs/data/submission_readiness_summary.json` | `REPRODUCIBLE` |
| 實驗 E4 | 非連網裝置影響學習 | controlled impact-learning check | `outputs/data/validation_summary.json` 或 demo output | 以既有 summary 與論文描述檢查，不等同實測因果 |
| 實驗 E5 | 窗戶矩陣與 direct input | boundary-condition sensitivity | `outputs/data/window_matrix_summary.json` | `REPRODUCIBLE` |
| 實驗 E6 | Hybrid residual robustness | model residual experiment | `outputs/data/hybrid_residual_summary.json`、`hybrid_residual_checkpoint.json` | `REPRODUCIBLE` |
| 實驗 E7 | 真實臥室快照 sparse calibration | real-bedroom snapshot | `outputs/data/bedroom_01_weekly/weekly_simulation_summary.json` | `REPRODUCIBLE`，但不是 dense ground truth |
| 驗證方案 E8 | 推薦動作 before/after 介入 | future intervention protocol | 尚未有完成實測 summary | `DOCUMENT_ONLY` / protocol-only |
| 實驗 E9 | Public task-aligned benchmark | public dataset benchmark | `outputs/data/public_benchmarks/*_hybrid_twin_comparison.json` | 有資料時 `REPRODUCIBLE`，缺資料時 `NEEDS_DATA` |

## 三、準備資料

先檢查資料目錄與 public dataset 狀態：

```bash
python3 scripts/prepare_experiment_data.py
```

這會建立並檢查：

- `outputs/data/`
- `outputs/data/public_benchmarks/`
- `outputs/data/raw_public/`
- `outputs/data/normalized_public/`

原始 public dataset 很大，不應 commit 進 repo。`.gitignore` 已明確忽略：

- `outputs/data/raw_public/`
- `outputs/data/normalized_public/`

## 四、public datasets 放置路徑

### SML2010

來源：UCI Machine Learning Repository，SML2010，DOI `10.24432/C5RS3S`，授權 CC BY 4.0。

需要的原始檔：

```text
outputs/data/raw_public/sml2010/NEW-DATA-1.T15.txt
outputs/data/raw_public/sml2010/NEW-DATA-2.T15.txt
```

可嘗試自動下載：

```bash
python3 scripts/prepare_experiment_data.py --dataset sml2010 --download
```

### CU-BEMS

來源：figshare / Scientific Data，CU-BEMS smart building electricity consumption and indoor environmental sensor datasets，version 6，授權 CC BY 4.0。

需要的原始檔：

```text
outputs/data/raw_public/cu-bems/2018Floor1.csv
...
outputs/data/raw_public/cu-bems/2018Floor7.csv
outputs/data/raw_public/cu-bems/2019Floor1.csv
...
outputs/data/raw_public/cu-bems/2019Floor7.csv
```

可嘗試自動下載：

```bash
python3 scripts/prepare_experiment_data.py --dataset cu-bems --download
```

下載後若尚未正規化：

```bash
python3 scripts/normalize_public_benchmark_data.py --dataset all
```

或由準備腳本一併執行：

```bash
python3 scripts/prepare_experiment_data.py --download --normalize
```

## 五、執行完整實驗

一般情況可直接跑總控腳本：

```bash
python3 scripts/run_all_thesis_experiments.py
```

此腳本會依序執行：

1. `scripts/prepare_experiment_data.py`
2. `scripts/run_demo.py`
3. `scripts/run_window_matrix.py`
4. `scripts/run_hybrid_residual_experiment.py --fourier-denoise`
5. `scripts/run_submission_readiness_experiments.py`
6. `scripts/run_bedroom_weekly_simulation.py`
7. public benchmark scripts，如果 normalized public data 已存在
8. `scripts/verify_thesis_results.py`

如果 public dataset 不存在，總控腳本會跳過 public benchmark，不會讓整體流程崩潰；最後驗證報告會將 public rows 標示為 `MISSING` / `NEEDS_DATA`。

若只想驗證既有輸出，不重跑實驗：

```bash
python3 scripts/verify_thesis_results.py
```

## 六、驗證報告

驗證腳本會輸出：

```text
outputs/data/thesis_result_verification_report.md
outputs/data/thesis_result_verification_report.json
```

每筆結果包含：

- `result_name`
- `thesis_value`
- `computed_value`
- `absolute_error`
- `tolerance`
- `status`: `PASS` / `FAIL` / `MISSING`
- `support_level`: `REPRODUCIBLE` / `DOCUMENT_ONLY` / `NEEDS_DATA`
- `source_file`
- `evidence_file`
- `suggested_script`

狀態解讀：

| status | 意義 |
|---|---|
| PASS | 文件中有該數字，且 evidence JSON 算出的值在 tolerance 內一致 |
| FAIL | evidence JSON 存在，但算出的值與論文值超過 tolerance |
| MISSING | 文件數字或 evidence JSON 缺失，不能視為已驗證 |

支撐層級解讀：

| support_level | 意義 |
|---|---|
| REPRODUCIBLE | 可由本地 JSON 輸出重新計算 |
| DOCUMENT_ONLY | 目前只在文件中看到，缺本地 evidence JSON |
| NEEDS_DATA | 需要 public/raw data 或缺少由資料產生的輸出 |

## 七、目前重點驗證數字

驗證腳本會檢查以下論文數字：

- 標準驗證規模：8 組標準情境、48 組窗戶矩陣
- hybrid residual 訓練規模：default split `576 / 192` train/test samples、LOO `8` folds
- real-bedroom snapshot 規模：7 天、`28` 筆快照
- base model 平均 field MAE：temperature `0.0474`、humidity `0.1765`、illuminance `2.0835`
- IDW baseline 平均 field MAE：temperature `0.1723`、humidity `0.4633`、illuminance `75.0516`
- hybrid residual default split：temperature `0.0023`、humidity `0.0041`、illuminance `0.1675`
- hybrid residual leave-one-scenario-out：temperature `0.0017`、humidity `0.0055`、illuminance `0.1581`
- real-bedroom pillow MAE before：`0.8967°C`、`4.1286%`、`358.6392 lux`
- real-bedroom pillow MAE after：`0.1676°C`、`0.3939%`、`21.3753 lux`
- SML2010：24 個 target-horizon tasks、12 個 lowest MAE、15 個勝過 linear regression、14 個勝過 persistence
- CU-BEMS：12 個 target-horizon tasks、9 個勝過 linear regression、0 個勝過 persistence

若任一數字 FAIL，不應直接改 JSON 或硬湊數字。正確流程是先確認是哪個實驗腳本、資料版本或論文文字過期，再決定是否重跑實驗或同步修正論文。
