import json
import argparse
import mcp.types as types

from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Literal


# Import helper functions for Yahoo Finance functionality
from .helper import (
    get_ticker_info,
    get_ticker_news,
    search_yahoo_finance,
    get_top_entities,
    get_price_history,
    get_ticker_option_chain,
    get_ticker_earnings,
    get_ticker_filings,
    get_filing_content,
    get_insider_transactions,
    get_institutional_holders,
    Sectors
)

mcp = FastMCP(
    name="yahoo-finance-server",
    json_response=False  # Use MCP format instead of JSON
)

@mcp.tool(
    name="get-ticker-info",
    description="Retrieve comprehensive stock data including company info, financials, trading metrics and governance data"
)
async def _handle_get_ticker_info(
    symbol: Annotated[str, Field(description="Stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')")]
) -> list[types.TextContent]:
    """
    Handle get-ticker-info tool execution using only fast_info fields.
    """
    try:
        symbol = symbol.upper()
        ticker_info = await get_ticker_info(symbol)

        # ticker_info is already a JSON string from helper.py
        return [
            types.TextContent(
                type="text",
                text=ticker_info,
            )
        ]

    except Exception as e:
        error_response = json.dumps(
            {"symbol": symbol, "error": str(e)}
        )
        return [
            types.TextContent(
                type="text",
                text=error_response,
            )
        ]


@mcp.tool(
    name="get-ticker-news",
    description="Fetch recent news articles related to a specific stock symbol with title, content, and source details"
)
async def _handle_get_ticker_news(
    symbol: Annotated[str, Field(description="Stock ticker symbol to get news for")],
    count: Annotated[int, Field(description="Number of news articles to fetch (default: 10, maximum: 50)", ge=1, le=50)] = 10
) -> list[types.TextContent]:
    """
    Handle get-ticker-news tool execution.
    """
    try:
        symbol = symbol.upper()

        news_data = await get_ticker_news(symbol, count)

        if not news_data.get("news"):
            return [
                types.TextContent(
                    type="text",
                    text=f"📰 No news found for {symbol}",
                )
            ]

        # Format the response nicely
        news_text = f"""📰 **Recent News for {symbol}** ({news_data['news_count']} articles)

"""

        for i, article in enumerate(news_data["news"], 1):
            summary_text = (
                f"\n• **Summary:** {article['summary']}"
                if article.get("summary") and article["summary"].strip()
                else ""
            )
            news_text += f"""**{i}. {article['title']}**
• **Publisher:** {article['publisher']}
• **Published:** {article['published']}
• **Link:** {article['link']}{summary_text}

"""

        return [
            types.TextContent(
                type="text",
                text=news_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving news for {symbol}: {str(e)}",
            )
        ]


@mcp.tool(
    name="search",
    description="Search Yahoo Finance for stocks, ETFs, and other financial instruments"
)
async def _handle_search(
    query: Annotated[str, Field(description="Search query (company name, ticker symbol, etc.)")],
    count: Annotated[int, Field(description="Number of search results to return (default: 10, maximum: 25)", ge=1, le=25)] = 10
) -> list[types.TextContent]:
    """
    Handle search tool execution.
    """
    try:

        search_data = await search_yahoo_finance(query, count)

        if not search_data.get("results") and not search_data.get("news"):
            return [
                types.TextContent(
                    type="text",
                    text=f"🔍 No results found for '{query}'",
                )
            ]

        return [
            types.TextContent(
                type="text",
                text=json.dumps(search_data),
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error searching for '{query}': {str(e)}",
            )
        ]


@mcp.tool(
    name="get-top-entities",
    description="Get top entities (ETFs, mutual funds, companies, growth companies, or performing companies) in a sector"
)
async def _handle_get_top_entities(
    entity_type: Annotated[Literal["etfs", "mutual_funds", "companies", "growth_companies", "performing_companies"], Field(description="Type of entities to retrieve")],
    sector: Annotated[Sectors, Field(description=f"Sector name {Sectors.__args__}")],
    count: Annotated[int, Field(description="Number of entities to return (default: 10, maximum: 20)", ge=1, le=20)] = 10
) -> list[types.TextContent]:
    """
    Handle get-top-entities tool execution.
    """
    try:

        entities_data = await get_top_entities(entity_type, sector, count)

        if not entities_data.get("results"):
            return [
                types.TextContent(
                    type="text",
                    text=f"🏆 No {entity_type} found for sector '{sector}'",
                )
            ]

        return [
            types.TextContent(
                type="text",
                text=json.dumps(entities_data),
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving top entities: {str(e)}",
            )
        ]


