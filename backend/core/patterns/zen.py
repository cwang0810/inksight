"""
ZEN 模式 - 禅意
显示极简的汉字（如"静"、"空"）
"""

from PIL import Image, ImageDraw
from .utils import (
    SCREEN_W,
    SCREEN_H,
    EINK_BG,
    EINK_FG,
    draw_status_bar,
    draw_footer,
    load_font,
)
from ..config import FONT_SIZES


def render_zen(
    date_str: str,
    weather_str: str,
    battery_pct: int,
    word: str,
    weather_code: int = -1,
    time_str: str = "",
) -> Image.Image:
    """渲染 ZEN 模式"""
    img = Image.new("1", (SCREEN_W, SCREEN_H), EINK_BG)
    draw = ImageDraw.Draw(img)

    # Faded status bar with dashed separator
    draw_status_bar(
        draw,
        img,
        date_str,
        weather_str,
        battery_pct,
        weather_code,
        dashed=True,
        time_str=time_str,
    )

    # Large centered character — Regular weight (not bold), zen aesthetic
    font = load_font("noto_serif_regular", FONT_SIZES["zen"]["word"])
    bbox = font.getbbox(word)
    char_w = bbox[2] - bbox[0]
    char_h = bbox[3] - bbox[1]
    x = (SCREEN_W - char_w) // 2
    y = (SCREEN_H - char_h) // 2 - 10
    draw.text((x, y), word, fill=EINK_FG, font=font)

    # Faded footer with dashed separator, minimal attribution
    draw_footer(draw, img, "ZEN", "— ...", dashed=True)

    return img
