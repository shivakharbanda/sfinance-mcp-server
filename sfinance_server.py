import json
import asyncio
import os
from typing import List, Dict, Any, Optional
import pandas as pd
import time
from datetime import datetime, timedelta

import mcp.types as types
from mcp.server import Server
import mcp.server.stdio

# Import your classes
from sfinance.sfinance import SFinance
from sfinance.exceptions import TickerNotFound, LoginRequiredError

from constants import SCREENER_PARAMS, SCREENER_OPERATORS

from dotenv import load_dotenv  # Add this import
load_dotenv()  # Add this line

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sfinance_server.log')
    ]
)
logger = logging.getLogger(__name__)


# Create server
server = Server("sfinance-server")

# Global SFinance instance - initialize lazily
sf = None

# Ticker cache with expiration
ticker_cache = {}
CACHE_EXPIRY_HOURS = 24  # Cache tickers for 24 hours

# Login state tracking
_login_attempted = False
_login_successful = False

def get_sfinance():
    """Lazy initialization of SFinance instance"""
    global sf, _login_attempted, _login_successful
    
    if sf is None:
        try:
            chrome_path = os.getenv('CHROME_PATH', "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
            screener_url = os.getenv('SCREENER_URL', "https://www.screener.in/")
            sf = SFinance(screener_url, chrome_path)
            
            # Attempt login if credentials are available
            if not _login_attempted:
                email = os.getenv('SCREENER_EMAIL')
                password = os.getenv('SCREENER_PASSWORD')
                
                if email and password:
                    try:
                        sf.login(email, password)
                        _login_successful = sf.fetcher.is_logged_in()
                        logger.info(f"Login successful: {_login_successful}")
                    except Exception as e:
                        logger.error(f"Login failed: {str(e)}")
                        _login_successful = False
                else:
                    logger.warning("No credentials provided in environment variables")
                    _login_successful = False
                
                _login_attempted = True
                
        except Exception as e:
            logger.error(f"Failed to initialize SFinance: {str(e)}")
            raise Exception(f"Failed to initialize SFinance: {str(e)}")
    
    return sf

def is_logged_in():
    """Check if user is logged in for screener functionality"""
    global _login_successful
    if sf is not None:
        return sf.fetcher.is_logged_in()
    return _login_successful

def get_ticker(symbol: str):
    """Get ticker object with caching"""
    global ticker_cache
    
    symbol = symbol.upper()
    current_time = datetime.now()
    
    # Check if ticker exists in cache and is not expired
    if symbol in ticker_cache:
        cached_ticker, cache_time = ticker_cache[symbol]
        if current_time - cache_time < timedelta(hours=CACHE_EXPIRY_HOURS):
            logger.info(f"Using cached ticker for {symbol}")
            return cached_ticker
        else:
            logger.info(f"Cache expired for {symbol}, fetching new ticker")
            del ticker_cache[symbol]
    
    # Create new ticker and cache it
    logger.info(f"Creating new ticker for {symbol}...")
    start_time = time.time()
    
    sf_instance = get_sfinance()
    ticker = sf_instance.ticker(symbol)
    
    end_time = time.time()
    logger.info(f"Ticker creation for {symbol} took {end_time - start_time:.2f} seconds")
    
    # Cache the ticker with current timestamp
    ticker_cache[symbol] = (ticker, current_time)
    
    return ticker

def clear_expired_cache():
    """Clear expired cache entries"""
    global ticker_cache
    current_time = datetime.now()
    expired_symbols = []
    
    for symbol, (ticker, cache_time) in ticker_cache.items():
        if current_time - cache_time >= timedelta(hours=CACHE_EXPIRY_HOURS):
            expired_symbols.append(symbol)
    
    for symbol in expired_symbols:
        del ticker_cache[symbol]
        logger.info(f"Cleared expired cache for {symbol}")

def get_cache_stats():
    """Get cache statistics"""
    current_time = datetime.now()
    active_cache = 0
    expired_cache = 0
    
    for symbol, (ticker, cache_time) in ticker_cache.items():
        if current_time - cache_time < timedelta(hours=CACHE_EXPIRY_HOURS):
            active_cache += 1
        else:
            expired_cache += 1
    
    stats =  {
        "active_cache_entries": active_cache,
        "expired_cache_entries": expired_cache,
        "total_cache_entries": len(ticker_cache),
        "cache_expiry_hours": CACHE_EXPIRY_HOURS,
        "login_status": is_logged_in()
    }
    logger.debug(f"Cache stats: {stats}")
    return stats

def df_to_json(df: pd.DataFrame) -> str:
    """Convert DataFrame to JSON string"""
    if df.empty:
        return json.dumps({"error": "No data available"})
    return df.to_json(orient='records', indent=2)

@server.list_prompts()
async def list_prompts() -> List[types.Prompt]:
    """List available prompt templates for stock screening"""
    return [
        types.Prompt(
            name="high_quality_stocks",
            description="Find high quality stocks with strong fundamentals",
            arguments=[
                types.PromptArgument(
                    name="min_piotroski_score",
                    description="Minimum Piotroski score (0-9, default: 7)",
                    required=False
                ),
                types.PromptArgument(
                    name="min_roe",
                    description="Minimum Return on Equity percentage (default: 15)",
                    required=False
                ),
                types.PromptArgument(
                    name="max_pe",
                    description="Maximum P/E ratio (default: 25)",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="value_stocks",
            description="Find undervalued stocks based on traditional value metrics",
            arguments=[
                types.PromptArgument(
                    name="max_pe",
                    description="Maximum P/E ratio (default: 15)",
                    required=False
                ),
                types.PromptArgument(
                    name="max_pb",
                    description="Maximum Price to Book ratio (default: 2)",
                    required=False
                ),
                types.PromptArgument(
                    name="min_dividend_yield",
                    description="Minimum dividend yield percentage (default: 2)",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="growth_stocks",
            description="Find growth stocks with strong revenue and profit growth",
            arguments=[
                types.PromptArgument(
                    name="min_sales_growth",
                    description="Minimum sales growth 3 years percentage (default: 15)",
                    required=False
                ),
                types.PromptArgument(
                    name="min_profit_growth",
                    description="Minimum profit growth 3 years percentage (default: 20)",
                    required=False
                ),
                types.PromptArgument(
                    name="min_roe",
                    description="Minimum Return on Equity percentage (default: 15)",
                    required=False
                )
            ]
        ),
        types.Prompt(
            name="custom_screener",
            description="Build a custom stock screening query with your own criteria",
            arguments=[
                types.PromptArgument(
                    name="criteria",
                    description="Describe the screening criteria you want (e.g., 'stocks with high ROE and low debt')",
                    required=True
                )
            ]
        )
    ]

@server.get_prompt()
async def get_prompt(name: str, arguments: Dict[str, str] | None) -> types.GetPromptResult:
    """Get specific prompt template"""
    
    if name == "high_quality_stocks":
        min_piotroski = arguments.get("min_piotroski_score", "7") if arguments else "7"
        min_roe = arguments.get("min_roe", "15") if arguments else "15"
        max_pe = arguments.get("max_pe", "25") if arguments else "25"
        
        query = f"Piotroski score > {min_piotroski} AND Return on equity > {min_roe} AND Price to Earning < {max_pe}"
        
        return types.GetPromptResult(
            description="Screen for high quality stocks with strong fundamentals",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Please screen for high quality stocks using this query: {query}\n\nThis will find companies with:\n- Piotroski score > {min_piotroski} (financial strength)\n- Return on equity > {min_roe}% (profitability)\n- P/E ratio < {max_pe} (reasonable valuation)"
                    )
                )
            ]
        )
    
    elif name == "value_stocks":
        max_pe = arguments.get("max_pe", "15") if arguments else "15"
        max_pb = arguments.get("max_pb", "2") if arguments else "2"
        min_dividend = arguments.get("min_dividend_yield", "2") if arguments else "2"
        
        query = f"Price to Earning < {max_pe} AND Price to book value < {max_pb} AND Dividend yield > {min_dividend}"
        
        return types.GetPromptResult(
            description="Screen for undervalued stocks",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Please screen for value stocks using this query: {query}\n\nThis will find companies with:\n- P/E ratio < {max_pe} (low valuation)\n- Price to book < {max_pb} (trading below book value)\n- Dividend yield > {min_dividend}% (income generating)"
                    )
                )
            ]
        )
    
    elif name == "growth_stocks":
        min_sales_growth = arguments.get("min_sales_growth", "15") if arguments else "15"
        min_profit_growth = arguments.get("min_profit_growth", "20") if arguments else "20"
        min_roe = arguments.get("min_roe", "15") if arguments else "15"
        
        query = f"Sales growth 3Years > {min_sales_growth} AND Profit growth 3Years > {min_profit_growth} AND Return on equity > {min_roe}"
        
        return types.GetPromptResult(
            description="Screen for growth stocks",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Please screen for growth stocks using this query: {query}\n\nThis will find companies with:\n- Sales growth > {min_sales_growth}% (3 years)\n- Profit growth > {min_profit_growth}% (3 years)\n- Return on equity > {min_roe}% (efficient capital use)"
                    )
                )
            ]
        )
    
    elif name == "custom_screener":
        criteria = arguments.get("criteria", "") if arguments else ""
        
        return types.GetPromptResult(
            description="Build custom screening query",
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Based on your criteria: '{criteria}'\n\nPlease help me build a custom stock screening query. Here are the available parameters:\n\n**Financial Ratios**: Price to Earning, Price to book value, Return on equity, Return on assets, Debt to equity, Current ratio, Quick ratio\n\n**Growth Metrics**: Sales growth 3Years, Profit growth 3Years, EPS growth 3Years, Sales growth 5Years\n\n**Profitability**: OPM (Operating Profit Margin), NPM (Net Profit Margin), Return on capital employed\n\n**Quality Scores**: Piotroski score, Earnings yield\n\n**Market Data**: Market Capitalization, Dividend yield, Promoter holding\n\n**Operators**: >, <, AND, OR\n\nExample: 'Return on equity > 20 AND Debt to equity < 0.5 AND Sales growth 3Years > 15'"
                    )
                )
            ]
        )
    
    else:
        raise ValueError(f"Unknown prompt: {name}")