@mcp.tool(
    name="get-price-history",
    description="Fetch historical price data for a given stock symbol over a specified period and interval"
)
async def _handle_get_price_history(
    symbol: Annotated[str, Field(description="Stock ticker symbol")],
    period: Annotated[Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"], Field(description="Period to fetch data for")] = "1y",
    interval: Annotated[Literal["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"], Field(description="Data interval")] = "1d"
) -> list[types.TextContent]:
    """
    Handle get-price-history tool execution.
    """
    try:
        symbol = symbol.upper()

        history_data = await get_price_history(symbol, period, interval)

        if not history_data.get("data"):
            return [
                types.TextContent(
                    type="text",
                    text=f"📈 No price history found for {symbol}",
                )
            ]

        # Format the response nicely - show last 10 data points
        history_text = f"""📈 **Price History for {symbol}**
**Period:** {period} | **Interval:** {interval} | **Data Points:** {history_data['count']}

**Recent Data (Last 10 points):**
"""

        recent_data = history_data["data"][-10:]  # Get last 10 data points
        for data_point in recent_data:
            history_text += f"""• **{data_point['date'][:10]}**: Open: ${data_point['open']:.2f}, High: ${data_point['high']:.2f}, Low: ${data_point['low']:.2f}, Close: ${data_point['close']:.2f}, Volume: {data_point['volume']:,}
"""

        # Add summary statistics
        closes = [d["close"] for d in history_data["data"] if d["close"] is not None]
        if closes:
            min_price = min(closes)
            max_price = max(closes)
            avg_price = sum(closes) / len(closes)

            history_text += f"""
**Summary Statistics:**
• **Period Low:** ${min_price:.2f}
• **Period High:** ${max_price:.2f}
• **Average Price:** ${avg_price:.2f}
• **Total Change:** {((closes[-1] - closes[0]) / closes[0] * 100):.2f}%
"""

        return [
            types.TextContent(
                type="text",
                text=history_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving price history for {symbol}: {str(e)}",
            )
        ]


@mcp.tool(
    name="ticker-option-chain",
    description="Get most recent or around certain date option chain data. Parameters include call or put, and date. If no date, use most recent top 10 day forward dates"
)
async def _handle_ticker_option_chain(
    symbol: Annotated[str, Field(description="Stock ticker symbol")],
    option_type: Annotated[Literal["call", "put", "both"], Field(description="Type of options to retrieve")] = "both",
    date: Annotated[str | None, Field(description="Specific expiration date in YYYY-MM-DD format. If not provided, uses most recent available dates")] = None
) -> list[types.TextContent]:
    """
    Handle ticker-option-chain tool execution.
    """
    try:
        symbol = symbol.upper()

        options_data = await get_ticker_option_chain(symbol, option_type, date)

        if options_data.get("error"):
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ {options_data['error']}",
                )
            ]

        # Format the response nicely
        options_text = f"""⚡ **Option Chain for {symbol}**
**Expiration Date:** {options_data.get('expiration_date', 'N/A')}
**Available Expirations:** {', '.join(options_data.get('available_expirations', [])[:5])}

"""

        if option_type in ["call", "both"] and "calls" in options_data:
            options_text += "**📈 CALL Options:**\n"
            calls = options_data["calls"][:10]  # Show first 10
            for call in calls:
                options_text += f"""• Strike: ${call['strike']:.2f} | Last: ${call['last_price']:.2f} | Bid: ${call['bid']:.2f} | Ask: ${call['ask']:.2f} | Vol: {call['volume']} | OI: {call['open_interest']} | IV: {call['implied_volatility']:.2%}
"""
            options_text += "\n"

        if option_type in ["put", "both"] and "puts" in options_data:
            options_text += "**📉 PUT Options:**\n"
            puts = options_data["puts"][:10]  # Show first 10
            for put in puts:
                options_text += f"""• Strike: ${put['strike']:.2f} | Last: ${put['last_price']:.2f} | Bid: ${put['bid']:.2f} | Ask: ${put['ask']:.2f} | Vol: {put['volume']} | OI: {put['open_interest']} | IV: {put['implied_volatility']:.2%}
"""

        return [
            types.TextContent(
                type="text",
                text=options_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving option chain for {symbol}: {str(e)}",
            )
        ]


