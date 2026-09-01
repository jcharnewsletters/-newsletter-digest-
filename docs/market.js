/* ============================================================
   Live market watchlists (Google-Finance style cards).

   The site is static, so prices are fetched in the browser:
     - stocks / indices / futures -> /api/quotes  (Vercel function proxy,
       needed because Yahoo blocks direct cross-site browser calls)
     - crypto -> CoinGecko directly (it allows cross-site calls, no key)

   Which stock list shows depends on New York market hours:
     weekdays 9:30am-4:00pm ET -> US indices + top stocks
     any other time           -> futures
   Crypto is 24/7.
   ============================================================ */
(function () {
  "use strict";

  // Display names keep the cards readable — Yahoo's own names are verbose
  // (e.g. "Mini Dow Jones Indus.-$5 Sep").
  var FUTURES = [
    { sym: "YM=F", name: "Dow Futures" },
    { sym: "ES=F", name: "S&P Futures" },
    { sym: "NQ=F", name: "Nasdaq Futures" },
    { sym: "GC=F", name: "Gold" },
    { sym: "CL=F", name: "Crude Oil" }
  ];
  var INDICES = [
    { sym: "^DJI", name: "Dow Jones" },
    { sym: "^GSPC", name: "S&P 500" },
    { sym: "^IXIC", name: "Nasdaq" },
    { sym: "^RUT", name: "Russell" },
    { sym: "^VIX", name: "VIX" }
  ];
  // Top 5 US companies by market cap. No free API ranks these live without an
  // API key, so this list is fixed — edit it here if the ranking shifts.
  var STOCKS = [
    { sym: "NVDA", name: "Nvidia" },
    { sym: "AAPL", name: "Apple" },
    { sym: "MSFT", name: "Microsoft" },
    { sym: "GOOGL", name: "Alphabet" },
    { sym: "AMZN", name: "Amazon" }
  ];

  var REFRESH_MS = 60000;

  /* ---------- New York clock ---------- */
  function nyParts() {
    var fmt = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/New_York",
      hour: "numeric", minute: "numeric", weekday: "short", hour12: false
    });
    var out = {};
    fmt.formatToParts(new Date()).forEach(function (p) { out[p.type] = p.value; });
    return {
      hour: parseInt(out.hour, 10) % 24,
      minute: parseInt(out.minute, 10),
      weekday: out.weekday
    };
  }
  function marketOpen() {
    var p = nyParts();
    if (["Sat", "Sun"].indexOf(p.weekday) !== -1) return false;
    var mins = p.hour * 60 + p.minute;
    return mins >= 570 && mins < 960;   // 9:30am -> 4:00pm ET
  }

  /* ---------- formatting ---------- */
  function fmtPrice(v) {
    var d = Math.abs(v) >= 1000 ? 2 : (Math.abs(v) >= 1 ? 2 : 4);
    return v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function fmtChange(v) {
    var d = Math.abs(v) >= 1 ? 2 : 4;
    return (v >= 0 ? "+" : "-") + Math.abs(v).toLocaleString("en-US",
      { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  /* ---------- sparkline ---------- */
  function sparkSVG(values, up) {
    if (!values || values.length < 2) return "";
    var w = 150, h = 40, min = Math.min.apply(null, values), max = Math.max.apply(null, values);
    var range = (max - min) || 1;
    var pts = values.map(function (v, i) {
      var x = (i / (values.length - 1)) * w;
      var y = h - ((v - min) / range) * h;
      return x.toFixed(1) + "," + y.toFixed(1);
    });
    var cls = up ? "up" : "down";
    return '<svg class="spark ' + cls + '" viewBox="0 0 ' + w + ' ' + h +
      '" preserveAspectRatio="none" aria-hidden="true">' +
      '<polygon points="0,' + h + ' ' + pts.join(" ") + ' ' + w + ',' + h + '"/>' +
      '<polyline points="' + pts.join(" ") + '"/></svg>';
  }

  /* ---------- card ---------- */
  function card(name, price, change, pct, spark) {
    var up = change >= 0;
    return '<article class="qcard ' + (up ? "up" : "down") + '">' +
      '<h4>' + name + '</h4>' +
      '<p class="qprice mono">' + fmtPrice(price) + '</p>' +
      '<p class="qchange mono">(' + fmtChange(change) + ')</p>' +
      '<p class="qpct mono">' + (up ? "+" : "") + pct.toFixed(2) + '%' +
        '<span class="arrow">' + (up ? "↑" : "↓") + '</span></p>' +
      '<div class="qspark">' + sparkSVG(spark, up) + '</div>' +
      '</article>';
  }

  function shell(id, label, note) {
    return '<div class="watchlist" id="' + id + '">' +
      '<p class="panel-label mono">' + label +
        (note ? ' <span class="dim">' + note + '</span>' : '') + '</p>' +
      '<div class="qgrid" data-slot="' + id + '">' +
        '<p class="qloading mono">loading quotes…</p>' +
      '</div></div>';
  }

  function fail(slot, msg) {
    var el = document.querySelector('[data-slot="' + slot + '"]');
    if (el) el.innerHTML = '<p class="qerror mono">' + msg + '</p>';
  }

  /* ---------- data ---------- */
  function loadYahoo(list, slot) {
    var syms = list.map(function (x) { return x.sym; }).join(",");
    return fetch("/api/quotes?symbols=" + encodeURIComponent(syms))
      .then(function (r) {
        if (!r.ok) throw new Error("http " + r.status);
        return r.json();
      })
      .then(function (data) {
        var by = {};
        (data.quotes || []).forEach(function (q) { by[q.symbol] = q; });
        var html = list.map(function (item) {
          var q = by[item.sym];
          return q ? card(item.name, q.price, q.change, q.changePct, q.spark) : "";
        }).join("");
        var el = document.querySelector('[data-slot="' + slot + '"]');
        if (el) el.innerHTML = html || '<p class="qerror mono">no quotes returned</p>';
      })
      .catch(function () {
        // The quote proxy only exists on the Vercel deployment.
        fail(slot, "live quotes unavailable here — open the site on Vercel");
      });
  }

  function loadCrypto(slot) {
    var url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd" +
      "&order=market_cap_desc&per_page=5&page=1&sparkline=true" +
      "&price_change_percentage=24h";
    return fetch(url)
      .then(function (r) {
        if (!r.ok) throw new Error("http " + r.status);
        return r.json();
      })
      .then(function (rows) {
        var html = rows.map(function (c) {
          var pct = c.price_change_percentage_24h || 0;
          var chg = typeof c.price_change_24h === "number"
            ? c.price_change_24h
            : c.current_price * (pct / 100);
          var sp = (c.sparkline_in_7d && c.sparkline_in_7d.price) || [];
          // 7d of hourly points is far more than the card needs.
          var thin = sp.filter(function (_, i) { return i % 4 === 0; });
          return card(c.name, c.current_price, chg, pct, thin);
        }).join("");
        var el = document.querySelector('[data-slot="' + slot + '"]');
        if (el) el.innerHTML = html;
      })
      .catch(function () { fail(slot, "crypto quotes unavailable right now"); });
  }

  /* ---------- mount ---------- */
  function render() {
    var open = marketOpen();
    var stocksHost = document.getElementById("market-stocks");
    var cryptoHost = document.getElementById("market-crypto");

    if (stocksHost) {
      stocksHost.innerHTML = open
        ? shell("wl-indices", "▲ us markets", "— live, market open") +
          shell("wl-stocks", "▲ top companies by market cap", "— live, market open")
        : shell("wl-futures", "▲ futures", "— market closed");
      if (open) {
        loadYahoo(INDICES, "wl-indices");
        loadYahoo(STOCKS, "wl-stocks");
      } else {
        loadYahoo(FUTURES, "wl-futures");
      }
    }
    if (cryptoHost) {
      cryptoHost.innerHTML = shell("wl-crypto", "▲ top crypto by market cap", "— 24/7");
      loadCrypto("wl-crypto");
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", render);
  } else {
    render();
  }
  setInterval(render, REFRESH_MS);
})();
