"""
营养模块测试

运行：python tests/test_nutrition.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from nutrition import (  # noqa: E402
    GOALS, build_catalog, build_meal, nutrition_profile, parse_nutrition_table,
    recommend,
)
from persona import normalize_orders  # noqa: E402

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


# 真实 list-nutrition-foods 返回的紧凑表格文本（原样截取）
REAL_TABLE = """[160]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  猪柳麦满分,null,1288,308,16,16,24,781,213
  猪柳蛋麦满分,null,1618,387,23,21,25,846,243
  中薯条,null,1210,289,4,12,38,165,18
  大薯条,null,1587,379,6,16,50,216,23
  小薯条,null,877,210,3,9,28,120,13
  迷你薯条,null,444,106,2,4,14,61,6
  麦乐鸡5块,null,890,213,12,12,13,422,9
  朱古力新地,null,1178,282,5,9,44,126,182
  圆筒冰淇淋,null,391,93,2,3,14,36,77
  大脆鸡扒麦满分,null,1510,361,16,17,35,804,130
  芝士双层安格斯厚牛堡,null,2926,700,58,46,60,1520,220
  原味板烧鸡腿炒双蛋堡,null,2190,419,27,21,30,1020,180
  卡布奇诺大杯,null,1165,223,13,10,20,110,190
  可乐大杯,null,1168,224,0,0,55,10,0
  雪碧小杯,null,394,76,0,0,19,4,0
  脆香油条,null,1056,202,5,12,19,320,20
"""


def test_parse() -> None:
    print("\n[1] 营养表解析")
    rows = parse_nutrition_table(REAL_TABLE)
    check("解析出行数", len(rows) == 16, f"实际 {len(rows)}")

    first = rows[0]
    check("名称正确", first["productName"] == "猪柳麦满分", f"实际 {first.get('productName')}")
    check("热量正确", first["energyKcal"] == 308, f"实际 {first.get('energyKcal')}")
    check("蛋白质正确", first["protein"] == 16, f"实际 {first.get('protein')}")
    check("碳水正确", first["carbohydrate"] == 24, f"实际 {first.get('carbohydrate')}")
    check("null 描述转空串", rows[0]["nutritionDescription"] == "")

    beef = [r for r in rows if r["productName"] == "芝士双层安格斯厚牛堡"][0]
    check("高热量单品数值正确", beef["energyKcal"] == 700 and beef["protein"] == 58)


def test_catalog() -> None:
    print("\n[2] 餐品目录")
    foods = build_catalog(parse_nutrition_table(REAL_TABLE))
    check("目录条目数", len(foods) == 16, f"实际 {len(foods)}")
    by_name = {f.name: f for f in foods}
    check("麦满分归类为早餐", by_name["猪柳蛋麦满分"].category == "早餐", f"实际 {by_name['猪柳蛋麦满分'].category}")
    check("带「堡」归类为汉堡", by_name["原味板烧鸡腿炒双蛋堡"].category == "汉堡", f"实际 {by_name['原味板烧鸡腿炒双蛋堡'].category}")
    check("薯条归类正确", by_name["中薯条"].category == "薯条")
    check("甜品归类正确", by_name["朱古力新地"].category == "甜品")
    check("饮料归类正确", by_name["可乐大杯"].category == "饮料")
    check("油条归类正确", by_name["脆香油条"].category == "早餐")


def test_recommend() -> None:
    print("\n[3] 分目标推荐")
    foods = build_catalog(parse_nutrition_table(REAL_TABLE))

    fat = recommend(foods, "减脂")
    check("减脂有推荐", len(fat) > 0)
    check("减脂首选是低热量高蛋白的", fat[0].kcal <= 450, f"实际 {fat[0].name} {fat[0].kcal}")

    muscle = recommend(foods, "增肌")
    check("增肌首选蛋白密度更高", muscle[0].protein_per_kcal > fat[0].protein_per_kcal,
          f"增肌 {muscle[0].protein_per_kcal:.1f} vs 减脂 {fat[0].protein_per_kcal:.1f}")

    budget = recommend(foods, "省钱")
    check("省钱推荐含小份", any("小" in f.name or "迷你" in f.name for f in budget),
          f"实际 {[f.name for f in budget]}")


def test_build_meal() -> None:
    print("\n[4] 套餐组合")
    foods = build_catalog(parse_nutrition_table(REAL_TABLE))

    meal = build_meal(foods, "减脂")
    check("套餐含主食", len(meal["items"]) >= 1)
    check("主食是主食类（热量 > 200）", meal["items"][0].kcal > 200, f"实际 {meal['items'][0].name}")
    check("减脂套餐热量 < 1000", meal["total_kcal"] < 1000, f"实际 {meal['total_kcal']}")
    check("合计等于各项之和", meal["total_kcal"] == round(sum(f.kcal for f in meal["items"])))
    check("有热量换算参照", isinstance(meal["equivalents"], list))
    check("有评价文案", len(meal["comment"]) > 10)

    cheat = build_meal(foods, "解馋")
    check("解馋套餐热量高于减脂", cheat["total_kcal"] > meal["total_kcal"],
          f"{cheat['total_kcal']} vs {meal['total_kcal']}")

    late = build_meal(foods, "加班")
    check("加班套餐蛋白更高", late["total_protein"] > meal["total_protein"],
          f"{late['total_protein']} vs {meal['total_protein']}")


def test_profile() -> None:
    print("\n[5] 营养画像（订单 × 营养表匹配）")
    foods = build_catalog(parse_nutrition_table(REAL_TABLE))
    orders = normalize_orders([
        {"orderId": "A1", "createTime": "2026-09-01 12:00:00", "orderStatus": "已完成",
         "realTotalAmount": "50", "orderProductList": [
             {"productName": "巨无霸", "quantity": 1},
             {"productName": "中薯条", "quantity": 1}]},
    ])
    p = nutrition_profile(orders, foods)
    check("有匹配计数", p["matched"] == 1, f"实际 {p['matched']}（巨无霸不在样本表内）")
    check("有未匹配计数", p["unmatched"] == 1)
    check("匹配率正确", abs(p["match_rate"] - 0.5) < 1e-6, f"实际 {p['match_rate']}")
    check("热量已累计", p["total_kcal"] == 289, f"实际 {p['total_kcal']}")


def test_goals() -> None:
    print("\n[6] 目标定义")
    check("五个目标齐全", len(GOALS) == 5, f"实际 {len(GOALS)}")
    for k in ("减脂", "增肌", "省钱", "解馋", "加班"):
        check(f"目标 {k} 存在", k in GOALS)
        check(f"目标 {k} 有说明", len(GOALS[k].brief) > 5)


if __name__ == "__main__":
    print("=" * 52)
    print("  mcd-soul-card 营养模块测试")
    print("=" * 52)
    test_parse()
    test_catalog()
    test_recommend()
    test_build_meal()
    test_profile()
    test_goals()
    print("\n" + "=" * 52)
    print(f"  通过 {PASS} · 失败 {FAIL}")
    print("=" * 52)
    sys.exit(1 if FAIL else 0)
