"""
create_icon.py
NIKKE スタイルのアプリアイコン（.ico）を生成する

デザイン:
  - ダークネイビー背景
  - ネオンシアンの照準リング
  - ネオンピンクのスコープ十字線
  - 中央に白のスタイライズド「N」

使い方:
  python create_icon.py
  → assets/icon.ico に保存される
"""
from __future__ import annotations

import math
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("[エラー] Pillow が必要です: pip install Pillow")
    raise


# ── カラーパレット ──
BG_COLOR    = (8,   8,  22, 255)   # ダークネイビー
CYAN        = (0,  210, 255)       # ネオンシアン（リング）
PINK        = (255, 30, 120)       # ネオンピンク（十字線）
WHITE_GLOW  = (210, 230, 255)      # 白（N 文字）
RING_DIM    = (0,  100, 160, 70)   # 内側の薄いリング


def _glow_circle(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int, radius: int,
    color: tuple, width: int, steps: int = 5,
) -> None:
    """グロー効果付きの円を描く（多重アルファ円で疑似グロー）。"""
    r, g, b = color
    for i in range(steps, 0, -1):
        a = int(200 * (i / steps) ** 2 * 0.45)
        ro = radius + (steps - i + 1) * 2
        draw.ellipse([cx - ro, cy - ro, cx + ro, cy + ro],
                     outline=(r, g, b, a), width=1)
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius],
                 outline=(r, g, b, 230), width=width)


def _glow_line(
    draw: ImageDraw.ImageDraw,
    p1: tuple, p2: tuple,
    color: tuple, width: int, steps: int = 3,
) -> None:
    """グロー効果付きのラインを描く。"""
    r, g, b = color
    for i in range(steps, 0, -1):
        a = int(200 * (i / steps) ** 2 * 0.35)
        w = width + (steps - i + 1) * 3
        draw.line([p1, p2], fill=(r, g, b, a), width=w)
    draw.line([p1, p2], fill=(r, g, b, 235), width=width)


def _draw_n(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int, size: int,
    color: tuple, stroke: int,
) -> None:
    """スタイライズド「N」を 3 本のラインで描く。"""
    h = int(size * 0.38)
    w = int(size * 0.28)
    s = stroke
    x1, x2 = cx - w // 2, cx + w // 2
    y1, y2 = cy - h // 2, cy + h // 2

    _glow_line(draw, (x1, y1), (x1, y2), color, s, steps=2)  # 左縦
    _glow_line(draw, (x1, y1), (x2, y2), color, s, steps=2)  # 斜め
    _glow_line(draw, (x2, y1), (x2, y2), color, s, steps=2)  # 右縦


def create_icon_image(size: int = 256) -> Image.Image:
    """指定サイズの NIKKE スタイルアイコン画像を生成する。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    s  = size
    cx = cy = s // 2

    # ── 角丸背景 ──
    mg = max(2, s // 20)
    draw.rounded_rectangle(
        [mg, mg, s - mg, s - mg],
        radius=s // 8,
        fill=BG_COLOR,
    )

    # ── 微細なグリッドライン（SF 感） ──
    grid_alpha = 18
    step = s // 8
    for i in range(0, s, step):
        draw.line([(i, mg), (i, s - mg)], fill=(30, 60, 120, grid_alpha), width=1)
        draw.line([(mg, i), (s - mg, i)], fill=(30, 60, 120, grid_alpha), width=1)

    # ── 外側リング（シアン） ──
    ring_r = int(s * 0.38)
    ring_w = max(3, s // 38)
    _glow_circle(draw, cx, cy, ring_r, CYAN, width=ring_w, steps=6)

    # ── 内側リング（薄いシアン） ──
    inner_r = int(s * 0.28)
    r2, g2, b2, a2 = RING_DIM
    draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
                 outline=(r2, g2, b2, a2), width=max(1, s // 72))

    # ── 十字スコープライン（ピンク） ──
    gap      = int(s * 0.065)   # リングとの隙間
    tick_out = int(s * 0.055)   # リング外の長さ
    tick_w   = max(2, s // 52)
    _glow_line(draw, (cx,          cy - ring_r - tick_out), (cx,          cy - ring_r + gap), PINK, tick_w)
    _glow_line(draw, (cx,          cy + ring_r + tick_out), (cx,          cy + ring_r - gap), PINK, tick_w)
    _glow_line(draw, (cx - ring_r - tick_out, cy), (cx - ring_r + gap, cy), PINK, tick_w)
    _glow_line(draw, (cx + ring_r + tick_out, cy), (cx + ring_r - gap, cy), PINK, tick_w)

    # ── 中央「N」 ──
    stroke = max(3, s // 26)
    _draw_n(draw, cx, cy, s, WHITE_GLOW, stroke)

    # ── 四隅のアクセントドット ──
    dot_r  = max(2, s // 52)
    offset = int(s * 0.14)
    dot_color = (*CYAN, 160)
    for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
        bx, by = cx + dx * offset, cy + dy * offset
        draw.ellipse([bx - dot_r, by - dot_r, bx + dot_r, by + dot_r],
                     fill=dot_color)

    return img


def make_ico(output_path: str | Path = "assets/icon.ico") -> None:
    """複数解像度を含む .ico ファイルを生成して保存する。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sizes   = [256, 128, 64, 48, 32, 16]
    base    = create_icon_image(256)
    images  = [base.resize((sz, sz), Image.LANCZOS) for sz in sizes]

    images[0].save(
        str(output_path),
        format="ICO",
        append_images=images[1:],
        sizes=[(sz, sz) for sz in sizes],
    )
    print(f"アイコン生成完了: {output_path}")


if __name__ == "__main__":
    make_ico()
