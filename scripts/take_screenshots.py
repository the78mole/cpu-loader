#!/usr/bin/env python3
"""Script to take screenshots of the CPU Loader web interface."""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def take_screenshots():
    """Take screenshots of the web interface."""
    screenshots_dir = Path(__file__).parent.parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch()
        context = await browser.new_context(viewport={"width": 1400, "height": 1000})
        page = await context.new_page()

        # Navigate to the application
        await page.goto("http://localhost:8000")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(1)  # Extra wait for everything to render

        # Screenshot 1: Initial view with no load
        await page.screenshot(path=screenshots_dir / "01-initial-view.png", full_page=True)
        print("✓ Screenshot 1: Initial view")

        # Screenshot 2: Set some CPU load using sliders
        # Set Thread 0 to 50%
        slider0 = page.locator('input[type="range"]').nth(0)
        await slider0.fill("50")
        await asyncio.sleep(0.5)

        # Set Thread 1 to 75%
        slider1 = page.locator('input[type="range"]').nth(1)
        await slider1.fill("75")
        await asyncio.sleep(0.5)

        # Set Thread 2 to 25%
        slider2 = page.locator('input[type="range"]').nth(2)
        await slider2.fill("25")
        await asyncio.sleep(3)  # Wait for visual bars to update

        await page.screenshot(path=screenshots_dir / "02-with-load.png", full_page=True)
        print("✓ Screenshot 2: With CPU load set")

        # Screenshot 3: Show different loads and real-time metrics
        # Change some values
        await slider0.fill("100")
        await slider1.fill("30")
        await slider2.fill("80")

        # Wait for real CPU metrics to update
        await asyncio.sleep(3)  # Wait for visual bars to update

        await page.screenshot(path=screenshots_dir / "03-live-metrics.png", full_page=True)
        print("✓ Screenshot 3: Live metrics updating")

        # Screenshot 4: Mobile view
        mobile_context = await browser.new_context(
            viewport={"width": 375, "height": 667},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto("http://localhost:8000")
        await mobile_page.wait_for_load_state("networkidle")

        # Set some load on mobile view
        mobile_slider0 = mobile_page.locator('input[type="range"]').nth(0)
        await mobile_slider0.fill("60")
        await asyncio.sleep(0.5)

        mobile_slider1 = mobile_page.locator('input[type="range"]').nth(1)
        await mobile_slider1.fill("40")
        await asyncio.sleep(3)  # Wait for visual bars to update

        await mobile_page.screenshot(path=screenshots_dir / "04-mobile-view.png", full_page=True)
        print("✓ Screenshot 4: Mobile view")

        await mobile_context.close()
        await browser.close()

    print(f"\n✅ All screenshots saved to: {screenshots_dir}")


if __name__ == "__main__":
    asyncio.run(take_screenshots())
