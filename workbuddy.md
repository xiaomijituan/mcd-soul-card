# WorkBuddy 开发对话上下文

> 本文件记录本项目使用腾讯 WorkBuddy 智能体完成开发的全过程，
> 用于核验「使用 WorkBuddy 开发参赛」的联动奖励条件。

---

## 一、项目信息

| 项目 | 内容 |
|---|---|
| 项目名称 | 麦门魂卡（mcd-soul-card） |
| 开发工具 | 腾讯 WorkBuddy 智能体 |
| 官网 | https://www.workbuddy.cn/ |
| 参赛赛事 | 麦当劳程序员创意开发大赛（1024 程序员节 · M-CODE） |
| 底层能力 | 麦当劳 MCP（`https://mcp.mcd.cn`） |

---

## 二、需求提出

用户通过微信收到活动推文（麦当劳 × WorkBuddy 联合举办「麦当劳程序员创意开发大赛」），
表示「我要参加」，希望通过 WorkBuddy 完成一个参赛作品。

**初始诉求**：
- 参加麦当劳程序员创意开发大赛
- 使用 WorkBuddy 开发
- 目标：冲榜拿奖

---

## 三、WorkBuddy 完成的调研工作

在动手写代码之前，WorkBuddy 先完成了完整的规则和竞争情报调研：

### 3.1 活动规则核实

- 抓取微信公众号原文（正文为 4 张图片，通过下载 + 图像识别完整转录）
- 定位到官方 GitHub 仓库：`https://github.com/M-China/mcd-developer-innovation-challenge`
- 拉取官方 `README.md` 与 `activityGuidelines.md` 原文，确认：
  - 活动时间：2026-10-09 10:30 至 2026-10-25 23:59
  - 定榜时间：2026-10-26 00:00
  - 排名依据：GitHub 公开 Star 数（Star > 0 才进入排行榜）
  - 必须文件清单：`README.md` / `CONTEST_DECLARATION.md` / `MCP_INTEGRATION.md` /
    `mcp-config.example.json` / 源代码 / `workbuddy.md`
  - Issue 报名的严格格式要求

### 3.2 MCP 能力清单

- 拉取 `mcd-mcp-server` 仓库文档，确认开放工具共 **33 个**
- 覆盖场景：菜单与营养查询、地址与门店、价格计算、下单与订单查询、
  优惠券、积分商城、抽奖、活动日历、团餐派对
- 实测端点 `https://mcp.mcd.cn`（无 Token 返回 403，确认需鉴权）

### 3.3 竞争情报

- 拉取官方 `RANKING.md`（更新于 2026-10-23 01:00:54）
- 关键数据：
  - 第 1 名：946 Star
  - 第 3 名：826 Star
  - 第 100 名门槛：**34 Star**
- 分析高 Star 项目的选题规律：省钱/优惠券类最热，趣味人格与年度报告类传播力最强

---

## 四、WorkBuddy 完成的设计与开发

### 4.1 产品定位

结合「传播力」与「可完成度」，选定方向：**年度报告 / 人格卡**。

核心创意：把订单数据翻译成有身份感、有梗、值得晒的「人格鉴定书」。

### 4.2 具体产出

| 文件 | 内容 |
|---|---|
| `src/mcp_client.py` | MCP Streamable HTTP 客户端，零依赖标准库实现，多层响应解析（Markdown 包装 / 嵌套 JSON 字符串 / JSON 后置说明） |
| `src/persona.py` | 人格鉴定算法：品类归类、段位分档、行为标签、口味雷达 |
| `src/nutrition.py` | 营养教练：营养表解析、餐品目录、按品类分层的五目标推荐、套餐组合、营养画像 |
| `src/card.py` | 卡片渲染：HTML + SVG 雷达图 + 营养账本模块，麦当劳红黄配色 |
| `src/main.py` | 主入口：串联 MCP 拉取 → 归一化 → 人格计算 → 卡片生成；另有 `--coach` 营养教练模式 |
| `web/index.html` | 网页版：单文件纯前端，答 5 题出卡，可保存图片 |
| `README.md` | 项目介绍、安装、使用示例、目标用户、实测踩坑清单 |
| `MCP_INTEGRATION.md` | MCP 接入说明：实际调用的 5 个 Tool、参数约束、调用流程、业务价值 |
| `CONTEST_DECLARATION.md` | 官方参赛声明原文 |
| `mcp-config.example.json` | 脱敏配置示例 |
| `SKILL.md` | Skill 定义 |
| `PROMO.md` | 冲榜推广物料（5 个平台成品文案） |
| `HANDOVER.md` | 参赛推送与报名交接文档 |
| `tests/test_normalize.py` | 38 项断言 |
| `tests/test_nutrition.py` | 41 项断言 |

### 4.3 技术决策

- **零依赖**：仅用 Python 标准库，clone 即可运行，无需 `pip install`
- **字段容错**：兼容 MCP 不同版本可能的字段命名差异
- **演示模式**：无 Token 也能出卡，降低传播门槛

---

## 五、真实 MCP 调用验证记录

WorkBuddy 在开发过程中已通过已配置的麦当劳 MCP 连接器完成**真实调用验证**，
以下为实测结果（Token 存放于 `~/.workbuddy/mcp.json` 的 `mcd-mcp` 配置项）：

