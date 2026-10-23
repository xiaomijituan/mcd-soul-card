"""
麦门魂卡 —— 卡片渲染

输出一张可直接分享的 HTML 卡片（含 SVG 雷达图），不依赖任何外部资源/网络，
可用浏览器或任意 HTML→图片工具导出为 PNG。

配色沿用麦当劳经典的红黄体系，保证一眼可辨。
"""

from __future__ import annotations

import html as _html
import math

RED = "#DA291C"
YELLOW = "#FFC72C"
DARK = "#1F1B16"
GRAY = "#8A8175"
BG_LIGHT = "#FFF8E7"


def _esc(text: str) -> str:
    return _html.escape(str(text))


def _radar_svg(radar: dict[str, int], size: int = 320) -> str:
    """手绘五维雷达图，返回 SVG 字符串。"""
    keys = list(radar.keys())
    values = [max(0, min(100, int(radar[k]))) for k in keys]
    n = len(keys)
    cx = cy = size / 2
    radius = size / 2 - 46

    def point(idx: int, ratio: float) -> tuple[float, float]:
        # 从正上方开始，顺时针排布
        angle = -math.pi / 2 + 2 * math.pi * idx / n
        return cx + radius * ratio * math.cos(angle), cy + radius * ratio * math.sin(angle)

    # 背景网格（4 圈）
    rings = ""
    for r in (0.25, 0.5, 0.75, 1.0):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, r) for i in range(n)))
        rings += (
            f'<polygon points="{pts}" fill="none" stroke="{GRAY}" '
            f'stroke-opacity="0.25" stroke-width="1"/>'
        )

    # 轴线
    axes = ""
    for i in range(n):
        x, y = point(i, 1.0)
        axes += (
            f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{GRAY}" stroke-opacity="0.25" stroke-width="1"/>'
        )

    # 数据多边形
    pts = " ".join(
        f"{x:.1f},{y:.1f}"
        for x, y in (point(i, values[i] / 100) for i in range(n))
    )
    dots = ""
    for i in range(n):
        x, y = point(i, values[i] / 100)
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{RED}"/>'

    # 维度标签
    labels = ""
    for i, key in enumerate(keys):
        x, y = point(i, 1.22)
        anchor = "middle"
        if x > cx + 8:
            anchor = "start"
        elif x < cx - 8:
            anchor = "end"
        labels += (
            f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="{anchor}" '
            f'font-size="15" font-weight="600" fill="{DARK}">{_esc(key)}</text>'
        )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        f"{rings}{axes}"
        f'<polygon points="{pts}" fill="{RED}" fill-opacity="0.22" '
        f'stroke="{RED}" stroke-width="2.5" stroke-linejoin="round"/>'
        f"{dots}{labels}</svg>"
    )


