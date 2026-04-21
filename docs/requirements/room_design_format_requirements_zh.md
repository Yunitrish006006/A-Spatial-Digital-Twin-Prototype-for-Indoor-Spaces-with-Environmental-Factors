# 房間設計與三維資料格式要求

本文件定義本專案新增或修改房間設計時必須提供的資料格式。目的不是做室內設計美術圖，而是讓房間幾何、感測器、裝置、家具與目標區域能直接對應到目前數位孿生模型的 `Room`、`Vector3`、`Zone`、`Device` 與 `Furniture` 資料結構。

## 1. 座標系與單位

- 單位一律使用公尺 `m`。
- 房間原點固定在地面西南角：`(x=0, y=0, z=0)`。
- `x` 軸表示房間寬度方向，合法範圍為 `0 <= x <= room.width`。
- `y` 軸表示房間長度方向，合法範圍為 `0 <= y <= room.length`。
- `z` 軸表示高度方向，合法範圍為 `0 <= z <= room.height`。
- 所有點位都必須提供完整三維座標 `{ "x": number, "y": number, "z": number }`。

## 2. 必填資料

每一份房間設計至少必須包含下列區塊：

| 區塊 | 必填欄位 | 用途 |
| --- | --- | --- |
| `room` | `name`, `width_m`, `length_m`, `height_m`, `base_temperature_c`, `base_humidity_pct`, `base_illuminance_lux` | 定義房間三維尺寸與室內基準環境 |
| `grid_resolution` | `nx`, `ny`, `nz` | 定義場估計網格解析度 |
| `sensors` | `name`, `position` | 定義感測器三維位置 |
| `zones` | `name`, `min_corner`, `max_corner` | 定義目標區域或評估區域 |
| `devices` | `name`, `kind`, `position`, `orientation`, `activation` | 定義冷氣、窗戶、照明等設備 |
| `furniture` | `name`, `kind`, `min_corner`, `max_corner` | 定義會阻擋或反射的家具/障礙物 |
| `environment` | `outdoor_temperature_c`, `outdoor_humidity_pct`, `sunlight_illuminance_lux`, `daylight_factor` | 定義窗戶與日照使用之外部條件 |

## 3. 房間尺寸資料要求

`room` 必須明確填入三個維度：

```json
{
  "width_m": 6.0,
  "length_m": 4.0,
  "height_m": 3.0
}
```

建議同時保留簡短的人類可讀描述：

```json
{
  "description": "single rectangular test room, 6m x 4m x 3m"
}
```

## 4. 感測器要求

本研究預設使用 8 顆角落感測器。若採用標準配置，感測器必須放在地面四角與天花板四角：

| 名稱 | 位置 |
| --- | --- |
| `floor_sw` | `(0, 0, 0)` |
| `floor_se` | `(width, 0, 0)` |
| `floor_nw` | `(0, length, 0)` |
| `floor_ne` | `(width, length, 0)` |
| `ceiling_sw` | `(0, 0, height)` |
| `ceiling_se` | `(width, 0, height)` |
| `ceiling_nw` | `(0, length, height)` |
| `ceiling_ne` | `(width, length, height)` |

若改用非標準感測器配置，必須在 `metadata.reason` 說明原因，且不得少於 8 顆，否則無法等價使用目前的 trilinear residual correction。

## 5. 區域與家具要求

`zones` 與 `furniture` 使用 bounding box 格式：

```json
{
  "min_corner": { "x": 2.0, "y": 1.0, "z": 0.0 },
  "max_corner": { "x": 4.2, "y": 3.0, "z": 2.2 }
}
```

必須符合：

- `min_corner.x < max_corner.x`
- `min_corner.y < max_corner.y`
- `min_corner.z < max_corner.z`
- bounding box 不得超出房間邊界
- 家具若需要參與遮擋與反射，需填 `metadata.block_strength`，建議範圍 `0.0` 到 `1.0`。
- 若設計草稿把 `block_strength` 放在家具物件第一層，驗證腳本會警告；轉入 Python model 前應移到 `metadata.block_strength`，以符合目前 `Furniture.metadata` 結構。

## 6. 裝置要求

`devices.kind` 目前支援：

- `ac`
- `window`
- `light`

每個裝置必須提供：

- `position`：裝置中心或代表點位置
- `orientation`：設備作用方向向量，例如冷氣朝房間內吹可用 `{ "x": -1.0, "y": 0.0, "z": -0.25 }`
- `activation`：啟用程度，範圍 `0.0` 到 `1.0`
- `influence_radius_m`：影響半徑，若省略，應使用專案預設值

## 7. 驗收檢查清單

房間設計提交前必須確認：

- 房間三維尺寸完整，且 `width_m`, `length_m`, `height_m` 皆大於 0。
- 所有 `Vector3` 點位都在房間邊界內。
- 標準配置下有 8 顆角落感測器，名稱與座標正確。
- 每個 zone / furniture 的 `min_corner` 與 `max_corner` 不反向、不重合、不超界。
- 每個 device 的 `kind` 屬於支援類型，且 `activation` 在 `0.0` 到 `1.0`。
- 所有數值使用公尺、攝氏、百分比與 lux，不混用公分或英尺。
- 若該房間要寫入 thesis / IEEE paper / slides，必須同步更新論文、簡報與輸出檔。

## 8. 建議工作流程

1. 先複製 `docs/templates/room_design_template.json`。
2. 填入房間尺寸、基準環境與外部環境。
3. 先放 8 顆角落感測器，再定義 zones。
4. 加入 `ac`, `window`, `light` 裝置。
5. 加入家具或遮擋物。
6. 檢查所有三維座標都在房間範圍內。
7. 執行 `python3 scripts/validate_room_design.py docs/templates/room_design_template.json` 檢查格式。
8. 若要轉成 Python scenario，再對應到 `digital_twin/core/scenarios.py` 的 `Room`, `Vector3`, `Zone`, `Device`, `Furniture`。

目前可參考的範例：

- `docs/templates/room_design_standard_room_example.json`：本專案標準房間。
- `docs/templates/room_design_bedroom_01.json`：臥室範例，房間尺寸為 `4.0m × 4.6m × 3.2m`。

## 9. 可直接使用的需求文字

若要請他人或 AI 產生房間設計，請使用以下要求：

```text
請依照本專案 room-design-v1 格式產生一份單房間三維設計資料。

必要條件：
1. 房間必須是單一矩形房間，單位一律使用公尺。
2. 必須提供 room.width_m、room.length_m、room.height_m 三個維度。
3. 座標原點固定在地面西南角，所有點位必須使用 {x, y, z}。
4. 必須提供 8 顆角落感測器：地面四角與天花板四角。
5. 必須提供 zones，且每個 zone 使用 min_corner / max_corner bounding box。
6. 必須提供 devices，至少包含 ac、window、light 三類裝置，並包含 position、orientation、activation。
7. 若有家具或障礙物，必須使用 min_corner / max_corner，且不得超出房間邊界。
8. 所有座標不得小於 0，也不得超過 room 的 width_m、length_m、height_m。
9. 輸出必須是合法 JSON，不要加入註解。
10. 格式請參考 docs/templates/room_design_template.json。
11. 可用 python3 scripts/validate_room_design.py <your_room_design.json> 驗證。

輸出內容需包含：
- room
- grid_resolution
- environment
- sensors
- zones
- devices
- furniture
- comfort_target
- metadata
```