@mcp.tool(
    name="ticker-earning",
    description="Get earnings data including annual or quarterly data, and upcoming earnings dates. Parameters include annual or quarter, and date. If no date, use most recent, also include the date of upcoming earning time if available"
)
async def _handle_ticker_earning(
    symbol: Annotated[str, Field(description="Stock ticker symbol")],
    period: Annotated[Literal["annual", "quarterly"], Field(description="Earnings period to retrieve")] = "annual",
    date: Annotated[str | None, Field(description="Specific date in YYYY-MM-DD format. If not provided, uses most recent data")] = None
) -> list[types.TextContent]:
    """
    Handle ticker-earning tool execution.
    """
    try:
        symbol = symbol.upper()

        earnings_data = await get_ticker_earnings(symbol, period, date)

        if earnings_data.get("error"):
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Error retrieving earnings: {earnings_data['error']}",
                )
            ]

        # Format the response nicely
        earnings_text = f"""💰 **Earnings Data for {symbol}**
**Period:** {period.title()}

**Key Metrics:**
• **Trailing EPS:** ${earnings_data.get('trailing_eps', 0):.2f}
• **Forward EPS:** ${earnings_data.get('forward_eps', 0):.2f}
• **P/E Ratio:** {earnings_data.get('pe_ratio', 0):.2f}
• **Forward P/E:** {earnings_data.get('forward_pe', 0):.2f}

"""

        # Historical earnings data
        if earnings_data.get("earnings_data"):
            earnings_text += f"**Historical {period.title()} Earnings:**\n"
            recent_earnings = earnings_data["earnings_data"][:4]  # Show last 4
            for earning in recent_earnings:
                earnings_text += f"""• **{earning['date']}**: Revenue: ${earning['total_revenue']:,} | Net Income: ${earning['net_income']:,} | EBITDA: ${earning['ebitda']:,}
"""
            earnings_text += "\n"

        # Upcoming earnings
        if earnings_data.get("upcoming_earnings"):
            earnings_text += "**Upcoming Earnings:**\n"
            for upcoming in earnings_data["upcoming_earnings"]:
                earnings_text += f"""• **Date:** {upcoming['earnings_date']} | **EPS Est:** ${upcoming['eps_estimate']:.2f}
"""

        return [
            types.TextContent(
                type="text",
                text=earnings_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving earnings for {symbol}: {str(e)}",
            )
        ]

@mcp.tool(
    name="get-insider-transactions",
    description="Retrieve insider trading transactions for a stock symbol including details on purchases, sales, and stock grants by company insiders"
)
async def _handle_get_insider_transactions(
    symbol: Annotated[str, Field(description="Stock ticker symbol to get insider transactions for")],
    count: Annotated[int, Field(description="Number of insider transactions to fetch (default: 50, maximum: 100)", ge=1)] = 50
) -> list[types.TextContent]:
    """
    Handle get-insider-transactions tool execution.
    """
    try:
        symbol = symbol.upper()

        insider_data = await get_insider_transactions(symbol, count)

        if insider_data.get("error"):
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Error retrieving insider transactions: {insider_data['error']}",
                )
            ]

        if not insider_data.get("transactions"):
            return [
                types.TextContent(
                    type="text",
                    text=f"📈 No insider transactions found for {symbol}",
                )
            ]

        # Format the response nicely
        insider_text = f"""📈 **Insider Transactions for {symbol}** ({insider_data['transactions_count']} transactions)

"""

        for i, transaction in enumerate(insider_data["transactions"], 1):
            # Format shares and value
            shares_str = f"{transaction['shares']:,}" if transaction['shares'] > 0 else "N/A"
            value_str = f"${transaction['value']:,.2f}" if transaction['value'] > 0 else "N/A"
            
            # Format ownership type
            ownership_desc = {
                'D': 'Direct',
                'I': 'Indirect', 
                'B': 'Beneficial'
            }.get(transaction['ownership'], transaction['ownership'])

            insider_text += f"""**{i}. {transaction['insider']}**
👤 **Position:** {transaction['position']}
📅 **Date:** {transaction['transaction_date']}
📊 **Shares:** {shares_str} | **Value:** {value_str} | **Ownership:** {ownership_desc}
💬 **Details:** {transaction['text']}

"""

        return [
            types.TextContent(
                type="text",
                text=insider_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving insider transactions for {symbol}: {str(e)}",
            )
        ]

