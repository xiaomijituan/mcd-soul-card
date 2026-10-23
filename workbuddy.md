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
| `src/mcp_client.py` | MCP Streamable HTTP 客户端，零依赖标准库实现，兼容 JSON 与 SSE 响应 |
| `src/persona.py` | 人格鉴定算法：品类归类、段位分档、行为标签、口味雷达 |
| `src/card.py` | 卡片渲染：HTML + SVG 雷达图，麦当劳红黄配色 |
| `src/main.py` | 主入口：串联 MCP 拉取 → 归一化 → 人格计算 → 卡片生成 |
| `web/index.html` | 网页版：单文件纯前端，答 5 题出卡，可保存图片 |
| `README.md` | 项目介绍、安装、使用示例、目标用户 |
| `MCP_INTEGRATION.md` | MCP 接入说明 |
| `CONTEST_DECLARATION.md` | 官方参赛声明原文 |
| `mcp-config.example.json` | 脱敏配置示例 |
| `SKILL.md` | Skill 定义 |

### 4.3 技术决策

- **零依赖**：仅用 Python 标准库，clone 即可运行，无需 `pip install`
- **字段容错**：兼容 MCP 不同版本可能的字段命名差异
- **演示模式**：无 Token 也能出卡，降低传播门槛

---

## 五、进行中的工作

- [ ] 申请并配置 MCP Token
- [ ] 用真实订单验证 MCP 调用链路
- [ ] 创建 GitHub 公开仓库并推送
- [ ] 通过指定 Issue 模板提交报名
- [ ] 冲榜推广（目标进入排行榜前列）

---

## 六、开发工具说明

本项目全程使用**腾讯 WorkBuddy** 智能体开发：

- 使用 WorkBuddy 完成活动规则抓取、官方文档解析与竞争情报分析
- 使用 WorkBuddy 完成产品设计、算法实现与代码编写
- 使用 WorkBuddy 完成仓库文件撰写与报名材料准备

WorkBuddy 是本次麦当劳程序员创意开发大赛的**官方合作伙伴**。
