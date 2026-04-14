# 系統架構圖

本文件將目前單房間三因子空間數位孿生原型的實作架構整理成 GitHub 可直接顯示的 Mermaid 圖表，方便用於 README、論文方法章、口試簡報與系統說明。

## 1. 整體分層架構

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    U1["Direct interfaces<br/>Web UI + CLI scripts"]
    U2["LLM / external interfaces<br/>MCP client + Gemma/Ollama"]
    A1["Integration layer<br/>mcp_server.py + gemma_bridge.py"]
    S1["Service layer<br/>service.py + scenarios.py + entities.py + math_utils.py"]
    P0["Physics / estimation core<br/>DigitalTwinModel + IDW + impact learning + action ranking"]
    N1["Neural residual layer<br/>hybrid_residual.py + checkpoint"]
    O1["Outputs<br/>JSON/CSV + figures + thesis/paper artifacts"]

    U1 --> S1
    U2 --> A1
    A1 --> S1
    S1 --> P0
    P0 --> N1
    N1 --> O1
    S1 --> O1
```

## 2. 主要執行資料流

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 20, 'rankSpacing': 28}} }%%
flowchart TB
    A["User input<br/>scenario / window / devices / furniture / timeline"] --> B["web_demo.py<br/>or MCP tool call"]
    B --> C["core/service.py"]
    C --> D["Build base<br/>scenario"]
    D --> E["Apply overrides<br/>device_specs / extra_devices / furniture<br/>indoor baseline / elapsed time"]
    E --> F["DigitalTwinModel.simulate()"]

    subgraph Estimate["Estimation Path"]
        direction TB
        F --> G["Predict field<br/>at grid points"]
        G --> H["Predict corner<br/>sensor values"]
        H --> I["Calibrate active<br/>device powers"]
        I --> J["Fit trilinear<br/>residual correction"]
        J --> K["Rebuild<br/>corrected field"]
        K --> L["Compute zone averages<br/>point samples / volume"]
    end

    L --> M["Optional hybrid<br/>residual correction"]
    M --> N["Ranking / baseline comparison<br/>learning panels / 3D preview"]
    N --> O["Web dashboard<br/>or MCP response"]
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
flowchart TB
    subgraph Room["Standard room topology (6 m x 4 m x 3 m)"]
        direction TB

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
%%{init: {'flowchart': {'nodeSpacing': 18, 'rankSpacing': 24}} }%%
flowchart TB
    A["Validation scenario<br/>room + environment + devices + furniture"] --> B["Apply truth adjustments<br/>to active devices"]
    B --> C["Truth simulation"]
    C --> D["Synthetic 8-corner observations"]
    D --> E["Nominal simulation<br/>with original device settings"]
    E --> F["Sensor-informed correction<br/>power calibration + trilinear residual"]
    F --> G["Corrected estimate"]
    G --> H["Optional hybrid residual correction"]
    H --> I["Reference builders<br/>IDW baseline + impact learning"]
    I --> J["Compare outputs<br/>truth vs corrected vs baseline"]
    J --> K["MAE metrics + action ranking<br/>+ exported summaries and figures"]
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
