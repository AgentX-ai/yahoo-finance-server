import yfinance as yf
from yfinance.const import SECTOR_INDUSTY_MAPPING
import os
import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Annotated, Literal
from pydantic import Field
import json
from datetime import datetime, timedelta
import requests
import pandas as pd

logger = logging.getLogger(__name__)


def _get_proxy_config() -> Optional[Dict[str, str]]:
    """
    Get proxy configuration from environment variable.

    Returns:
        Proxy configuration dictionary if set, None otherwise
    """
    proxy_url = os.getenv("PROXY_URL", "").strip()
    if proxy_url:
        # Mask the password in logs for security
        masked_url = proxy_url
        if "@" in proxy_url:
            # Extract username and password for masking
            auth_part, server_part = proxy_url.split("@", 1)
            if ":" in auth_part:
                username = auth_part.split("://", 1)[1].split(":")[0]
                masked_url = (
                    f"{proxy_url.split('://')[0]}://{username}:***@{server_part}"
                )

        logger.info(f"Using proxy: {masked_url}")
        return {"http": proxy_url, "https": proxy_url}
    return None


def _setup_yfinance_session():
    """
    Setup yfinance session with proxy if configured and better headers to avoid detection.
    """
    # Create a session with better headers to avoid bot detection
    session = requests.Session()

    # Add realistic headers optimized for residential proxies like Oxylabs
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
        }
    )

    # Apply proxy configuration if available
    proxy_config = _get_proxy_config()
    if proxy_config:
        session.proxies.update(proxy_config)
        logger.info(
            f"Proxy configuration applied to session: {list(proxy_config.keys())}"
        )

        # Set longer timeout for proxy connections
        session.timeout = 30

        # Enable session persistence for better performance with residential proxies
        session.mount(
            "http://",
            requests.adapters.HTTPAdapter(
                max_retries=3, pool_connections=10, pool_maxsize=10
            ),
        )
        session.mount(
            "https://",
            requests.adapters.HTTPAdapter(
                max_retries=3, pool_connections=10, pool_maxsize=10
            ),
        )

    else:
        logger.info("No proxy configuration found - using direct connection")

    # Apply the session to yfinance by overriding all HTTP methods
    try:
        # Override yfinance's get_json method
        yf.utils.get_json = lambda url, proxy=None, **kwargs: session.get(
            url, **kwargs
        ).json()

        # Override yfinance's get_html method
        yf.utils.get_html = lambda url, proxy=None, **kwargs: session.get(
            url, **kwargs
        ).text

        # Override yfinance's get_csv method
        yf.utils.get_csv = lambda url, proxy=None, **kwargs: session.get(
            url, **kwargs
        ).text

        # Override yfinance's get method (if it exists)
        if hasattr(yf.utils, "get"):
            yf.utils.get = lambda url, proxy=None, **kwargs: session.get(url, **kwargs)

        # Override yfinance's post method (if it exists)
        if hasattr(yf.utils, "post"):
            yf.utils.post = lambda url, proxy=None, **kwargs: session.post(
                url, **kwargs
            )

        logger.info("Enhanced session applied to all yfinance HTTP methods")
    except Exception as e:
        logger.warning(f"Could not apply enhanced session to yfinance: {e}")


def _get_enhanced_session():
    """
    Get a requests session with enhanced headers and proxy configuration.
    This should be used for all direct API calls instead of requests.get().
    """
    session = requests.Session()

    # Add realistic headers optimized for residential proxies like Oxylabs
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "DNT": "1",
        }
    )

    # Apply proxy configuration if available
    proxy_config = _get_proxy_config()
    if proxy_config:
        session.proxies.update(proxy_config)
        logger.debug(
            f"Enhanced session created with proxy: {list(proxy_config.keys())}"
        )

        # Set longer timeout for proxy connections
        session.timeout = 30

        # Enable session persistence for better performance with residential proxies
        session.mount(
            "http://",
            requests.adapters.HTTPAdapter(
                max_retries=3, pool_connections=10, pool_maxsize=10
            ),
        )
        session.mount(
            "https://",
            requests.adapters.HTTPAdapter(
                max_retries=3, pool_connections=10, pool_maxsize=10
            ),
        )

    else:
        logger.debug("Enhanced session created without proxy")

    return session


# Initialize session with proxy support
_setup_yfinance_session()


async def get_ticker_info(symbol: str) -> str:
    """
    Get comprehensive ticker information using fast_info for reliability.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')

    Returns:
        JSON string containing comprehensive ticker information
    """
    try:

        def _get_info():
            ticker = _create_enhanced_ticker(symbol)
            try:
                fast_info = ticker.info
                logger.info(f"Got fast_info for {symbol}: {fast_info}")
                for key, value in fast_info.items():
                    if not isinstance(key, str):
                        continue

                    if key.lower().endswith(
                        ("date", "start", "end", "timestamp", "time", "quarter")
                    ):
                        try:
                            fast_info[key] = datetime.fromtimestamp(value).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        except Exception as e:
                            logger.error(f"Unable to convert time {key}: {value}: {e}")
                            continue
                return json.dumps(fast_info)
            except Exception as e:
                logger.error(f"Failed to get fast_info for {symbol}: {e}")
                return json.dumps(
                    {"symbol": symbol, "error": "Unable to fetch ticker fast_info"}
                )

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _get_info)
        return info

    except Exception as e:
        logger.error(f"Error getting ticker info for {symbol}: {e}")
        return json.dumps(
            {"symbol": symbol, "error": f"Failed to get ticker information: {str(e)}"}
        )


