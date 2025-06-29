# SFinance MCP Server

A Model Context Protocol (MCP) server that provides access to Indian stock market data.Built on top of the [SFinance package](https://github.com/shivakharbanda/sfinance).

## Prerequisites

- Python 3.8 or higher
- Google Chrome browser
- Screener.in account

## Installation

1. **Clone and setup**
   ```bash
   git clone https://github.com/shivakharbanda/sfinance-mcp-server.git
   cd sfinance-mcp-server
   python -m venv .venv
   ```

2. **Activate virtual environment**
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment variables**
   Create `.env` file in project root:
   ```
   SCREENER_EMAIL=your-email@example.com
   SCREENER_PASSWORD=YourPassword123
   CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
   SCREENER_URL=https://www.screener.in/
   ```

## Configuration Options

### Option 1: Virtual Environment Activation (Recommended)

**Windows:**
```json
{
  "mcpServers": {
    "sfinance": {
      "command": "cmd",
      "args": [
        "/c",
        "cd /d C:\\path\\to\\your\\project\\sfinance-mcp-server && .venv\\Scripts\\activate && python sfinance_server.py"
      ],
      "env": {
        "SCREENER_EMAIL": "your-email@example.com",
        "SCREENER_PASSWORD": "YourPassword123",
        "CHROME_PATH": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "SCREENER_URL": "https://www.screener.in/"
      }
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "sfinance": {
      "command": "bash",
      "args": [
        "-c",
        "cd /path/to/your/project/sfinance-mcp-server && source .venv/bin/activate && python sfinance_server.py"
      ],
      "env": {
        "SCREENER_EMAIL": "your-email@example.com",
        "SCREENER_PASSWORD": "YourPassword123",
        "CHROME_PATH": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "SCREENER_URL": "https://www.screener.in/"
      }
    }
  }
}
```

### Option 2: Direct Python Path

**Windows:**
```json
{
  "mcpServers": {
    "sfinance": {
      "command": "C:\\path\\to\\your\\project\\sfinance-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\path\\to\\your\\project\\sfinance-mcp-server\\sfinance_server.py"
      ],
      "env": {
        "SCREENER_EMAIL": "your-email@example.com",
        "SCREENER_PASSWORD": "YourPassword123",
        "CHROME_PATH": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        "SCREENER_URL": "https://www.screener.in/"
      }
    }
  }
}
```

**macOS/Linux:**
```json
{
  "mcpServers": {
    "sfinance": {
      "command": "/path/to/your/project/sfinance-mcp-server/.venv/bin/python",
      "args": [
        "/path/to/your/project/sfinance-mcp-server/sfinance_server.py"
      ],
      "env": {
        "SCREENER_EMAIL": "your-email@example.com",
        "SCREENER_PASSWORD": "YourPassword123",
        "CHROME_PATH": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "SCREENER_URL": "https://www.screener.in/"
      }
    }
  }
}
```

## Configuration File Locations

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

## Required Changes

1. Replace `C:\\path\\to\\your\\project\\sfinance-mcp-server` with your actual project path
2. Update `SCREENER_EMAIL` and `SCREENER_PASSWORD` with your credentials
3. Verify Chrome path matches your installation
4. Restart Claude Desktop after configuration

## Features

- **Stock Analysis**: Company overview, financial statements, quarterly results, shareholding patterns
- **Stock Screening**: Custom queries with financial parameters and pre-built templates
- **Indian Market Focus**: NSE/BSE listed companies

## Usage

### Stock Analysis
```
Get overview for RELIANCE
Get income statement for TCS
Get quarterly results for HDFCBANK
```

### Stock Screening
```
Screen stocks with Piotroski score > 7 AND Return on equity > 15
Find value stocks with Price to Earning < 15 AND Dividend yield > 3
```

## Available Tools

### Stock Data
- `get_overview` - Company overview and metrics
- `get_income_statement` - P&L statement
- `get_balance_sheet` - Balance sheet data
- `get_cash_flow` - Cash flow statement
- `get_quarterly_results` - Quarterly results
- `get_shareholding` - Shareholding pattern
- `get_peer_comparison` - Industry comparison

### Screening
- `screen_stocks` - Custom stock screening
- `get_screening_parameters` - Available parameters

### Utilities
- `check_login_status` - Verify login status
- `get_cache_stats` - Cache information
- `clear_cache` - Clear cache

## Prompt Templates

- **High Quality Stocks** - Strong fundamentals
- **Value Stocks** - Undervalued opportunities  
- **Growth Stocks** - High-growth companies
- **Custom Screener** - Build your own criteria

## Dependencies

- [SFinance](https://github.com/shivakharbanda/sfinance) - Core library
- MCP - Model Context Protocol
- pandas - Data handling
- python-dotenv - Environment variables

## License

Apache License 2.0

## Disclaimer

For educational purposes only. Always verify financial data from official sources before making investment decisions.

## Legal Notice

⚠️ **Users are solely responsible for ensuring that their use of this software complies with the terms of service of any website they access.**

**This project is not affiliated with, endorsed by, or sponsored by Screener.in, Mittal Analytics Private Limited, or any other third-party data provider.**