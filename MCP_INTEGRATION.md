# MCP 接入说明

## 一、使用的 MCP Server

| 项目 | 内容 |
|---|---|
| 服务方 | 麦当劳中国（McDonald's China） |
| MCP Server | `mcd-mcp` |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 鉴权方式 | 请求头 `Authorization: Bearer <MCP Token>` |
| 官方文档 | https://github.com/M-China/mcd-mcp-server |
| Token 申请 | https://open.mcd.cn/mcp （手机号登录后，控制台激活） |

速率限制：每个 Token 每分钟最多 600 次请求，超限返回 `429`。
本项目的调用量远低于该阈值（一次生成魂卡通常 3～5 次请求）。

**实测**：握手成功，`tools/list` 返回 **35 个工具**（官方文档列出 33 个，
线上已额外提供 `query-survey-coupon` 等）。以下为本项目**实际调用**的工具。

---

## 二、实际调用的 Tools

### 1. `order-list` —— 获取历史订单列表

**入参**：`{ "page": 1, "pageSize": 100 }`

**产出**：`data.list[]`，每条含 `orderId` / `createTime` / `orderStatus` /
`realTotalAmount` / `storeName` / `orderProductList[]`。

**在本项目中的作用**：
- 订单总数 → 决定段位
- 累加 `realTotalAmount` → 总消费与客单价
- 解析 `createTime` → 判断常驻时段（早餐/午餐/下午茶/晚餐/夜宵）
- `orderStatus` → 过滤已取消订单
- `orderProductList[].comboItemList` → 展开套餐子项

---

### 2. `query-order` —— 查询订单详情

**入参**：`{ "orderId": "订单号" }`

**在本项目中的作用**：当 `order-list` 返回结果不含商品明细时逐单补齐，
支撑「本命单品 TOP 5」排行与品类归类。

---

### 3. `list-nutrition-foods` —— 餐品营养信息列表

**入参**：`{}`

**产出**：**160 个餐品**的真实营养数据（能量 kJ/kcal、蛋白质、脂肪、
碳水化合物、钠、钙）。

> ⚠️ 该接口返回的**不是 JSON**，而是紧凑表格文本：
> ```
> [160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
>   猪柳麦满分,null,1288,308,16,16,24,781,213
>   中薯条,null,1210,289,4,12,38,165,18
> ```
> 由 `src/nutrition.py` 的 `parse_nutrition_table()` 解析。

**在本项目中的作用**：
- 把订单中的餐品映射到营养数据，算出「麦门营养账本」（累计千卡 / 蛋白 / 碳水 / 脂肪）
- 为营养教练提供真实数据源，支撑减脂 / 增肌 / 省钱 / 解馋 / 加班五种目标的套餐推荐
- 换算生活化热量参照物（如「约等于 12.2 罐可乐」）

---

### 4. `query-nearby-stores` —— 查询附近可用门店

**入参**：`{ "beType": 1, "searchType": 2, "city": "济南", "keyword": "历下" }`

> ⚠️ 实测要点：`searchType=2`（按位置搜索）时 **city 与 keyword 必须同时提供**，
> 只给其一会返回 `600058 城市名或者关键词不能为空`。
> `searchType=1` 是「收藏餐厅」模式，账号无收藏时返回 `600050`。

**产出**：门店 `storeCode` / `storeName` / `address` / `distance`。

**在本项目中的作用**：为营养教练提供「参考门店」，让推荐结果落到具体店上。
**该步骤为可选增强**：失败或门店打烊时自动降级，不影响营养推荐主流程。

---

### 5. `query-meals` —— 查询当前可售卖的餐品列表

**入参**：`{ "storeCode": "3350157", "orderType": 1, "beType": 1 }`

> ⚠️ 实测要点：该接口**受门店营业时间限制**，非营业时段返回
> `600057 门店可能已关闭或不在营业时间`。因此本项目将其定位为可选增强，
> 核心推荐逻辑不依赖它。

**在本项目中的作用**：获取门店实时在售餐品与价格，可用于校准推荐结果。

---

## 三、调用流程

