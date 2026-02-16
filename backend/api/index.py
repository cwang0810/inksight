from __future__ import annotations

import asyncio
import random
import traceback
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Response, Body
from fastapi.responses import HTMLResponse, JSONResponse

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from core.config import (
    SUPPORTED_MODES,
    DEFAULT_CITY,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_MODEL,
    DEFAULT_LANGUAGE,
    DEFAULT_CONTENT_TONE,
    DEFAULT_MODES,
)
from core.context import get_date_context, get_weather, calc_battery_pct
from core.content import (
    generate_content,
    generate_briefing_content,
    generate_artwall_content,
    generate_recipe_content,
    generate_fitness_content,
)
from core.config_store import (
    init_db,
    save_config,
    get_active_config,
    get_config_history,
    activate_config,
)
from core.cache import content_cache
from core.renderer import (
    render_mode,
    render_error,
    image_to_bmp_bytes,
    image_to_png_bytes,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="InkSight API", version="1.0.0", lifespan=lifespan)

# Debug mode: used by firmware to enable fast refresh (1 min) for testing
# Backend cache is always enabled regardless of this flag
DEBUG_MODE = False  # Set to False in production

_cycle_index: dict[str, int] = {}


# ── Mode resolution ──────────────────────────────────────────


def _choose_persona_from_config(config: dict, peek_next: bool = False) -> str:
    """Choose persona based on refresh strategy

    Args:
        config: User configuration
        peek_next: If True, return the NEXT persona without incrementing counter (for pre-generation)
    """
    modes = config.get("modes", DEFAULT_MODES)
    if not modes:
        modes = DEFAULT_MODES

    strategy = config.get("refresh_strategy", "random")
    print(
        f"[STRATEGY] refresh_strategy={strategy}, modes={modes}, peek_next={peek_next}"
    )

    if strategy == "cycle":
        mac = config.get("mac", "default")
        idx = _cycle_index.get(mac, 0)
        persona = modes[idx % len(modes)]
        if not peek_next:
            _cycle_index[mac] = idx + 1
            print(
                f"[CYCLE] {mac}: index {idx} → {idx + 1}, persona={persona}, modes={modes}"
            )
        return persona
    else:
        return random.choice(modes)


def _resolve_mode(
    mac: str | None, config: dict | None, persona_override: str | None
) -> str:
    """Determine which persona to use for this request."""
    if persona_override and persona_override.upper() in SUPPORTED_MODES:
        persona = persona_override.upper()
        print(f"[REQUEST] Using override persona: {persona}")
    elif config:
        persona = _choose_persona_from_config(config)
        mac_key = config.get("mac", "default")
        print(
            f"[REQUEST] Chosen persona: {persona}, mac_key={mac_key}, "
            f"current_index={_cycle_index.get(mac_key, 0)}"
        )
    else:
        persona = random.choice(["STOIC", "ROAST", "ZEN", "DAILY"])
        print(f"[REQUEST] No config, random persona: {persona}")
    return persona


# ── Content generation + rendering ───────────────────────────

# Mode-specific content generators (modes not using the generic generate_content)
_CUSTOM_GENERATORS = {
    "BRIEFING": lambda cfg: generate_briefing_content(
        llm_provider=cfg.get("llm_provider", DEFAULT_LLM_PROVIDER),
        llm_model=cfg.get("llm_model", DEFAULT_LLM_MODEL),
    ),
    "ARTWALL": lambda cfg, date_str="", weather_str="", festival="": generate_artwall_content(
        date_str=date_str,
        weather_str=weather_str,
        festival=festival,
        llm_provider=cfg.get("llm_provider", "aliyun"),
        llm_model=cfg.get("llm_model", "qwen-image-max"),
    ),
    "RECIPE": lambda cfg: generate_recipe_content(
        llm_provider=cfg.get("llm_provider", DEFAULT_LLM_PROVIDER),
        llm_model=cfg.get("llm_model", DEFAULT_LLM_MODEL),
    ),
    "FITNESS": lambda cfg: generate_fitness_content(
        llm_provider=cfg.get("llm_provider", DEFAULT_LLM_PROVIDER),
        llm_model=cfg.get("llm_model", DEFAULT_LLM_MODEL),
    ),
}


async def _render_for_persona(
    persona: str,
    config: dict | None,
    date_ctx: dict,
    weather: dict,
    battery_pct: float,
) -> "Image.Image":
    """Generate content for *persona* and render to an e-ink image."""
    date_str = date_ctx["date_str"]
    time_str = date_ctx.get("time_str", "")
    weather_str = weather["weather_str"]
    weather_code = weather.get("weather_code", -1)
    cfg = config or {}

    # Custom content generators for BRIEFING / ARTWALL / RECIPE / FITNESS
    if persona == "ARTWALL":
        content = await generate_artwall_content(
            date_str=date_str,
            weather_str=weather_str,
            festival=date_ctx.get("festival", ""),
            llm_provider=cfg.get("llm_provider", "aliyun"),
            llm_model=cfg.get("llm_model", "qwen-image-max"),
        )
    elif persona in _CUSTOM_GENERATORS:
        content = await _CUSTOM_GENERATORS[persona](cfg)
    else:
        # Standard modes: STOIC, ROAST, ZEN, DAILY (+ fallback)
        content = await generate_content(
            persona=persona,
            date_str=date_str,
            weather_str=weather_str,
            character_tones=cfg.get("character_tones", []),
            language=cfg.get("language", DEFAULT_LANGUAGE),
            content_tone=cfg.get("content_tone", DEFAULT_CONTENT_TONE),
            festival=date_ctx.get("festival", ""),
            daily_word=date_ctx.get("daily_word", ""),
            upcoming_holiday=date_ctx.get("upcoming_holiday", ""),
            days_until_holiday=date_ctx.get("days_until_holiday", 0),
            llm_provider=cfg.get("llm_provider", DEFAULT_LLM_PROVIDER),
            llm_model=cfg.get("llm_model", DEFAULT_LLM_MODEL),
        )

    return render_mode(
        persona,
        content,
        date_str=date_str,
        weather_str=weather_str,
        battery_pct=battery_pct,
        weather_code=weather_code,
        time_str=time_str,
        date_ctx=date_ctx,
    )


