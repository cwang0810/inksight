"""
ERROR 模式 - 错误显示
当服务不可用时显示错误信息
"""

from PIL import Image, ImageDraw
from .utils import SCREEN_W, SCREEN_H, EINK_BG, EINK_FG, load_font


def draw_warning_triangle(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 40):
    """Draw a warning triangle ⚠ centred at (cx, cy)."""
    half = size // 2
    # Outer triangle
    top = (cx, cy - half)
    bl = (cx - half, cy + half // 2 + 4)
    br = (cx + half, cy + half // 2 + 4)
    draw.polygon([top, bl, br], outline=EINK_FG)
    draw.polygon([top, bl, br], outline=EINK_FG)
    # Shift inward for second outline pass
    inset = 2
    top2 = (cx, cy - half + inset + 1)
    bl2 = (cx - half + inset + 1, cy + half // 2 + 4 - inset)
    br2 = (cx + half - inset - 1, cy + half // 2 + 4 - inset)
    draw.polygon([top2, bl2, br2], outline=EINK_FG)
    # Exclamation mark — vertical line
    draw.line([(cx, cy - 6), (cx, cy + 4)], fill=EINK_FG, width=2)
    # Exclamation mark — dot
    draw.rectangle([cx - 1, cy + 8, cx + 1, cy + 10], fill=EINK_FG)


def render_error(
    mac: str = "A1:B2:C3:D4", voltage: str = "3.25V", retry_min: int = 60
) -> Image.Image:
    """渲染错误页面"""
    img = Image.new("1", (SCREEN_W, SCREEN_H), EINK_BG)
    draw = ImageDraw.Draw(img)

    font_title = load_font("inter_medium", 16)
    font_detail = load_font("inter_medium", 11)
    font_info = load_font("inter_medium", 10)

    # Warning triangle icon
    icon_cy = SCREEN_H // 2 - 50
    draw_warning_triangle(draw, SCREEN_W // 2, icon_cy)

    # Title
    title = "Service Unavailable"
    bbox = font_title.getbbox(title)
    x = (SCREEN_W - (bbox[2] - bbox[0])) // 2
    draw.text((x, icon_cy + 34), title, fill=EINK_FG, font=font_title)

    # Detail
    detail = "Unable to reach InkSight cloud service."
    bbox2 = font_detail.getbbox(detail)
    x2 = (SCREEN_W - (bbox2[2] - bbox2[0])) // 2
    draw.text((x2, icon_cy + 62), detail, fill=EINK_FG, font=font_detail)

    # Device info line
    info = f"MAC: {mac}  |  {voltage}  |  Retry in {retry_min}min"
    bbox3 = font_info.getbbox(info)
    x3 = (SCREEN_W - (bbox3[2] - bbox3[0])) // 2
    draw.text((x3, icon_cy + 82), info, fill=EINK_FG, font=font_info)

    return img
