import asyncio
from playwright.async_api import async_playwright, BrowserContext, Browser
import json
import time

async def get_search_product_links(query: str, context: BrowserContext):
    """
    Navigates to the ZeptoNow search page for a given query, scrolls to load all products,
    and scrapes product names and URLs.

    Args:
        query (str): The search query (e.g., "laptop").
        context (BrowserContext): The Playwright browser context.

    Returns:
        list: A list of dictionaries, where each dictionary contains 'name' and 'url'
              for a scraped product. Returns an empty list if an error occurs.
    """
    page = await context.new_page()
    url = f"https://www.zeptonow.com/search?query={query}"
    print(f"Navigating to {query} page...")

    try:
        # Navigate to the URL and wait for the DOM content to be loaded.
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        # Wait for an additional 2 seconds to ensure dynamic content loads.
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"Error loading {query} page: {e}")
        await page.close()
        return [] # Return an empty list if there's an error loading the page
    
    # Scroll down the page to load all products dynamically.
    last_height = await page.evaluate("() => document.body.scrollHeight")
    while True:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000) 
        new_height = await page.evaluate("() => document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    # Locate all product cards using the data-testid.
    product_cards = await page.locator('//a[@data-testid="product-card"]').all()

    products = []

    # Iterate through each product card to extract name and URL.
    for product_card in product_cards:
        product_data = {}
        name = await product_card.locator('h5[data-testid="product-card-name"]').text_content()
        product_data['name'] = name.strip() if name else None
        href = await product_card.get_attribute('href')
        product_data['url'] = "https://www.zeptonow.com" + href if href else None
        products.append(product_data)

    print(f"Scraped {len(products)} products from {query} page.")

    await page.close()

    return products

async def main(query: str, browser: Browser):
    """
    Main asynchronous function to launch the browser, create a context,
    scrape product links, and measure the time taken.

    Args:
        query (str): The search query for products.

    Returns:
        tuple: A tuple containing the list of scraped products and the time taken in seconds.
    """
    async with async_playwright() as playwright:
        context = await browser.new_context()

        # Call the function to get product links.
        products = await get_search_product_links(query, context)

        # Close the browser context and browser.
        await context.close()
        await browser.close()

    return products
    
async def extract_search_pl_api(query: str, browser: Browser):
    return await main(query, browser)