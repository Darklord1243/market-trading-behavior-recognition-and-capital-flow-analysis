# 跑通 Baseline｜赛题一：市场参与者交易行为识别与资金流向分析

> 本文档整理自赛事官方指导材料，按「赛题说明 → 建模思路 → Baseline 实现 → 运行指南」重组。  
> **平台补充说明**（`pattern_type` 开放标签、A 榜提交流程、`transaction_date` 格式、自采数据、样例标签无效等）见 [`官方答疑与提交说明.md`](./官方答疑与提交说明.md)。

---

## 目录

**第一部分：赛题说明**

1. [项目简介](#一项目简介)
2. [任务介绍](#二任务介绍)
3. [任务数据与数据集构成](#三任务数据与数据集构成)
4. [任务规则及提交说明](#四任务规则及提交说明)

**第二部分：问题建模**

5. [赛题核心分析](#五赛题核心分析)
6. [任务分层拆解](#六任务分层拆解)
7. [开发建议](#七开发建议)
8. [解题思考过程](#八解题思考过程)

**第三部分：Baseline 方案**

9. [Baseline 架构与代码](#九baseline-架构与代码)
10. [核心代码详解](#十核心代码详解)
11. [运行说明](#十一运行说明)
12. [设计思路与核心逻辑](#十二设计思路与核心逻辑)

---

# 第一部分：赛题说明

## 一、项目简介

### 赛题背景

本赛题聚焦构建一套「市场参与者交易行为识别与资金流向分析」的体系化解决方案，要求结合逐笔成交数据、订单簿微观结构特征、个股基本面等信息，实现从海量高频数据中自动解析不同参与者的买卖行为和资金流向，识别背后真实意图的模型——例如识别不同订单的资金属性（游资/量化私募/散户等），分析资金背后意图（吸筹、试盘、对倒、拉升、出货等），并生成清晰易懂的资金流向分析结果（当前谁占主导，买入还是卖出，真实意图是什么）。

解决该问题将帮助投资者穿透复杂盘面、理性跟随不同机构资金动向，优化买卖时机，降低被游资或虚假挂单误导的风险，实现从「凭感觉跟风」到「有数据支撑的辅助决策」。

在股票投资中，市场参与者（公募基金、量化私募、游资等）的大额买卖行为往往对股价产生显著影响，其资金流向被视为重要的行情风向标。但普通投资者面对 Level-2 数据时普遍存在两大痛点：

| 痛点 | 说明 |
|------|------|
| 信息「碎片化」 | 单个指标难以还原机构真实的建仓、拉抬或出货意图，机构常通过拆单、对倒等方式隐藏真实动作 |
| 解读「滞后性」 | 多数资金流向指标基于日线统计，盘中动态变化无法捕捉，等信号明确时股价往往已大幅偏离理想买点 |

**通俗理解**：假设你是一个散户，看到某只股票突然放量大涨。你想知道——这是游资在拉涨停准备出货，还是量化基金在程序化做 T+0 套利？如果是前者，你该跟；如果是后者，你该躲。本赛题就是训练 AI 来自动回答这个问题。

参赛者基于 A 股个股的逐笔委托、逐笔成交、逐笔撤单、十档盘口快照四大类全量 Level-2 数据，构建完整的方法论体系，精细化区分游资/量化两类机构资金，识别各类市场参与者的买卖方向与交易意图，最终输出可落地的交易模式识别与资金流向分析结果。

---

## 二、任务介绍

本赛题包含两大核心任务，所有输出结果需严格匹配赛事指定格式，最终用于平台 T+5 日实盘行情回溯评测。

### Task 1：交易模式识别（无监督聚类任务）

| 项目 | 内容 |
|------|------|
| **核心目标** | 基于全量 Level-2 特征，对单日个股的交易行为进行无监督聚类，划分出具有显著区分度的交易模式，输出可解释的模式类型与业务说明 |
| **核心要求** | 聚类结果需满足「类内高聚合、类间高区分」，模式解释需贴合 A 股市场真实交易逻辑，无业务常识错误 |
| **输出文件** | `pattern_reco.csv`，固定 4 个字段，顺序不可修改：`stock_code`（股票代码）、`transaction_date`（交易日期）、`pattern_type`（交易模式类别）、`pattern_explanation`（交易模式详细说明） |
| **标签说明** | **`pattern_type` 可自由定义、不限个数**；评分侧重标签合理性与 `pattern_explanation` 可解释性。下文 Baseline 默认 **k=8** 并内置 **8 类候选名称**，仅为参考实现，非赛题硬性枚举。详见 [`官方答疑与提交说明.md`](./官方答疑与提交说明.md) |

### Task 2：资金类型与交易意图识别（无真值规则判别任务）

| 项目 | 内容 |
|------|------|
| **核心目标** | 基于 Level-2 数据特征，识别单日个股的主导资金类型，同时判断资金的核心交易意图 |
| **核心要求** | 资金类型仅可输出「游资/量化机构」两类，交易意图仅可输出「买入/卖出/T0交易」三类，严格匹配赛事指定分类 |
| **输出文件** | `predict_result.csv`，固定 4 个字段，顺序不可修改：`stock_code`、`transaction_date`、`capital_type`（主导资金类型）、`capital_intention`（资金交易意图） |

---

## 三、任务数据与数据集构成

### 原始数据字段构成

官方**样例**训练数据包含 **65 个核心字段**，覆盖四大类核心数据维度：

- 逐笔委托
- 逐笔成交
- 逐笔撤单
- 十档盘口快照

> **数据获取说明**：样例集仅 **1 只股票 × 1 天**；全量股票名单与 L2 明细由选手通过公开渠道自行获取。自采 API 数据的列名**不必**与样例 65 列一一对应，对齐下方 **7 大类特征集**即可。详见 [`官方答疑与提交说明.md`](./官方答疑与提交说明.md)。

### 官方参考特征集

赛事官方提供了 **7 大类**标准化参考特征集，是本次赛题的核心特征依据。所有特征均基于当日盘中可获取数据计算，**无未来函数风险**：

| # | 特征集 | 说明 |
|---|--------|------|
| 1 | **OSS** 大单分级特征 | 超大/大/中/小单的金额、笔数占比，游资基准占比等 |
| 2 | **RS** 订单时序特征 | 成交间隔变异系数、拆单相似度、订单爆发率、买卖间隔分化等 |
| 3 | **CB** 撤单系列特征 | 快速撤单占比、买卖撤单分化、撤单间隔变异系数等 |
| 4 | **AP** 主动成交特征 | 主动买卖占比、连续成交笔数、单边强度、净成交占比等 |
| 5 | **OBP** 盘口微观特征 | 最优档位挂单、价差穿越、挂单偏移、盘口失衡度等 |
| 6 | **PD** 价格发现特征 | 多维度价格冲击、盘口失衡、成交效率等 |
| 7 | **PI** 日内时段特征 | 开盘 30 分钟/尾盘 10 分钟成交占比、赫芬达尔集中度、价格波动等 |

---

## 四、任务规则及提交说明

### 提交格式要求

- 所有结果文件需打包为 `submit.zip` 压缩包，内部包含 `pattern_reco.csv` 和 `predict_result.csv` 两个文件，**不得嵌套文件夹**
- 两个 CSV 文件的字段顺序、名称必须与赛事要求完全一致，不得修改、新增、删除字段
- 资金类型仅可输出「游资/量化机构」，交易意图仅可输出「买入/卖出/T0交易」
- 所有结果需基于当日盘中可获取数据生成，**无未来函数**
- 编码格式为 **UTF-8-sig**，避免中文乱码，无空行、无缺失值
- A 榜即时反馈：`transaction_date` 须为**被预测交易日（昨日）**；答案约每日 18:00 更新，次日 08:00 前上传可得即时分（非最终成绩）。详见 [`官方答疑与提交说明.md`](./官方答疑与提交说明.md)

### 评分规则

**A/B 榜总得分 = 交易模式识别分 × 0.4 + 参与者识别分 × 0.6**

#### Task 1 交易模式识别（40%）

基于轮廓系数、CH 指数、Wasserstein 距离、DTW 时序距离四大指标，评估聚类的类内聚合度与类间区分度：

| 指标 | 说明 |
|------|------|
| 轮廓系数 | 衡量类内聚合度与类间区分度，取值范围 [-1, 1]，越接近 1 效果越好 |
| CH 指数 | 衡量类间方差与类内方差的比值，值越高聚类效果越好 |
| Wasserstein 距离 | 衡量不同交易模式的分布差异，距离越大区分度越好 |
| DTW 时序距离 | 衡量不同交易行为的时间序列差异，距离越大区分度越好 |

#### Task 2 资金类型识别（60%）

基于平台 T+5 日实盘回溯的真实资金标签，计算加权 F1-Score，评估分类准确率：

| 指标 | 说明 |
|------|------|
| 加权 F1-Score | 基于平台 T+5 日实盘回溯的真实标签计算，是分类任务的核心评分指标，越接近 1 效果越好 |
| 精确率（Precision） | 预测为某类资金的样本中，真实为该类的比例，衡量查准率 |
| 召回率（Recall） | 真实为某类资金的样本中，被正确预测的比例，衡量查全率 |

### 合规红线要求

1. **严禁使用未来函数**：所有特征、模型、规则仅可使用当日盘中可获取的 Level-2 数据，不得使用当日收盘后、未来交易日的任何数据
2. **严禁硬编码个股标签**：不得针对特定个股、特定日期设置固定的标签规则，所有规则需具备普适性
3. **严禁使用平台评测真值**：平台 T+5 日回溯的真实资金标签仅用于线上评分，严禁导入模型训练、规则优化环节，违者取消比赛成绩
4. **代码可复现性要求**：B 榜前 15 名队伍需提交完整项目代码，确保评审可完整复现结果，代码逻辑需与方案报告一致

---

# 第二部分：问题建模

## 五、赛题核心分析

### 赛事背景

本赛题是国内金融 AI 领域面向全量 Level-2 高频数据的机构资金识别专项赛事，核心解决 A 股市场中机构资金行为隐蔽、普通投资者无法穿透的行业痛点。本赛题希望参赛者基于 A 股个股的逐笔委托、逐笔成交、逐笔撤单和十档盘口快照数据（提示：可通过淘宝、闲鱼、百度网盘等渠道自行获取相关数据），构建一套完整方法论体系，对游资/量化两类机构进行精细化的区分，识别各类参与者的买卖方向、买卖意图。整体方法的技术手段不做强制要求，鼓励参赛者结合大模型等 AI 技术和经典量化模型给出更好的解决方案。

### 问题本质

本赛题的核心是**无监督场景下的金融时间序列数据挖掘与行为识别问题**，可拆解为两个相互耦合的子问题：

1. **Task 1 无监督聚类问题**：无任何标注标签，基于高维的 Level-2 时间序列特征，对单日个股的交易行为进行分簇，核心目标是最大化类内聚合度与类间区分度，同时为每个簇赋予可解释的业务含义
2. **Task 2 无真值规则判别问题**：无官方提供的训练标签，基于 A 股量化交易的行业常识与资金行为规律，构建多维度的量化打分规则，区分游资/量化机构两类资金，同时识别资金的交易意图，核心目标是最大化与实盘真实资金行为的匹配度

**核心难点**

- 高频 Level-2 数据维度高、噪声大，需要从海量数据中提取与机构交易行为强相关的有效特征
- 机构交易行为具有极强的隐蔽性，需要穿透拆单、对倒、虚假挂撤单等操作，识别真实的资金属性与意图
- 无任何标注标签，无法使用传统的有监督机器学习算法，所有方案需基于金融逻辑与无监督方法构建，同时保证可解释性

### Baseline 技术建模框架

Baseline 技术建模框架分为 4 个核心层级，从数据输入到结果输出形成完整闭环，全程无未来函数、无监督学习，完全贴合赛事要求：

```
原始 Level-2 数据输入（逐笔成交/委托/撤单/十档盘口）
        ↓
数据预处理层：数据清洗、时间标准化、JSON 盘口解析、异常值过滤、时序排序
        ↓
特征工程层：全量官方 7 大类参考特征提取 + 十档盘口衍生特征构建，按个股+交易日聚合为特征矩阵
        ↓
建模推理层
    ├ Task 1：多维全特征 KMeans 聚类（默认 k=8）→ 簇画像统计 → 多条件联合匹配 `pattern_type`（内置 8 类候选名）
    └ Task 2：11 维度归一化多因子打分 → 资金类型判定 + 盘口+主动成交联合规则识别交易意图
        ↓
结果输出层：格式校验、空值填充、编码标准化，生成赛事要求的两个 CSV 提交文件
```

---

## 六、任务分层拆解

Baseline 完整开发流程可拆解为 4 个核心层级：

### ① 数据理解层

| 项目 | 内容 |
|------|------|
| **目标** | 深入理解 Level-2 快照数据的结构和含义 |
| **关键动作** | 熟悉 65 个字段的业务含义（价格、累计成交量/额、盘口 JSON、时间戳等） |
| | 解析 `bids` 和 `asks` 的 JSON 数组结构，提取盘口深度、大单占比等信息 |
| **关键发现 1** | `volume`/`amount`/`transactions`/`bigordervolume` 均为**当日累计值**（从开盘累加到当前快照），需 `diff` 得到逐笔量 |
| **关键发现 2** | `date` 字段为 UTC 毫秒级时间戳，直接 `.dt.hour` 得到的是 UTC 小时（0–8），而 **`hh` 字段才是北京时间小时（8–16）**。必须使用 `hh` 做时段判定 |
| **关键发现 3** | `bigordervolume`、`changepercent`、`rangepercent` 等字段直接有值可用，无需重新计算 |

### ② 特征工程层

| 项目 | 内容 |
|------|------|
| **目标** | 从原始高频数据中提取对交易行为和资金流向有区分度的特征 |
| **关键动作** | 累计值转逐笔：`volume`/`amount`/`transactions`/`bigordervolume`.diff() |
| | OSS 大单分级：基于逐笔量按超大单/大单/中单/小单分级统计金额和笔数占比 |
| | TRD 交易结构：平均每笔交易量、交易量标准差、大单成交量占比、日内涨跌幅/振幅 |
| | RS 时序特征：成交间隔变异系数、拆单相似度、订单爆发率 |
| | AP 主动成交：基于价格变动判定主动买卖方向，统计主动买卖占比和连续笔数 |
| | PI 日内时段：开盘 30 分钟和尾盘 10 分钟的成交额占比（使用 `hh` 列的北京时间） |
| | PD 价格发现：价格冲击指标、订单簿不平衡比率 |
| | OBP 盘口特征（两套方案）：方案 A 从首条 bids/asks JSON 提取；方案 B 利用 `totalbidvolume`/`totalaskvolume` 等字段计算全天统计量 |

### ③ 模型构建层

| 项目 | 内容 |
|------|------|
| **目标** | 构建交易模式聚类和参与者识别的模型 |
| **Task 1** | KMeans 聚类（Baseline 默认 **k=8**，随样本数动态降级），基于簇画像多条件联合匹配（≥3 个条件命中才生效），映射为 Baseline **内置 8 类候选** `pattern_type`（赛题允许自定义标签） |
| **Task 2** | 11 维度多因子加权打分，正向维度（大额/单边/冲击/时段集中）得分越高越像游资，反向维度得分越高越像量化。意图采用双源盘口失衡度（首条快照+全天均值）与主动成交占比联合规则 |

### ④ 结果输出层

| 项目 | 内容 |
|------|------|
| **目标** | 按照赛题要求格式输出结果文件，并进行格式校验 |
| **输出** | `pattern_reco.csv`：`stock_code`, `transaction_date`, `pattern_type`, `pattern_explanation` |
| | `predict_result.csv`：`stock_code`, `transaction_date`, `capital_type`, `capital_intention` |
| **校验** | 字段顺序、合法值检查（`capital_type` 仅含游资/量化机构，`capital_intention` 仅含买入/卖出/T0交易） |
| **提交** | 打包为 `submit.zip` |

---

## 七、开发建议

1. **从简单开始**：先跑通 Baseline，理解数据流和任务目标，再逐步优化特征和模型
2. **重视特征工程**：高频数据的特征提取是核心，建议多尝试盘口微观结构特征（OFI、价差动态、大单冲击等）
3. **注意累计值转逐笔**：`volume`/`amount`/`transactions`/`bigordervolume` 均为累计值，直接使用会导致 OSS 分类错误
4. **注意时区问题**：`date` 字段是 UTC 时间戳，`hh` 字段是北京时间小时。时段判断**必须使用 `hh`**
5. **伪标签/规则质量**：Task 2 没有真实标签，规则设计的金融逻辑合理性直接影响模型效果
6. **代码可复现性**：固定随机种子，使用相对路径，代码注释充分，确保环境可复现
7. **善用已有字段**：训练数据中很多字段（如 `changepercent`、`rangepercent`、`bigordervolume`）已经直接有值，直接使用比重新计算更准确

---

## 八、解题思考过程

面对本赛题，完整的解题思考过程可分为以下 6 个核心步骤：

### 步骤 1：深度审题，明确核心要求与约束

1. 明确 Task 1 是无监督聚类任务，无任何标注标签，核心是「类内聚合、类间区分」，输出需要有明确的业务解释
2. 明确 Task 2 是无真值的规则判别任务，无官方训练标签，核心是贴合 A 股资金行为规律，输出严格匹配赛事指定的分类
3. 明确合规红线：严禁使用未来函数、严禁硬编码标签、严禁使用平台评测真值，所有结果需基于当日盘中数据生成
4. 明确提交格式：两个 CSV 文件的字段顺序、名称、编码必须完全符合要求，不得修改

### 步骤 2：数据探查，理解数据结构与业务含义

1. 查看原始数据的 65 个字段，区分基础信息、逐笔成交、盘口快照、行情统计四大类数据
2. 重点探查 `bids`/`asks` 十档盘口的 JSON 格式，明确数据结构，设计 JSON 解析逻辑
3. 查看数据的时间粒度、覆盖范围，明确「股票代码 + 交易日期」是最小的样本单元
4. 探查核心指标的分布特征，识别异常值，为后续的数据清洗和特征提取提供依据

### 步骤 3：核心问题拆解，方案选型

1. **数据预处理**：「读取 → 清洗 → 转换 → JSON 解析 → 排序」的标准化预处理流程
2. **特征工程**：基于官方 7 大类参考特征集，设计「官方特征全量落地 + 盘口衍生特征补充」的特征体系
3. **Task 1 聚类**：选择 KMeans 作为基础聚类算法；设计「多条件联合匹配」的模式命名逻辑
4. **Task 2 分类**：选择「多因子量化打分」方案，基于 A 股行业常识构建规则
5. **意图识别**：采用「主动成交 + 盘口失衡 + 资金类型」的联合规则

### 步骤 4：方案落地，全流程跑通

1. 编写数据预处理代码，验证 JSON 解析、格式转换的逻辑
2. 编写特征提取代码，生成特征矩阵
3. 编写 Task 1 聚类代码，验证聚类效果
4. 编写 Task 2 打分代码，验证规则的合理性
5. 编写结果输出代码，验证格式的合规性

### 步骤 5：效果评估，迭代优化

1. 聚类效果优化：调整聚类数、特征组合、距离度量方式
2. 分类规则优化：调整打分维度、权重配置、特征阈值
3. 特征工程优化：筛选有效特征，新增衍生特征
4. 逻辑优化：优化交易模式匹配规则、交易意图判定规则

### 步骤 6：方案整理，提交准备

1. 代码整理：模块划分清晰，注释充分，确保可复现
2. 文档整理：编写完整的方案报告
3. 提交文件校验：再次校验两个 CSV 文件的字段、格式、数据
4. 打包提交：将所有文件打包为 `submit.zip`

---

# 第三部分：Baseline 方案

## 九、Baseline 架构与代码

**架构**：特征工程（8 类 56 维）→ KMeans 聚类（Task 1）+ 多因子打分（Task 2）

**运行**

```bash
python main.py
python main.py --input data.xlsx
python main.py --input "data/*.xlsx" -o out/
```

**输出**：`pattern_reco.csv` / `predict_result.csv`

---

## 十、核心代码详解

本 Baseline 方案的代码分为 5 个核心模块：数据处理、特征提取、模型训练、结果预测、离线评估。

### 数据处理

核心代码位于 `load_and_preprocess()` 函数：

```python
def load_and_preprocess():
    df = pd.read_excel(INPUT_PATH, engine='openpyxl')
    # 日期时间标准化
    # 注意：date 字段为 UTC 毫秒级时间戳，hh 字段为北京时间（UTC+8）的小时数
    df['transaction_date'] = df['dt'].astype(str)
    df['datetime'] = pd.to_datetime(df['date'], unit='ms')
    df['hour'] = df['hh']  # 北京时间小时，用于 PI 日内时段特征
    df['minute'] = df['datetime'].dt.minute  # 分钟，UTC 和北京时区一致
    df = df.rename(columns={'symbol': 'stock_code'})
    # 异常值过滤
    df = df[(df['price'] > 0) & (df['volume'] >= 0) & (df['amount'] >= 0)]
    # 时序排序
    df = df.sort_values(by=['stock_code', 'transaction_date', 'datetime'])
    return df
```

**重要说明**

- `date` 字段为 UTC 毫秒级时间戳，通过 `pd.to_datetime(unit='ms')` 转换为 datetime（UTC 时间）
- **`hour` 必须使用 `df['hh']`（北京时间小时），而非 `df['datetime'].dt.hour`（UTC 小时）**。这是训练数据最关键的时区陷阱——UTC 小时为 0–8，而北京交易时间为 9:30–15:00。如果直接用 UTC 小时做时段判断，开盘 30 分钟（9:30–10:00）和尾盘 10 分钟（14:50–15:00）的条件永远无法匹配，导致 PI 特征全为 0
- `minute` 使用 `df['datetime'].dt.minute`，因为 UTC 和北京时间的分钟偏移量一致（都是整 8 小时）
- 按股票代码、交易日、时间戳排序后，`volume` 单调递增，`diff` 可正确得到逐笔量

### 特征提取

**累计值转逐笔量**

```python
group['tick_volume'] = group['volume'].diff().fillna(0).clip(lower=0)
group['tick_amount'] = group['amount'].diff().fillna(0).clip(lower=0)
group['tick_transactions'] = group['transactions'].diff().fillna(0).clip(lower=0)
if 'bigordervolume' in group.columns:
    group['tick_big_order_volume'] = group['bigordervolume'].diff().fillna(0).clip(lower=0)
```

**OSS 大单分级特征**

```python
# 阈值：超大单 ≥50000 股，大单 ≥10000 股，中单 ≥1000 股，小单 <1000 股
mega_mask = group['tick_volume'] >= 50000
large_mask = (group['tick_volume'] >= 10000) & (group['tick_volume'] < 50000)
mid_mask = (group['tick_volume'] >= 1000) & (group['tick_volume'] < 10000)
small_mask = group['tick_volume'] < 1000

feature['oss_mega_amount_pct'] = group.loc[mega_mask, 'tick_amount'].sum() / total_tick_amount
feature['oss_large_amount_pct'] = group.loc[large_mask, 'tick_amount'].sum() / total_tick_amount
```

**AP 主动成交特征**

```python
group['price_change'] = group['price'].diff()
active_buy_amt = group.loc[group['price_change'] > 0, 'tick_amount'].sum()
active_sell_amt = group.loc[group['price_change'] < 0, 'tick_amount'].sum()
feature['ap_active_buy_pct'] = active_buy_amt / (active_buy_amt + active_sell_amt)
feature['ap_active_sell_pct'] = active_sell_amt / (active_buy_amt + active_sell_amt)
```

**PI 日内时段特征（使用北京时间 `hh` 列）**

```python
# 开盘 30 分钟（9:30-10:00）
open_30min = group[
    ((group['hour'] == 9) & (group['minute'] >= 30)) |
    ((group['hour'] == 10) & (group['minute'] == 0))
]
# 尾盘 10 分钟（14:50-15:00）
close_10min = group[(group['hour'] == 14) & (group['minute'] >= 50)]
feature['pi_open_30min_amount_pct'] = open_30min['tick_amount'].sum() / total_tick_amount
feature['pi_close_10min_amount_pct'] = close_10min['tick_amount'].sum() / total_tick_amount
feature['pi_time_concentration'] = feature['pi_open_30min_amount_pct'] + feature['pi_close_10min_amount_pct']
```

**OBP 盘口特征（A/B 两套方案互补）**

```python
# 方案 A：从首条 bids/asks JSON 提取精确档位盘口特征
book_feature = get_book_feat(group['bids'].iloc[0], group['asks'].iloc[0])
feature.update(book_feature)

# 方案 B：利用 totalbidvolume/totalaskvolume 计算全天盘口统计量
total_bid = group['totalbidvolume'].values
total_ask = group['totalaskvolume'].values
imbalance_series = (total_bid - total_ask) / (total_bid + total_ask + 1e-8)
feature['obp_imbalance_mean'] = np.nanmean(imbalance_series)
feature['obp_imbalance_std'] = np.nanstd(imbalance_series)
```

### 模型训练

**Task 1 — KMeans + 多条件联合匹配**

```python
n_clusters_actual = min(N_CLUSTERS, n_samples)
kmeans = KMeans(n_clusters=n_clusters_actual, random_state=RANDOM_SEED, n_init=10)
df_feature['cluster_id'] = kmeans.fit_predict(X_scaled)

# 多条件联合匹配（≥3 个条件命中才生效）
# 游资强势连板拉升：超大单>12% + 买盘失衡>0.2 + 主动买入>55% + 时段集中>30%
if profile.get('oss_mega_amount_pct', 0) > 0.12: scores['游资强势连板拉升'] += 1
if profile.get('book_imbalance', 0) > 0.2: scores['游资强势连板拉升'] += 1
# ... 8 种模式共 30+ 条件

if max(scores.values()) >= 3:
    pattern_name = max(scores, key=scores.get)
else:
    pattern_name = '机构长线配置'  # 默认兜底
```

**Task 2 — 11 维多因子打分**

```python
dim_list = [
    ['oss_mega_amount_pct', 'oss_large_amount_pct'],  # 1. OSS 大额成交
    ['rs_split_similarity', 'rs_burst_ratio'],         # 2. RS 拆单时序
    ['cb_fast_cancel_ratio', 'cb_buy_cancel_ratio'],   # 3. CB 撤单分化
    ['ap_active_buy_pct', 'ap_active_net_pct'],        # 4. AP 主动单边
    ['spread', 'book_imbalance'],                      # 5. OBP 盘口
    ['pd_impact', 'pd_Q1_ratio'],                      # 6. PD 价格冲击
    ['pi_time_concentration', 'pi_price_std_pct'],     # 7. PI 时段波动
    ['ap_active_buy_run_max'],                         # 8. 连续买入
    ['big_bid_ratio', 'big_ask_ratio'],                # 9. 盘口大单
    ['cb_sell_cancel_ratio'],                          # 10. 卖出撤单
    ['ap_unilateral_intensity'],                       # 11. 单边强度
]

yz_like_dims = {0, 3, 5, 6}  # 游资倾向维度
return '游资' if score_yz >= score_qt else '量化机构'
```

### 结果预测

**意图判定（双源信号联合）**

```python
def get_intention(row):
    buy_pct = row.get('ap_active_buy_pct', 0.5)
    sell_pct = row.get('ap_active_sell_pct', 0.5)
    imbalance_snap = row.get('book_imbalance', 0)
    imbalance_mean = row.get('obp_imbalance_mean', 0)
    imbalance = 0.4 * imbalance_snap + 0.6 * imbalance_mean

    if buy_pct > 0.6 and imbalance > 0.08:
        return '买入'
    elif sell_pct > 0.6 and imbalance < -0.08:
        return '卖出'
    else:
        return 'T0交易'
```

### 离线评估

```python
sil_score = silhouette_score(X_scaled, df_feature['cluster_id'])
ch_score = calinski_harabasz_score(X_scaled, df_feature['cluster_id'])
db_score = davies_bouldin_score(X_scaled, df_feature['cluster_id'])

assert df_result['capital_type'].isin(['游资', '量化机构']).all()
assert df_result['capital_intention'].isin(['买入', '卖出', 'T0交易']).all()
```

---

## 十一、运行说明

### 环境要求

- Python >= 3.8
- pandas, numpy, scikit-learn, openpyxl

### 安装依赖

```bash
python3 -m pip install pandas numpy scikit-learn openpyxl
```

### 运行方式

```bash
python main.py
```

### 预期输出

```
【1/5】数据预处理开始
预处理完成 | 有效数据行数: 4937 | 覆盖股票数: 1
【2/5】全量特征提取开始
特征提取完成 | 总特征数: 52 维 | 总样本数: 1
【3/5】Task1 交易模式聚类开始
>>> 样本数 (1) < 预设聚类数 (8)，动态调整为 1
Task1 聚类完成 | 样本数不足，仅生成 1 个聚类
交易模式分布:
游资强势连板拉升    1
【4/5】Task2 资金与意图识别开始
Task2 识别完成
资金类型分布: 游资    1
交易意图分布: T0交易    1
【5/5】结果保存与离线评估开始
所有流程完成！
```

**说明**：训练数据仅 1 只股票 × 1 天，样本数为 1，聚类数自动降级为 1。A/B 榜有 100 只股票 × 多天，样本充足时 Baseline **默认 k=8** 可正常运行，各项评估指标可正常计算；`pattern_type` 最终标签策略见 [`官方答疑与提交说明.md`](./官方答疑与提交说明.md)。

### 输出文件

| 文件 | 字段 |
|------|------|
| `pattern_reco.csv` | `stock_code`, `transaction_date`, `pattern_type`, `pattern_explanation` |
| `predict_result.csv` | `stock_code`, `transaction_date`, `capital_type`, `capital_intention` |

---

## 十二、设计思路与核心逻辑

### 设计思路

本 Baseline 的设计思路是 **「特征工程先行，规则后模型，先简单后复杂」**：

1. **累计值转逐笔**：`volume`/`amount`/`transactions`/`bigordervolume` 均为累计值，必须 `diff` 后才能正确进行 OSS 大单分类
2. **时区处理**：`date` 字段为 UTC 时间戳，必须使用 `hh` 列（北京时间）进行时段判定，否则 PI 特征全为 0
3. **特征工程覆盖 8 大类**：参照赛题官方参考特征集，从快照数据中还原 OSS/TRD/RS/CB/AP/PI/PD/OBP 八类特征
4. **规则启发**：利用金融领域先验知识（游资激进、量化稳健）设计打分规则
5. **多条件联合匹配**：Task 1 的模式匹配采用 ≥3 个条件命中才生效的策略
6. **双源信号联合**：Task 2 的意图判定采用首条快照 + 全天均值的加权综合
7. **边界处理鲁棒**：支持少样本（聚类数动态降级）、缺失值填充、格式合法性校验

### 核心逻辑

1. **数据安全逻辑**：所有特征、规则、模型均基于当日盘中可获取数据，无未来函数、无跨日数据、无硬编码标签
2. **Task 1 核心逻辑**：数学聚类 → 全维度簇画像 → 多条件联合匹配 `pattern_type`（Baseline 内置 8 类候选；赛题不限标签个数）
3. **Task 2 核心逻辑**：11 维度归一化多因子打分，游资侧重大额成交、单边买入、盘口买盘失衡，量化机构侧重小单高频、拆单均匀、窄价差、多空均衡
4. **双任务联动逻辑**：Task 1 的聚类结果可反向校验 Task 2 的资金类型判定
5. **可解释性逻辑**：所有特征、规则、模式都有对应的金融逻辑解释，无黑箱模型
