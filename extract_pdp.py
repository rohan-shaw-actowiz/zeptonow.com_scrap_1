import asyncio
from playwright.async_api import async_playwright, BrowserContext, Page, Browser
import json
import time

async def get_product_details(product_url: str, context: BrowserContext):
    page = await context.new_page()
    print(f"Navigating to {product_url}...")

    try:
        await page.goto(product_url, wait_until='domcontentloaded', timeout=60000)
        # Wait for an additional 2 seconds to ensure dynamic content loads.
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"Error loading {product_url} page: {e}")
        await page.close()
        return
    
    product_details = {}

    try:
        product_name = await page.locator('h1').text_content()
        product_details['name'] = product_name.strip() if product_name else "Unknown Product Name"
    except Exception as e:
        print(f"Error getting product name: {e}")

    try:
        product_image_locator = page.locator(f"//div[contains(@class, 'no-scrollbar')]//div[@class='relative aspect-square h-full w-full snap-center']//img[@alt='{product_name}']").first
        product_image = await product_image_locator.get_attribute('src')
        product_details['image'] = product_image.strip() if product_image else "Unknown Product Image"
    except Exception as e:
        print(f"Error getting product image: {e}")

    try:
        product_price = await page.locator('//span[contains(text(), "₹")]').first.text_content()
        product_details['price'] = float(product_price.replace('₹', '').strip()) if product_price else "Unknown Product Price"
    except Exception as e:
        print(f"Error getting product price: {e}")

    try:
        product_quantity = await page.locator('//p[contains(text(), "Net Qty")]//span').text_content()
        product_details['quantity'] = product_quantity.strip() if product_quantity else "Unknown Product Quantity"
    except Exception as e:
        print(f"Error getting product quantity: {e}")

    try:
        rating = await page.locator('//div/child::span[@class="font-bold"]').text_content()
        product_details['rating'] = rating.strip() if rating else "Unknown Product Rating"
    except Exception as e:
        print(f"Error getting product rating: {e}")

    try:
        products_info_div = page.locator('//div[@id="productHighlights"]//div//div//div').first
        for info in await products_info_div.locator('div').all():
            key = await info.locator('h3').text_content()
            value = await info.locator('p').text_content()
            product_details[key.strip()] = value.strip() if value else "Unknown Product Info"
    except Exception as e:
        print(f"Error getting product info: {e}")

    await page.close()
    return product_details

async def main(product_url: str, browser: Browser):
    context = await browser.new_context()
    product_details = await get_product_details(product_url, context)
    await context.close()
    return product_details

async def extract_pdp_api(product_url: str, browser: Browser):
    return await main(product_url, browser)