"""
测试 FITNESS 模式
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
from core.content import generate_fitness_content
from core.patterns.fitness import render_fitness

load_dotenv()


async def main():
    print("Testing FITNESS mode...")
    
    content = await generate_fitness_content(
        llm_provider="deepseek",
        llm_model="deepseek-chat",
    )
    
    print(f"Generated content:")
    print(f"  Workout: {content['workout_name']} ({content['duration']})")
    print(f"  Exercises: {len(content['exercises'])} items")
    print(f"  Tip: {content['tip'][:50]}...")
    
    img = render_fitness(
        date_str="2月14日 周六",
        weather_str="晴 15°C",
        battery_pct=85,
        workout_name=content["workout_name"],
        duration=content["duration"],
        exercises=content["exercises"],
        tip=content["tip"],
        weather_code=0,
        time_str="14:30",
    )
    
    img.save("test_fitness_output.png")
    print("✓ Saved to test_fitness_output.png")


if __name__ == "__main__":
    asyncio.run(main())
