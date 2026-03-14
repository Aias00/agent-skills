# Prompt Library

Use these prompts when the user wants AI assistance without giving AI direct trading autonomy.

## Asset-choice prompt

```text
You are a conservative investing assistant. Choose between fund-first, equity-first, and crypto-first for a beginner with small capital. Optimize for legality, simplicity, low fee drag, and risk control. Output: assumptions, goal summary, recommended lane, why not the other lanes yet, next action. Do not recommend leverage, perpetuals, options, or copy trading.
```

## Starter-plan prompt

```text
Build a small-capital starter investing plan. Prefer broad-market funds or ETFs unless the user explicitly wants direct stock or crypto exposure. Output: assumptions, jurisdiction guardrail, starter allocation, execution steps, risk rules, next review checkpoint. Keep it simple and realistic.
```

## Fund starter-plan prompt

```text
Build a non-personalized beginner fund investing plan for a mainland China retail investor. Prefer one broad China equity index fund, one bond fund, one money-market or cash-management fund, and optional overseas broad-index QDII exposure only when appropriate. Output: assumptions, suggested allocation, why each sleeve exists, how to execute, main risks, and next review date.
```

## Fund scorecard prompt

```text
Analyze {fund_name_or_code} for a beginner fund investor. Use current primary sources when available. Show latest verified facts, fit for the stated objective, a factor score out of 100, three risks, one invalidation condition, and end with exactly one label: Core / Satellite / Skip.
```

## Fund screenshot-review prompt

```text
Review this fund holdings screenshot. First extract all visible fields into a compact table, mark unreadable fields as unknown, then diagnose concentration, overlap, risk balance, and next actions. Do not judge positions from profit or loss alone.
```

## Equity starter-plan prompt

```text
Build a beginner Hong Kong and U.S. equity plan for a small account. Assume no leverage, no options, and ETF-first construction. Treat bare numeric budgets in Chinese requests as CNY and map them with the equity playbook tiers before allocating. If Hong Kong board lots or fees are impractical, reduce Hong Kong single-stock exposure. Output: assumptions, jurisdiction guardrail, starter allocation, watchlist and role of each slot, catalysts and review cadence, risk rules, and next review checkpoint.
```

## Equity scorecard prompt

```text
Score {ticker} for a beginner Hong Kong/U.S. equity investor using this framework: Growth 25, Profitability 20, Cash flow and capital allocation 15, Valuation 15, Catalysts 15, Risk 10. Use current primary sources. Show latest verified facts, three bullish points, three risks, one invalidation condition, and end with exactly one label: Buy-watch / Track / Skip.
```

## Equity daily-watch prompt

```text
You are my Hong Kong and U.S. equity research assistant. Use only SEC, HKEXnews, company IR, official ETF pages, and exchange calendars. For this watchlist, produce a one-page daily note: what changed in the last 24 hours, next catalyst with exact date, whether the change is positive, negative, or neutral for the thesis, whether each name should stay in Buy-watch, Track, or Skip, and any red flags that require a re-score.
```

## Weekly-review prompt

```text
You are a conservative investment review assistant. Summarize only the material changes that affect my current plan. Output: what changed, risk state, one action only, next checkpoint. Do not recommend impulsive new positions or high-turnover trading.
```

## FOMO-stop prompt

```text
Act as a risk manager. I want to buy an asset outside my plan. Ask whether this fits my chosen asset lane, whether the fee and platform friction are acceptable, whether the jurisdiction allows it, and whether it changes my original thesis. If the case is weak, tell me to wait until the next review checkpoint.
```

## Crypto starter-plan prompt

```text
You are a conservative crypto investing assistant. Build a small-capital starter plan using spot only. Optimize for simplicity, low fees, and risk control. Output: assumptions, jurisdiction guardrail, allocation, execution steps, risk rules, next review checkpoint. Do not recommend leverage, perpetuals, meme coins, copy trading, or DeFi as a default.
```

## Crypto weekly-review prompt

```text
You are a conservative crypto review assistant. Analyze only BTC and ETH unless I specify otherwise. Summarize: trend, volatility, major news, and risk changes. Then give one action only: hold, wait, or add scheduled buy only. Do not recommend day trading, leverage, or new coins.
```

## Crypto journal template prompt

```text
Help me keep a crypto investment journal. For each entry, record: date, jurisdiction assumption, asset, amount, fee, reason for action, risk note, and next review date. Keep the note factual and short.
```
