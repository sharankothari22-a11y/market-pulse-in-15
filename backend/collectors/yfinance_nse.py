# yfinance NSE collector for top Indian stocks
import yfinance as yf
import logging
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Top 10 NSE stocks by market cap
NSE_TOP_10 = [
    'RELIANCE.NS',
    'TCS.NS', 
    'HDFCBANK.NS',
    'INFY.NS',
    'ICICIBANK.NS',
    'HINDUNILVR.NS',
    'SBIN.NS',
    'BAJFINANCE.NS',
    'BHARTIARTL.NS',
    'KOTAKBANK.NS',
]

# Additional popular stocks
NSE_ADDITIONAL = [
    'IRFC.NS',
    'WIPRO.NS',
    'AXISBANK.NS',
    'LT.NS',
    'MARUTI.NS',
]

def get_stock_data(symbol: str) -> Dict[str, Any]:
    """Fetch stock data for a single symbol using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='2d')
        
        if hist.empty or len(hist) < 2:
            logger.warning(f"Insufficient data for {symbol}")
            return None
        
        price = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change_pct = ((price - prev) / prev) * 100
        volume = hist['Volume'].iloc[-1] if 'Volume' in hist.columns else 0
        
        # Get company name from info (may be slow, so we use a default)
        clean_symbol = symbol.replace('.NS', '')
        
        return {
            'symbol': clean_symbol,
            'ticker': symbol,
            'ltp': round(price, 2),
            'price': round(price, 2),
            'prev_close': round(prev, 2),
            'change': round(price - prev, 2),
            'change_percent': round(change_pct, 2),
            'volume': int(volume),
            'changeType': 'positive' if change_pct >= 0 else 'negative',
        }
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")
        return None


def fetch_nse_top_movers(symbols: List[str] = None, max_workers: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch stock data for multiple NSE symbols in parallel.
    
    Args:
        symbols: List of NSE symbols (e.g., ['RELIANCE.NS', 'TCS.NS'])
                 Defaults to top 10 NSE stocks if not provided.
        max_workers: Number of parallel threads
        
    Returns:
        List of stock data dictionaries sorted by absolute change %
    """
    if symbols is None:
        symbols = NSE_TOP_10
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(get_stock_data, symbol): symbol 
            for symbol in symbols
        }
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                if data:
                    results.append(data)
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
    
    # Sort by absolute change percentage (top movers)
    results.sort(key=lambda x: abs(x.get('change_percent', 0)), reverse=True)
    
    return results


def fetch_all_nse_stocks() -> List[Dict[str, Any]]:
    """Fetch data for all tracked NSE stocks (top 10 + additional)."""
    all_symbols = NSE_TOP_10 + NSE_ADDITIONAL
    return fetch_nse_top_movers(all_symbols)


# Quick test
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Fetching NSE top movers...")
    movers = fetch_nse_top_movers()
    for stock in movers:
        print(f"{stock['symbol']}: ₹{stock['ltp']} ({stock['change_percent']:+.2f}%)")
