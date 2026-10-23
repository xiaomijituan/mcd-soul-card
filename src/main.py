"""
麦门魂卡 —— 主入口

用法：
    export MCD_MCP_TOKEN='你的Token'
    python src/main.py                 # 拉取真实订单，生成卡片
    python src/main.py --demo          # 用示例数据演示（无需 Token）
    python src/main.py --limit 50      # 限制拉取订单数
    python src/main.py --json out.json # 同时导出人格数据
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from card import render_card          # noqa: E402
from mcp_client import McDonaldMCP, MCPError  # noqa: E402
from persona import build_persona, normalize_orders  # noqa: E402

DEMO_ORDERS = [
    {
        "orderId": "DEMO001",
        "orderTime": "2026-03-11 08:12:00",
        "payAmount": 18.5,
        "items": [{"name": "猪柳蛋麦满分", "qty": 1, "price": 12.0},
                  {"name": "小杯美式", "qty": 1, "price": 6.5}],
        "couponUsed": True,
    },
    {
        "orderId": "DEMO002",
        "orderTime": "2026-05-02 12:38:00",
        "payAmount": 42.0,
        "items": [{"name": "巨无霸", "qty": 1, "price": 25.0},
                  {"name": "中份薯条", "qty": 1, "price": 11.0},
                  {"name": "中杯可乐", "qty": 1, "price": 9.0}],
        "couponUsed": False,
    },
    {
        "orderId": "DEMO003",
        "orderTime": "2026-07-19 23:41:00",
        "payAmount": 33.0,
        "items": [{"name": "麦辣鸡腿堡", "qty": 1, "price": 22.0},
                  {"name": "中份薯条", "qty": 1, "price": 11.0}],
        "couponUsed": True,
    },
    {
        "orderId": "DEMO004",
        "orderTime": "2026-08-30 15:20:00",
        "payAmount": 21.0,
        "items": [{"name": "大杯拿铁", "qty": 1, "price": 15.0},
                  {"name": "圆筒冰淇淋", "qty": 1, "price": 6.0}],
        "couponUsed": False,
    },
    {
        "orderId": "DEMO005",
        "orderTime": "2026-10-08 19:05:00",
        "payAmount": 56.0,
        "items": [{"name": "双层牛堡", "qty": 1, "price": 28.0},
                  {"name": "大份薯条", "qty": 1, "price": 13.0},
                  {"name": "麦旋风", "qty": 1, "price": 8.0},
                  {"name": "中杯可乐", "qty": 1, "price": 9.0}],
        "couponUsed": True,
    },
]


def fetch_orders(limit: int = 100):
    """通过 MCP 拉取历史订单。"""
    client = McDonaldMCP()
    client.initialize()

    raw = client.call("order-list", {"page": 1, "pageSize": limit})
    orders = normalize_orders(raw)

    # 若列表不含明细，则逐单补齐
    for order in orders:
        if order.order_id and not order.items:
            try:
                detail = client.call("query-order", {"orderId": order.order_id})
                patched = normalize_orders(detail)
                if patched and patched[0].items:
                    order.items = patched[0].items
            except MCPError:
                continue
    return orders, client


def summarize(persona) -> str:
    """终端可读的鉴定摘要。"""
    lines = [
        "",
        "=" * 46,
        f"  麦门魂卡 · 鉴定结果",
        "=" * 46,
        f"  人格称号：{persona.title}",
        f"  段位徽章：{persona.rank}",
        f"  行为标签：{' / '.join(persona.tags)}",
        "-" * 46,
    ]
    for k, v in persona.stats.items():
        lines.append(f"  {k:<8}: {v}")
    lines.append("-" * 46)
    lines.append("  本命单品：")
    for name, cnt in persona.top_items:
        lines.append(f"    · {name}  ×{cnt}")
    lines.append("=" * 46)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="麦门魂卡：用麦当劳 MCP 生成你的麦门人格卡")
    parser.add_argument("--demo", action="store_true", help="使用示例数据，无需 MCP Token")
    parser.add_argument("--limit", type=int, default=100, help="拉取订单数量上限")
    parser.add_argument("--out", default="mcd_soul_card.html", help="卡片输出路径")
    parser.add_argument("--json", dest="json_out", default="", help="同时导出人格数据 JSON")
    args = parser.parse_args()

    owner = os.getenv("GITHUB_OWNER", "mcd-soul-card")

    try:
        if args.demo:
            orders = normalize_orders(DEMO_ORDERS)
            print("[演示模式] 使用内置示例订单，未调用 MCP。")
        else:
            orders, _ = fetch_orders(args.limit)
            print(f"[MCP] 成功拉取 {len(orders)} 条历史订单。")

        persona = build_persona(orders)

        if orders:
            print(summarize(persona))
        else:
            print("[提示] 未获取到订单数据，已生成空白卡片。")

        path = render_card(persona, owner=owner, output_path=args.out)
        print(f"\n卡片已生成：{path}")

        if args.json_out:
            with open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "title": persona.title,
                        "rank": persona.rank,
                        "tags": persona.tags,
                        "radar": persona.radar,
                        "stats": persona.stats,
                        "top_items": persona.top_items,
                        "verdict": persona.verdict,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            print(f"数据已导出：{args.json_out}")

        return 0

    except MCPError as exc:
        print(f"\n[错误] {exc}", file=sys.stderr)
        print("提示：可用 --demo 先查看卡片效果。", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
