# 系統架構圖

本文件將目前單房間三因子空間數位孿生原型的實作架構整理成 GitHub 可直接顯示的 Mermaid 圖表，方便用於 README、論文方法章、口試簡報與系統說明。

正式論文與簡報輸出的 SVG 由 `scripts/build_architecture_diagrams.py` 產生。該腳本目前使用統一的 16:9 local SVG renderer，讓圖 3-1、圖 3-2、圖 3-3、圖 3-4、圖 3-5 與圖 5-1 保持相同字級、色彩、框線與箭頭風格；其中圖 3-1 由 Python top-down tree renderer 產生，用於整理整個系統的抽象責任邊界。下方 Mermaid 區塊保留作為語意草稿與 GitHub 預覽。

## 1. 整體分層架構

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    ROOT["單房間三因子空間數位孿生系統<br/>Sparse IoT sensing + non-networked appliances"]

    ROOT --> OBS["情境與觀測層<br/>room state enters one shared path"]
    ROOT --> MODEL["估測與學習層<br/>interpretable model first"]
    ROOT --> SERVICE["服務與決策層<br/>same estimator, multiple access surfaces"]

    OBS --> ROOM["Room schema<br/>geometry / zones / furniture blockers"]
    OBS --> SENSOR["Sparse IoT evidence<br/>8 corner sensors / outdoor + time"]

    MODEL --> FIELD["T/H/L field model<br/>bulk + local field / device influence"]
    MODEL --> LEARN["Calibration + learning<br/>power scale / trilinear / impact + hybrid residual"]

    SERVICE --> TOOLS["Tool interfaces<br/>scripts / Web / MCP + Gemma bridge"]
    SERVICE --> OUT["Decision outputs<br/>point / zone / 3D / action ranking"]
```

## 2. 主要執行資料流

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 22, 'rankSpacing': 32}} }%%
flowchart TB
    A["User input\nscenario / devices / environment / timeline"]

    subgraph Entry["Entry layer"]
        direction LR
        B1["web_demo.py"]
        B2["MCP tool call"]
    end

    subgraph Build["Scenario build"]
        direction LR
        C["core/service.py"] --> D["Build base scenario"]
        D --> E["Apply overrides\ndevices / furniture / baseline"]
    end

    subgraph Estimate["Estimation path"]
        direction LR
        F["DigitalTwinModel.simulate()"] --> G["Field + sensor prediction"]
        G --> H["Power calibration\n+ trilinear correction"]
        H --> I["Zone averages / point samples"]
    end

    subgraph Output["Output"]
        direction LR
        M["Hybrid residual correction"] --> N["Action ranking + dashboard / MCP"]
    end

    A --> Entry
    Entry --> Build
    Build --> Estimate
    Estimate --> Output
```

## 3. 感測器校正與學習流程

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    T1["Truth-adjusted devices"] --> T2["Truth simulation"]
    T2 --> T3["Synthetic 8-corner sensor observations"]

    B1["Nominal device settings"] --> B2["Nominal simulation"]
    B2 --> B3["Predicted sensor values"]

    T3 --> C1["Sensor residuals"]
    B3 --> C1

    C1 --> C2["Active device power calibration"]
    C2 --> C3["Trilinear residual correction<br/>8 parameters"]
    C3 --> C4["Corrected field reconstruction"]

    T3 --> L1["Before / after observations"]
    B2 --> L1
    L1 --> L2["Least-squares appliance impact learning"]

    C4 --> R1["Target-zone estimates"]
    L2 --> R2["Learned appliance impact coefficients"]
    R1 --> R3["Action ranking / recommendation"]
```

## 4. 模型學習推論與推薦資料流

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 18, 'rankSpacing': 28, 'curve': 'basis'}} }%%
flowchart LR
    subgraph Train["A. Learning and training path"]
        direction TB
        T0["Raw records<br/>corner sensors / device events / outdoor / scenario"] --> T1["Time alignment<br/>unit and coordinate normalization"]
        T1 --> T2["Scenario state assembly<br/>baseline + outdoor + devices + furniture + time"]
        T2 --> T3["Nominal field estimate<br/>temperature / humidity / illuminance"]
        T3 --> T4["Sparse calibration<br/>power scale + trilinear residual"]
        T4 --> T5{"Training branch"}
        T5 --> T6["Impact learning<br/>before-after delta + device spatial basis"]
        T5 --> T7["Hybrid residual learning<br/>features + residual labels"]
        T6 --> A1[("Learned impact coefficients")]
        T7 --> A2[("Residual checkpoint")]
        T7 --> A3[("Validation summary JSON")]
    end

    subgraph Runtime["B. Runtime inference and recommendation path"]
        direction TB
        R0["Runtime input<br/>MCP / web demo / script / API"] --> R1["Scenario override and validation<br/>baseline + devices + furniture + time"]
        R1 --> R2["Nominal T/H/L estimate<br/>variable-specific physical models"]
        R2 --> R3["Sparse correction<br/>registered sensors or calibration state"]
        R3 --> R4["Optional hybrid residual<br/>add learned residual if checkpoint exists"]
        R4 --> R5["Point or zone prediction<br/>temperature + humidity + illuminance"]
        R5 --> R6["Recommendation precondition<br/>point sample or cluster sample + T/H/L target"]
        R6 --> R7{"Complete scope + target?"}
        R7 -- "No" --> R8["Return prediction<br/>or missing-target error"]
        R7 -- "Yes" --> R9["Counterfactual action simulation<br/>rerun inference for each candidate"]
        R9 --> R10["Rank by comfort penalty reduction<br/>recommended device operation"]
    end

    A1 -. "device impact coefficients" .-> R3
    A2 -. "optional residual model" .-> R4
    A3 -. "reproducible evidence" .-> R10
```

