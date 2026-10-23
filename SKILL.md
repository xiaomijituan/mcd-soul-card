---
name: mcd-soul-card
description: 麦门魂卡 —— 基于麦当劳 MCP 的历史订单数据，鉴定用户的麦门人格（主魂、段位、行为标签、口味雷达），生成一张可分享的专属卡片。当用户提到「麦门人格」「麦当劳年度报告」「我的麦当劳数据」「麦门魂卡」「测测我的麦门属性」「看看我吃了多少麦当劳」时使用。也可用于演示麦当劳 MCP（order-list / query-order / list-nutrition-foods）的组合调用范式。
version: 1.0.0
---

# 麦门魂卡（mcd-soul-card）

把用户沉睡的麦当劳订单，变成一张值得晒出去的人格卡。

---

## 前置条件

1. 已申请麦当劳 MCP Token：https://open.mcd.cn/mcp （手机号登录 → 控制台 → 激活）
2. 已配置环境变量：

```bash
export MCD_MCP_TOKEN='你的Token'
```

> Windows PowerShell 用：`$env:MCD_MCP_TOKEN='你的Token'`

3. 已在 WorkBuddy 中接入 MCP（连接器 → 自定义连接器 → 配置MCP）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

---

## 执行

```bash
cd mcd-soul-card
python src/main.py                              # 生成真实魂卡
python src/main.py --demo                       # 无 Token 演示
python src/main.py --out my.html --json d.json  # 指定输出并导出数据
```

输出：`mcd_soul_card.html`，浏览器打开即可查看与截图分享。

---

## 参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `--demo` | 用内置示例订单，不调用 MCP | 否 |
| `--limit` | 拉取订单数上限 | 100 |
| `--out` | 卡片输出路径 | `mcd_soul_card.html` |
| `--json` | 导出人格数据 JSON | 不导出 |

---

## 鉴定维度

| 输出 | 依据 |
|---|---|
| 主魂 | 品类件数占比最高的那一类 |
| 段位 | 累计订单数（5 / 20 / 50 / 100 分档） |
| 行为标签 | 时段分布、用券率、品类集中度 |
| 口味雷达 | 品类结构 + 营养数据加权（0–100） |
| 本命单品 | 回购次数 TOP 5 |

品类名：汉堡 / 薯条 / 炸鸡 / 咖啡 / 甜品 / 早餐 / 饮料 / 其他

---

## 错误处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `未检测到 MCD_MCP_TOKEN` | 环境变量未配置 | 配置后重试 |
| `401` | Token 无效或过期 | 重新申请 Token |
| `429` | 超过 600 次/分钟 | 降低 `--limit` 或稍后重试 |
| `403` | 请求被拒 | 确认 Token 已激活 |

---

## 合规

- Token 仅从环境变量读取，**禁止硬编码**进任何文件
- `mcp-config.example.json` 只保留 `${MCD_MCP_TOKEN}` 占位符
- 输出卡片不含任何凭证或敏感个人信息
- 输出仅供参考，**不构成营养或医疗建议**
