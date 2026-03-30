import json
import os
import time
import argparse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Literal
import pandas as pd

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from sfinance.sfinance import SFinance
from sfinance.exceptions import TickerNotFound, LoginRequiredError

from constants import SCREENER_PARAMS, SCREENER_OPERATORS

from dotenv import load_dotenv
load_dotenv()

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sfinance_server.log')
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared state — populated once during lifespan, reused by all tool calls
# ---------------------------------------------------------------------------

app_state: dict = {}
CACHE_EXPIRY_HOURS = 24


# ---------------------------------------------------------------------------
# Lifespan — SFinance initializes and logs in ONCE at server startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(server: FastMCP):
    chrome_path = os.getenv('CHROME_PATH', "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
    screener_url = os.getenv('SCREENER_URL', "https://www.screener.in/")

    logger.info("Starting SFinance server — initializing browser...")
    sf = SFinance(screener_url, chrome_path)

    login_successful = False
    email = os.getenv('SCREENER_EMAIL')
    password = os.getenv('SCREENER_PASSWORD')
    if email and password:
        try:
            sf.login(email, password)
            login_successful = sf.fetcher.is_logged_in()
            logger.info(f"Login successful: {login_successful}")
        except Exception as e:
            logger.error(f"Login failed: {e}")
    else:
        logger.warning("No credentials in env — running without login")

    app_state["sf"] = sf
    app_state["login_successful"] = login_successful
    app_state["ticker_cache"] = {}

    yield

    logger.info("Shutting down — closing browser...")
    try:
        sf.close()
    except Exception as e:
        logger.error(f"Error closing SFinance: {e}")


# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("sfinance-server", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_logged_in() -> bool:
    sf = app_state.get("sf")
    if sf is not None:
        return sf.fetcher.is_logged_in()
    return app_state.get("login_successful", False)


def get_ticker(symbol: str):
    symbol = symbol.upper()
    cache: dict = app_state["ticker_cache"]
    now = datetime.now()

    if symbol in cache:
        ticker, cache_time = cache[symbol]
        if now - cache_time < timedelta(hours=CACHE_EXPIRY_HOURS):
            logger.info(f"Cache hit for {symbol}")
            return ticker
        logger.info(f"Cache expired for {symbol}")
        del cache[symbol]

    logger.info(f"Creating ticker for {symbol}...")
    t0 = time.time()
    ticker = app_state["sf"].ticker(symbol)
    logger.info(f"Ticker {symbol} loaded in {time.time() - t0:.2f}s")
    cache[symbol] = (ticker, now)
    return ticker


def clear_expired_cache():
    cache: dict = app_state.get("ticker_cache", {})
    now = datetime.now()
    expired = [s for s, (_, t) in cache.items()
               if now - t >= timedelta(hours=CACHE_EXPIRY_HOURS)]
    for s in expired:
        del cache[s]
        logger.info(f"Cleared expired cache for {s}")


def df_to_json(df: pd.DataFrame) -> str:
    if df.empty:
        return json.dumps({"error": "No data available"})
    return df.to_json(orient='records', indent=2)


# ---------------------------------------------------------------------------
# Tools — ticker data
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_overview(symbol: str) -> str:
    """Get company overview for an Indian stock listed on NSE/BSE. E.g. INFY, TCS, RELIANCE."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    return json.dumps(ticker.get_overview(), indent=2)


@mcp.tool()
async def get_income_statement(symbol: str) -> str:
    """Get income statement for an Indian company. Data sourced from screener.in."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    return df_to_json(ticker.get_income_statement())


@mcp.tool()
async def get_balance_sheet(symbol: str) -> str:
    """Get balance sheet for an Indian company listed on NSE/BSE."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    return df_to_json(ticker.get_balance_sheet())


@mcp.tool()
async def get_cash_flow(symbol: str) -> str:
    """Get cash flow statement for an Indian company."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    return df_to_json(ticker.get_cash_flow())


@mcp.tool()
async def get_quarterly_results(symbol: str) -> str:
    """Get quarterly results for an Indian company from screener.in."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    return df_to_json(ticker.get_quarterly_results())


@mcp.tool()
async def get_shareholding(symbol: str) -> str:
    """Get shareholding pattern for an Indian company (promoter, institutional, public holdings)."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    return df_to_json(ticker.get_shareholding())


@mcp.tool()
async def get_peer_comparison(symbol: str) -> str:
    """Get peer comparison for an Indian company — P/E, market cap, revenue growth vs industry peers."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    return df_to_json(ticker.get_peer_comparison())


# ---------------------------------------------------------------------------
# Tools — document access (login required)
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_announcements(
    symbol: str,
    tab: Literal["recent", "important"] = "recent"
) -> str:
    """
    Get company announcements for an Indian stock. Login required.
    Returns title, subtitle, and URL for each announcement.
    tab: 'recent' (default) or 'important'
    """
    clear_expired_cache()
    ticker = get_ticker(symbol)
    df = ticker.get_announcements(tab=tab)
    return df_to_json(df)


@mcp.tool()
async def get_annual_reports(symbol: str) -> str:
    """Get list of annual reports with download URLs for an Indian stock. Login required."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    df = ticker.get_annual_reports()
    return df_to_json(df)


@mcp.tool()
async def get_credit_ratings(symbol: str) -> str:
    """Get credit rating documents with download URLs for an Indian stock. Login required."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    df = ticker.get_credit_ratings()
    return df_to_json(df)


@mcp.tool()
async def get_concalls(symbol: str) -> str:
    """Get conference call documents (transcripts, PPTs, recordings) for an Indian stock. Login required."""
    clear_expired_cache()
    ticker = get_ticker(symbol)
    df = ticker.get_concalls()
    return df_to_json(df)


@mcp.tool()
async def download_documents(
    symbol: str,
    doc_type: Literal["announcements", "annual_reports", "credit_ratings", "concalls"],
    folder_path: str,
    link_type: Literal["transcript", "ppt", "rec", "all"] = "all",
    tab: Literal["recent", "important"] = "recent",
    year: Optional[int] = None,
    period: Optional[str] = None,
    n: Optional[int] = None
) -> str:
    """
    Batch download company documents to a local folder. Login required.
    doc_type: 'announcements', 'annual_reports', 'credit_ratings', or 'concalls'
    link_type: for concalls — 'transcript', 'ppt', 'rec', or 'all'
    tab: for announcements — 'recent' or 'important'
    year: for annual_reports — filter by year (e.g. 2023)
    period: for concalls — filter by period string (e.g. 'Q3 2024')
    n: max number of documents to download
    """
    clear_expired_cache()
    ticker = get_ticker(symbol)
    downloaded = ticker.download_documents(
        doc_type=doc_type,
        folder_path=folder_path,
        link_type=link_type,
        tab=tab,
        year=year,
        period=period,
        n=n
    )
    result = {
        "symbol": symbol.upper(),
        "doc_type": doc_type,
        "folder_path": folder_path,
        "downloaded_count": len(downloaded),
        "files": downloaded
    }
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tools — screener
# ---------------------------------------------------------------------------

@mcp.tool()
async def screen_stocks(
    query: str,
    sort: str = "",
    order: Literal["asc", "desc"] = "desc",
    page: int = 1
) -> str:
    """
    Screen Indian stocks based on financial criteria. Login required.
    query: e.g. 'Piotroski score > 7 AND Return on equity > 15'
    Supported operators: +, -, /, *, >, <, AND, OR
    """
    if not is_logged_in():
        return json.dumps({
            "error": "Login required",
            "message": "Stock screening requires login to screener.in",
            "instruction": "Set SCREENER_EMAIL and SCREENER_PASSWORD environment variables and restart the server"
        }, indent=2)

    screener = app_state["sf"].screener()
    df = screener.load_raw_query(query=query, sort=sort, order=order, page=page)
    result = {
        "query": query,
        "sort": sort,
        "order": order,
        "page": page,
        "total_results": len(df),
        "results": df.to_dict('records') if not df.empty else []
    }
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_screening_parameters(
    category: Literal["ratios", "growth", "profitability", "annual", "quarterly",
                      "balance_sheet", "cash_flow", "price", "all"] = "all"
) -> str:
    """
    Get available parameters for stock screening with descriptions and examples.
    category: filter by category or 'all' for everything
    """
    if category == "all":
        result = {
            "parameters": SCREENER_PARAMS,
            "operators": SCREENER_OPERATORS,
            "note": "Use exact parameter names in queries. Case sensitive."
        }
    elif category in SCREENER_PARAMS:
        result = {
            "category": category,
            "parameters": SCREENER_PARAMS[category],
            "operators": SCREENER_OPERATORS
        }
    else:
        result = {
            "error": f"Unknown category: {category}",
            "available_categories": list(SCREENER_PARAMS.keys()) + ["all"]
        }
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tools — cache / utility
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_cache_stats() -> str:
    """Get ticker cache statistics and current login status."""
    cache: dict = app_state.get("ticker_cache", {})
    now = datetime.now()
    active = sum(1 for _, t in cache.values()
                 if now - t < timedelta(hours=CACHE_EXPIRY_HOURS))
    expired = len(cache) - active
    return json.dumps({
        "active_cache_entries": active,
        "expired_cache_entries": expired,
        "total_cache_entries": len(cache),
        "cache_expiry_hours": CACHE_EXPIRY_HOURS,
        "login_status": is_logged_in()
    }, indent=2)


@mcp.tool()
async def clear_cache(symbol: Optional[str] = None) -> str:
    """
    Clear cached ticker objects to force fresh data on next request.
    symbol: specific symbol to clear, or omit to clear everything.
    """
    cache: dict = app_state.get("ticker_cache", {})
    if symbol:
        symbol = symbol.upper()
        if symbol in cache:
            del cache[symbol]
            return json.dumps({"message": f"Cleared cache for {symbol}"}, indent=2)
        return json.dumps({"message": f"No cache found for {symbol}"}, indent=2)
    count = len(cache)
    cache.clear()
    return json.dumps({"message": f"Cleared all cache ({count} entries)"}, indent=2)


@mcp.tool()
async def check_login_status() -> str:
    """Check whether the server is logged into screener.in."""
    logged_in = is_logged_in()
    return json.dumps({
        "logged_in": logged_in,
        "message": "Logged in to screener.in" if logged_in else "Not logged in.",
        "note": "Set SCREENER_EMAIL and SCREENER_PASSWORD environment variables for automatic login"
    }, indent=2)


# ---------------------------------------------------------------------------
# Health check endpoint (HTTP only)
# ---------------------------------------------------------------------------

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "login": is_logged_in(),
        "cached_tickers": len(app_state.get("ticker_cache", {}))
    })


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

@mcp.prompt()
def high_quality_stocks(
    min_piotroski_score: str = "7",
    min_roe: str = "15",
    max_pe: str = "25"
) -> str:
    """Find high quality stocks with strong fundamentals."""
    query = f"Piotroski score > {min_piotroski_score} AND Return on equity > {min_roe} AND Price to Earning < {max_pe}"
    return (
        f"Please screen for high quality stocks using this query: {query}\n\n"
        f"This will find companies with:\n"
        f"- Piotroski score > {min_piotroski_score} (financial strength)\n"
        f"- Return on equity > {min_roe}% (profitability)\n"
        f"- P/E ratio < {max_pe} (reasonable valuation)"
    )


@mcp.prompt()
def value_stocks(
    max_pe: str = "15",
    max_pb: str = "2",
    min_dividend_yield: str = "2"
) -> str:
    """Find undervalued stocks based on traditional value metrics."""
    query = f"Price to Earning < {max_pe} AND Price to book value < {max_pb} AND Dividend yield > {min_dividend_yield}"
    return (
        f"Please screen for value stocks using this query: {query}\n\n"
        f"This will find companies with:\n"
        f"- P/E ratio < {max_pe} (low valuation)\n"
        f"- Price to book < {max_pb} (trading below book value)\n"
        f"- Dividend yield > {min_dividend_yield}% (income generating)"
    )


@mcp.prompt()
def growth_stocks(
    min_sales_growth: str = "15",
    min_profit_growth: str = "20",
    min_roe: str = "15"
) -> str:
    """Find growth stocks with strong revenue and profit growth."""
    query = f"Sales growth 3Years > {min_sales_growth} AND Profit growth 3Years > {min_profit_growth} AND Return on equity > {min_roe}"
    return (
        f"Please screen for growth stocks using this query: {query}\n\n"
        f"This will find companies with:\n"
        f"- Sales growth > {min_sales_growth}% (3 years)\n"
        f"- Profit growth > {min_profit_growth}% (3 years)\n"
        f"- Return on equity > {min_roe}% (efficient capital use)"
    )


@mcp.prompt()
def custom_screener(criteria: str) -> str:
    """Build a custom stock screening query from plain-language criteria."""
    return (
        f"Based on your criteria: '{criteria}'\n\n"
        "Please help me build a custom stock screening query. Available parameters:\n\n"
        "**Financial Ratios**: Price to Earning, Price to book value, Return on equity, "
        "Return on assets, Debt to equity, Current ratio, Quick ratio\n\n"
        "**Growth Metrics**: Sales growth 3Years, Profit growth 3Years, EPS growth 3Years, "
        "Sales growth 5Years\n\n"
        "**Profitability**: OPM (Operating Profit Margin), NPM (Net Profit Margin), "
        "Return on capital employed\n\n"
        "**Quality Scores**: Piotroski score, Earnings yield\n\n"
        "**Market Data**: Market Capitalization, Dividend yield, Promoter holding\n\n"
        "**Operators**: >, <, AND, OR\n\n"
        "Example: 'Return on equity > 20 AND Debt to equity < 0.5 AND Sales growth 3Years > 15'"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="sfinance MCP server")
    parser.add_argument(
        "--transport",
        default=os.getenv("TRANSPORT", "stdio"),
        choices=["stdio", "http"],
        help="Transport mode: 'stdio' (default, for Claude Desktop) or 'http'"
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HOST", "0.0.0.0"),
        help="Host to bind to for HTTP transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "8000")),
        help="Port for HTTP transport (default: 8000)"
    )
    args = parser.parse_args()

    if args.transport == "http":
        logger.info(f"Starting HTTP server on {args.host}:{args.port}")
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        logger.info("Starting stdio server")
        mcp.run()
