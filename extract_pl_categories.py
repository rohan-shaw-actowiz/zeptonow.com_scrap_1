import asyncio
from playwright.async_api import async_playwright, BrowserContext, Page, Browser
import json
import time

# List to store category and subcategory data
category_items = []
MAX_CONCURRENT_SUBCATEGORIES = 5 # Control how many subcategories to scrape in parallel

async def get_categories_links(page: Page):
    """
    Navigates to the all categories page, renders the content,
    and extracts category and subcategory names and URLs.
    """
    print("Navigating to categories page...")
    try:
        await page.goto('https://www.zeptonow.com/pip/all-categories/9277', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_selector('div[data-type="CATEGORY_GRID_V2"]', timeout=30000)
        print("Category grid loaded.")
    except Exception as e:
        print(f"Error loading categories page or grid: {e}")
        return

    category_grids = await page.locator('div[data-type="CATEGORY_GRID_V2"]').all()

    for category_grid_locator in category_grids:
        category_data = {}
        category_type_element = await category_grid_locator.locator('h4').first.text_content()
        category_type = category_type_element.strip() if category_type_element else "Unknown Category"
        print(f"Scraping category: {category_type}")
        category_data[category_type] = []

        subcategory_grids = await category_grid_locator.locator('div[id="CATEGORY_GRID_V3-element"]').all()

        for subcategory_grid_locator in subcategory_grids:
            subcategory_data = {}
            subcategory_name_element = await subcategory_grid_locator.locator('img').first.get_attribute('alt')
            subcategory_data['name'] = subcategory_name_element.strip() if subcategory_name_element else "Unknown Subcategory"

            subcategory_href_element = await subcategory_grid_locator.locator('a').first.get_attribute('href')
            subcategory_data['url'] = 'https://www.zeptonow.com' + subcategory_href_element.strip() if subcategory_href_element else None

            if subcategory_data['url']: 
                category_data[category_type].append(subcategory_data)
        category_items.append(category_data)
    print(f"Finished scraping {len(category_items)} main categories.")

async def scrape_subcategory_products(context: BrowserContext, subcategory_item: dict):
    """
    Navigates to a single subcategory, handles infinite scrolling,
    and extracts product names and URLs. Runs within its own browser context.
    """
    page = await context.new_page()
    subcategory_url = subcategory_item['url']
    print(f"[{subcategory_item['name']}] Navigating to subcategory...")

    try:
        await page.goto(subcategory_url, wait_until='domcontentloaded', timeout=60000)
        # Give some time for initial content to load after navigation
        await page.wait_for_timeout(2000)
    except Exception as e:
        print(f"[{subcategory_item['name']}] Error navigating to subcategory URL {subcategory_url}: {e}")
        await page.close()
        return

    scroll_container_locator = page.locator('div.grid[class*="product-card"]').first.or_(
        page.locator('//div[@class="no-scrollbar grid grid-cols-2 content-start gap-y-4 gap-x-2 px-2.5 py-4 md:grid-cols-3 md:gap-x-3 md:p-3 lg:grid-cols-5 xl:grid-cols-6"]').first
    )

    if not await scroll_container_locator.count():
        print(f"[{subcategory_item['name']}] Could not find product list container, skipping.")
        await page.close()
        return

    scroll_count = 0
    max_scrolls = 35
    previous_product_count = 0

    print(f"[{subcategory_item['name']}] Starting infinite scroll...")
    while scroll_count < max_scrolls:
        try:
            await scroll_container_locator.evaluate("(el) => window.scrollTo(0, el.scrollHeight)")

            await page.wait_for_timeout(1500) # Wait for 1.5 seconds for content to appear

            current_product_count = await page.locator('a[data-testid="product-card"]').count()
            print(f"[{subcategory_item['name']}] Scroll {scroll_count + 1}/{max_scrolls}: Products found: {current_product_count}")

            if current_product_count == previous_product_count and scroll_count > 0:
                print(f"[{subcategory_item['name']}] No new products loaded, breaking infinite scroll.")
                break

            previous_product_count = current_product_count
            scroll_count += 1
        except Exception as e:
            print(f"[{subcategory_item['name']}] Error during scrolling: {e}")
            break # Exit scroll loop on error

    product_cards = await page.locator('a[data-testid="product-card"]').all()
    subcategory_item['products'] = []

    for product_card_locator in product_cards:
        product_data = {}
        try:
            name_element = await product_card_locator.locator('h5[data-testid="product-card-name"]').first.text_content()
            product_data['name'] = name_element.strip() if name_element else None

            href_element = await product_card_locator.get_attribute('href')
            product_data['url'] = "https://www.zeptonow.com" + href_element.strip() if href_element else None

            if product_data['name'] and product_data['url']: 
                subcategory_item['products'].append(product_data)
        except Exception as e:
            print(f"[{subcategory_item['name']}] Error extracting product data: {e}")
            continue # Continue to next product card if one fails

    print(f"[{subcategory_item['name']}] Scraped {len(subcategory_item['products'])} products.")
    await page.close()

async def main(browser: Browser):
    """
    Main asynchronous function to run the Playwright scraper with parallel processing.
    """
    async with async_playwright() as p:    
        # Create a single context for initial category scraping
        category_context = await browser.new_context()
        category_page = await category_context.new_page()
        await get_categories_links(category_page)
        await category_context.close()

        all_subcategory_tasks = []
        for category in category_items:
            for subcategory_list in category.values():
                for subcategory_item in subcategory_list:
                    if subcategory_item['url']:
                        # Create a new context for each subcategory task for isolation
                        context = await browser.new_context()
                        all_subcategory_tasks.append(
                            scrape_subcategory_products(context, subcategory_item)
                        )
        
        print(f"\nStarting parallel product scraping for {len(all_subcategory_tasks)} subcategories...")
        # Run tasks in chunks to control concurrency
        for i in range(0, len(all_subcategory_tasks), MAX_CONCURRENT_SUBCATEGORIES):
            chunk = all_subcategory_tasks[i:i + MAX_CONCURRENT_SUBCATEGORIES]
            await asyncio.gather(*chunk)
            print(f"Completed {min(i + MAX_CONCURRENT_SUBCATEGORIES, len(all_subcategory_tasks))} of {len(all_subcategory_tasks)} subcategories.")
            await asyncio.sleep(1)

        await browser.close()
        print("Browser closed.")

        return category_items

async def extract_category_pl_api(browser: Browser):
    return await main(browser)