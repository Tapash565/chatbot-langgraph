"""Stock price tool using Alpha Vantage."""
import requests
import time
from langchain_core.tools import tool

from backend.core.config import config
from backend.core.logging import get_logger, log_span

logger = get_logger(__name__)


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch the latest stock price for a given symbol.

    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')

    Returns:
        A dictionary with stock data or error message
    """
    logger.info("stock_price_request", symbol=symbol)

    api_key = config.ALPHA_VANTAGE_API_KEY
    if not api_key:
        logger.warning("stock_price_missing_api_key")
        return {
            "error": "ALPHA_VANTAGE_API_KEY environment variable is not set",
            "symbol": symbol,
        }

    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"

    with log_span("stock_price_fetch", symbol=symbol):
        try:
            start_time = time.perf_counter()
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "stock_price_success",
                symbol=symbol,
                duration_ms=round(duration_ms, 2),
            )
            return response.json()
        except requests.exceptions.Timeout:
            logger.error("stock_price_timeout", symbol=symbol)
            return {
                "error": f"Request timed out while fetching stock price for {symbol}",
                "symbol": symbol,
            }
        except requests.exceptions.RequestException as e:
            logger.error("stock_price_error", symbol=symbol, error=str(e))
            return {
                "error": f"Request failed: {str(e)}",
                "symbol": symbol,
            }
        except Exception as e:
            logger.error(
                "stock_price_exception",
                symbol=symbol,
                error=str(e),
                error_type=type(e).__name__,
            )
            return {
                "error": f"Unexpected error: {str(e)}",
                "symbol": symbol,
            }