# ── Main orchestrator ────────────────────────────────────────


async def _build_image(v: float, mac: str | None, persona_override: str | None = None):
    battery_pct = calc_battery_pct(v)

    config = None
    if mac:
        config = await get_active_config(mac)

    persona = _resolve_mode(mac, config, persona_override)

    # Try cache first
    if mac and config:
        await content_cache.check_and_regenerate_all(mac, config, v)
        cached_img = await content_cache.get(mac, persona, config)
        if cached_img:
            print(f"[CACHE HIT] {mac}:{persona} - Returning cached image")
            return cached_img
        print(f"[CACHE MISS] {mac}:{persona} - Generating fallback content")

    # Cache miss — generate now
    city = config.get("city", DEFAULT_CITY) if config else None
    date_ctx, weather = await asyncio.gather(
        get_date_context(),
        get_weather(city=city),
    )

    img = await _render_for_persona(persona, config, date_ctx, weather, battery_pct)

    # Store in cache
    if mac and config:
        await content_cache.set(mac, persona, img)

    return img


# ── Render endpoints ─────────────────────────────────────────


@app.get("/api/render")
async def render(
    v: float = Query(default=3.3, description="Battery voltage"),
    mac: str | None = Query(default=None, description="Device MAC address"),
    persona: str | None = Query(default=None, description="Force persona"),
):
    import time

    start_time = time.time()
    print(f"[RENDER] Request started: mac={mac}, v={v}, persona={persona}")

    try:
        img = await _build_image(v, mac, persona)
        bmp_bytes = image_to_bmp_bytes(img)
        elapsed = time.time() - start_time
        print(
            f"[RENDER] ✓ Success in {elapsed:.2f}s - Generated BMP: {len(bmp_bytes)} bytes for {mac}:{persona}"
        )
        return Response(content=bmp_bytes, media_type="image/bmp")
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"[RENDER] ✗ Failed in {elapsed:.2f}s - Error: {e}")
        traceback.print_exc()
        err_img = render_error(mac=mac or "unknown")
        return Response(
            content=image_to_bmp_bytes(err_img), media_type="image/bmp", status_code=500
        )


@app.get("/api/preview")
async def preview(
    v: float = Query(default=3.3, description="Battery voltage"),
    mac: str | None = Query(default=None, description="Device MAC address"),
    persona: str | None = Query(default=None, description="Force persona"),
):
    try:
        img = await _build_image(v, mac, persona)
        png_bytes = image_to_png_bytes(img)
        print(f"[PREVIEW] Generated PNG: {len(png_bytes)} bytes")
        return Response(content=png_bytes, media_type="image/png")
    except Exception:
        traceback.print_exc()
        err_img = render_error(mac=mac or "unknown")
        return Response(
            content=image_to_png_bytes(err_img), media_type="image/png", status_code=500
        )


# ── Config endpoints ─────────────────────────────────────────


@app.post("/api/config")
async def post_config(body: dict = Body(...)):
    mac = body.get("mac")
    if not mac:
        return JSONResponse({"error": "mac is required"}, status_code=400)
    config_id = await save_config(mac, body)

    saved_config = await get_active_config(mac)
    if saved_config:
        print(
            f"[CONFIG VERIFY] Saved config id={saved_config.get('id')}, "
            f"refresh_strategy={saved_config.get('refresh_strategy')}"
        )

    return {"ok": True, "config_id": config_id}


@app.get("/api/config/{mac}")
async def get_config(mac: str):
    config = await get_active_config(mac)
    if not config:
        return JSONResponse({"error": "no config found"}, status_code=404)
    return config


@app.get("/api/config/{mac}/history")
async def get_config_hist(mac: str):
    history = await get_config_history(mac)
    return {"mac": mac, "configs": history}


@app.put("/api/config/{mac}/activate/{config_id}")
async def put_activate(mac: str, config_id: int):
    ok = await activate_config(mac, config_id)
    if not ok:
        return JSONResponse({"error": "config not found"}, status_code=404)
    return {"ok": True}


# ── Misc endpoints ───────────────────────────────────────────


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", response_class=HTMLResponse)
async def preview_page():
    html_path = Path(__file__).resolve().parent.parent.parent / "web" / "preview.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/config", response_class=HTMLResponse)
async def config_page():
    html_path = Path(__file__).resolve().parent.parent.parent / "web" / "config.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
