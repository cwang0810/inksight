"""
测试 BRIEFING 模式
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from core.content import generate_briefing_content
from core.patterns.briefing import render_briefing

load_dotenv()


async def main():
    print("Testing BRIEFING mode...")
    
    content = await generate_briefing_content(
        llm_provider="deepseek",
        llm_model="deepseek-chat",
        summarize=True
    )
    
    print(f"\nGenerated content:")
    print(f"\n=== HN items ({len(content['hn_items'])}) ===")
    for i, item in enumerate(content['hn_items'], 1):
        print(f"\n{i}. {item.get('title', '')}")
        print(f"   Score: {item.get('score', 0)} pts")
        if item.get('summary'):
            print(f"   Summary: {item.get('summary')}")
    
    print(f"\n=== PH item ===")
    print(f"Name: {content['ph_item'].get('name', 'N/A')}")
    if content['ph_item'].get('tagline_original'):
        print(f"Tagline (Original): {content['ph_item'].get('tagline_original')}")
    if content['ph_item'].get('tagline'):
        print(f"Tagline (Summary): {content['ph_item'].get('tagline')}")
    
    print(f"\n=== AI Insight ===")
    print(content['insight'])
    
    img = render_briefing(
        date_str="2月14日 周六",
        weather_str="晴 15°C",
        battery_pct=85,
        hn_items=content["hn_items"],
        ph_item=content["ph_item"],
        insight=content["insight"],
        weather_code=0,
        time_str="14:30",
    )
    
    img.save("test_briefing_output.png")
    print("✓ Saved to test_briefing_output.png")


if __name__ == "__main__":
    asyncio.run(main())
