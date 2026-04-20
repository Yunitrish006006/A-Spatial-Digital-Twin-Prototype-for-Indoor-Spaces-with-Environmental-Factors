# 系統架構圖

本文件將目前單房間三因子空間數位孿生原型的實作架構整理成 GitHub 可直接顯示的 Mermaid 圖表，方便用於 README、論文方法章、口試簡報與系統說明。

## 1. 整體分層架構

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    U1["Human interaction layer<br/>Web interface"]
    U2["AI tool-access layer<br/>MCP-compatible clients + LLM bridge"]
    S1["Service orchestration layer<br/>scenario assembly + parameter management"]
    P0["Environmental digital twin core<br/>bulk + local field estimation + appliance influence modeling"]
    C1["Calibration and impact-learning layer<br/>power calibration + trilinear correction + least-squares learning"]
    N1["Optional residual neural layer<br/>hybrid residual correction"]
    O1["System outputs<br/>spatial field estimate + zone estimate + action ranking + 3D visualization"]

    U1 --> S1
    U2 --> S1
    S1 --> P0
    P0 --> C1
    C1 --> N1
    C1 --> O1
    N1 --> O1
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

## 4. 可模組化裝置與家具架構

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

## 5. 房間感測器與目標區域配置

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

## 6. 驗證與實驗流程圖

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

## 7. 程式碼結構圖

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

## 8. 文件與輸出結構圖

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

## 9. 圖表使用建議

- 若要放進 GitHub repo，直接保留 Mermaid 區塊即可。
- 若要放進論文正文，建議優先使用第 1 張、第 2 張、第 3 張、第 5 張與第 6 張。
- 第 4 張適合放方法章或附錄，用來說明裝置與家具的可模組化設計。
- 第 7 張與第 8 張較適合 README、系統說明或口試備用頁，不建議放論文正文。
