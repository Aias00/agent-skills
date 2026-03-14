# Fund Scorecard

Use this file when the user asks whether a specific fund is worth buying, or asks to compare multiple funds in the same category.

## Factor weights

| Factor | Weight | What to check |
| --- | ---: | --- |
| Objective fit | 25 | Whether the fund matches the user's horizon, risk tolerance, and role in the portfolio |
| Cost and tracking quality | 15 | Management fee, custody fee, tracking error, or implementation efficiency |
| Drawdown and volatility | 20 | Max drawdown, volatility, downside capture, recovery speed |
| Strategy and portfolio quality | 15 | Holdings concentration, sector or duration risk, style drift, credit quality for bond funds |
| Manager or issuer robustness | 10 | Manager tenure, process stability, issuer reputation, mandate consistency |
| Size and liquidity | 10 | Fund size, trading liquidity for ETFs, closure or liquidation risk |
| Current event risk | 5 | Recent manager change, benchmark change, regulation, abnormal flows, unusual concentration |

## Score bands

- `80-100`: `Core`
- `70-79`: `Satellite`
- `<70`: `Skip`

Any unresolved red flag can override the numeric score.

## Minimum evidence package

Before scoring, verify:

- latest available fee structure and date
- latest available fund size and date
- benchmark and strategy description
- latest manager tenure or manager-change status
- recent `1y` and `3y` performance plus drawdown data with dates
- top holdings or sector concentration for equity funds
- duration, credit quality, and concentration for bond funds
- at least three reasons to own the fund
- at least three concrete risks
- one explicit invalidation condition

## Red flags

Treat these as strong negatives:

- strategy drift away from stated benchmark or mandate
- performance driven mainly by one crowded theme
- expense ratio much higher than similar alternatives without a clear edge
- manager turnover or major process change without evidence of continuity
- small size combined with weak liquidity or closure risk

## Output template

```markdown
## Latest verified facts
- ...

## Fit for this objective
- ...

## Score
- Objective fit (25): x
- Cost and tracking quality (15): x
- Drawdown and volatility (20): x
- Strategy and portfolio quality (15): x
- Manager or issuer robustness (10): x
- Size and liquidity (10): x
- Current event risk (5): x
- Total: x/100

## Risks
- ...

## Invalidation
- ...

## Conclusion
- Core / Satellite / Skip
```
