# SFinance MCP Server

A Model Context Protocol (MCP) server that provides access to Indian stock market data. Built on top of the [SFinance package](https://github.com/shivakharbanda/sfinance).

Supports both **stdio** (Claude Desktop) and **HTTP** transports.

## Prerequisites

- Python 3.11.6 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- Google Chrome browser
- Screener.in account

## Installation

1. **Clone and setup**
   ```bash
   git clone https://github.com/shivakharbanda/sfinance-mcp-server.git
   cd sfinance-mcp-server
   uv sync
   ```

2. **Environment variables**
   Create a `.env` file in the project root:
   ```
   SCREENER_EMAIL=your-email@example.com
   SCREENER_PASSWORD=YourPassword123
   CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe
   SCREENER_URL=https://www.screener.in/
   ```

## Running the Server

### HTTP mode (remote / API access)

```bash
uv run python sfinance_server.py --transport http
```

The server starts at `http://0.0.0.0:8000/mcp`.

Custom host/port:
```bash
uv run python sfinance_server.py --transport http --host 127.0.0.1 --port 9000
```

Or via environment variables:
```bash
TRANSPORT=http HOST=0.0.0.0 PORT=8000 uv run python sfinance_server.py
```

Health check endpoint: `GET http://localhost:8000/health`

### Stdio mode (Claude Desktop)

```bash
uv run python sfinance_server.py
```

## Claude Desktop Configuration

### Option 1: uv run (Recommended)

**Windows:**
```json
{
  "mcpServers": {
    "sfinance": {
      "command": "uv",
      "args": [
        "run",
        "--directory", "C:\\path\\to\\sfinance-mcp-server",
        "python", "sfinance_server.py"
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
      "command": "uv",
      "args": [
        "run",
        "--directory", "/path/to/sfinance-mcp-server",
        "python", "sfinance_server.py"
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

### Option 2: HTTP transport (connect to a running server)

If you already have the server running in HTTP mode, point Claude Desktop at it:
```json
{
  "mcpServers": {
    "sfinance": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Configuration File Locations

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

## Features

- **Stock Analysis**: Company overview, financial statements, quarterly results, shareholding patterns, peer comparison
- **Document Access** *(login required)*: Announcements, annual reports, credit ratings, concall transcripts/PPTs
- **Document Download** *(login required)*: Batch download any document type to a local folder
- **Stock Screening** *(login required)*: Custom queries with financial parameters and pre-built templates
- **Indian Market Focus**: NSE/BSE listed companies via screener.in

## Available Tools

### Stock Data
| Tool | Description |
|------|-------------|
| `get_overview` | Company overview and about |
| `get_income_statement` | P&L statement |
| `get_balance_sheet` | Balance sheet |
| `get_cash_flow` | Cash flow statement |
| `get_quarterly_results` | Quarterly results |
| `get_shareholding` | Shareholding pattern |
| `get_peer_comparison` | Industry peer comparison |

### Documents *(login required)*
| Tool | Description |
|------|-------------|
| `get_announcements` | Recent or important company announcements |
| `get_annual_reports` | Annual report list with download URLs |
| `get_credit_ratings` | Credit rating documents |
| `get_concalls` | Concall transcripts, PPTs, and recordings |
| `download_documents` | Batch download documents to a local folder |

### Screening *(login required)*
| Tool | Description |
|------|-------------|
| `screen_stocks` | Custom stock screening with financial criteria |
| `get_screening_parameters` | Browse available screening parameters |

### Utilities
| Tool | Description |
|------|-------------|
| `check_login_status` | Verify screener.in login |
| `get_cache_stats` | Cache information |
| `clear_cache` | Clear ticker cache |

## Usage Examples

```
Get overview for RELIANCE
Get income statement for TCS
Get concalls for INFY
Download the last 3 annual reports for HDFCBANK to C:\Downloads\HDFCBANK
Screen stocks with Piotroski score > 7 AND Return on equity > 15
Find value stocks with Price to Earning < 15 AND Dividend yield > 3
```

## Prompt Templates

- **High Quality Stocks** - Strong fundamentals (Piotroski, ROE, P/E)
- **Value Stocks** - Undervalued opportunities (P/E, P/B, dividend yield)
- **Growth Stocks** - High-growth companies (sales/profit growth, ROE)
- **Custom Screener** - Build your own criteria

## Dependencies

- [sfinance](https://github.com/shivakharbanda/sfinance) - Core data library
- [fastmcp](https://gofastmcp.com) - MCP server framework (stdio + HTTP)
- pandas - Data handling
- python-dotenv - Environment variables

## License

Apache License 2.0

## Disclaimer

For educational purposes only. Always verify financial data from official sources before making investment decisions.

## Legal Notice

**Users are solely responsible for ensuring that their use of this software complies with the terms of service of any website they access.**

**This project is not affiliated with, endorsed by, or sponsored by Screener.in, Mittal Analytics Private Limited, or any other third-party data provider.**