| 验证项 | 实测结果 |
|---|---|
| MCP 握手 `initialize` | ✅ 成功 |
| `tools/list` | ✅ 返回 **35 个工具**（官方文档列出 33 个，线上已多出 `query-survey-coupon` 等） |
| `order-list` | ✅ 调用成功，返回 `{"success":true,"code":200}` |
| `list-nutrition-foods` | ✅ 返回 **160 个餐品**的真实营养数据（能量/蛋白质/脂肪/碳水/钠/钙） |
| `query-nearby-stores` | ✅ 返回 **5 家真实门店**（含 storeCode / 店名 / 地址 / 距离） |
| `query-meals` | ⚠️ 返回 `600057 门店可能已关闭或不在营业时间`（真实世界限制，非代码问题） |
| `query-my-account` | ✅ 返回账户积分等真实数据 |
| `mall-points-products` | ✅ 返回积分商城真实商品列表 |
| `campaign-calendar` | ✅ 返回活动日历 |
| `now-time-info` | ✅ 返回服务器时间 |

**响应格式的关键发现（踩坑记录）**：

麦当劳 MCP Server 的响应并非纯 JSON，而是 Markdown 包装：

```
# API Response Information
...
## Response Structure     <- 字段说明
## Original Response      <- 真正的 JSON 在这里
{"success":true,"code":200,"data":{...}}
```

且真实字段名为 `createTime` / `realTotalAmount` / `orderProductList[].productName`，
与直觉命名不同。`mcp_client._extract_payload()` 与 `persona.normalize_orders()`
针对这两点做了专门处理，并已固化为测试用例。

**当前账号历史订单为空**（`order-list` 返回 `data.list = []`），
因此人格鉴定走「无订单」分支；营养、积分、优惠券等能力均有真实数据支撑。

---

## 六、测试与质量

`tests/test_normalize.py` 共 **38 项断言，全部通过**，覆盖：

- Markdown 包装响应的 JSON 提取
- 真实字段名（`createTime` / `realTotalAmount` / `orderProductList`）解析
- 套餐子项（`comboItemList`）展开
- 已取消订单过滤
- 空 `data` 不产生假订单
- 品类关键词归类（汉堡/薯条/炸鸡/咖啡/甜品/早餐/饮料）
- 时段标签的平票不误判
- 雷达图数值范围
- 真实 MCP 连通性（设置 Token 时自动执行）

运行方式：

```bash
MCD_MCP_TOKEN=xxx python tests/test_normalize.py
```

---

## 七、开发过程中的问题修复记录

| # | 问题 | 修复 |
|---|---|---|
| 1 | 本机无 `requests`，项目无法直接运行 | 改用 Python 标准库 `urllib` 重写传输层，做到**零依赖** |
| 2 | MCP 返回 Markdown，`json.loads` 失败 | 新增 `_extract_payload()` 提取 `## Original Response` 后的 JSON |
| 3 | 部分工具的 JSON 后面还跟着说明文字 | 改用 `raw_decode` 只解析 JSON 前缀 |
| 4 | `data` 字段本身是字符串化 JSON | 新增 `_deep_parse()` 递归还原嵌套 JSON |
| 5 | 说明文字里的 `data[].xxx` 被误判成空数组 | 扫描时只接受 `{` 开头且结果为 dict |
| 6 | 字段名与直觉不符，取不到数据 | 归一化层兼容多组候选键名 |
| 7 | 套餐子项未计入统计 | 递归展开 `comboItemList` |
| 8 | 已取消订单被计入人格 | 按 `orderStatus` 过滤 |
| 9 | 空 `data` 被兜底成 1 条假订单 | 增加 `_ORDER_MARKERS` 校验 |
| 10 | 时段平票时误打「深夜食堂常客」 | 阈值改为占比严格 > 50%，否则标「多时段型」 |
| 11 | 雷达图右侧维度标签被裁切 | SVG 增加左右留白，标签半径比 1.22 → 1.18 |
| 12 | 营养数据是非 JSON 的紧凑表格文本 | 新增 `parse_nutrition_table()` 按 `[总数]{字段}:` 格式解析 |
| 13 | 减脂推荐把 0 千卡的饮料选成主食 | 改为**按品类分组、组内比较**，主食强制热量 > 200 |
| 14 | `query-nearby-stores` 返回 600058 | `searchType=2` 时 city 与 keyword 必须同时提供 |
| 15 | `query-meals` 打烊时不可用 | 定位为可选增强，核心推荐逻辑可独立降级 |

---

## 八、进行中的工作

- [x] 活动规则与竞争情报调研
- [x] 产品设计与算法实现
- [x] 真实 MCP 调用验证
- [x] 全部报名文件准备就绪
- [x] 交接文档 `HANDOVER.md`
- [ ] 创建 GitHub 公开仓库并推送（见 `HANDOVER.md`）
- [ ] 提交报名 Issue
- [ ] 冲榜推广（目标：进入排行榜前列）

---

## 九、开发工具说明

本项目全程使用**腾讯 WorkBuddy** 智能体开发：

- 使用 WorkBuddy 完成活动规则抓取、官方文档解析与竞争情报分析
- 使用 WorkBuddy 完成产品设计、算法实现与代码编写
- 使用 WorkBuddy 完成真实 MCP 连通性验证与缺陷修复
- 使用 WorkBuddy 完成仓库文件撰写、报名材料与推广物料准备

WorkBuddy 是本次麦当劳程序员创意开发大赛的**官方合作伙伴**。
