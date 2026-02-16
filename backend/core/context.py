from __future__ import annotations

import httpx
import random
from datetime import datetime
from zhdate import ZhDate
from .config import (
    WEEKDAY_CN,
    MONTH_CN,
    SOLAR_FESTIVALS,
    LUNAR_FESTIVALS,
    IDIOMS,
    POEMS,
    CITY_COORDINATES,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    OPEN_METEO_URL,
    HOLIDAY_WORK_API_URL,
    HOLIDAY_NEXT_API_URL,
)


def _resolve_city(city: str | None) -> tuple[float, float]:
    if not city:
        return DEFAULT_LATITUDE, DEFAULT_LONGITUDE
    coords = CITY_COORDINATES.get(city)
    if coords:
        return coords
    for name, c in CITY_COORDINATES.items():
        if name in city or city in name:
            return c
    return DEFAULT_LATITUDE, DEFAULT_LONGITUDE


async def get_holiday_info(date: datetime) -> dict:
    date_str = date.strftime("%Y-%m-%d")
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(HOLIDAY_WORK_API_URL, params={"date": date_str})
            resp.raise_for_status()
            result = resp.json()

            if result.get("code") == 200 and result.get("data"):
                data = result["data"]
                is_work = data.get("work", True)
                return {
                        "is_holiday": not is_work,
                        "holiday_name": "",
                        "is_workday": is_work,
                    }
            else:
                return {"is_holiday": False, "holiday_name": "", "is_workday": False}
    except Exception:
        return {"is_holiday": False, "holiday_name": "", "is_workday": False}


async def get_upcoming_holiday(now: datetime) -> dict:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(HOLIDAY_NEXT_API_URL)
            resp.raise_for_status()
            result = resp.json()

            if result.get("code") == 200 and result.get("data"):
                data = result["data"]
                holiday_date_str = data.get("date", "")

                if holiday_date_str:
                    from datetime import datetime as dt

                    holiday_date = dt.strptime(holiday_date_str, "%Y-%m-%d")
                    days_until = (holiday_date.date() - now.date()).days

                    return {
                        "days_until": days_until if days_until > 0 else 0,
                        "holiday_name": data.get("name", ""),
                        "date": holiday_date.strftime("%m月%d日"),
                        "holiday_duration": data.get("days", 0),
                    }
    except Exception:
        pass
    
    return {"days_until": 0, "holiday_name": "", "date": "", "holiday_duration": 0}


async def get_date_context() -> dict:
    now = datetime.now()
    day_of_year = now.timetuple().tm_yday
    days_in_year = (
        366
        if (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0))
        else 365
    )
    
    festival = SOLAR_FESTIVALS.get((now.month, now.day), "")
    
    try:
        lunar = ZhDate.from_datetime(now)
        lunar_festival = LUNAR_FESTIVALS.get((lunar.lunar_month, lunar.lunar_day), "")
        if lunar_festival and not festival:
            festival = lunar_festival
    except Exception:
        pass
    
    holiday_info = await get_holiday_info(now)
    if holiday_info["holiday_name"] and not festival:
        festival = holiday_info["holiday_name"]
    
    upcoming = await get_upcoming_holiday(now)
    
    daily_word = random.choice(IDIOMS + POEMS)
    
    return {
        "date_str": f"{now.month}月{now.day}日 {WEEKDAY_CN[now.weekday()]}",
        "time_str": f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}",
        "weekday": now.weekday(),
        "hour": now.hour,
        "is_weekend": now.weekday() >= 5,
        "year": now.year,
        "day": now.day,
        "month_cn": MONTH_CN[now.month - 1],
        "weekday_cn": WEEKDAY_CN[now.weekday()],
        "day_of_year": day_of_year,
        "days_in_year": days_in_year,
        "festival": festival,
        "is_holiday": holiday_info["is_holiday"],
        "is_workday": holiday_info["is_workday"],
        "upcoming_holiday": upcoming["holiday_name"],
        "days_until_holiday": upcoming["days_until"],
        "holiday_date": upcoming["date"],
        "daily_word": daily_word,
    }


async def get_weather(
    lat: float | None = None, lon: float | None = None, city: str | None = None
) -> dict:
    if lat is None or lon is None:
        lat, lon = _resolve_city(city)

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code",
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(OPEN_METEO_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            current = data["current"]
            return {
                "temp": round(current["temperature_2m"]),
                "weather_code": current["weather_code"],
                "weather_str": f"{round(current['temperature_2m'])}°C",
            }
    except Exception:
        return {"temp": 0, "weather_code": -1, "weather_str": "--°C"}


def calc_battery_pct(voltage: float) -> int:
    return int(voltage / 3.30 * 100)


def choose_persona(weekday: int, hour: int) -> str:
    import random

    return random.choice(["STOIC", "ROAST", "ZEN", "DAILY"])
