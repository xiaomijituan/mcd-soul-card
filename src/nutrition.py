"""
麦门营养教练

基于麦当劳 MCP 的真实营养数据（`list-nutrition-foods`）做套餐推荐。

设计要点：
1. 数据全部来自 MCP 真实返回，不内置任何硬编码餐品表
2. 门店菜单（`query-meals`）受营业时间限制，失败时自动降级，
   不影响营养推荐主流程 —— 这是实测踩过的坑
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from persona import classify

# --------------------------------------------------------------- 营养表解析


def parse_nutrition_table(raw) -> list[dict]:
    """
    解析 `list-nutrition-foods` 的返回。

    该接口返回的是紧凑表格文本而非 JSON：

        [160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
          猪柳麦满分,null,1288,308,16,16,24,781,213
          中薯条,null,1210,289,4,12,38,165,18

    返回 [{productName, energyKcal, protein, fat, carbohydrate, ...}, ...]
    """
    # 已经是对象列表（未来接口若改为 JSON）
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        inner = raw.get("data")
        if isinstance(inner, list):
            return [x for x in inner if isinstance(x, dict)]
        return []

    if not isinstance(raw, str):
        return []

    text = raw.strip()
    m = re.search(r"\{([^}]*)\}\s*:", text)
    if not m:
        return []
    fields = [f.strip() for f in m.group(1).split(",")]
    n = len(fields)
    if n < 3:
        return []

    body = text[m.end():]
    rows: list[dict] = []

    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("[") or line.startswith("{"):
            continue
        parts = line.split(",")
        if len(parts) < n:
            continue

        # 末尾 n-2 列固定是数值，前面的部分为「名称[,描述]」
        split_at = len(parts) - (n - 2)
        head, tail = parts[:split_at], parts[split_at:]

        name = head[0].strip()
        if not name:
            continue
        desc = head[1].strip() if len(head) > 1 else ""

        rec: dict = {fields[0]: name, fields[1]: ("" if desc == "null" else desc)}
        for i, fname in enumerate(fields[2:]):
            raw_val = tail[i].strip() if i < len(tail) else ""
            rec[fname] = _num(raw_val)
        rows.append(rec)

    return rows


def _num(v: str) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ------------------------------------------------------------------ 餐品模型


@dataclass
class Food:
    name: str
    kcal: float = 0.0
    protein: float = 0.0
    fat: float = 0.0
    carb: float = 0.0
    sodium: float = 0.0
    category: str = "其他"
    desc: str = ""

    @property
    def protein_per_kcal(self) -> float:
        """每 100 千卡的蛋白质克数 —— 减脂/增肌场景的关键指标。"""
        if self.kcal <= 0:
            return 0.0
        return self.protein / self.kcal * 100


def build_catalog(rows: list[dict]) -> list[Food]:
    foods: list[Food] = []
    for r in rows:
        name = str(r.get("productName") or "").strip()
        if not name:
            continue
        foods.append(
            Food(
                name=name,
                kcal=_num(r.get("energyKcal")),
                protein=_num(r.get("protein")),
                fat=_num(r.get("fat")),
                carb=_num(r.get("carbohydrate")),
                sodium=_num(r.get("sodium")),
                category=classify(name),
                desc=str(r.get("nutritionDescription") or ""),
            )
        )
    return foods


# ------------------------------------------------------------------ 目标定义


@dataclass
class Goal:
    key: str
    label: str
    brief: str
    sort_key: str = "balanced"
    limit: int = 5


GOALS: dict[str, Goal] = {
    "减脂": Goal("减脂", "减脂", "同等热量下蛋白质占比最高，碳水负担最小", "fatloss", 5),
    "增肌": Goal("增肌", "增肌", "单位热量蛋白质密度最高，扛饿又长肉", "muscle", 5),
    "省钱": Goal("省钱", "省钱", "小份单品，热量密度低，最能控制预算", "budget", 5),
    "解馋": Goal("解馋", "解馋", "热量不低但分量可控，罪恶感与满足感平衡", "cheat", 5),
    "加班": Goal("加班", "加班续命", "热量足、蛋白够，深夜顶得住", "late", 5),
}


def _score(f: Food, mode: str) -> float:
    """越小越优先（在同品类内部比较）。"""
    if mode == "fatloss":
        # 热量适中 + 蛋白质密度高
        return -(f.protein_per_kcal * 10) + abs(f.kcal - 420) * 0.35
    if mode == "muscle":
        # 蛋白质密度优先，热量可以稍高
        return -(f.protein_per_kcal * 12) + abs(f.kcal - 560) * 0.20
    if mode == "budget":
        # 小份优先
        small = 1.0 if any(w in f.name for w in ("小", "迷你")) else 0.0
        return f.kcal - small * 220
    if mode == "cheat":
        # 热量高 + 分量小
        small = 1.0 if any(w in f.name for w in ("小", "迷你", "派", "筒")) else 0.0
        return -(f.kcal * 0.8) + small * 350
    if mode == "late":
        return -(f.protein * 9 + f.kcal * 0.35)
    return f.kcal


def _group_by_category(foods: list[Food]) -> dict[str, list[Food]]:
    """按品类分组，组内按目标打分排序。"""
    groups: dict[str, list[Food]] = {}
    for f in foods:
        if f.kcal <= 0:
            continue
        groups.setdefault(f.category, []).append(f)
    return groups


def _pick(candidates: list[Food], goal_key: str, min_kcal: float = 0.0) -> Food | None:
    """从候选中挑一个最合适的。"""
    goal = GOALS.get(goal_key) or GOALS["减脂"]
    pool = [f for f in candidates if f.kcal >= min_kcal]
    if not pool:
        pool = list(candidates)
    if not pool:
        return None
    return min(pool, key=lambda f: (_score(f, goal.sort_key), f.kcal))


def recommend(foods: list[Food], goal_key: str) -> list[Food]:
    """按目标从真实营养数据中挑出推荐单品（跨品类各取最优）。"""
    groups = _group_by_category(foods)
    goal = GOALS.get(goal_key) or GOALS["减脂"]
    out: list[Food] = []
    for cat in ("汉堡", "炸鸡", "早餐", "薯条", "甜品", "咖啡", "饮料"):
        pool = groups.get(cat, [])
        if not pool:
            continue
        pick = _pick(pool, goal_key, min_kcal=30 if cat in ("汉堡", "炸鸡", "早餐") else 0)
        if pick is not None:
            out.append(pick)
    return out[: goal.limit]


def build_meal(foods: list[Food], goal_key: str) -> dict:
    """组一个套餐：主食 + 小食 + 饮品。全部基于真实营养数据计算。"""
    goal = GOALS.get(goal_key) or GOALS["减脂"]
    groups = _group_by_category(foods)

    mains = groups.get("汉堡", []) + groups.get("炸鸡", []) + groups.get("早餐", [])
    sides = groups.get("薯条", []) + groups.get("甜品", [])
    drinks = groups.get("咖啡", []) + groups.get("饮料", [])

    # --- 主食：必须有足够热量，不能是饮料充数
    main = _pick(mains, goal_key, min_kcal=200)
    if main is None:
        ranked = recommend(foods, goal_key)
        main = ranked[0] if ranked else None

    meal: list[Food] = [main] if main else []

    # --- 小食
    side = None
    if goal_key in ("减脂", "省钱"):
        smalls = [f for f in sides if any(w in f.name for w in ("小", "迷你"))]
        side = _pick(smalls, goal_key) or _pick(sides, goal_key)
    elif goal_key == "解馋":
        smalls = [f for f in sides if any(w in f.name for w in ("小", "迷你", "派", "筒"))]
        side = _pick(smalls, goal_key) or _pick(sides, goal_key)
    else:
        side = _pick(sides, goal_key)
    if side is not None:
        meal.append(side)

    # --- 饮品
    drink = None
    if goal_key == "加班":
        drink = _pick(groups.get("咖啡", []), goal_key) or _pick(drinks, goal_key)
    elif goal_key == "增肌":
        drink = _pick(drinks, goal_key, min_kcal=30)
    else:
        drink = _pick(drinks, goal_key, min_kcal=20)
    if drink is not None:
        meal.append(drink)

    meal = [f for f in meal if f is not None]

    total_kcal = sum(f.kcal for f in meal)
    total_protein = sum(f.protein for f in meal)
    total_fat = sum(f.fat for f in meal)
    total_carb = sum(f.carb for f in meal)
    total_sodium = sum(f.sodium for f in meal)

    return {
        "goal": goal,
        "items": meal,
        "total_kcal": round(total_kcal),
        "total_protein": round(total_protein),
        "total_fat": round(total_fat),
        "total_carb": round(total_carb),
        "total_sodium": round(total_sodium),
        "equivalents": _equivalents(total_kcal),
        "comment": _comment(goal_key, total_kcal, total_protein),
    }


def _equivalents(kcal: float) -> list[str]:
    """把热量换算成生活化参照物。"""
    out = []
    if kcal <= 0:
        return out
    if kcal / 139 >= 0.5:
        out.append(f"{kcal / 139:.1f} 罐可乐")
    if kcal / 250 >= 0.4:
        out.append(f"{kcal / 250:.1f} 份麦辣鸡腿堡")
    if kcal / 220 >= 0.4:
        out.append(f"{kcal / 220:.1f} 份薯条")
    return out


def _comment(goal_key: str, kcal: float, protein: float) -> str:
    pct = (protein * 4 / kcal * 100) if kcal else 0
    if goal_key == "减脂":
        return (
            f"这一套约 {kcal:.0f} 千卡、蛋白质 {protein:.0f} 克，"
            f"蛋白质供能占比 {pct:.0f}%。对控脂期来说相当克制 —— 吃得饱，热量没失控。"
        )
    if goal_key == "增肌":
        return (
            f"这一套约 {kcal:.0f} 千卡、蛋白质 {protein:.0f} 克，"
            f"蛋白质供能占比 {pct:.0f}%。练完后来这一套，合成原料是够的。"
        )
    if goal_key == "省钱":
        return f"这一套约 {kcal:.0f} 千卡，全是小份组合，是麦门里最省的吃法之一。"
    if goal_key == "解馋":
        return f"这一套约 {kcal:.0f} 千卡 —— 罪恶感有了，胃也舒服了，今天到此为止。"
    return f"这一套约 {kcal:.0f} 千卡、蛋白质 {protein:.0f} 克，深夜扛饿够用了。"


# ------------------------------------------------------------------ 营养画像


def nutrition_profile(orders, foods: list[Food]) -> dict:
    """
    用真实订单 + 真实营养表，算出用户的累计营养摄入画像。
    订单里匹配不到的餐品会被跳过，并统计匹配率（体现数据可靠性）。
    """
    by_name = {f.name: f for f in foods}
    matched = 0
    unmatched = 0
    total_kcal = total_protein = total_fat = total_carb = 0.0

    for o in orders:
        for it in o.items:
            food = _lookup(it.name, by_name)
            if food is None:
                unmatched += it.qty
                continue
            matched += it.qty
            total_kcal += food.kcal * it.qty
            total_protein += food.protein * it.qty
            total_fat += food.fat * it.qty
            total_carb += food.carb * it.qty

    total = matched + unmatched
    return {
        "matched": matched,
        "unmatched": unmatched,
        "match_rate": (matched / total) if total else 0.0,
        "total_kcal": round(total_kcal),
        "total_protein": round(total_protein),
        "total_fat": round(total_fat),
        "total_carb": round(total_carb),
        "equivalents": _equivalents(total_kcal),
    }


def _lookup(name: str, by_name: dict[str, Food]) -> Food | None:
    """按名称匹配营养数据：精确 → 去修饰词 → 包含。"""
    if name in by_name:
        return by_name[name]
    for mod in ("超值", "经典款", "尊享", "加长", "大份", "中份", "小份", "大", "中", "小"):
        if mod in name:
            trimmed = name.replace(mod, "").strip()
            if trimmed in by_name:
                return by_name[trimmed]
    for key, food in by_name.items():
        if key and (key in name or name in key):
            return food
    return None
