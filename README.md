# Yahoo Finance MCP Server

[![Website](https://img.shields.io/badge/Website-🌐-purple)](https://www.agentx.so/mcp/yahoo-finance)
[![Discord](https://img.shields.io/badge/Discord-Join-7289DA?logo=discord&logoColor=white)](https://discord.gg/dJkAbUq9rU)

📈 **A Model Context Protocol (MCP) server that lets your AI interact with Yahoo Finance** - get comprehensive stock market data, news, financials, and more.

## ✨ Features

- 📊 **Stock Data** - Get comprehensive ticker information including company details, financials, and trading metrics
- 📰 **News Feed** - Fetch recent news articles related to specific stock symbols
- 🔍 **Search** - Find stocks, ETFs, and other financial instruments with news results
- 🏆 **Top Entities** - Get top performing companies, ETFs, and mutual funds by sector
- 📈 **Price History** - Fetch historical price data with customizable periods and intervals
- ⚡ **Options Chain** - Get option chain data for stocks including calls and puts
- 💰 **Earnings** - Access earnings data including upcoming earnings dates
- 🌐 **Proxy Support** - Works with HTTP/HTTPS/SOCKS proxies
- 🚀 **Fast & Async** - Non-blocking operations using asyncio
- 🔧 **Easy Integration** - Standard MCP protocol for AI assistants

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip or uvx package manager
- (Optional) Proxy server for better reliability

### Installation

#### Using uvx (Recommended)

```bash
# Install with namespace
uvx yahoo-finance-server
```

#### Using pip

```bash
pip install yahoo-finance-server
```

#### From source

```bash
git clone https://github.com/AgentX-ai/AgentX-mcp-servers.git
cd AgentX-mcp-servers/yahoo_finance_server
pip install -e .
```

### Configuration

#### Proxy Setup (Recommended)

For better reliability and to avoid rate limiting, set up a proxy:

```bash
# HTTP/HTTPS proxy
export PROXY_URL="http://proxy.example.com:8080"

# SOCKS proxy with auth
export PROXY_URL="socks5://user:pass@127.0.0.1:1080/"
```

#### Running the Server

```bash
# Basic run (stdio transport)
yahoo-finance-server

# Run with proxy
PROXY_URL="http://127.0.0.1:7890" yahoo-finance-server

# Run with HTTP transport
yahoo-finance-server --transport http --host localhost --port 3000

# Run with HTTP transport and proxy
PROXY_URL="http://127.0.0.1:7890" yahoo-finance-server --transport http --host 0.0.0.0 --port 8080
```

##### Transport Options

**Stdio Transport (Default)**
- Best for development and AI assistant integration
- Communication via stdin/stdout pipes
- Usage: `yahoo-finance-server` or `yahoo-finance-server --transport stdio`

**HTTP Transport**
- StreamableHttp transport (replaces deprecated SSE)
- Allows web-based connections and remote access
- Usage: `yahoo-finance-server --transport http --host localhost --port 3000`
- Inspector URL: `http://localhost:3000`

## 🛠️ API Reference

### Available Tools

#### 1. **get-ticker-info**

Get comprehensive stock information including company details, financials, and trading metrics.

```json
{
  "name": "get-ticker-info",
  "arguments": {
    "symbol": "AAPL"
  }
}
```

#### 2. **get-ticker-news**

Get recent news articles for a stock symbol.

```json
{
  "name": "get-ticker-news",
  "arguments": {
    "symbol": "AAPL",
    "count": 10
  }
}
```

#### 3. **search**

Search for stocks, ETFs, and other financial instruments with related news.

```json
{
  "name": "search",
  "arguments": {
    "query": "Apple Inc",
    "count": 10
  }
}
```

#### 4. **get-top-entities**

Get top performing entities in a sector.

```json
{
  "name": "get-top-entities",
  "arguments": {
    "entity_type": "companies", // Options: "etfs", "mutual_funds", "companies", "growth_companies", "performing_companies"
    "sector": "technology", // See supported sectors below
    "count": 10
  }
}
```

Supported sectors:

- basic-materials
- communication-services
- consumer-cyclical
- consumer-defensive
- energy
- financial-services
- healthcare
- industrials
- real-estate
- technology
- utilities

#### 5. **get-price-history**

Get historical price data with customizable periods and intervals.

```json
{
  "name": "get-price-history",
  "arguments": {
    "symbol": "AAPL",
    "period": "1y", // Options: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
    "interval": "1d" // Options: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
  }
}
```

#### 6. **ticker-option-chain**

Get option chain data for stocks.

```json
{
  "name": "ticker-option-chain",
  "arguments": {
    "symbol": "AAPL",
    "option_type": "call", // Options: "call", "put", "both"
    "date": "2024-01-19" // Optional: YYYY-MM-DD format
  }
}
```

#### 7. **ticker-earning**

Get earnings data including historical and upcoming earnings.

```json
{
  "name": "ticker-earning",
  "arguments": {
    "symbol": "AAPL",
    "period": "annual", // Options: "annual", "quarterly"
    "date": "2023-12-31" // Optional: YYYY-MM-DD format
  }
}
```

## 🧪 Testing

### Using MCP Inspector

**With Stdio Transport (Default)**
```bash
npx @modelcontextprotocol/inspector yahoo-finance-server
```

**With HTTP Transport**
```bash
# Terminal 1: Start server with HTTP transport
yahoo-finance-server --transport http --host localhost --port 3000

# Terminal 2: Connect inspector to HTTP server
npx @modelcontextprotocol/inspector http://localhost:3000
```

### Manual Testing

```bash
python -c "
import asyncio
from yahoo_finance_server.helper import get_ticker_info

async def test():
    info = await get_ticker_info('AAPL')
    print(f'✅ Stock: {info[\"longName\"]}')

asyncio.run(test())
"
```

## 📋 Requirements

- Python 3.11+
- yfinance==0.2.62
- requests>=2.31.0
- pandas>=2.0.0
- mcp>=1.9.3

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Homepage**: [GitHub Repository](https://github.com/AgentX-ai/AgentX-mcp-servers/tree/main/yahoo_finance_server)
- **Issues**: [Report Issues](https://github.com/AgentX-ai/AgentX-mcp-servers/issues)
- **MCP Documentation**: [Model Context Protocol](https://modelcontextprotocol.io)

---

**Made with ❤️ for the finance community**
