"""
测试 ARTWALL 模式
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from core.content import generate_artwall_content
from core.patterns.artwall import render_artwall

load_dotenv()


async def main():
    print("Testing ARTWALL mode...")
    
    content = await generate_artwall_content(
        date_str="2月14日",
        weather_str="晴 15°C",
        festival="情人节",
        llm_provider="aliyun",
        llm_model="qwen-image-max",
    )
    
    print(f"Generated content:")
    print(f"  Title: {content['artwork_title']}")
    print(f"  Image URL: {content.get('image_url', 'N/A')[:50]}...")
    print(f"  Description: {content['description']}")
    
    img = render_artwall(
        date_str="2月14日 周六",
        weather_str="晴 15°C",
        battery_pct=85,
        artwork_title=content["artwork_title"],
        image_url=content.get("image_url", ""),
        description=content["description"],
        model_name=content.get("model_name", "qwen-image-max"),
        weather_code=0,
        time_str="14:30",
    )
    
    img.save("test_artwall_output.png")
    print("✓ Saved to test_artwall_output.png")


if __name__ == "__main__":
    asyncio.run(main())
