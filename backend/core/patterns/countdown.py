"""
COUNTDOWN 模式 - 重要日倒计时 / 正计日
纯日期计算，无需 LLM 调用
"""

import datetime
import logging
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

logger = logging.getLogger(__name__)


def render_countdown(
    date_str: str,
    weather_str: str,
    battery_pct: int,
    events: list[dict],
    weather_code: int = -1,
    time_str: str = "",
) -> Image.Image:
    """
    渲染 COUNTDOWN 模式

    Args:
        events: 事件列表 [{"name": str, "date": "YYYY-MM-DD", "type": "countdown"|"countup", "days": int}, ...]
                events should be pre-processed with "days" field computed.
    """
    img = Image.new("1", (SCREEN_W, SCREEN_H), EINK_BG)
    draw = ImageDraw.Draw(img)

    draw_status_bar(
        draw, img, date_str, weather_str, battery_pct, weather_code, time_str=time_str,
    )

    font_label = load_font("noto_serif_regular", 12)
    font_name = load_font("noto_serif_regular", 14)
    font_days_big = load_font("noto_serif_bold", 48)
    font_days_unit = load_font("noto_serif_regular", 14)
    font_small = load_font("noto_serif_light", 10)

    if not events:
        # Empty state
        msg = "暂无倒计时事件"
        bbox = draw.textbbox((0, 0), msg, font=font_label)
        mw = bbox[2] - bbox[0]
        draw.text(((SCREEN_W - mw) // 2, SCREEN_H // 2 - 10), msg, fill=EINK_FG, font=font_label)
        draw_footer(draw, img, "COUNTDOWN", "")
        return img

    y = 42

    # Show up to 3 events
    display_events = events[:3]

    if len(display_events) == 1:
        # Single event: large centered display
        evt = display_events[0]
        name = evt.get("name", "")
        days = evt.get("days", 0)
        evt_type = evt.get("type", "countdown")
        target_date = evt.get("date", "")

        y = 60

        # Event name
        bbox = draw.textbbox((0, 0), name, font=font_name)
        nw = bbox[2] - bbox[0]
        draw.text(((SCREEN_W - nw) // 2, y), name, fill=EINK_FG, font=font_name)
        y += 28

        # Prefix text
        if evt_type == "countdown":
            prefix = "\u8fd8\u6709"
            suffix = "\u5929"
        else:
            prefix = "\u5df2\u7ecf"
            suffix = "\u5929"

        bbox_p = draw.textbbox((0, 0), prefix, font=font_label)
        pw = bbox_p[2] - bbox_p[0]
        draw.text(((SCREEN_W - pw) // 2, y), prefix, fill=EINK_FG, font=font_label)
        y += 20

        # Large day number
        days_str = str(abs(days))
        bbox_d = draw.textbbox((0, 0), days_str, font=font_days_big)
        dw = bbox_d[2] - bbox_d[0]
        dh = bbox_d[3] - bbox_d[1]
        dx = (SCREEN_W - dw) // 2
        draw.text((dx, y), days_str, fill=EINK_FG, font=font_days_big)

        # "天" suffix next to number
        draw.text((dx + dw + 4, y + dh - 20), suffix, fill=EINK_FG, font=font_days_unit)
        y += dh + 16

        # Target date
        if target_date:
            bbox_t = draw.textbbox((0, 0), target_date, font=font_small)
            tw = bbox_t[2] - bbox_t[0]
            draw.text(((SCREEN_W - tw) // 2, y), target_date, fill=EINK_FG, font=font_small)

    else:
        # Multiple events: compact list
        y = 48

        draw.text((24, y), "\u91cd\u8981\u65e5\u5b50", fill=EINK_FG, font=font_label)
        y += 18
        draw.line([(24, y), (SCREEN_W - 24, y)], fill=EINK_FG, width=1)
        y += 14

        font_evt_name = load_font("noto_serif_regular", 13)
        font_evt_days = load_font("noto_serif_bold", 28)
        font_evt_unit = load_font("noto_serif_regular", 11)

        for evt in display_events:
            if y > SCREEN_H - 55:
                break

            name = evt.get("name", "")
            days = evt.get("days", 0)
            evt_type = evt.get("type", "countdown")
            target_date = evt.get("date", "")

            # Event name (left)
            draw.text((32, y), name, fill=EINK_FG, font=font_evt_name)

            # Days number (right-aligned)
            days_str = str(abs(days))
            label = "\u8fd8\u6709" if evt_type == "countdown" else "\u5df2\u7ecf"
            unit = "\u5929"

            bbox_d = draw.textbbox((0, 0), days_str, font=font_evt_days)
            dw = bbox_d[2] - bbox_d[0]
            bbox_u = draw.textbbox((0, 0), unit, font=font_evt_unit)
            uw = bbox_u[2] - bbox_u[0]

            right_x = SCREEN_W - 32
            draw.text((right_x - dw - uw - 4, y - 4), days_str, fill=EINK_FG, font=font_evt_days)
            draw.text((right_x - uw, y + 10), unit, fill=EINK_FG, font=font_evt_unit)

            y += 18

            # Target date and type label below
            meta = f"{label} \u00b7 {target_date}"
            draw.text((32, y), meta, fill=EINK_FG, font=font_small)

            y += 24

            # Dashed separator
            if evt != display_events[-1]:
                for x in range(32, SCREEN_W - 32, 6):
                    draw.line([(x, y), (min(x + 3, SCREEN_W - 32), y)], fill=EINK_FG, width=1)
                y += 10

    draw_footer(draw, img, "COUNTDOWN", "")

    return img