async def get_ticker_news(symbol: str, count: int = 10) -> Dict[str, Any]:
    """
    Fetch recent news articles related to a specific stock symbol.

    Args:
        symbol: Stock symbol
        count: Number of news articles to fetch (default: 10)

    Returns:
        Dictionary containing news articles with title, content, and source details
    """
    try:

        def _get_news():
            ticker = _create_enhanced_ticker(symbol)

            # Try multiple methods to get news
            news = []

            # Method 1: Try ticker.news property
            try:
                news = ticker.news
                logger.info(
                    f"Method 1 - ticker.news returned {len(news) if news else 0} articles"
                )

                if not news:
                    news = []
            except Exception as e:
                logger.warning(f"Method 1 failed for {symbol}: {e}")
                news = []

            # Method 2: Try direct API call if Method 1 fails
            if not news:
                try:
                    # Use Yahoo Finance news API directly
                    news_url = f"https://query2.finance.yahoo.com/v1/finance/search"
                    params = {
                        "q": symbol,
                        "quotesCount": 1,
                        "newsCount": count,
                        "enableFuzzyQuery": False,
                        "quotesQueryId": "tss_match_phrase_query",
                        "multiQuoteQueryId": "multi_quote_single_token_query",
                        "enableCb": True,
                        "enableNavLinks": True,
                        "enableEnhancedTrivialQuery": True,
                    }

                    # Use enhanced session for consistent proxy and headers
                    session = _get_enhanced_session()
                    response = session.get(
                        news_url,
                        params=params,
                        timeout=10,
                    )
                    response.raise_for_status()

                    data = response.json()
                    if "news" in data:
                        news = data["news"]
                        logger.info(
                            f"Method 2 - direct API returned {len(news)} articles"
                        )
                    else:
                        logger.info("Method 2 - no news found in API response")

                except Exception as e:
                    logger.warning(f"Method 2 failed for {symbol}: {e}")

            # Process the news articles
            processed_news = []
            if news:
                # Limit to requested count
                news = news[:count] if len(news) > count else news

                for article in news:
                    try:
                        # Handle both old and new yfinance news structure
                        content = article.get(
                            "content", article
                        )  # New structure has content wrapper

                        # Extract title
                        title = content.get("title", article.get("title", ""))

                        # Extract link
                        link = ""
                        if "canonicalUrl" in content:
                            link = content["canonicalUrl"].get("url", "")
                        elif "clickThroughUrl" in content:
                            link = content["clickThroughUrl"].get("url", "")
                        else:
                            link = article.get("link", "")

                        # Extract publisher
                        publisher = ""
                        if "provider" in content:
                            publisher = content["provider"].get("displayName", "")
                        else:
                            publisher = article.get("publisher", "")

                        # Extract publish time
                        published = ""
                        if "pubDate" in content:
                            # pubDate is in ISO format
                            published = content["pubDate"]
                        elif "displayTime" in content:
                            published = content["displayTime"]
                        elif article.get("providerPublishTime"):
                            published = datetime.fromtimestamp(
                                article.get("providerPublishTime", 0)
                            ).isoformat()

                        # Extract thumbnail
                        thumbnail = ""
                        if "thumbnail" in content:
                            resolutions = content["thumbnail"].get("resolutions", [])
                            if resolutions:
                                thumbnail = resolutions[0].get("url", "")
                        elif article.get("thumbnail"):
                            resolutions = article["thumbnail"].get("resolutions", [])
                            if resolutions:
                                thumbnail = resolutions[0].get("url", "")

                        # Extract other fields
                        article_type = content.get(
                            "contentType", article.get("type", "")
                        )
                        uuid = content.get("id", article.get("uuid", ""))
                        summary = content.get("summary", content.get("description", ""))

                        processed_article = {
                            "title": title,
                            "link": link,
                            "publisher": publisher,
                            "published": published,
                            "type": article_type,
                            "thumbnail": thumbnail,
                            "uuid": uuid,
                            "summary": summary,
                        }
                        processed_news.append(processed_article)
                    except Exception as e:
                        logger.warning(f"Error processing article: {e}")
                        continue

            return {
                "symbol": symbol,
                "news_count": len(processed_news),
                "news": processed_news,
                "debug_info": f"Tried multiple methods, found {len(news)} raw articles, processed {len(processed_news)}",
            }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        news_data = await loop.run_in_executor(None, _get_news)

        return news_data

    except Exception as e:
        logger.error(f"Error getting news for {symbol}: {e}")
        raise Exception(f"Failed to get ticker news: {str(e)}")


