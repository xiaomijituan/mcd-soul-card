# 🤝 交接文档 —— mcd-soul-card 参赛推送与报名

> 本文档写给**接手的 Agent / 开发者**。
> 项目代码已全部完成并通过测试，剩下的都是「建仓库 → 推送 → 提交报名 Issue」三步。
> ⏰ **截榜时间：2026-10-25 23:59（北京时间）**，请优先完成前三步。

---

## 0. 一句话现状

| 项目 | 状态 |
|---|---|
| 产品代码 | ✅ 完成，79 项测试全通过 |
| 真实 MCP 调用 | ✅ 已验证（握手成功，35 个工具可用，160 餐品真实营养数据） |
| 本地 Git 仓库 | ✅ 已初始化，4 次提交 |
| **GitHub 远程仓库** | ❌ **未创建 —— 这是你要做的第一件事** |
| **报名 Issue** | ❌ **未提交 —— 这是你要做的最后一步** |
| 推广物料 | ✅ 已备好（`PROMO.md`） |

**项目路径**：`E:\AI\AgentData\WorkBuddyData\mcd-soul-card`
**目标仓库地址**：`https://github.com/xiaomijituan/mcd-soul-card`

**项目包含两个能力**：
1. **麦门魂卡** —— 读历史订单 → 鉴定麦门人格 → 出可分享卡片
2. **麦门营养教练** —— 用 160 个餐品真实营养数据 → 按减脂/增肌/省钱/解馋/加班推荐套餐

---

## 1. 第一步：创建远程仓库并推送

### 1.1 你需要什么

一个 **GitHub Personal Access Token**（PAT）。创建方法：

1. 打开 https://github.com/settings/tokens/new
2. **Note** 填 `mcd-soul-card`
3. **Expiration** 选 `30 days`
4. **Scopes** 勾选 `repo`（勾 `public_repo` 亦可）
5. 点 **Generate token** → **立刻复制**（只显示一次）

> Token 只用于本次推送，用完建议去 https://github.com/settings/tokens 撤销。
> 它**不要**写进仓库任何文件。

### 1.2 建仓库（API 方式，推荐）

```bash
export GH_TOKEN='你的PAT'

curl -X POST https://api.github.com/user/repos \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{
    "name": "mcd-soul-card",
    "description": "麦门魂卡：基于麦当劳 MCP 的麦门人格鉴定器，1024 程序员节参赛作品",
    "private": false,
    "has_issues": true,
    "auto_init": false
  }'
```

**必须** `private: false`（公开仓库），`has_issues: true`（要用来提交报名 Issue）。

### 1.3 推送

```bash
cd "E:/AI/AgentData/WorkBuddyData/mcd-soul-card"
git remote add origin https://github.com/xiaomijituan/mcd-soul-card.git
git push -u origin main
```

推送时 git 会提示输入 Username / Password：
- **Username**：`xiaomijituan`
- **Password**：粘贴 PAT（不是 GitHub 登录密码）

> 若不想明文传 PAT，可改用 SSH：把本机 `C:\Users\24563\.ssh\amc-agentmemory2026.pub`
> 的内容添加到 https://github.com/settings/keys 后用 SSH 地址推送。

### 1.4 验证

```bash
curl -s https://api.github.com/repos/xiaomijituan/mcd-soul-card | python -c "import json,sys;d=json.load(sys.stdin);print('private =',d.get('private'),'| default_branch =',d.get('default_branch'),'| url =',d.get('html_url'))"
```

必须看到 `private = False`。

---

## 2. 第二步：提交报名 Issue（最关键，格式很严）

### 2.1 官方活动仓库

https://github.com/M-China/mcd-developer-innovation-challenge

### 2.2 提交方式

**方式 A（网页，推荐）**：打开上面的 Issues → New issue → 选择官方模板 →
标题与正文按下面填 → Submit。

**方式 B（API）**：

```bash
export GH_TOKEN='你的PAT'

curl -X POST https://api.github.com/repos/M-China/mcd-developer-innovation-challenge/issues \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d '{"title":"【参赛申请】麦门魂卡 - 用麦当劳 MCP 鉴定你的麦门人格",
       "body":"【参赛申请】\n项目名称：麦门魂卡\n项目地址：https://github.com/xiaomijituan/mcd-soul-card\n项目简介：用麦当劳 MCP 读取你的历史订单，鉴定你的麦门人格（主魂/段位/行为标签/五维口味雷达），生成一张可分享的专属魂卡。零依赖实现，附网页版答5题即出卡。"}'
```

