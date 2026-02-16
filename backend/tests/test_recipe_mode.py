"""
测试 RECIPE 模式 - 早中晚三餐方案
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from core.content import generate_recipe_content
from core.patterns.recipe import render_recipe

load_dotenv()

CACHE_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "test_recipe_cache.json")


async def main():
    print("Testing RECIPE mode (早中晚三餐方案)...")
    
    if os.path.exists(CACHE_FILE):
        print(f"Loading cached recipe from {CACHE_FILE}...")
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            content = json.load(f)
        print("✓ Using cached data")
    else:
        print("Generating new meal plan...")
        content = await generate_recipe_content(
            llm_provider="deepseek",
            llm_model="deepseek-chat",
        )
        
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)
        print(f"✓ Cached to {CACHE_FILE}")
    
    print(f"\nGenerated content:")
    print(f"时令: {content['season']}")
    print(f"\n早餐: {content['breakfast']}")
    print(f"\n午餐:")
    print(f"  荤菜: {content['lunch']['meat']}")
    print(f"  素菜: {content['lunch']['veg']}")
    print(f"  主食: {content['lunch']['staple']}")
    print(f"  做法: {content['lunch']['steps']}")
    print(f"\n晚餐:")
    print(f"  荤菜: {content['dinner']['meat']}")
    print(f"  素菜: {content['dinner']['veg']}")
    print(f"  主食: {content['dinner']['staple']}")
    print(f"  做法: {content['dinner']['steps']}")
    print(f"\n营养: {content['nutrition']}")
    
    img = render_recipe(
        date_str="2月14日 周六",
        weather_str="晴 15°C",
        battery_pct=85,
        season=content["season"],
        breakfast=content["breakfast"],
        lunch=content["lunch"],
        dinner=content["dinner"],
        nutrition=content["nutrition"],
        weather_code=0,
        time_str="14:30",
    )
    
    img.save("test_recipe_output.png")
    print("\n✓ Saved to test_recipe_output.png")
    print(f"\nTip: Delete {CACHE_FILE} to fetch a new meal plan")


if __name__ == "__main__":
    asyncio.run(main())