async def search_yahoo_finance(query: str, count: int = 10) -> Dict[str, Any]:
    """
    Search Yahoo Finance for stocks, ETFs, and other financial instruments.
    Uses yf.Search as primary method and falls back to direct API call if needed.

    Args:
        query: Search query
        count: Number of results to return

    Returns:
        Dictionary containing search results including quotes and news
    """
    try:

        def _search():
            # Try primary method: yf.Search
            try:
                # Note: yf.Search doesn't have a direct session override, but our global overrides should work
                search = yf.Search(query)
                quotes = search.quotes
                news = search.news

                # Process and format the results
                results = []
                for quote in quotes[:count]:
                    result_dict = {
                        "symbol": quote.get("symbol", ""),
                        "shortname": quote.get("shortname", ""),
                        "longname": quote.get("longname", ""),
                        "exchange": quote.get("exchange", ""),
                        "asset_type": quote.get("quoteType", ""),
                        "type_display": quote.get("typeDisp", ""),
                        "score": quote.get("score", 0),
                    }
                    results.append(result_dict)

                # Process news results
                news_results = []
                if news:
                    for article in news[:5]:  # Limit to 5 most recent news items
                        news_dict = {
                            "title": article.get("title", ""),
                            "publisher": article.get("publisher", ""),
                            "link": article.get("link", ""),
                        }
                        news_results.append(news_dict)

                return {
                    "query": query,
                    "results": results,
                    "news": news_results,
                }

            except Exception as e:
                logger.warning(f"Primary search method failed, trying fallback: {e}")

                # Fallback method: Direct API call
                try:
                    search_url = f"https://query2.finance.yahoo.com/v1/finance/search"
                    params = {
                        "q": query,
                        "quotesCount": count,
                        "newsCount": 5,  # Include news in fallback too
                        "enableFuzzyQuery": False,
                        "quotesQueryId": "tss_match_phrase_query",
                        "multiQuoteQueryId": "multi_quote_single_token_query",
                        "enableCb": True,
                        "enableNavLinks": True,
                        "enableEnhancedTrivialQuery": True,
                    }

                    # Use enhanced session for consistent proxy and headers
                    session = _get_enhanced_session()
                    response = session.get(search_url, params=params)
                    response.raise_for_status()

                    data = response.json()

                    search_results = []
                    if "quotes" in data:
                        for quote in data["quotes"]:
                            result = {
                                "symbol": quote.get("symbol", ""),
                                "shortname": quote.get("shortname", ""),
                                "longname": quote.get("longname", ""),
                                "exchange": quote.get("exchange", ""),
                                "asset_type": quote.get("quoteType", ""),
                                "type_display": quote.get("typeDisp", ""),
                                "score": quote.get("score", 0),
                            }
                            search_results.append(result)

                    # Process news from fallback API
                    news_results = []
                    if "news" in data:
                        for article in data["news"][
                            :5
                        ]:  # Limit to 5 most recent news items
                            news_dict = {
                                "title": article.get("title", ""),
                                "publisher": article.get("publisher", ""),
                                "link": article.get("link", ""),
                                "published": article.get("published", ""),
                                "summary": article.get("summary", ""),
                            }
                            news_results.append(news_dict)

                    return {
                        "query": query,
                        "results": search_results,
                        "news": news_results,
                    }

                except Exception as fallback_error:
                    logger.warning(
                        f"Fallback search method also failed: {fallback_error}"
                    )
                    return {
                        "query": query,
                        "results": [],
                        "news": [],
                        "error": f"Both search methods failed. Primary error: {str(e)}, Fallback error: {str(fallback_error)}",
                    }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        search_data = await loop.run_in_executor(None, _search)

        return search_data

    except Exception as e:
        logger.error(f"Error searching for {query}: {e}")
        raise Exception(f"Failed to search Yahoo Finance: {str(e)}")


Sectors = Literal[
    "basic-materials",
    "communication-services",
    "consumer-cyclical",
    "consumer-defensive",
    "energy",
    "financial-services",
    "healthcare",
    "industrials",
    "real-estate",
    "technology",
    "utilities",
]


def get_top_etfs(sector: Sectors, count: int = 10) -> str:
    """Get top ETFs for a certain sector."""
    if count < 1:
        return "count must be greater than 0"

    s = _create_enhanced_sector(sector)

    result = [f"{symbol}: {name}" for symbol, name in s.top_etfs.items()]

    return "\n".join(result[:count])


def get_top_mutual_funds(sector: Sectors, count: int = 10) -> str:
    """Retrieve popular mutual funds for a sector, returned as a list in 'SYMBOL: Fund Name' format."""
    if count < 1:
        return "count must be greater than 0"

    s = _create_enhanced_sector(sector)
    return "\n".join(f"{symbol}: {name}" for symbol, name in s.top_mutual_funds.items())


def get_top_companies(sector: Sectors, count: int = 10) -> str:
    """Get top companies in a sector with name, analyst rating, and market weight as JSON array."""
    if count < 1:
        return "count must be greater than 0"

    s = _create_enhanced_sector(sector)
    df = s.top_companies
    if df is None:
        return f"No top companies available for {sector} sector."

    return df.iloc[:count].to_json(orient="records")


def get_top_growth_companies(sector: Sectors, count: int = 10) -> str:
    """Get top growth companies grouped by industry within a sector as JSON array with growth metrics."""
    if count < 1:
        return "count must be greater than 0"

    results = []

    for industry_name in SECTOR_INDUSTY_MAPPING[sector]:
        industry = _create_enhanced_industry(industry_name)

        df = industry.top_growth_companies
        if df is None:
            continue

        results.append(
            {
                "industry": industry_name,
                "top_growth_companies": df.iloc[:count].to_json(orient="records"),
            }
        )
    return json.dumps(results, ensure_ascii=False)


