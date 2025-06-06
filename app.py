from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from extract_pdp import extract_pdp_api
from extract_pl_categories import extract_category_pl_api
from extract_pl_search import extract_search_pl_api
from playwright.async_api import async_playwright
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Store the Playwright instance directly in app.state
    app.state.playwright = await async_playwright().start()
    app.state.browser = await app.state.playwright.chromium.launch(headless=True)

@app.on_event("shutdown")
async def shutdown_event():
    browser = app.state.browser
    if browser is not None:
        await browser.close()
        app.state.browser = None
    # Close the Playwright instance
    if app.state.playwright is not None:
        await app.state.playwright.stop()
        app.state.playwright = None

@app.get("/")
async def root():
    return {"message": "api running"}

@app.get("/extract_pdp_api")
async def extract_pdp_api_endpoint(product_url: str):
    start_time = time.perf_counter()
    result = await extract_pdp_api(product_url, app.state.browser)
    end_time = time.perf_counter()
    timetaken = end_time - start_time
    return {"result": result, "timetaken": timetaken}

@app.get("/extract_search_pl_api/{query}")
async def extract_search_pl_api_endpoint(query: str):
    start_time = time.perf_counter()
    result =  await extract_search_pl_api(query, app.state.browser)
    end_time = time.perf_counter()
    timetaken = end_time - start_time
    num_products = len(result)
    return {"result": result, "timetaken": timetaken, "num_products": num_products}

@app.get("/extract_category_pl_api")
async def extract_category_pl_api_endpoint():
    start_time = time.perf_counter()
    result = await extract_category_pl_api(app.state.browser)
    end_time = time.perf_counter()
    timetaken = end_time - start_time
    num_products = len(result)
    return {"result": result, "timetaken": timetaken}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)