@mcp.tool(
    name="get-institutional-holders",
    description="Retrieve institutional holders data for a stock symbol including major institutional investors, their holdings percentages, and recent changes"
)
async def _handle_get_institutional_holders(
    symbol: Annotated[str, Field(description="Stock ticker symbol to get institutional holders for")],
    count: Annotated[int, Field(description="Number of institutional holders to fetch (default: 10, maximum: 50)", ge=1, le=50)] = 10
) -> list[types.TextContent]:
    """
    Handle get-institutional-holders tool execution.
    """
    try:
        symbol = symbol.upper()

        institutional_data = await get_institutional_holders(symbol, count)

        if institutional_data.get("error"):
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Error retrieving institutional holders: {institutional_data['error']}",
                )
            ]

        if not institutional_data.get("holders"):
            return [
                types.TextContent(
                    type="text",
                    text=f"🏢 No institutional holders found for {symbol}",
                )
            ]

        # Format the response nicely
        institutional_text = f"""🏢 **Institutional Holders for {symbol}** ({institutional_data['holders_count']} holders)

"""

        for i, holder in enumerate(institutional_data["holders"], 1):
            # Format shares and value with commas
            shares_str = f"{holder['shares']:,}" if holder['shares'] > 0 else "N/A"
            value_str = f"${holder['value']:,}" if holder['value'] > 0 else "N/A"
            
            # Format percentage held and change
            pct_held_str = f"{holder['pct_held']:.2%}" if holder['pct_held'] > 0 else "N/A"
            pct_change_str = f"{holder['pct_change']:+.2%}" if holder['pct_change'] != 0 else "0.00%"

            institutional_text += f"""**{i}. {holder['holder']}**
📅 **Date Reported:** {holder['date_reported']}
📊 **Shares Held:** {shares_str} | **Percentage:** {pct_held_str}
💰 **Value:** {value_str} | **Change:** {pct_change_str}

"""

        return [
            types.TextContent(
                type="text",
                text=institutional_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving institutional holders for {symbol}: {str(e)}",
            )
        ]

@mcp.tool(
    name="get-sec-filings",
    description="Retrieve recent SEC filings for a stock symbol including 10-K, 10-Q, 8-K and other regulatory filings with document details and links"
)
async def _handle_get_sec_filings(
    symbol: Annotated[str, Field(description="Stock ticker symbol to get SEC filings for")],
    count: Annotated[int, Field(description="Number of SEC filings to fetch (default: 100)", ge=1)] = 100
) -> list[types.TextContent]:
    """
    Handle get-sec-filings tool execution.
    """
    try:
        filings_data = await get_ticker_filings(symbol, count)

        if filings_data.get("error"):
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Error retrieving SEC filings: {filings_data['error']}",
                )
            ]

        if not filings_data.get("filings"):
            return [
                types.TextContent(
                    type="text",
                    text=f"📋 No SEC filings found for {symbol}",
                )
            ]

        # Format the response nicely
        filings_text = f"""📋 **SEC Filings for {symbol}** ({filings_data['filings_count']} filings)

"""

        for i, filing in enumerate(filings_data["filings"], 1):
            filing_date = filing.get("date") or filing.get("filing_date", "")
            acceptance_date = filing.get("acceptance_date", "")
            report_date = filing.get("report_date", "")
            edgar_url = filing.get("edgar_url", "")
            
            date_info = f"📅 **Date:** {filing_date}"
            if acceptance_date:
                date_info += f" | **Accepted:** {acceptance_date}"
            if report_date:
                date_info += f" | **Report Date:** {report_date}"
            
            # Handle exhibits - show all available documents (URLs only, no content)
            exhibits_info = ""
            if filing.get("exhibits") and len(filing["exhibits"]) > 0:
                exhibits_info = f"\n📄 **Documents ({filing.get('total_exhibits', 0)}):**"
                for exhibit in filing["exhibits"]:
                    exhibits_info += f"\n  • **{exhibit['exhibit_type']}**: {exhibit['url']}"
            elif edgar_url:
                exhibits_info = f"\n🔗 **EDGAR Link:** {edgar_url}"
            elif filing.get("url"):
                exhibits_info = f"\n🔗 **Document Link:** {filing['url']}"
                
            # Add note about content retrieval
            if filing.get("exhibits") and len(filing["exhibits"]) > 0:
                exhibits_info += f"\n💡 **Note:** Use get-filing-content tool with URLs above to retrieve document content"

            filings_text += f"""**{i}. {filing['type']}**
📝 **Title:** {filing.get('title', 'N/A')}
{date_info}{exhibits_info}

"""

        # Return the main summary as text, but we could extend this to return
        # individual documents as EmbeddedResource for binary content
        results = [
            types.TextContent(
                type="text",
                text=filings_text,
            )
        ]
        
        # Optionally, we could add individual documents as embedded resources
        # for direct access to file content (especially for PDFs, images, etc.)
        # This would allow tools to access the raw file content directly
        for filing in filings_data["filings"]:
            for exhibit in filing.get("exhibits", []):
                if exhibit.get("content") and not exhibit.get("error"):
                    # For binary content (PDFs, etc.), we could add as EmbeddedResource
                    if exhibit.get("content_type") in ["application/pdf", "image/png", "image/jpeg"]:
                        # Note: This would require the content to be properly formatted
                        # For now, keeping as text summary, but structure is ready for expansion
                        pass
        
        return results

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving SEC filings for {symbol}: {str(e)}",
            )
        ]

