import json
import asyncio
from typing import List, Dict, Any
import pandas as pd
import time
from datetime import datetime, timedelta

import mcp.types as types
from mcp.server import Server
import mcp.server.stdio

# Import your classes
from sfinance.sfinance import SFinance

# Create server
server = Server("sfinance-server")

# Global SFinance instance - initialize lazily
sf = None

# Ticker cache with expiration
ticker_cache = {}
CACHE_EXPIRY_HOURS = 24  # Cache tickers for 24 hours

def get_sfinance():
    """Lazy initialization of SFinance instance"""
    global sf
    if sf is None:
        try:
            sf = SFinance("https://www.screener.in/", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe")
        except Exception as e:
            raise Exception(f"Failed to initialize SFinance: {str(e)}")
    return sf

def get_ticker(symbol: str):
    """Get ticker object with caching"""
    global ticker_cache
    
    symbol = symbol.upper()
    current_time = datetime.now()
    
    # Check if ticker exists in cache and is not expired
    if symbol in ticker_cache:
        cached_ticker, cache_time = ticker_cache[symbol]
        if current_time - cache_time < timedelta(hours=CACHE_EXPIRY_HOURS):
            print(f"Using cached ticker for {symbol}")
            return cached_ticker
        else:
            print(f"Cache expired for {symbol}, fetching new ticker")
            del ticker_cache[symbol]
    
    # Create new ticker and cache it
    print(f"Creating new ticker for {symbol}...")
    start_time = time.time()
    
    sf_instance = get_sfinance()
    ticker = sf_instance.ticker(symbol)
    
    end_time = time.time()
    print(f"Ticker creation took {end_time - start_time:.2f} seconds")
    
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
        print(f"Cleared expired cache for {symbol}")

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
    
    return {
        "active_cache_entries": active_cache,
        "expired_cache_entries": expired_cache,
        "total_cache_entries": len(ticker_cache),
        "cache_expiry_hours": CACHE_EXPIRY_HOURS
    }

def df_to_json(df: pd.DataFrame) -> str:
    """Convert DataFrame to JSON string"""
    if df.empty:
        return json.dumps({"error": "No data available"})
    return df.to_json(orient='records', indent=2)

@server.list_tools()
async def list_tools() -> List[types.Tool]:
    return [
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
        
        # Handle ticker-based tools
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
        
        else:
            raise ValueError(f"Unknown tool: {name}")
            
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