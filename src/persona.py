"""
麦门魂卡 —— 人格鉴定算法

输入：麦当劳历史订单（来自 MCP order-list / query-order）
输出：人格称号、段位、标签、口味雷达、鉴定文案

设计原则：
1. 数据要准 —— 所有结论都能回溯到订单里的真实数字
2. 梗要懂 —— 用麦门黑话，但不过度玩梗导致看不懂
3. 值得晒 —— 称号要有身份感，让人想截图发出去
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

# --------------------------------------------------------------------- 品类

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    ("汉堡", ["堡", "汉堡", "巨无霸", "麦香鱼", "麦香鸡", "吉士", "双牛", "辣腿堡", "牛堡"]),
    ("薯条", ["薯条", "薯格", "薯饼", "扭扭薯条"]),
    ("炸鸡", ["鸡腿", "鸡翅", "鸡块", "麦辣鸡", "脆皮", "炸鸡", "麦麦脆汁鸡"]),
    ("咖啡", ["咖啡", "美式", "拿铁", "卡布", "澳白", "馥芮白", "espresso", "麦咖啡"]),
    ("甜品", ["新地", "麦旋风", "甜筒", "冰淇淋", "冰激凌", "派", "蛋糕", "圆筒"]),
    ("早餐", ["早餐", "粥", "油条", "豆浆", "猪柳", "火腿扒", "热香饼", "炒蛋"]),
    ("饮料", ["可乐", "雪碧", "橙汁", "柠檬茶", "奶茶", "气泡水", "矿泉水", "果汁"]),
]

CATEGORY_ORDER = ["汉堡", "薯条", "炸鸡", "咖啡", "甜品", "早餐", "饮料"]

# 主魂：品类 -> 称号
SOUL_NAMES: dict[str, str] = {
    "汉堡": "堡垒守望者",
    "薯条": "薯条原教旨主义者",
    "炸鸡": "脆皮狂信徒",
    "咖啡": "咖啡续命工程师",
    "甜品": "甜蜜暴击收藏家",
    "早餐": "晨间能量启动器",
    "饮料": "快乐水管道工",
}

# 段位：按累计订单数
RANKS: list[tuple[int, str, str]] = [
    (100, "麦门永恒", "你的血液里已经流淌着冰可乐"),
    (50, "麦门圣徒", "麦门荣光与你同在"),
    (20, "麦门长老", "你已经超越了绝大多数信徒"),
    (5, "麦门信徒", "真信徒，无需多言"),
    (0, "麦门路人", "你与麦门的故事，才刚刚开始"),
]


def classify(name: str) -> str:
    """按餐品名归类，未命中则返回『其他』。"""
    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in name:
                return category
    return "其他"


# ------------------------------------------------------------------ 数据结构


@dataclass
class Item:
    name: str
    category: str
    qty: int = 1
    price: float = 0.0


@dataclass
class Order:
    order_id: str = ""
    created_at: datetime | None = None
    amount: float = 0.0
    items: list[Item] = field(default_factory=list)
    coupon_used: bool = False
    store_name: str = ""


@dataclass
class Persona:
    """人格鉴定结果。"""

    title: str                  # 人格称号
    rank: str                   # 段位
    rank_note: str              # 段位注脚
    tags: list[str]             # 行为标签
    radar: dict[str, int]       # 口味雷达（0-100）
    stats: dict[str, Any]       # 关键数据
    verdict: str                # 鉴定文案
    top_items: list[tuple[str, int]]


# ------------------------------------------------------------------ 归一化

# MCP 各工具返回字段命名可能不一致，这里尽量兼容常见写法
_TIME_KEYS = [
    "orderTime", "order_time", "createdAt", "created_at", "createTime",
    "create_time", "payTime", "pay_time", "time", "date",
]
_AMOUNT_KEYS = [
    "payAmount", "pay_amount", "totalAmount", "total_amount", "amount",
    "actualAmount", "actual_amount", "price", "total",
]


def _first(d: dict, keys: list[str], default=None):
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return default


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e11:  # 毫秒
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        s = value.strip().replace("Z", "")
        for fmt in (
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d",
        ):
            try:
                return datetime.strptime(s[:19], fmt)
            except ValueError:
                continue
    return None


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace("¥", "").replace(",", "").strip())
    except ValueError:
        return 0.0


def normalize_orders(raw: Any) -> list[Order]:
    """
    把 MCP 返回的原始数据归一化成 Order 列表。
    兼容 dict / list / 带 content 文本等多种返回形态。
    """
    if raw is None:
        return []

    # 若是字符串，尝试按 JSON 解析
    if isinstance(raw, str):
        try:
            raw = json_loads(raw)
        except Exception:
            return []

    records = _extract_records(raw)
    orders: list[Order] = []

    for rec in records:
        if not isinstance(rec, dict):
            continue
        order = Order(
            order_id=str(_first(rec, ["orderId", "order_id", "orderNo", "order_no", "id"], "")),
            created_at=_to_datetime(_first(rec, _TIME_KEYS)),
            amount=_to_float(_first(rec, _AMOUNT_KEYS, 0.0)),
            store_name=str(_first(rec, ["storeName", "store_name", "shopName", "shop_name"], "")),
            coupon_used=bool(_first(rec, ["couponUsed", "coupon_used", "useCoupon"], False)),
        )
        order.items = _extract_items(rec)
        if order.amount == 0.0 and order.items:
            order.amount = sum(i.price * i.qty for i in order.items)
        orders.append(order)

    orders.sort(key=lambda o: o.created_at or datetime.min)
    return orders


def json_loads(s: str):
    import json

    return json.loads(s)


def _extract_records(raw: Any) -> list[Any]:
    """从各种包装层里抽出订单记录数组。"""
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, dict):
        return []

    for key in ("orders", "orderList", "order_list", "list", "data", "result", "items"):
        val = raw.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            inner = _extract_records(val)
            if inner:
                return inner
    return [raw]


def _extract_items(rec: dict) -> list[Item]:
    raw_items = None
    for key in ("items", "itemList", "item_list", "products", "goods", "details", "mealList"):
        if isinstance(rec.get(key), list):
            raw_items = rec[key]
            break

    items: list[Item] = []
    for it in raw_items or []:
        if not isinstance(it, dict):
            continue
        name = str(_first(it, ["name", "itemName", "item_name", "productName", "goodsName", "title"], "")).strip()
        if not name:
            continue
        qty = int(_to_float(_first(it, ["qty", "quantity", "count", "num"], 1.0)) or 1)
        price = _to_float(_first(it, ["price", "amount", "total", "salePrice"], 0.0))
        items.append(Item(name=name, category=classify(name), qty=max(1, qty), price=price))
    return items


# ------------------------------------------------------------------ 人格计算


def _time_slot(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    h = dt.hour
    if 5 <= h < 10:
        return "早餐"
    if 10 <= h < 14:
        return "午餐"
    if 14 <= h < 17:
        return "下午茶"
    if 17 <= h < 22:
        return "晚餐"
    return "夜宵"


def build_persona(orders: list[Order], nutrition: dict[str, dict] | None = None) -> Persona:
    """根据订单数据算出完整人格。"""
    if not orders:
        return _empty_persona()

    total_orders = len(orders)
    total_amount = sum(o.amount for o in orders)
    total_items = sum(i.qty for o in orders for i in o.items)

    # ---- 品类分布
    cat_counter: Counter[str] = Counter()
    item_counter: Counter[str] = Counter()
    for o in orders:
        for i in o.items:
            cat_counter[i.category] += i.qty
            item_counter[i.name] += i.qty

    top_category = max(CATEGORY_ORDER, key=lambda c: cat_counter.get(c, 0)) if cat_counter else "汉堡"
    soul = SOUL_NAMES.get(top_category, "麦门野生信徒")
    top_items = item_counter.most_common(5)

    # ---- 段位
    rank, rank_note = "麦门路人", RANKS[-1][2]
    for threshold, name, note in RANKS:
        if total_orders >= threshold:
            rank, rank_note = name, note
            break

    # ---- 行为标签
    slot_counter: Counter[str] = Counter()
    for o in orders:
        slot = _time_slot(o.created_at)
        if slot:
            slot_counter[slot] += 1
    coupon_rate = sum(1 for o in orders if o.coupon_used) / total_orders

    tags: list[str] = []
    if coupon_rate >= 0.5:
        tags.append("麦麦省猎人")
    elif coupon_rate <= 0.1 and total_orders >= 3:
        tags.append("原价贵族")

    if slot_counter:
        dominant_slot = slot_counter.most_common(1)[0][0]
        if dominant_slot == "夜宵":
            tags.append("深夜食堂常客")
        elif dominant_slot == "早餐":
            tags.append("早餐战士")
        elif dominant_slot == "下午茶":
            tags.append("摸鱼下午茶搭子")

    if cat_counter.get("咖啡", 0) >= max(3, total_items * 0.25):
        tags.append("咖啡因依赖")
    if cat_counter.get("甜品", 0) >= max(2, total_items * 0.2):
        tags.append("甜食至上")
    if cat_counter.get("薯条", 0) >= max(3, total_items * 0.2):
        tags.append("薯条脑")
    if total_orders >= 30:
        tags.append("麦门常驻代表")

    # 至少给两个标签，避免卡片太空
    if not tags:
        tags = ["潜力信徒", "待开发魂"]
    tags = tags[:5]

    # ---- 口味雷达
    total_cat = sum(cat_counter.values()) or 1
    radar = {
        "罪恶度": min(100, int(cat_counter.get("汉堡", 0) / total_cat * 220)),
        "碳水值": min(100, int((cat_counter.get("薯条", 0) + cat_counter.get("汉堡", 0)) / total_cat * 180)),
        "肉食度": min(100, int((cat_counter.get("炸鸡", 0) + cat_counter.get("汉堡", 0)) / total_cat * 180)),
        "咖啡因": min(100, int(cat_counter.get("咖啡", 0) / total_cat * 260)),
        "甜度": min(100, int(cat_counter.get("甜品", 0) / total_cat * 280)),
    }
    # 让雷达图不至于全是 0，保留一点视觉存在感
    radar = {k: max(v, 8) for k, v in radar.items()}

    # ---- 时间跨度
    dated = [o.created_at for o in orders if o.created_at]
    first_at = min(dated) if dated else None
    last_at = max(dated) if dated else None
    days = (last_at - first_at).days + 1 if first_at and last_at else 0

    stats = {
        "订单总数": total_orders,
        "总消费": round(total_amount, 2),
        "餐品件数": total_items,
        "客单价": round(total_amount / total_orders, 2) if total_orders else 0,
        "首次下单": first_at.strftime("%Y-%m-%d") if first_at else "—",
        "最近下单": last_at.strftime("%Y-%m-%d") if last_at else "—",
        "麦龄": f"{days} 天" if days else "—",
        "最常出没": slot_counter.most_common(1)[0][0] if slot_counter else "—",
    }

    title = f"{soul}"
    verdict = _make_verdict(soul, rank, stats, top_items, coupon_rate)

    return Persona(
        title=title,
        rank=rank,
        rank_note=rank_note,
        tags=tags,
        radar=radar,
        stats=stats,
        verdict=verdict,
        top_items=top_items,
    )


def _make_verdict(
    soul: str,
    rank: str,
    stats: dict[str, Any],
    top_items: list[tuple[str, int]],
    coupon_rate: float,
) -> str:
    """生成有梗但不尬的鉴定文案。"""
    fav = top_items[0][0] if top_items else "神秘单品"
    fav_n = top_items[0][1] if top_items else 0

    line1 = f"经麦门数据中心鉴定：你共下单 {stats['订单总数']} 次，累计 {stats['总消费']} 元，麦龄 {stats['麦龄']}。"
    line2 = f"你的主魂为「{soul}」，段位「{rank}」——{stats['最常出没']}时段是你最常出没的时刻。"
    line3 = f"最爱的单品是「{fav}」，已回购 {fav_n} 次，这就是你的本命。"

    if coupon_rate >= 0.5:
        line4 = "你用券率超过五成，是麦麦省的资深猎人，每一分钱都花在刀刃上。"
    elif coupon_rate <= 0.1:
        line4 = "你几乎不用券，是麦门世界里少见的原价贵族，从容且体面。"
    else:
        line4 = "你在省钱与随心之间找到了平衡，是个懂生活的人。"

    return "\n".join([line1, line2, line3, line4])


def _empty_persona() -> Persona:
    return Persona(
        title="尚未觉醒的麦魂",
        rank="麦门路人",
        rank_note="还没有订单，去点一单试试吧",
        tags=["待开发魂"],
        radar={"罪恶度": 8, "碳水值": 8, "肉食度": 8, "咖啡因": 8, "甜度": 8},
        stats={
            "订单总数": 0, "总消费": 0, "餐品件数": 0, "客单价": 0,
            "首次下单": "—", "最近下单": "—", "麦龄": "—", "最常出没": "—",
        },
        verdict="没有检测到历史订单，无法完成鉴定。请授权后重试。",
        top_items=[],
    )