@mcp.tool(
    name="get-filing-content",
    description="Download and retrieve the full content of a specific SEC filing document by URL"
)
async def _handle_get_filing_content(
    url: Annotated[str, Field(description="URL of the SEC filing document to download (obtained from get-sec-filings tool)")]
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle get-filing-content tool execution.
    """
    try:
        content_data = await get_filing_content(url)
        
        if content_data.get("error"):
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Error retrieving filing content: {content_data['error']}",
                )
            ]
        
        # Format the response with content info and preview
        content_text = f"""📄 **SEC Filing Content**
🔗 **URL:** {content_data['url']}
📊 **Content Type:** {content_data['content_type']}
📏 **Size:** {content_data['size']} bytes
✅ **Status:** {content_data['status']}

"""
        
        # Add content based on type and size
        if content_data.get("content"):
            content = content_data["content"]
            
            if content_data["content_type"].startswith("text/") or "xml" in content_data["content_type"]:
                # For text content, show the full content
                content_text += f"""**📋 Content:**
```
{content}
```"""
            elif content_data["content_type"] == "application/pdf":
                # For PDF, show that it's base64 encoded
                content_text += f"""**📋 Content:** PDF document (base64 encoded)
**💡 Note:** This is a PDF file encoded in base64 format. The content can be decoded and saved as a PDF file.

**🔍 Base64 Content Preview:**
```
{content[:500]}...
```"""
            else:
                # For other binary content
                content_text += f"""**📋 Content:** Binary file (base64 encoded)
**💡 Note:** This is a binary file encoded in base64 format.

**🔍 Base64 Content Preview:**
```
{content[:500]}...
```"""
        
        return [
            types.TextContent(
                type="text",
                text=content_text,
            )
        ]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"❌ Error retrieving filing content for {url}: {str(e)}",
            )
        ]


async def main():
    """Main entry point for the Yahoo Finance MCP server."""
    parser = argparse.ArgumentParser(description="Yahoo Finance MCP Server")
    parser.add_argument(
        "--transport", 
        choices=["stdio", "http"], 
        default="stdio",
        help="Transport method (stdio or http)"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP server (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP server (default: 8000)"
    )
    
    args = parser.parse_args()
    
    if args.transport == "http":
        print(f"Starting Yahoo Finance MCP Server with HTTP transport on http://{args.host}:{args.port}")
        print(f"Inspector URL: http://{args.host}:{args.port}")
        
        try:
            mcp.settings.host = args.host
            mcp.settings.port = args.port
            await mcp.run_streamable_http_async()
            
        except ImportError as e:
            print(f"❌ HTTP transport dependencies not available: {e}")
            print("Install required dependencies: pip install uvicorn starlette")
            print("Or use stdio transport: python -m src.yahoo_finance_server --transport stdio")
            return
    else:
        print("Starting Yahoo Finance MCP Server with stdio transport")
        # Use stdio transport for MCP communication
        await mcp.run_stdio_async()