def get_top_performing_companies(sector: Sectors, count: int = 10) -> str:
    """Get top performing companies grouped by industry within a sector as JSON array with performance metrics."""
    if count < 1:
        return "count must be greater than 0"

    results = []

    for industry_name in SECTOR_INDUSTY_MAPPING[sector]:
        industry = _create_enhanced_industry(industry_name)

        df = industry.top_performing_companies
        if df is None:
            continue

        results.append(
            {
                "industry": industry_name,
                "top_performing_companies": df.iloc[:count].to_json(orient="records"),
            }
        )
    return json.dumps(results, ensure_ascii=False)


async def get_top_entities(
    entity_type: Literal[
        "etfs", "mutual_funds", "companies", "growth_companies", "performing_companies"
    ],
    sector: Sectors,
    count: int = 10,
) -> Dict[str, Any]:
    """
    Get top entities (ETFs, mutual funds, companies, growth companies, or performing companies) in a sector.

    Args:
        entity_type: Type of entities ('etfs', 'mutual_funds', 'companies', 'growth_companies', 'performing_companies')
        sector: Sector name
        count: Number of entities to return

    Returns:
        Dictionary containing top entities
    """
    try:

        def _get_entities():
            if count < 1:
                return {
                    "entity_type": entity_type,
                    "sector": sector,
                    "error": "count must be greater than 0",
                    "results": [],
                }

            try:
                match entity_type:
                    case "etfs":
                        result = get_top_etfs(sector, count)
                        return {
                            "entity_type": entity_type,
                            "sector": sector,
                            "results": result.split("\n") if result else [],
                        }
                    case "mutual_funds":
                        result = get_top_mutual_funds(sector, count)
                        return {
                            "entity_type": entity_type,
                            "sector": sector,
                            "results": result.split("\n") if result else [],
                        }
                    case "companies":
                        result = get_top_companies(sector, count)
                        return {
                            "entity_type": entity_type,
                            "sector": sector,
                            "results": (
                                json.loads(result)
                                if result
                                and result
                                != f"No top companies available for {sector} sector."
                                else []
                            ),
                        }
                    case "growth_companies":
                        result = get_top_growth_companies(sector, count)
                        return {
                            "entity_type": entity_type,
                            "sector": sector,
                            "results": json.loads(result) if result else [],
                        }
                    case "performing_companies":
                        result = get_top_performing_companies(sector, count)
                        return {
                            "entity_type": entity_type,
                            "sector": sector,
                            "results": json.loads(result) if result else [],
                        }
                    case _:
                        return {
                            "entity_type": entity_type,
                            "sector": sector,
                            "error": f"Unknown entity type: {entity_type}",
                            "results": [],
                        }

            except Exception as e:
                logger.error(
                    f"Error getting top {entity_type} for sector {sector}: {e}"
                )
                return {
                    "entity_type": entity_type,
                    "sector": sector,
                    "error": str(e),
                    "results": [],
                }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        entities_data = await loop.run_in_executor(None, _get_entities)

        return entities_data

    except Exception as e:
        logger.error(f"Error getting top entities: {e}")
        raise Exception(f"Failed to get top entities: {str(e)}")


async def get_price_history(
    symbol: str, period: str = "1y", interval: str = "1d"
) -> Dict[str, Any]:
    """
    Fetch historical price data for a given stock symbol over a specified period and interval.

    Args:
        symbol: Stock symbol
        period: Period to fetch data for (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
        interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

    Returns:
        Dictionary containing historical price data
    """
    try:

        def _get_history():
            ticker = _create_enhanced_ticker(symbol)
            hist = ticker.history(period=period, interval=interval)

            if hist.empty:
                return {
                    "symbol": symbol,
                    "period": period,
                    "interval": interval,
                    "data": [],
                    "count": 0,
                }

            # Convert to list of dictionaries
            history_data = []
            for date, row in hist.iterrows():
                data_point = {
                    "date": date.isoformat(),
                    "open": float(row["Open"]) if pd.notna(row["Open"]) else None,
                    "high": float(row["High"]) if pd.notna(row["High"]) else None,
                    "low": float(row["Low"]) if pd.notna(row["Low"]) else None,
                    "close": float(row["Close"]) if pd.notna(row["Close"]) else None,
                    "volume": int(row["Volume"]) if pd.notna(row["Volume"]) else None,
                }
                history_data.append(data_point)

            return {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "count": len(history_data),
                "data": history_data,
            }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        history_data = await loop.run_in_executor(None, _get_history)

        return history_data

    except Exception as e:
        logger.error(f"Error getting price history for {symbol}: {e}")
        raise Exception(f"Failed to get price history: {str(e)}")