## 5. 可模組化裝置與家具架構

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    D["Device sources<br/>built-in devices + device_specs + extra_devices"]
    F["Furniture sources<br/>built-in furniture + extra_furniture"]
    D --> S["Scenario state"]
    F --> S
    S --> M["DigitalTwinModel"]
    M --> E1["Device local effects"]
    M --> E2["Bulk room state"]
    M --> E3["Obstacle-aware attenuation"]
    E1 --> R["Spatial field output"]
    E2 --> R
    E3 --> R
```

## 6. 房間感測器與目標區域配置

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 18, 'rankSpacing': 24}} }%%
flowchart LR
    subgraph Room["Standard room topology (6 m x 4 m x 3 m)"]
        direction LR

        subgraph Ceiling["Ceiling layer sensors"]
            direction LR
            CSW["ceiling_sw"]
            CSE["ceiling_se"]
            CNW["ceiling_nw"]
            CNE["ceiling_ne"]
        end

        subgraph Devices["Main devices"]
            direction LR
            WIN["window_main<br/>left wall"]
            LGT["light_main<br/>ceiling center"]
            ACM["ac_main<br/>right wall"]
        end

        subgraph Zones["Target zones"]
            direction LR
            ZW["window_zone"]
            ZC["center_zone"]
            ZD["door_side_zone"]
        end

        subgraph Floor["Floor layer sensors"]
            direction LR
            FSW["floor_sw"]
            FSE["floor_se"]
            FNW["floor_nw"]
            FNE["floor_ne"]
        end
    end

    Ceiling --> Devices
    Devices --> Zones
    Zones --> Floor
```

## 7. 驗證與實驗流程圖

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    A["Validation scenario\nroom + environment + devices + furniture"]

    subgraph Sim["Simulation"]
        direction LR
        B["Apply truth adjustments\nto active devices"] --> C["Truth simulation"]
        C --> D["Synthetic 8-corner observations"]
        D --> E["Nominal simulation\nwith original device settings"]
    end

    subgraph Corr["Correction"]
        direction LR
        F["Sensor-informed correction\npower calibration + trilinear residual"] --> G["Corrected estimate"]
        G --> H["Optional hybrid residual correction"]
    end

    subgraph Eval["Evaluation"]
        direction LR
        I["Reference builders\nIDW baseline + impact learning"] --> J["Compare outputs\ntruth vs corrected vs baseline"]
        J --> K["MAE metrics + action ranking\n+ exported summaries and figures"]
    end

    A --> Sim
    Sim --> Corr
    Corr --> Eval
```

## 8. 程式碼結構圖

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    REPO["Repository root"]
    REPO --> DT["digital_twin/"]
    REPO --> SCRIPTS["scripts/"]
    REPO --> TESTS["tests/"]

    DT --> CORE["core/<br/>entities / scenarios / service / demo"]
    DT --> PHY["physics/<br/>model / baselines / learning / recommendations"]
    DT --> NEU["neural/<br/>hybrid_residual"]
    DT --> MCP["mcp/<br/>mcp_server / gemma_bridge"]
    DT --> WEB["web/<br/>web_demo / render"]
```

## 9. 文件與輸出結構圖

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    REPO["Repository root"]
    REPO --> DOCS["docs/"]
    REPO --> OUT["outputs/"]

    DOCS --> THESIS["thesis/"]
    DOCS --> MODELS["models/"]
    DOCS --> DMCP["mcp/"]
    DOCS --> DWEB["web/"]
    DOCS --> EXP["experiments/"]
    DOCS --> PAPERS["papers/ieee/"]
    DOCS --> ADMIN["admin/"]

    OUT --> DATA["data/"]
    OUT --> FIG["figures/"]
    OUT --> PAP["papers/"]
```

## 10. 圖表使用建議

- 若要放進 GitHub repo，直接保留 Mermaid 區塊即可。
- 若要放進論文正文，建議優先使用第 1 張、第 2 張、第 3 張、第 4 張、第 6 張與第 7 張。
- 第 4 張適合放方法章與口試簡報，用來說明資料如何從訓練一路接到推論與推薦。
- 第 5 張適合放方法章或附錄，用來說明裝置與家具的可模組化設計。
- 第 8 張與第 9 張較適合 README、系統說明或口試備用頁，不建議放論文正文。
