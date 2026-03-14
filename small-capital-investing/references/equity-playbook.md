# Equity Playbook

Use this file when the user wants a Hong Kong or U.S. stock or ETF plan, watchlist, earnings follow-up, or a small-capital equity starter setup.

This file is the canonical source for Hong Kong/U.S. equity starter tiers and allocation examples. If `starter-allocations.md` is also loaded, this file wins for `equity-first` sizing.

## Default assumptions

- no leverage
- no options
- no day trading
- `10-20%` cash buffer
- keep the first version to `2-4` holdings unless capital is clearly large enough
- prefer ETFs before single stocks

If the broker supports U.S. fractional shares, prefer U.S. ETFs for the first layer. If not, prefer lower-share-price ETFs such as `SPLG` and `QQQM` instead of `SPY` and `QQQ`.

## Currency and tier selection

- In Chinese-language requests, treat a bare budget such as `2000块`, `5000`, or `1万` as `CNY` unless the user explicitly says `美元`, `港币`, or another currency.
- For `equity-first` tiering, select buckets by the `CNY` amount first.
- If the user gives `USD` or `HKD`, map it to the nearest `CNY` tier using a current verified FX rate when the cutover matters, and state the date.
- If the budget sits near a tier boundary and live FX is unavailable, say the tier mapping is approximate and choose the more conservative bucket.

Example:

- `2000元做港美股` => `Tier A`

## Starter tiers

### Tier A: under `15000` yuan, or about `US$2,000` / `HK$15,000`

Default:

- `60%` `SPLG`
- `20%` `QQQM`
- `20%` cash

Rules:

- default to U.S.-first exposure
- do not hold more than `3` positions
- skip individual stocks unless the user insists

### Tier B: `15000-80000` yuan, or about `US$2,000-10,000` / `HK$15,000-78,000`

Default:

- `50%` `SPLG` or `VOO`
- `20%` `QQQM`
- `10%` `3067.HK`
- `10%` one U.S. large-cap stock
- `10%` cash

Rules:

- max `4` positions
- only one individual-stock slot
- for a true beginner, prefer `MSFT` before higher-volatility names

### Tier C: `80000-240000` yuan, or about `US$10,000-30,000` / `HK$78,000-234,000`

Default:

- `40%` S&P 500 ETF
- `20%` Nasdaq-100 ETF
- `10%` `3067.HK`
- `10%` one U.S. large-cap stock
- `10%` one Hong Kong large-cap or tech leader
- `10%` cash

Rules:

- max `6` positions
- rebalance monthly or after earnings

## Default investable universe

- U.S. core ETFs: `SPLG` or `VOO`, `QQQM` or `QQQ`
- Hong Kong core ETF: `3067.HK`
- U.S. satellite stocks: `MSFT`, `AMZN`, `META`, `NVDA`
- Hong Kong satellite stocks: `0700.HK`, `9988.HK`, `1810.HK`, `0981.HK`

## Hong Kong-specific guardrails

- Check board lot size before proposing any Hong Kong stock trade.
- If one board lot consumes more than `10%` of total capital, skip that stock and use `3067.HK` instead.
- If fees or FX friction materially distort the position size, keep Hong Kong single stocks on the watchlist and build the U.S. core first.

## Research pack

For each stock or ETF candidate, verify:

- most recent quarter revenue
- EPS or net profit where relevant
- margin trend or operating leverage
- operating cash flow or free cash flow if available
- management guidance changes
- next earnings or catalyst date
- buybacks, CAPEX, product, regulatory, or customer-concentration updates
- a clear invalidation condition

Always separate facts from inference.

## Review cadence

- daily: check material news and upcoming catalysts only
- weekly: rerun the scorecard
- monthly or post-earnings: rebalance only if thesis or weights changed

## Behavioral rules

- add new positions only after earnings or on broad pullbacks with unchanged thesis
- do not average down just because a stock fell
- review once a week, not every hour
- if the thesis breaks, reduce or exit instead of arguing with the market