### 2.3 ⚠️ 格式红线（官方明确警告过）

官方原文：
> **报名Issue的【标题】和【正文】之间暂不要使用换行符，如【项目简介】和【项目简介内容】之间暂不要使用换行符**
> **项目地址链接暂不要使用 Markdown 格式组织文本**

也就是说：

```
标题：【参赛申请】麦门魂卡 - 用麦当劳 MCP 鉴定你的麦门人格
正文：【参赛申请】\n项目名称：麦门魂卡\n项目地址：https://github.com/xiaomijituan/mcd-soul-card\n项目简介：……
```

- 正文里**只用 `\n`**，不要有多余空行
- 项目地址**裸写**，不要写成 `[名称](url)`

### 2.4 验证报名成功

提交后官方机器人会在 Issue 下回复。**必须看到成功通知**才算报名成功。
如果回复失败，会说明原因 —— 按提示改完**重新提交一个新的 Issue**。

```bash
curl -s "https://api.github.com/repos/M-China/mcd-developer-innovation-challenge/issues?state=all&per_page=100" \
  -H "Authorization: Bearer $GH_TOKEN" | python -c "
import json,sys
for i in json.load(sys.stdin):
    if 'xiaomijituan' in (i.get('body') or '') or '麦门魂卡' in (i.get('title') or ''):
        print(i['number'], '|', i['title'], '|', i['state'], '| comments =', i['comments'])
"
```

---

## 3. 报名资格硬性条件（对照检查）

| 条件 | 状态 |
|---|---|
| 仓库为 **Public** | 建库时设 `private: false` |
| 含 `README.md` | ✅ |
| 含 `CONTEST_DECLARATION.md`（**内容不可改**） | ✅ 官方原文 |
| 含 `MCP_INTEGRATION.md` | ✅ |
| 含 `mcp-config.example.json`（仅占位符） | ✅ `${MCD_MCP_TOKEN}` |
| 含源代码 | ✅ `src/` |
| 含 `workbuddy.md`（WorkBuddy 专项奖励必需） | ✅ |
| 真实使用麦当劳 MCP | ✅ 已实测，详见 `workbuddy.md` |
| 仓库创建时间在 2025-12-25 ~ 2026-10-25 | ✅ 现在创建符合 |
| Issue 格式合规 | ⚠️ 严格按上面第 2.3 节 |

---

## 4. 提交后：冲 Star（这才是排名的唯一依据）

> 官方规则：**「比赛排名以 GitHub 上项目的 Star 数量为评判依据」**
> Star 数 > 0 才能进排行榜；前 100 名门槛约 **34 Star**；前三名约 **826 Star**。

现成的推广文案在 **`PROMO.md`**，含小红书 / V2EX / 掘金 / 朋友圈 / 短视频五个平台的成品文案。
README 首屏已放效果图 + 点 Star 引导语，网页版结果页也有引导按钮。

**执行顺序建议**：
1. 报名成功 → 立刻发小红书（转化最快）
2. 同日发 V2EX + 掘金
3. 每天固定时间重复发，换文案换图
4. 10-25 晚上做最后一轮「冲榜中，还差 XX 个 Star」

---

## 5. 项目结构速览

```
E:\AI\AgentData\WorkBuddyData\mcd-soul-card\
├── README.md                 项目门面（首屏效果图 + Star 引导）
├── CONTEST_DECLARATION.md    官方参赛声明（原文，未改动）
├── MCP_INTEGRATION.md        MCP 接入说明（Tool / 调用流程 / 业务价值）
├── mcp-config.example.json   脱敏配置（只有 ${MCD_MCP_TOKEN} 占位符）
├── workbuddy.md              WorkBuddy 开发上下文（专项奖励核验用）
├── SKILL.md                  Skill 定义
├── PROMO.md                  冲榜推广物料（5 平台文案）
├── HANDOVER.md               本文档
├── src/
│   ├── main.py               入口：拉取 → 归一化 → 算人格 → 出卡片
│   ├── mcp_client.py         MCP Streamable HTTP 客户端（零依赖，含多层响应解析）
│   ├── persona.py            人格算法（品类归类 / 段位 / 标签 / 雷达）
│   ├── nutrition.py          营养教练（营养表解析 / 分目标推荐 / 套餐组合 / 画像）
│   └── card.py               卡片渲染（HTML + SVG 雷达图 + 营养账本）
├── web/index.html            网页版（单文件，答 5 题出卡，离线可用）
├── tests/
│   ├── test_normalize.py     38 项断言
│   └── test_nutrition.py     41 项断言
└── images/demo_card.png      示例卡片图
```

