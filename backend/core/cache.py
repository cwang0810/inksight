from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Optional
from PIL import Image

from .config import (
    CACHEABLE_MODES,
    DEFAULT_CITY,
    DEFAULT_LANGUAGE,
    DEFAULT_CONTENT_TONE,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    DEFAULT_MODES,
)
from .context import get_date_context, get_weather, calc_battery_pct
from .content import generate_content
from .renderer import render_mode


class ContentCache:
    def __init__(self):
        self._cache: dict[str, tuple[Image.Image, datetime]] = {}
        self._lock = asyncio.Lock()

    def _get_cache_key(self, mac: str, persona: str) -> str:
        return f"{mac}:{persona}"

    def _get_ttl_minutes(self, config: dict) -> int:
        """Calculate cache TTL based on refresh interval and number of modes"""
        refresh_interval = config.get("refresh_interval", 60)
        modes = config.get("modes", DEFAULT_MODES)
        mode_count = len([m for m in modes if m in CACHEABLE_MODES])

        # TTL = refresh_interval × mode_count (complete one cycle)
        # Add 10% buffer to avoid edge cases
        ttl_minutes = int(refresh_interval * mode_count * 1.1)
        return ttl_minutes

    async def get(
        self, mac: str, persona: str, config: dict, ttl_minutes: int | None = None
    ) -> Optional[Image.Image]:
        """Get cached image if available and not expired"""
        async with self._lock:
            key = self._get_cache_key(mac, persona)
            if key in self._cache:
                img, timestamp = self._cache[key]
                if ttl_minutes is None:
                    ttl_minutes = self._get_ttl_minutes(config)
                if datetime.now() - timestamp < timedelta(minutes=ttl_minutes):
                    return img
                else:
                    print(f"[CACHE] {key} expired (TTL={ttl_minutes}min)")
                    del self._cache[key]
            return None

    async def set(self, mac: str, persona: str, img: Image.Image):
        """Store image in cache"""
        async with self._lock:
            key = self._get_cache_key(mac, persona)
            self._cache[key] = (img, datetime.now())

    async def check_and_regenerate_all(
        self, mac: str, config: dict, v: float = 3.3
    ) -> bool:
        """Check if all modes are cached, if not, regenerate all modes"""
        modes = [m for m in config.get("modes", DEFAULT_MODES) if m in CACHEABLE_MODES]

        if not modes:
            return False

        ttl_minutes = self._get_ttl_minutes(config)
        refresh_interval = config.get("refresh_interval", 60)
        mode_count = len(modes)
        print(
            f"[CACHE] TTL: {refresh_interval}min × {mode_count} modes × 1.1 = {ttl_minutes}min"
        )

        needs_regeneration = False
        for persona in modes:
            cached = await self.get(mac, persona, config, ttl_minutes)
            if not cached:
                needs_regeneration = True
                print(f"[CACHE] {mac}:{persona} missing or expired")
                break

        if not needs_regeneration:
            print(f"[CACHE] All {len(modes)} modes cached for {mac}")
            return True

        print(f"[CACHE] Regenerating all {len(modes)} modes for {mac}...")
        await self._generate_all_modes(mac, config, modes, v)
        return True

    async def _generate_all_modes(
        self, mac: str, config: dict, modes: list[str], v: float
    ):
        """Generate and cache all modes"""
        battery_pct = calc_battery_pct(v)
        city = config.get("city", DEFAULT_CITY)

        date_ctx, weather = await asyncio.gather(
            get_date_context(),
            get_weather(city=city),
        )

        tasks = [
            self._generate_single_mode(mac, persona, battery_pct, config, date_ctx, weather)
            for persona in modes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        print(f"[CACHE] ✓ Generated {success_count}/{len(modes)} modes for {mac}")

    async def _generate_single_mode(
        self,
        mac: str,
        persona: str,
        battery_pct: float,
        config: dict,
        date_ctx: dict,
        weather: dict,
    ) -> bool:
        """Generate and cache a single mode using the shared render_mode dispatcher."""
        try:
            print(f"[CACHE] Generating {mac}:{persona}...")

            date_str = date_ctx["date_str"]
            time_str = date_ctx.get("time_str", "")
            weather_str = weather["weather_str"]
            weather_code = weather.get("weather_code", -1)

            content = await generate_content(
                persona=persona,
                date_str=date_str,
                weather_str=weather_str,
                character_tones=config.get("character_tones", []),
                language=config.get("language", DEFAULT_LANGUAGE),
                content_tone=config.get("content_tone", DEFAULT_CONTENT_TONE),
                festival=date_ctx.get("festival", ""),
                daily_word=date_ctx.get("daily_word", ""),
                upcoming_holiday=date_ctx.get("upcoming_holiday", ""),
                days_until_holiday=date_ctx.get("days_until_holiday", 0),
                llm_provider=config.get("llm_provider", DEFAULT_LLM_PROVIDER),
                llm_model=config.get("llm_model", DEFAULT_LLM_MODEL),
            )

            img = render_mode(
                persona,
                content,
                date_str=date_str,
                weather_str=weather_str,
                battery_pct=battery_pct,
                weather_code=weather_code,
                time_str=time_str,
                date_ctx=date_ctx,
            )

            await self.set(mac, persona, img)
            print(f"[CACHE] ✓ {mac}:{persona}")
            return True

        except Exception as e:
            print(f"[CACHE] ✗ {mac}:{persona} failed: {e}")
            return False


# Global cache instance
content_cache = ContentCache()
