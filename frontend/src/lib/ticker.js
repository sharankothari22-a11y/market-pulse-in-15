// Indian equity ticker validation.
// Accepts: 2-10 uppercase letters (e.g. RELIANCE), optionally suffixed
// with .NS or .BO (e.g. RELIANCE.NS, TATAMOTORS.BO).
const TICKER_RE = /^[A-Z]{2,10}(\.(NS|BO))?$/;

export const TICKER_ERROR_MSG =
  'Indian tickers only. Try: RELIANCE, TCS, HDFCBANK';

export function validateTicker(ticker) {
  const cleaned = String(ticker ?? '').trim().toUpperCase();
  if (!cleaned) return { ok: false, value: '', error: TICKER_ERROR_MSG };
  if (!TICKER_RE.test(cleaned)) {
    return { ok: false, value: cleaned, error: TICKER_ERROR_MSG };
  }
  return { ok: true, value: cleaned, error: null };
}