---

## 6. 常用命令

```bash
cd "E:/AI/AgentData/WorkBuddyData/mcd-soul-card"

# 跑测试（79 项断言）
python tests/test_normalize.py
python tests/test_nutrition.py

# 演示模式出卡（订单用示例，营养数据走真实 MCP）
MCD_MCP_TOKEN=xxx python src/main.py --demo --out images/demo_card.html

# 真实数据出卡
MCD_MCP_TOKEN=xxx python src/main.py --out my_card.html

# 营养教练
MCD_MCP_TOKEN=xxx python src/main.py --coach 减脂
MCD_MCP_TOKEN=xxx python src/main.py --coach 增肌 --city 济南 --keyword 历下
```

**MCP Token 已在 `C:\Users\24563\.workbuddy\mcp.json` 中配置好**
（`mcd-mcp` → `https://mcp.mcd.cn` → Bearer），直接读该文件即可取用：

```python
import json, io, os
cfg = json.load(io.open(r'C:\Users\24563\.workbuddy\mcp.json', encoding='utf-8'))
os.environ['MCD_MCP_TOKEN'] = cfg['mcpServers']['mcd-mcp']['headers']['Authorization'].replace('Bearer ','').strip()
```

---

## 7. 已踩过的坑（别再踩）

| 坑 | 说明 |
|---|---|
| **MCP 返回是 Markdown 不是 JSON** | 真实数据在 `## Original Response` 之后，`mcp_client._extract_payload()` 已处理 |
| **JSON 后面还跟着说明文字** | `json.loads` 整体解析失败，改用 `raw_decode` 只取 JSON 前缀 |
| **`data` 字段本身是字符串化 JSON** | 需递归深度解析才能拿到真正的数组 |
| **说明文字里的 `data[].xxx` 会被误判** | 扫描 JSON 时只接受 `{` 开头且结果为 dict，否则 `[]` 会被当成空数组 |
| **字段名不能猜** | 真实字段是 `createTime` / `realTotalAmount` / `orderProductList[].productName`，不是 `orderTime`/`payAmount`/`items` |
| **套餐子项要展开** | `orderProductList[].comboItemList` 里的商品同样计入统计 |
| **已取消订单要过滤** | `orderStatus` 含「取消」的订单不计入人格统计 |
| **空 data 会造出假订单** | `{"data":{}}` 会被兜底成 1 条空订单，已用 `_ORDER_MARKERS` 修掉 |
| **时段标签平票会误判** | 必须占比 **> 50%** 才算「常驻」，否则标「多时段型」 |
| **营养数据不是 JSON** | 是 `[160]{字段}:` 的紧凑表格文本，需自行解析 |
| **推荐不能全局排序** | 必须按品类分层，否则减脂模式会把 0 千卡的饮料选成主食 |
| **门店查询要 city + keyword 同给** | `searchType=2` 时只给一个会返回 600058 |
| **门店菜单受营业时间限制** | 打烊时 `query-meals` 返回 600057，营养推荐必须能独立降级 |
| **官方账号无历史订单** | 当前 MCP Token 对应账号 `order-list` 返回空，**不是 bug**。营养/积分/优惠券等工具均有真实数据 |

---

## 8. 一页纸 Checklist

- [ ] 拿到 GitHub PAT
- [ ] 建公开仓库 `mcd-soul-card`（private=false, has_issues=true）
- [ ] `git push -u origin main`
- [ ] 验证仓库为 public
- [ ] 在官方仓库提交报名 Issue（**严格按 2.3 节的格式**）
- [ ] 确认机器人回复报名成功
- [ ] 抄 `PROMO.md` 的文案去小红书 / V2EX / 掘金发第一轮
- [ ] 盯着 Star 数增长

---

**祝冲榜顺利 🍔⭐**
