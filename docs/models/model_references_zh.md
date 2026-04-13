# 單房間數位孿生模型升級與參考文獻

## 模型升級重點

原本模型偏向「局部影響場」：

- 冷氣、窗戶、照明只在設備附近產生衰減影響
- 全室背景溫度主要維持在 `room.base_temperature`
- 因此容易出現「局部冷、遠端仍接近原始高溫」的結果

目前已改成 `bulk + local field` 混合模型：

- `bulk state`：表示全室平均溫濕度隨時間朝準穩態收斂
- `local field`：表示冷氣出風、窗邊交換、局部熱源造成的空間差異
- `stratification`：保留簡化垂直分層，但會因冷氣/開窗混合作用而減弱

這種做法更接近 control-oriented reduced-order model：

- 比 CFD 輕量
- 比 purely local heuristic 更合理
- 也比完全 well-mixed 單區模型更能保留空間差異

## 建議優先引用的文獻

### 1. 數位孿生總覽

1. Andres Sebastian Cespedes-Cubides, Muhyiddine Jradi, “A review of building digital twins to improve energy efficiency in the building operational stage,” *Energy Informatics*, 2024. DOI: `10.1186/s42162-024-00313-7`
   Link: https://doi.org/10.1186/s42162-024-00313-7
   Relevance: 可用來界定建築數位孿生在 operation stage 的定義、資料整合層次、以及「多數案例缺乏完整閉環」這件事。

### 2. 控制導向簡化熱模型

2. Per Bacher, Henrik Madsen, “Identifying suitable models for the heat dynamics of buildings,” *Energy and Buildings*, 2011. DOI: `10.1016/j.enbuild.2011.02.005`
   Link: https://doi.org/10.1016/j.enbuild.2011.02.005
   Relevance: 灰箱/簡化熱動態模型的經典參考，適合支撐你把房間熱反應建成可校正、可控制、可用感測資料更新的 reduced-order model。

3. Petri Hietaharju, Mika Ruusunen, Kauko Leiviskä, “A Dynamic Model for Indoor Temperature Prediction in Buildings,” *Energies*, 2018. DOI: `10.3390/en11061477`
   Link: https://doi.org/10.3390/en11061477
   Relevance: 強調少量參數、容易部署、可用於預測與控制，和你目前的單房間原型很接近。

4. Gargya Gokhale, Bert Claessens, Chris Develder, “Physics informed neural networks for control oriented thermal modeling of buildings,” *Applied Energy*, 2022. DOI: `10.1016/j.apenergy.2022.118852`
   Link: https://doi.org/10.1016/j.apenergy.2022.118852
   Relevance: 如果你後面想把本地 Gemma 或其他模型接進來做 hybrid twin，這篇很適合當「physics-informed + data-driven」延伸方向。

### 3. 室內空間分布與 zonal / hybrid 模型

5. E.J. Teshome, F. Haghighat, “Zonal Models for Indoor Air Flow - A Critical Review,” *International Journal of Ventilation*, 2004. DOI: `10.1080/14733315.2004.11683908`
   Link: https://doi.org/10.1080/14733315.2004.11683908
   Relevance: 可用來說明 zonal model 介於 CFD 與 single-zone 之間，是你論文方法定位的重要理論背景。

6. Ahmed Megri, Yao Yu, Rui Miao, Xiaoou Hu, “A new dynamic zOnal model with air-diffuser (DOMA) - Application to thermal comfort prediction,” *Indoor and Built Environment*, 2022. DOI: `10.1177/1420326X211060486`
   Link: https://doi.org/10.1177/1420326X211060486
   Relevance: 直接支撐「瞬態 zonal / subzonal 模型」這條路，特別適合引用在冷氣送風、時間響應、空間分布這幾段。

7. B. Huljak, J.A. Acero, Z.H. Kyaw, F. Chinesta, “Hybrid models for simulating indoor temperature distribution in air-conditioned spaces,” *Frontiers in Built Environment*, 2025. DOI: `10.3389/fbuil.2025.1690062`
   Link: https://doi.org/10.3389/fbuil.2025.1690062
   Relevance: 很接近你要做的路線。它把 CFD、reduced-order model 與 sparse sensors 結合，屬於相當值得直接對照的近期文獻。

### 4. 有限感測器下的場估測

8. Weixin Qian, Chenxi Li, Hu Gao, Lei Zhuang, Yanyu Lu, Site Hu, Jing Liu, “Estimating indoor air temperature and humidity distributions by data assimilation with finite observations: Validation using an actual residential room,” *Building and Environment*, 2025. DOI: `10.1016/j.buildenv.2024.112495`
   Link: https://doi.org/10.1016/j.buildenv.2024.112495
   Relevance: 非常貼近你的問題設定。它直接處理「有限感測器推估室內溫濕度場」，而且還討論 sensor placement。

9. Y. Lisa Chen, Jin Wen, “Application of zonal model on indoor air sensor network design,” *Proceedings of SPIE*, 2007. DOI: `10.1117/12.716356`
   Link: https://doi.org/10.1117/12.716356
   Relevance: 適合拿來支撐你論文裡對「角落感測器配置」與「感測器數量有限時如何設計推估方法」的敘述。

### 5. 快速模擬與即時控制

10. Zhuangbo Feng, Chuck Wah Yu, Shi-Jie Cao, “Fast prediction for indoor environment: Models assessment,” *Indoor and Built Environment*, 2019. DOI: `10.1177/1420326X19852450`
    Link: https://doi.org/10.1177/1420326X19852450
    Relevance: 可拿來說明為何論文不走 full CFD，而是選擇 fast model / reduced model / hybrid model 這條路。

## 對你論文最有用的引用組合

如果你只想先抓最核心的 5 篇：

1. Cespedes-Cubides and Jradi (2024): 數位孿生定位
2. Bacher and Madsen (2011): 灰箱熱動態模型
3. Megri et al. (2022): 動態 zonal 模型
4. Qian et al. (2025): 有限感測器下的溫濕度場估測
5. Huljak et al. (2025): hybrid spatial thermal model + sparse sensors

## 對你現在系統的直接啟發

- 你的原型可以明確定位為：`single-room, control-oriented, reduced-order spatial digital twin`
- 目前的 `bulk + local field` 很適合寫成：
  `a control-oriented reduced-order surrogate of the indoor thermal-humidity field`
- 如果後續加上 Gemma / MCP，論文可以再往：
  `physics-guided digital twin service with local LLM-assisted analysis`
  發展
