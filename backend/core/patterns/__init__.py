"""
Patterns 包
每个模式一个文件，便于扩展和维护
"""

from .stoic import render_stoic
from .roast import render_roast
from .zen import render_zen
from .daily import render_daily
from .error import render_error
from .briefing import render_briefing
from .artwall import render_artwall
from .recipe import render_recipe
from .fitness import render_fitness
from .poetry import render_poetry
from .countdown import render_countdown

__all__ = [
    "render_stoic",
    "render_roast",
    "render_zen",
    "render_daily",
    "render_error",
    "render_briefing",
    "render_artwall",
    "render_recipe",
    "render_fitness",
    "render_poetry",
    "render_countdown",
]
