// Vercel serverless function: market quote proxy.
//
// The digest site is static, so the browser has to fetch live prices itself —
// but Yahoo's API blocks cross-site browser calls (CORS). This function makes
// the request server-side, where CORS doesn't apply, and hands back a small
// JSON payload. Runs in well under a second, so it fits comfortably inside
// Vercel's function time limit.
//
//   GET /api/quotes?symbols=^DJI,^GSPC,^IXIC
//   -> [{ symbol, price, prevClose, change, changePct, spark: [...] }, ...]

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

// Only these symbols may be requested, so the endpoint can't be used as an
// open proxy for arbitrary URLs.
const ALLOWED = new Set([
  "YM=F", "ES=F", "NQ=F", "GC=F", "CL=F",              // futures
  "^DJI", "^GSPC", "^IXIC", "^RUT", "^VIX",            // US indices
  "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN",             // mega-cap stocks
  "META", "AVGO", "TSLA", "BRK-B", "TSM",              // alternates
]);

async function fetchOne(symbol) {
  const url =
    "https://query1.finance.yahoo.com/v8/finance/chart/" +
    encodeURIComponent(symbol) +
    "?range=1d&interval=5m";

  const res = await fetch(url, { headers: { "User-Agent": UA } });
  if (!res.ok) throw new Error("upstream " + res.status);

  const data = await res.json();
  const result = data?.chart?.result?.[0];
  if (!result) throw new Error("no result");

  const meta = result.meta || {};
  const price = meta.regularMarketPrice;
  // Previous close is the right baseline for "change today"; fall back to the
  // first point of the session if Yahoo omits it.
  const closes = (result.indicators?.quote?.[0]?.close || []).filter(
    (v) => typeof v === "number"
  );
  const prevClose =
    typeof meta.chartPreviousClose === "number"
      ? meta.chartPreviousClose
      : closes[0];

  if (typeof price !== "number" || typeof prevClose !== "number") {
    throw new Error("missing price");
  }

  // Thin the sparkline down to ~40 points to keep the payload small.
  const step = Math.max(1, Math.ceil(closes.length / 40));
  const spark = closes.filter((_, i) => i % step === 0);

  return {
    symbol,
    price,
    prevClose,
    change: price - prevClose,
    changePct: prevClose ? ((price - prevClose) / prevClose) * 100 : 0,
    spark,
  };
}

export default async function handler(req, res) {
  const raw = (req.query.symbols || "").toString();
  const symbols = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => ALLOWED.has(s))
    .slice(0, 12);

  if (!symbols.length) {
    res.status(400).json({ error: "no valid symbols requested" });
    return;
  }

  const settled = await Promise.allSettled(symbols.map(fetchOne));
  const quotes = settled
    .filter((r) => r.status === "fulfilled")
    .map((r) => r.value);

  // Cache at the edge for a minute; serve slightly stale data while
  // revalidating so a burst of visitors doesn't hammer the upstream API.
  res.setHeader(
    "Cache-Control",
    "public, s-maxage=60, stale-while-revalidate=300"
  );
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.status(200).json({ quotes, asOf: new Date().toISOString() });
}