@server.list_tools()
async def list_tools() -> List[types.Tool]:
    return [
        # Existing tools (unchanged)
        types.Tool(
            name="get_overview",
            description="Get company overview for Indian stocks listed on NSE/BSE. Use Indian stock symbols like INFY, TCS, RELIANCE, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string", 
                        "description": "Indian stock symbol (e.g., INFY, TCS, RELIANCE, HDFCBANK)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_income_statement", 
            description="Get income statement for Indian companies. Data sourced from screener.in",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string", 
                        "description": "Indian stock symbol (e.g., INFY, TCS, RELIANCE)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_balance_sheet",
            description="Get balance sheet for Indian companies listed on NSE/BSE", 
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string", 
                        "description": "Indian stock symbol (e.g., INFY, TCS, RELIANCE)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_cash_flow",
            description="Get cash flow statement for Indian companies",
            inputSchema={
                "type": "object", 
                "properties": {
                    "symbol": {
                        "type": "string", 
                        "description": "Indian stock symbol (e.g., INFY, TCS, RELIANCE)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_quarterly_results",
            description="Get quarterly results for Indian companies from screener.in",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string", 
                        "description": "Indian stock symbol (e.g., INFY, TCS, RELIANCE)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_shareholding",
            description="Get shareholding pattern for Indian companies (promoter, institutional, public holdings)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string", 
                        "description": "Indian stock symbol (e.g., INFY, TCS, RELIANCE)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_peer_comparison",
            description="Get peer comparison analysis for Indian companies. Compares the company with its industry peers on key financial metrics like P/E ratio, market cap, revenue growth, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string", 
                        "description": "Indian stock symbol (e.g., INFY, TCS, RELIANCE, HDFCBANK)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        
        # New screener tools
        types.Tool(
            name="screen_stocks",
            description="Screen Indian stocks based on financial criteria. Login required. Use criteria like 'Piotroski score > 7', 'Return on equity > 15', etc. Supported operators: +, -, /, *, >, <, AND, OR",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Screening query using financial parameters (e.g., 'Piotroski score > 7 AND Return on equity > 15')"
                    },
                    "sort": {
                        "type": "string",
                        "description": "Sort by parameter (e.g., 'Market Capitalization', 'Return on equity')",
                        "default": ""
                    },
                    "order": {
                        "type": "string",
                        "description": "Sort order: 'asc' or 'desc'",
                        "enum": ["asc", "desc"],
                        "default": "desc"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                        "default": 1
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_screening_parameters",
            description="Get comprehensive list of available parameters for stock screening with descriptions and examples",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Filter by category: 'ratios', 'growth', 'profitability', 'annual', 'quarterly', 'balance_sheet', 'cash_flow', 'price'",
                        "enum": ["ratios", "growth", "profitability", "annual", "quarterly", "balance_sheet", "cash_flow", "price", "all"]
                    }
                },
                "required": []
            }
        ),
        
        # Existing cache tools
        types.Tool(
            name="get_cache_stats",
            description="Get ticker cache statistics and performance info",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="clear_cache",
            description="Clear all cached ticker objects (use when you want fresh data)",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Optional: specific symbol to clear from cache. If not provided, clears all cache."
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="check_login_status",
            description="Check if logged into screener.in for advanced features",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    try:
        # Handle cache management tools first
        if name == "get_cache_stats":
            stats = get_cache_stats()
            return [types.TextContent(type="text", text=json.dumps(stats, indent=2))]
        
        elif name == "clear_cache":
            global ticker_cache
            symbol = arguments.get("symbol")
            
            if symbol:
                symbol = symbol.upper()
                if symbol in ticker_cache:
                    del ticker_cache[symbol]
                    result = {"message": f"Cleared cache for {symbol}"}
                else:
                    result = {"message": f"No cache found for {symbol}"}
            else:
                cache_count = len(ticker_cache)
                ticker_cache.clear()
                result = {"message": f"Cleared all cache ({cache_count} entries)"}
            
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "check_login_status":
            login_status = is_logged_in()
            result = {
                "logged_in": login_status,
                "message": "Logged in to screener.in" if login_status else "Not logged in. Screener functionality requires login.",
                "note": "Set SCREENER_EMAIL and SCREENER_PASSWORD environment variables for automatic login"
            }
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Handle new screener tools
        elif name == "screen_stocks":
              
            query = arguments["query"]
            sort_by = arguments.get("sort", "")
            order = arguments.get("order", "desc")
            page = arguments.get("page", 1)
            
            try:
                sf_instance = get_sfinance()
                if not is_logged_in():
                    error_msg = {
                        "error": "Login required",
                        "message": "Stock screening requires login to screener.in",
                        "instruction": "Set SCREENER_EMAIL and SCREENER_PASSWORD environment variables and restart the server"
                    }
                    return [types.TextContent(type="text", text=json.dumps(error_msg, indent=2))]
          
                screener = sf_instance.screener()
                
                df = screener.load_raw_query(
                    query=query,
                    sort=sort_by,
                    order=order,
                    page=page
                )
                
                result = {
                    "query": query,
                    "sort": sort_by,
                    "order": order,
                    "page": page,
                    "total_results": len(df),
                    "results": df.to_dict('records') if not df.empty else []
                }
                
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
                
            except Exception as e:
                error_msg = {
                    "error": "Screening failed",
                    "message": str(e),
                    "query": query
                }
                return [types.TextContent(type="text", text=json.dumps(error_msg, indent=2))]
        
        elif name == "get_screening_parameters":
            category = arguments.get("category", "all")
            
            parameters = SCREENER_PARAMS
            
            operators_info = SCREENER_OPERATORS
            
            if category == "all":
                result = {
                    "parameters": parameters,
                    "operators": operators_info,
                    "note": "Use exact parameter names in queries. Case sensitive."
                }
            else:
                if category in parameters:
                    result = {
                        "category": category,
                        "parameters": parameters[category],
                        "operators": operators_info
                    }
                else:
                    result = {
                        "error": f"Unknown category: {category}",
                        "available_categories": list(parameters.keys()) + ["all"]
                    }
            
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
        
        # Handle existing ticker-based tools (unchanged logic)
        else:
            symbol = arguments["symbol"].upper()
            
            # Clear expired cache periodically
            clear_expired_cache()
            
            # Get ticker (from cache or create new)
            ticker = get_ticker(symbol)
            
            if name == "get_overview":
                result = ticker.get_overview()
                return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_income_statement":
                df = ticker.get_income_statement()
                return [types.TextContent(type="text", text=df_to_json(df))]
            
            elif name == "get_balance_sheet":
                df = ticker.get_balance_sheet()
                return [types.TextContent(type="text", text=df_to_json(df))]
            
            elif name == "get_cash_flow":
                df = ticker.get_cash_flow()
                return [types.TextContent(type="text", text=df_to_json(df))]
            
            elif name == "get_quarterly_results":
                df = ticker.get_quarterly_results()
                return [types.TextContent(type="text", text=df_to_json(df))]
            
            elif name == "get_shareholding":
                df = ticker.get_shareholding()
                return [types.TextContent(type="text", text=df_to_json(df))]
            
            elif name == "get_peer_comparison":
                df = ticker.get_peer_comparison()
                return [types.TextContent(type="text", text=df_to_json(df))]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
                
    except TickerNotFound as e:
        error_msg = {
            "error": "Ticker not found",
            "message": str(e),
            "suggestion": "Please verify the stock symbol is correct and listed on NSE/BSE"
        }
        return [types.TextContent(type="text", text=json.dumps(error_msg, indent=2))]
    except LoginRequiredError as e:
        error_msg = {
            "error": "Login required",
            "message": str(e),
            "instruction": "Set SCREENER_EMAIL and SCREENER_PASSWORD environment variables for automatic login"
        }
        return [types.TextContent(type="text", text=json.dumps(error_msg, indent=2))]
    except Exception as e:
        import traceback
        error_msg = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        return [types.TextContent(type="text", text=json.dumps(error_msg, indent=2))]

# Run the server
async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream, 
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())