```
┌────────────────────────────────────────────────────────┐
│ 1. 读取环境变量 MCD_MCP_TOKEN                          │
│    （未配置则直接抛错，绝不硬编码）                     │
└──────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│ 2. MCP 握手                                          │
│    POST initialize (protocolVersion 2025-06-18)      │
│    ← 保存 Mcp-Session-Id                              │
│    POST notifications/initialized                    │
└──────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│ 3. 响应解析（两层）                                   │
│    Markdown 包装 → 提取 ## Original Response 后的 JSON │
│    递归深度解析 → 还原被字符串化的嵌套 JSON            │
│    raw_decode → 容忍 JSON 后跟随的说明文字             │
└──────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│ 4. 拉取数据                                          │
│    tools/call order-list       → 历史订单              │
│    tools/call query-order      → 补齐明细（按需）      │
│    tools/call list-nutrition-foods → 160 餐品营养数据 │
│    tools/call query-nearby-stores → 附近门店（可选）  │
│    tools/call query-meals      → 门店菜单（可选）      │
└──────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│ 5. 归一化                                           │
│    兼容多种字段命名 → 统一 Order / Item 结构          │
│    过滤已取消订单 · 展开套餐子项 · 匹配营养数据        │
└──────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────┐
│ 6. 计算与渲染                                       │
│    人格算法 → 主魂/段位/标签/雷达                      │
│    营养算法 → 画像/套餐推荐/热量换算                  │
│    渲染 → 可分享的 HTML 卡片（含 SVG 雷达图）         │
└──────────────────────────────────────────────────────┘
```

### 对应代码位置

| 步骤 | 文件 |
|---|---|
| Token 读取 / 握手 / 响应解析 / 工具调用 | `src/mcp_client.py` |
| 订单拉取与补齐 | `src/main.py` → `fetch_orders()` |
| 营养数据拉取 | `src/main.py` → `fetch_nutrition()` |
| 门店查询 | `src/main.py` → `fetch_nearby_stores()` |
| 数据归一化 | `src/persona.py` → `normalize_orders()` |
| 人格计算 | `src/persona.py` → `build_persona()` |
| 营养表解析 / 目录构建 | `src/nutrition.py` → `parse_nutrition_table()` / `build_catalog()` |
| 分目标推荐 / 套餐组合 | `src/nutrition.py` → `recommend()` / `build_meal()` |
| 营养画像 | `src/nutrition.py` → `nutrition_profile()` |
| 卡片渲染 | `src/card.py` |

---

## 四、业务价值

1. **把沉睡的订单数据变成情绪价值**
   历史订单原本只是消费记录，本项目将其转化为有身份感、有社交属性的「人格卡」，
   让数据产生二次价值。

2. **把营养表格变成能用的决策**
   麦当劳 MCP 提供了 160 个餐品的真实营养数据，本项目将其转化为
   「我想减脂，今天该吃什么」的可执行答案 —— 按品类分层比较，
   避免出现「把 0 千卡的饮料当主食」这类错误推荐。

3. **为麦当劳 MCP 提供可直接体验的应用示范**
   完整演示了 `order-list` / `query-order` / `list-nutrition-foods` /
   `query-nearby-stores` / `query-meals` 的组合用法，并记录了每一个真实的
   响应格式坑与参数约束，为其他开发者提供可复用的接入范式。

4. **天然的传播入口**
   卡片自带分享属性，用户晒卡即形成传播，反向为麦当劳 MCP 生态带来曝光。

---

## 五、安全与合规

- MCP Token **仅从环境变量 `MCD_MCP_TOKEN` 读取**，代码中不存在任何硬编码凭证。
- 仓库中的 `mcp-config.example.json` 仅含 `${MCD_MCP_TOKEN}` 占位符，不含真实密钥。
- 输出卡片不展示任何账号凭证或个人敏感信息。
- 项目为零依赖实现，仅使用 Python 标准库，避免供应链风险。
- 所有输出均标注「仅供参考，不构成营养或医疗建议」。

---

## 六、实测踩坑清单

开发过程中通过真实调用发现了以下问题，均已修复并固化为测试用例：

| 问题 | 现象 | 处理 |
|---|---|---|
| 响应是 Markdown 包装 | `json.loads` 直接失败 | 提取 `## Original Response` 后的 JSON |
| JSON 后面跟着说明文字 | 整体解析失败 | 改用 `raw_decode` 只取 JSON 前缀 |
| `data` 字段是字符串化 JSON | 取到的是 str | 递归深度解析 |
| 说明文字含 `data[].xxx` | 被误判为空数组 | 扫描时只接受 `{` 开头且结果为对象 |
| 字段名与直觉不符 | 取不到数据 | 归一化层兼容多组候选键名 |
| 套餐子项未计入 | 统计偏小 | 递归展开 `comboItemList` |
| 已取消订单被计入 | 人格失真 | 按 `orderStatus` 过滤 |
| 空 `data` 造出假订单 | 显示 1 单但全 0 | 增加 `_ORDER_MARKERS` 校验 |
| `query-nearby-stores` 参数 | 600058 | `searchType=2` 时 city 与 keyword 同给 |
| `query-meals` 600057 | 打烊时不可用 | 定位为可选增强，主流程可独立降级 |
| 营养数据非 JSON | 解析失败 | 按 `[总数]{字段}:` 格式自行解析 |