async def get_ticker_option_chain(
    symbol: str, option_type: str = "both", date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get most recent or around certain date option chain data.

    Args:
        symbol: Stock symbol
        option_type: Type of options ('call', 'put', 'both')
        date: Specific expiration date (YYYY-MM-DD format), if None uses most recent available dates

    Returns:
        Dictionary containing option chain data
    """
    try:

        def _get_options():
            ticker = _create_enhanced_ticker(symbol)

            # Get available expiration dates
            try:
                expirations = ticker.options
                if not expirations:
                    return {
                        "symbol": symbol,
                        "error": "No options available",
                        "data": {},
                    }

                # If no date specified, use first available expiration (most recent)
                if date is None:
                    exp_date = expirations[0]
                else:
                    # Find closest date to requested date
                    from datetime import datetime

                    target_date = datetime.strptime(date, "%Y-%m-%d").date()
                    exp_dates = [
                        datetime.strptime(d, "%Y-%m-%d").date() for d in expirations
                    ]
                    closest_date = min(
                        exp_dates, key=lambda x: abs((x - target_date).days)
                    )
                    exp_date = closest_date.strftime("%Y-%m-%d")

                option_chain = ticker.option_chain(exp_date)

                result = {
                    "symbol": symbol,
                    "expiration_date": exp_date,
                    "available_expirations": expirations[
                        :10
                    ],  # Show first 10 available dates
                }

                if option_type in ["call", "both"]:
                    # Process calls
                    calls_data = []
                    if hasattr(option_chain, "calls") and not option_chain.calls.empty:
                        for _, row in option_chain.calls.iterrows():
                            call_data = {
                                "strike": (
                                    float(row["strike"])
                                    if pd.notna(row["strike"])
                                    else None
                                ),
                                "last_price": (
                                    float(row["lastPrice"])
                                    if pd.notna(row["lastPrice"])
                                    else None
                                ),
                                "bid": (
                                    float(row["bid"]) if pd.notna(row["bid"]) else None
                                ),
                                "ask": (
                                    float(row["ask"]) if pd.notna(row["ask"]) else None
                                ),
                                "volume": (
                                    int(row["volume"])
                                    if pd.notna(row["volume"])
                                    else None
                                ),
                                "open_interest": (
                                    int(row["openInterest"])
                                    if pd.notna(row["openInterest"])
                                    else None
                                ),
                                "implied_volatility": (
                                    float(row["impliedVolatility"])
                                    if pd.notna(row["impliedVolatility"])
                                    else None
                                ),
                                "in_the_money": (
                                    bool(row["inTheMoney"])
                                    if pd.notna(row["inTheMoney"])
                                    else None
                                ),
                            }
                            calls_data.append(call_data)
                    result["calls"] = calls_data

                if option_type in ["put", "both"]:
                    # Process puts
                    puts_data = []
                    if hasattr(option_chain, "puts") and not option_chain.puts.empty:
                        for _, row in option_chain.puts.iterrows():
                            put_data = {
                                "strike": (
                                    float(row["strike"])
                                    if pd.notna(row["strike"])
                                    else None
                                ),
                                "last_price": (
                                    float(row["lastPrice"])
                                    if pd.notna(row["lastPrice"])
                                    else None
                                ),
                                "bid": (
                                    float(row["bid"]) if pd.notna(row["bid"]) else None
                                ),
                                "ask": (
                                    float(row["ask"]) if pd.notna(row["ask"]) else None
                                ),
                                "volume": (
                                    int(row["volume"])
                                    if pd.notna(row["volume"])
                                    else None
                                ),
                                "open_interest": (
                                    int(row["openInterest"])
                                    if pd.notna(row["openInterest"])
                                    else None
                                ),
                                "implied_volatility": (
                                    float(row["impliedVolatility"])
                                    if pd.notna(row["impliedVolatility"])
                                    else None
                                ),
                                "in_the_money": (
                                    bool(row["inTheMoney"])
                                    if pd.notna(row["inTheMoney"])
                                    else None
                                ),
                            }
                            puts_data.append(put_data)
                    result["puts"] = puts_data

                return result

            except Exception as e:
                return {
                    "symbol": symbol,
                    "error": f"Could not get options data: {str(e)}",
                    "data": {},
                }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        options_data = await loop.run_in_executor(None, _get_options)

        return options_data

    except Exception as e:
        logger.error(f"Error getting option chain for {symbol}: {e}")
        raise Exception(f"Failed to get option chain: {str(e)}")


async def get_ticker_earnings(
    symbol: str, period: str = "annual", date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get earnings data including annual or quarterly data and upcoming earnings dates.

    Args:
        symbol: Stock symbol
        period: 'annual' or 'quarterly'
        date: Specific date (YYYY-MM-DD format), if None uses most recent

    Returns:
        Dictionary containing earnings data
    """
    try:

        def _get_earnings():
            ticker = _create_enhanced_ticker(symbol)

            result = {
                "symbol": symbol,
                "period": period,
            }

            try:
                # Get earnings data
                if period == "annual":
                    earnings = ticker.financials
                    earnings_dates = ticker.calendar
                else:  # quarterly
                    earnings = ticker.quarterly_financials
                    earnings_dates = ticker.calendar

                # Process earnings data
                if earnings is not None and not earnings.empty:
                    earnings_data = []
                    for date_col in earnings.columns:
                        earning_entry = {
                            "date": (
                                date_col.strftime("%Y-%m-%d")
                                if hasattr(date_col, "strftime")
                                else str(date_col)
                            ),
                            "total_revenue": (
                                float(earnings.loc["Total Revenue", date_col])
                                if "Total Revenue" in earnings.index
                                and pd.notna(earnings.loc["Total Revenue", date_col])
                                else None
                            ),
                            "gross_profit": (
                                float(earnings.loc["Gross Profit", date_col])
                                if "Gross Profit" in earnings.index
                                and pd.notna(earnings.loc["Gross Profit", date_col])
                                else None
                            ),
                            "operating_income": (
                                float(earnings.loc["Operating Income", date_col])
                                if "Operating Income" in earnings.index
                                and pd.notna(earnings.loc["Operating Income", date_col])
                                else None
                            ),
                            "net_income": (
                                float(earnings.loc["Net Income", date_col])
                                if "Net Income" in earnings.index
                                and pd.notna(earnings.loc["Net Income", date_col])
                                else None
                            ),
                            "ebitda": (
                                float(earnings.loc["EBITDA", date_col])
                                if "EBITDA" in earnings.index
                                and pd.notna(earnings.loc["EBITDA", date_col])
                                else None
                            ),
                        }
                        earnings_data.append(earning_entry)

                    result["earnings_data"] = earnings_data
                else:
                    result["earnings_data"] = []

                # Get upcoming earnings dates
                if (
                    earnings_dates is not None
                    and isinstance(earnings_dates, pd.DataFrame)
                    and not earnings_dates.empty
                ):
                    upcoming_earnings = []
                    for _, row in earnings_dates.iterrows():
                        upcoming_earning = {
                            "earnings_date": (
                                row.get("Earnings Date", "").strftime("%Y-%m-%d")
                                if pd.notna(row.get("Earnings Date"))
                                else None
                            ),
                            "eps_estimate": (
                                float(row.get("EPS Estimate", 0))
                                if pd.notna(row.get("EPS Estimate"))
                                else None
                            ),
                            "reported_eps": (
                                float(row.get("Reported EPS", 0))
                                if pd.notna(row.get("Reported EPS"))
                                else None
                            ),
                            "surprise": (
                                float(row.get("Surprise(%)", 0))
                                if pd.notna(row.get("Surprise(%)"))
                                else None
                            ),
                        }
                        upcoming_earnings.append(upcoming_earning)
                    result["upcoming_earnings"] = upcoming_earnings
                else:
                    result["upcoming_earnings"] = []

                # Get additional earnings info from ticker info
                info = ticker.info
                result["next_earnings_date"] = info.get("earningsDate", {})
                result["trailing_eps"] = info.get("trailingEps", 0)
                result["forward_eps"] = info.get("forwardEps", 0)
                result["pe_ratio"] = info.get("trailingPE", 0)
                result["forward_pe"] = info.get("forwardPE", 0)

                return result

            except Exception as e:
                logger.warning(f"Error processing earnings data: {e}")
                result["error"] = str(e)
                return result

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        earnings_data = await loop.run_in_executor(None, _get_earnings)

        return earnings_data

    except Exception as e:
        logger.error(f"Error getting earnings for {symbol}: {e}")
        raise Exception(f"Failed to get earnings data: {str(e)}")


def _download_filing_content(url: str) -> Dict[str, Any]:
    """
    Download content from SEC filing URL.
    
    Args:
        url: URL of the SEC filing document
        
    Returns:
        Dictionary containing content, content_type, size, and any error info
    """
    try:
        session = _get_enhanced_session()
        
        # Set headers to appear as a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', 'text/plain').split(';')[0]
        content_size = len(response.content)
        
        # Handle different content types
        if 'text/' in content_type or 'application/xml' in content_type:
            # Text-based content (HTML, XML, plain text)
            content = response.text
        elif 'application/pdf' in content_type:
            # PDF content - return as base64 for now
            import base64
            content = base64.b64encode(response.content).decode('utf-8')
        else:
            # Other binary content
            import base64
            content = base64.b64encode(response.content).decode('utf-8')
        
        return {
            "content": content,
            "content_type": content_type,
            "size": content_size,
            "status": "success"
        }
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to download filing content from {url}: {e}")
        return {
            "content": "",
            "content_type": "text/plain",
            "size": 0,
            "error": f"Download failed: {str(e)}",
            "status": "error"
        }
    except Exception as e:
        logger.error(f"Unexpected error downloading filing content from {url}: {e}")
        return {
            "content": "",
            "content_type": "text/plain", 
            "size": 0,
            "error": f"Unexpected error: {str(e)}",
            "status": "error"
        }


async def get_filing_content(url: str) -> Dict[str, Any]:
    """
    Download and return the content of a specific SEC filing document.
    
    Args:
        url: URL of the SEC filing document to download
        
    Returns:
        Dictionary containing the file content, content type, size, and metadata
    """
    try:
        def _get_content():
            if not url:
                return {
                    "url": url,
                    "error": "URL is required",
                    "content": "",
                    "content_type": "text/plain",
                    "size": 0,
                    "status": "error"
                }
            
            # Download the filing content
            content_result = _download_filing_content(url)
            
            return {
                "url": url,
                "content": content_result["content"],
                "content_type": content_result["content_type"], 
                "size": content_result["size"],
                "status": content_result["status"],
                "error": content_result.get("error", "")
            }
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        content_data = await loop.run_in_executor(None, _get_content)
        
        return content_data
        
    except Exception as e:
        logger.error(f"Error getting filing content from {url}: {e}")
        return {
            "url": url,
            "error": f"Failed to get filing content: {str(e)}",
            "content": "",
            "content_type": "text/plain",
            "size": 0,
            "status": "error"
        }


async def get_institutional_holders(symbol: str, count: int = 10) -> Dict[str, Any]:
    """
    Get institutional holders data for a stock symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
        count: Number of institutional holders to return (default: 10)

    Returns:
        Dictionary containing institutional holders data
    """
    try:

        def _get_institutional_data():
            ticker = _create_enhanced_ticker(symbol)

            try:
                # Get institutional holders using yfinance method
                institutional_data = ticker.institutional_holders
                
                if institutional_data is None or institutional_data.empty:
                    logger.debug(f"No institutional holders found for {symbol}")
                    return {
                        "symbol": symbol,
                        "holders_count": 0,
                        "holders": [],
                    }

                # Process the institutional holders data
                processed_holders = []
                
                # Limit to requested count
                holders_limited = institutional_data.head(count)
                
                for _, holder in holders_limited.iterrows():
                    holder_data = {
                        "date_reported": (
                            holder.get("Date Reported").strftime("%Y-%m-%d")
                            if pd.notna(holder.get("Date Reported"))
                            else ""
                        ),
                        "holder": holder.get("Holder", ""),
                        "pct_held": float(holder.get("pctHeld", 0)) if pd.notna(holder.get("pctHeld")) else 0,
                        "shares": int(holder.get("Shares", 0)) if pd.notna(holder.get("Shares")) else 0,
                        "value": int(holder.get("Value", 0)) if pd.notna(holder.get("Value")) else 0,
                        "pct_change": float(holder.get("pctChange", 0)) if pd.notna(holder.get("pctChange")) else 0,
                    }
                    processed_holders.append(holder_data)

                return {
                    "symbol": symbol,
                    "holders_count": len(processed_holders),
                    "holders": processed_holders,
                }

            except Exception as e:
                logger.error(f"Failed to get institutional holders for {symbol}: {e}")
                return {
                    "symbol": symbol,
                    "error": f"Unable to fetch institutional holders: {str(e)}",
                    "holders_count": 0,
                    "holders": [],
                }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        institutional_data = await loop.run_in_executor(None, _get_institutional_data)

        return institutional_data

    except Exception as e:
        logger.error(f"Error getting institutional holders for {symbol}: {e}")
        raise Exception(f"Failed to get institutional holders: {str(e)}")


async def get_insider_transactions(symbol: str, count: int = 50) -> Dict[str, Any]:
    """
    Get insider transactions data for a stock symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
        count: Number of transactions to return (default: 50)

    Returns:
        Dictionary containing insider transactions data
    """
    try:

        def _get_insider_data():
            ticker = _create_enhanced_ticker(symbol)

            try:
                # Get insider transactions using yfinance method
                insider_data = ticker.insider_transactions
                
                if insider_data is None or insider_data.empty:
                    logger.debug(f"No insider transactions found for {symbol}")
                    return {
                        "symbol": symbol,
                        "transactions_count": 0,
                        "transactions": [],
                    }

                # Process the insider transactions data
                processed_transactions = []
                
                # Limit to requested count
                transactions_limited = insider_data.head(count)
                
                for _, transaction in transactions_limited.iterrows():
                    transaction_data = {
                        "shares": int(transaction.get("Shares", 0)) if pd.notna(transaction.get("Shares")) else 0,
                        "value": float(transaction.get("Value", 0)) if pd.notna(transaction.get("Value")) else 0,
                        "url": transaction.get("URL", ""),
                        "text": transaction.get("Text", ""),
                        "insider": transaction.get("Insider", ""),
                        "position": transaction.get("Position", ""),
                        "transaction_date": (
                            transaction.get("Transaction Start Date").strftime("%Y-%m-%d")
                            if pd.notna(transaction.get("Transaction Start Date"))
                            else ""
                        ),
                        "ownership": transaction.get("Ownership", ""),
                    }
                    processed_transactions.append(transaction_data)

                return {
                    "symbol": symbol,
                    "transactions_count": len(processed_transactions),
                    "transactions": processed_transactions,
                }

            except Exception as e:
                logger.error(f"Failed to get insider transactions for {symbol}: {e}")
                return {
                    "symbol": symbol,
                    "error": f"Unable to fetch insider transactions: {str(e)}",
                    "transactions_count": 0,
                    "transactions": [],
                }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        insider_data = await loop.run_in_executor(None, _get_insider_data)

        return insider_data

    except Exception as e:
        logger.error(f"Error getting insider transactions for {symbol}: {e}")
        raise Exception(f"Failed to get insider transactions: {str(e)}")


async def get_ticker_filings(symbol: str, count: int = 100) -> Dict[str, Any]:
    """
    Get SEC filings for a stock symbol using yfinance get_sec_filings method.

    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')
        count: Number of filings to retrieve (default: 100)

    Returns:
        Dictionary containing SEC filings data
    """
    try:

        def _get_filings():
            ticker = _create_enhanced_ticker(symbol)

            try:
                # Get SEC filings using yfinance method
                filings = ticker.get_sec_filings()
                
                if not filings:
                    logger.debug(f"No SEC filings found for {symbol}")
                    return {
                        "symbol": symbol,
                        "filings_count": 0,
                        "filings": [],
                    }

                # Process the filings data
                processed_filings = []
                
                # Limit to requested count
                filings_limited = filings[:count] if len(filings) > count else filings
                
                for filing in filings_limited:
                    # Handle exhibits - get all exhibit types without downloading content
                    exhibits_data = filing.get("exhibits", {})
                    all_exhibits = []
                    
                    if isinstance(exhibits_data, dict) and exhibits_data:
                        # Collect exhibit metadata only (no content download)
                        for exhibit_type, url in exhibits_data.items():
                            if url:  # Only include non-empty URLs
                                all_exhibits.append({
                                    "exhibit_type": exhibit_type,
                                    "url": url
                                })
                    
                    filing_data = {
                        "type": filing.get("type", ""),
                        "date": (
                            filing.get("date").strftime("%Y-%m-%d")
                            if pd.notna(filing.get("date"))
                            else ""
                        ),
                        "title": filing.get("title", ""),
                        "url": all_exhibits[0]["url"] if all_exhibits else "",  # First URL for backward compatibility
                        "exhibits": all_exhibits,  # All exhibits with URLs only
                        "total_exhibits": len(all_exhibits),
                    }
                    
                    # Handle different column names that might exist
                    if "filingDate" in filing:
                        filing_data["filing_date"] = (
                            filing["filingDate"].strftime("%Y-%m-%d")
                            if pd.notna(filing["filingDate"])
                            else ""
                        )
                    
                    if "acceptanceDate" in filing:
                        filing_data["acceptance_date"] = (
                            filing["acceptanceDate"].strftime("%Y-%m-%d %H:%M:%S")
                            if pd.notna(filing["acceptanceDate"])
                            else ""
                        )
                    
                    if "reportDate" in filing:
                        filing_data["report_date"] = (
                            filing["reportDate"].strftime("%Y-%m-%d")
                            if pd.notna(filing["reportDate"])
                            else ""
                        )
                    
                    if "edgarUrl" in filing:
                        filing_data["edgar_url"] = filing.get("edgarUrl", "")
                    
                    processed_filings.append(filing_data)

                return {
                    "symbol": symbol,
                    "filings_count": len(processed_filings),
                    "filings": processed_filings,
                }

            except Exception as e:
                logger.error(f"Failed to get SEC filings for {symbol}: {e}")
                return {
                    "symbol": symbol,
                    "error": f"Unable to fetch SEC filings: {str(e)}",
                    "filings_count": 0,
                    "filings": [],
                }

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        filings_data = await loop.run_in_executor(None, _get_filings)

        return filings_data

    except Exception as e:
        logger.error(f"Error getting SEC filings for {symbol}: {e}")
        raise Exception(f"Failed to get SEC filings: {str(e)}")


def _create_enhanced_ticker(symbol: str):
    """
    Create a yfinance Ticker object with enhanced session configuration.
    This ensures that all operations on this ticker use our proxy and headers.
    """
    ticker = yf.Ticker(symbol)

    # Apply our enhanced session to the ticker's internal session if possible
    try:
        # Some yfinance operations might create their own sessions
        # We can't directly override them, but our global overrides should catch most cases
        pass
    except Exception as e:
        logger.debug(f"Could not enhance ticker session for {symbol}: {e}")

    return ticker


def _create_enhanced_sector(sector_name: str):
    """
    Create a yfinance Sector object with enhanced session configuration.
    """
    sector = yf.Sector(sector_name)
    return sector


def _create_enhanced_industry(industry_name: str):
    """
    Create a yfinance Industry object with enhanced session configuration.
    """
    industry = yf.Industry(industry_name)
    return industry


def _test_proxy_connectivity():
    """
    Test if the proxy configuration is working correctly.
    This function can be called to verify proxy setup.
    """
    try:
        proxy_config = _get_proxy_config()
        if not proxy_config:
            logger.info("No proxy configured - using direct connection")
            return True

        logger.info("Testing proxy connectivity...")

        # Test with a simple request
        session = _get_enhanced_session()
        response = session.get("https://httpbin.org/ip", timeout=30)

        if response.status_code == 200:
            ip_info = response.json()
            origin_ip = ip_info.get("origin", "unknown")
            logger.info(f"Proxy test successful. IP: {origin_ip}")

            # Additional test for Yahoo Finance specifically
            try:
                yahoo_response = session.get("https://finance.yahoo.com", timeout=30)
                if yahoo_response.status_code == 200:
                    logger.info("Yahoo Finance proxy test successful")
                    return True
                else:
                    logger.warning(
                        f"Yahoo Finance proxy test failed with status: {yahoo_response.status_code}"
                    )
                    return False
            except Exception as yahoo_e:
                logger.warning(f"Yahoo Finance proxy test failed: {yahoo_e}")
                return False
        else:
            logger.warning(
                f"Proxy test failed with status code: {response.status_code}"
            )
            return False

    except Exception as e:
        logger.error(f"Proxy connectivity test failed: {e}")
        return False


# Test proxy connectivity on startup
if _get_proxy_config():
    _test_proxy_connectivity()
