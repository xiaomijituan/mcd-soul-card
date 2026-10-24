"""
mcd-soul-card 测试

运行：python tests/test_normalize.py

不依赖任何第三方库，也不调用真实 MCP（除非设置了 MCD_MCP_TOKEN）。
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from mcp_client import McDonaldMCP          # noqa: E402
from persona import build_persona, normalize_orders  # noqa: E402

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


# --------------------------------------------------------------- 真实响应样本
# 麦当劳 MCP Server 的响应是 Markdown 包装，真正数据在 ## Original Response 之后。
# 下面的样本按线上真实字段结构构造：
#   data.list[].orderId / createTime / orderStatus / realTotalAmount / storeName
#   data.list[].orderProductList[].productName / quantity / comboItemList
SAMPLE_MD = """# API Response Information

Below is the response from an API call.

## Response Structure

- **data.list[].orderId**: 订单编码 (Type: string)
- **data.list[].createTime**: 下单时间 (Type: string)
- **data.list[].orderStatus**: 订单状态 (Type: string)
- **data.list[].realTotalAmount**: 总金额 (Type: string)
- **data.list[].orderProductList[].productName**: 商品名称 (Type: string)

## Original Response
""" + json.dumps(
    {
        "success": True,
        "code": 200,
        "message": "请求成功",
        "data": {
            "list": [
                {
                    "orderId": "R001",
                    "createTime": "2026-08-11 08:12:00",
                    "orderStatus": "已完成",
                    "realTotalAmount": "38.50",
                    "storeName": "测试门店",
                    "orderProductList": [
                        {
                            "productCode": "C1",
                            "productName": "猪柳蛋麦满分",
                            "quantity": 1,
                            "comboItemList": [{"productName": "香煎饼", "quantity": 1}],
                        },
                        {"productCode": "C2", "productName": "中份薯条", "quantity": 1},
                    ],
                },
                {
                    "orderId": "R002",
                    "createTime": "2026-09-02 23:40:00",
                    "orderStatus": "已完成",
                    "realTotalAmount": "45.00",
                    "storeName": "测试门店",
                    "orderProductList": [
                        {"productName": "巨无霸", "quantity": 1},
                        {"productName": "中份薯条", "quantity": 1},
                        {"productName": "麦旋风", "quantity": 1},
                    ],
                },
                {
                    "orderId": "R003",
                    "createTime": "2026-10-01 12:00:00",
                    "orderStatus": "已取消",
                    "realTotalAmount": "20.00",
                    "storeName": "测试门店",
                    "orderProductList": [{"productName": "香辣鸡腿堡", "quantity": 1}],
                },
            ]
        },
    },
    ensure_ascii=False,
)


def test_markdown_extraction() -> None:
    print("\n[1] Markdown 包装响应提取")
    payload = McDonaldMCP._extract_payload(SAMPLE_MD)
    check("提取出 dict", isinstance(payload, dict), f"实际 {type(payload).__name__}")
    check("success 字段存在", isinstance(payload, dict) and payload.get("success") is True)
    check("能取到 data.list", isinstance(payload, dict) and len(payload["data"]["list"]) == 3)


def test_normalize() -> None:
    print("\n[2] 订单归一化")
    orders = normalize_orders(McDonaldMCP._extract_payload(SAMPLE_MD))
    check("已取消订单被过滤", len(orders) == 2, f"实际 {len(orders)}")
    check("按时间升序", orders and orders[0].order_id == "R001")

    o1 = orders[0]
    check("orderId 解析", o1.order_id == "R001")
    check("createTime 解析", o1.created_at is not None and o1.created_at.hour == 8)
    check("realTotalAmount 解析", o1.amount == 38.50, f"实际 {o1.amount}")
    check("storeName 解析", o1.store_name == "测试门店")
    check("orderProductList 解析", len(o1.items) == 3, f"实际 {len(o1.items)}")
    check(
        "套餐子项被展开",
        any(i.name == "香煎饼" for i in o1.items),
        f"实际 {[i.name for i in o1.items]}",
    )


def test_classify() -> None:
    print("\n[3] 品类归类")
    from persona import classify

    cases = {
        "巨无霸": "汉堡",
        "麦辣鸡腿汉堡": "汉堡",
        "中份薯条": "薯条",
        "麦辣鸡腿堡": "汉堡",   # 麦当劳菜单里它属于汉堡类，虽是炸鸡口味
        "麦辣鸡": "炸鸡",        # 不带「堡」的才是纯炸鸡
        "大杯拿铁": "咖啡",
        "麦旋风": "甜品",
        "猪柳蛋麦满分": "早餐",
        "中杯可乐": "饮料",
        "神秘汉堡": "汉堡",
    }
    for name, expect in cases.items():
        got = classify(name)
        check(f"{name} -> {expect}", got == expect, f"实际 {got}")


def test_persona() -> None:
    print("\n[4] 人格计算")
    orders = normalize_orders(McDonaldMCP._extract_payload(SAMPLE_MD))
    p = build_persona(orders)
    check("有人格称号", bool(p.title), f"实际 '{p.title}'")
    check("有段位", bool(p.rank))
    check("有行为标签", len(p.tags) > 0)
    check("雷达图五维", len(p.radar) == 5, f"实际 {len(p.radar)}")
    check("雷达值在 0-100", all(0 <= v <= 100 for v in p.radar.values()))
    check("有鉴定文案", len(p.verdict) > 20)
    check("本命单品有统计", len(p.top_items) > 0)
    check(
        "订单少时平票不误判时段标签",
        "深夜食堂常客" not in p.tags and "早餐战士" not in p.tags,
        f"实际 tags={p.tags}",
    )
    check("平票时最常出没标为多时段型", p.stats["最常出没"] == "多时段型", f"实际 {p.stats['最常出没']}")


def test_slot_tagging() -> None:
    print("\n[4b] 时段标签判定")
    # 3 单夜宵 + 1 单午餐 → 夜宵占比 75%，应打上「深夜食堂常客」
    night = [
        {
            "orderId": f"N{i}",
            "createTime": t,
            "orderStatus": "已完成",
            "realTotalAmount": "30.00",
            "orderProductList": [{"productName": "巨无霸", "quantity": 1}],
        }
        for i, t in enumerate(
            ["2026-09-01 22:30:00", "2026-09-05 23:10:00", "2026-09-09 01:20:00"]
        )
    ]
    night.append(
        {
            "orderId": "N9",
            "createTime": "2026-09-11 12:00:00",
            "orderStatus": "已完成",
            "realTotalAmount": "30.00",
            "orderProductList": [{"productName": "巨无霸", "quantity": 1}],
        }
    )
    p = build_persona(normalize_orders(night))
    check("夜宵主导时打标签", "深夜食堂常客" in p.tags, f"实际 tags={p.tags}")
    check("最常出没=夜宵", p.stats["最常出没"] == "夜宵", f"实际 {p.stats['最常出没']}")


def test_empty() -> None:
    print("\n[5] 空数据兜底")
    p = build_persona([])
    check("空订单不崩溃", p.title != "")
    check("雷达仍有五维", len(p.radar) == 5)
    check("给出提示文案", "没有检测到历史订单" in p.verdict)


def test_live_mcp() -> None:
    print("\n[6] 真实 MCP 连通（仅在配置了 Token 时执行）")
    if not os.getenv("MCD_MCP_TOKEN"):
        print("  ⏭  跳过（未设置 MCD_MCP_TOKEN）")
        return
    try:
        c = McDonaldMCP()
        c.initialize()
        tools = c.list_tools()
        check(f"握手成功，工具数={len(tools)}", len(tools) > 0)
        raw = c.call("order-list", {"page": 1, "pageSize": 10})
        check("order-list 调用成功", raw is not None)
        orders = normalize_orders(raw)
        check("归一化未报错", isinstance(orders, list))
        print(f"     当前账号历史订单数：{len(orders)}")
    except Exception as exc:  # noqa: BLE001
        check("真实 MCP 调用", False, f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    print("=" * 52)
    print("  mcd-soul-card 测试")
    print("=" * 52)
    test_markdown_extraction()
    test_normalize()
    test_classify()
    test_persona()
    test_slot_tagging()
    test_empty()
    test_live_mcp()
    print("\n" + "=" * 52)
    print(f"  通过 {PASS} · 失败 {FAIL}")
    print("=" * 52)
    sys.exit(1 if FAIL else 0)