def render_card(persona, owner: str = "", output_path: str = "mcd_soul_card.html") -> str:
    """把人格结果渲染成一张 HTML 卡片，返回文件路径。"""

    tags_html = "".join(
        f'<span class="tag">{_esc(t)}</span>' for t in persona.tags
    )

    stats_html = ""
    primary = ["订单总数", "总消费", "餐品件数", "客单价"]
    for key in primary:
        val = persona.stats.get(key, "—")
        stats_html += (
            f'<div class="stat"><div class="stat-v">{_esc(val)}</div>'
            f'<div class="stat-k">{_esc(key)}</div></div>'
        )

    meta_html = "".join(
        f'<div class="meta"><span class="meta-k">{_esc(k)}</span>'
        f'<span class="meta-v">{_esc(v)}</span></div>'
        for k, v in persona.stats.items()
        if k not in primary
    )

    top_html = "".join(
        f'<li><span class="rk">{i}</span><span class="nm">{_esc(n)}</span>'
        f'<span class="qt">×{c}</span></li>'
        for i, (n, c) in enumerate(persona.top_items, 1)
    ) or '<li class="empty">暂无数据</li>'

    verdict_html = "<br>".join(_esc(l) for l in persona.verdict.split("\n"))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>麦门魂卡 · {_esc(persona.title)}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:{BG_LIGHT};
    font-family:"PingFang SC","Microsoft YaHei","Helvetica Neue",Arial,sans-serif;
    display:flex; justify-content:center; padding:24px;
  }}
  .card {{
    width:680px; background:#fff; border-radius:26px; overflow:hidden;
    box-shadow:0 18px 48px rgba(31,27,22,.14); border:3px solid {DARK};
  }}
  .head {{
    background:{RED}; color:#fff; padding:26px 30px 22px;
    display:flex; align-items:center; justify-content:space-between;
  }}
  .brand {{ font-size:13px; letter-spacing:3px; opacity:.9; font-weight:600; }}
  .badge {{
    background:{YELLOW}; color:{DARK}; font-size:13px; font-weight:800;
    padding:6px 14px; border-radius:999px; letter-spacing:1px;
  }}
  .title-wrap {{ padding:30px 30px 10px; text-align:center; }}
  .rank {{
    display:inline-block; background:{YELLOW}; color:{DARK};
    font-size:15px; font-weight:800; padding:7px 18px;
    border-radius:999px; margin-bottom:16px; letter-spacing:1px;
  }}
  .title {{
    font-size:40px; font-weight:900; color:{DARK};
    line-height:1.28; letter-spacing:1px;
  }}
  .note {{ margin-top:10px; font-size:14px; color:{GRAY}; }}
  .tags {{ padding:18px 30px 6px; display:flex; flex-wrap:wrap; gap:9px; justify-content:center; }}
  .tag {{
    background:{BG_LIGHT}; border:1.5px solid {YELLOW}; color:{DARK};
    font-size:13px; font-weight:700; padding:6px 13px; border-radius:999px;
  }}
  .stats {{ display:flex; padding:22px 20px 8px; }}
  .stat {{ flex:1; text-align:center; border-right:1px solid #EFE7D8; }}
  .stat:last-child {{ border-right:none; }}
  .stat-v {{ font-size:26px; font-weight:900; color:{RED}; }}
  .stat-k {{ font-size:12px; color:{GRAY}; margin-top:5px; }}
  .radar {{ display:flex; justify-content:center; padding:6px 0 4px; }}
  .body {{ padding:6px 30px 8px; }}
  .sec-t {{ font-size:14px; font-weight:800; color:{DARK}; margin:14px 0 10px; letter-spacing:1px; }}
  .meta {{ display:flex; justify-content:space-between; font-size:13px; padding:7px 0; border-bottom:1px dashed #EFE7D8; }}
  .meta-k {{ color:{GRAY}; }}
  .meta-v {{ color:{DARK}; font-weight:700; }}
  ol {{ list-style:none; }}
  ol li {{ display:flex; align-items:center; font-size:14px; padding:8px 0; border-bottom:1px dashed #EFE7D8; }}
  .rk {{ width:24px; height:24px; border-radius:8px; background:{RED}; color:#fff; font-size:12px; font-weight:800; display:flex; align-items:center; justify-content:center; margin-right:12px; }}
  .nm {{ flex:1; color:{DARK}; font-weight:600; }}
  .qt {{ color:{GRAY}; font-size:13px; }}
  .empty {{ color:{GRAY}; font-size:13px; }}
  .verdict {{
    margin:16px 0 4px; background:{BG_LIGHT}; border-left:5px solid {YELLOW};
    padding:16px 18px; border-radius:0 14px 14px 0;
    font-size:14px; line-height:1.85; color:{DARK};
  }}
  .foot {{
    background:{DARK}; color:#fff; padding:16px 30px;
    display:flex; justify-content:space-between; align-items:center; font-size:12px;
  }}
  .foot b {{ color:{YELLOW}; }}
</style>
</head>
<body>
<div class="card">
  <div class="head">
    <div>
      <div class="brand">MCD SOUL CARD</div>
      <div style="font-size:20px;font-weight:900;margin-top:4px;">麦门魂卡</div>
    </div>
    <div class="badge">1024 限定</div>
  </div>

  <div class="title-wrap">
    <div class="rank">{_esc(persona.rank)}</div>
    <div class="title">{_esc(persona.title)}</div>
    <div class="note">{_esc(persona.rank_note)}</div>
  </div>

  <div class="tags">{tags_html}</div>

  <div class="stats">{stats_html}</div>

  <div class="radar">{_radar_svg(persona.radar)}</div>

  <div class="body">
    <div class="sec-t">麦门档案</div>
    {meta_html}

    <div class="sec-t">本命单品 TOP 5</div>
    <ol>{top_html}</ol>

    <div class="sec-t">鉴定结论</div>
    <div class="verdict">{verdict_html}</div>
  </div>

  <div class="foot">
    <div>数据来自 <b>麦当劳 MCP</b> · 仅供参考，不构成营养建议</div>
    <div>{_esc(owner) if owner else "mcd-soul-card"}</div>
  </div>
</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
