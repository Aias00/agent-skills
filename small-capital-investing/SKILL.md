---
name: small-capital-investing
description: Build a beginner-friendly AI-assisted workflow for small-capital investing across mainland China funds, Hong Kong and U.S. equities, and optional crypto using asset routing, lane-specific scorecards, screenshot review, current-source verification, and risk rules. Use when users ask to 用 AI 做投资入门、小资金投资、基金怎么配、定投方案、基金持仓截图分析、港美股怎么配、港美股选股盯盘、基金/股票是否值得买、或在基金/港美股/加密之间做选择，尤其当目标是先做研究和风控，而不是追热点、杠杆或保证收益。
---

# Small-Capital Investing

## Language

Match the user's language.

## Scope

Use this skill for:

- choosing between funds, HK/US equities, and crypto for a beginner or small account
- building starter allocations for `200`, `500`, `1000`, `5000`, `10000`, or similar budgets
- creating fund-first, equity-first, or conservative crypto starter plans
- giving direct but non-personalized fund allocation suggestions and 定投 plans
- reviewing fund holdings screenshots or floating profit/loss screenshots
- grading a named fund, ETF, stock, or short watchlist
- designing AI-assisted weekly review, journaling, earnings-watch, and watchlist routines
- checking whether fees, board lots, minimum orders, or legal access make a plan practical

Do not use this skill for:

- leverage, options, perpetuals, copy trading, or signal-selling defaults
- guaranteed-return claims
- tax or legal workaround advice
- rumor-only theses with no current evidence
- crowded multi-asset plans that ignore capital size and friction

## Core Stance

Treat AI as a research assistant and risk-control operator, not as an investment oracle.

Default assumptions unless the user explicitly overrides them:

- beginner-friendly
- low turnover
- `1-4` sleeves only
- simple beats clever for small accounts
- broad-market funds or ETFs before single names
- crypto is a satellite or a separate learning sleeve unless the user explicitly wants crypto-first and it is legally permissible
- for fund-first plans, keep beginner portfolios to `2-4` funds
- for equity-first plans, prefer ETF-first and keep `2-6` holdings total

If the user gives no asset preference, default to `funds/ETF first`, then consider equities, and only then consider crypto.

If the user asks how to choose between asset classes, load:
[references/asset-routing.md](references/asset-routing.md)

If the user is new, capital-constrained, or asks for a concrete allocation before a lane is clearly chosen, load:
[references/starter-allocations.md](references/starter-allocations.md)

If the user wants a fund plan, asks for 基金建议/定投/基金组合, or asks whether a specific fund is worth buying, load:
[references/fund-playbook.md](references/fund-playbook.md)

If the user wants a fund scorecard or shortlist comparison, load:
[references/fund-scorecard.md](references/fund-scorecard.md)

If the user provides fund holdings screenshots or P/L screenshots, load:
[references/fund-portfolio-review.md](references/fund-portfolio-review.md)

If the user wants a Hong Kong or U.S. equity plan, watchlist, earnings follow-up, or stock/ETF scorecard, load:
[references/equity-playbook.md](references/equity-playbook.md)

If the user wants a Hong Kong or U.S. stock or ETF scorecard, load:
[references/equity-scorecard.md](references/equity-scorecard.md)

If the user explicitly wants crypto, asks for a `BTC` or `BTC/ETH` spot plan, or mentions `200/500/1000 元` crypto starter budgets, load:
[references/crypto-playbook.md](references/crypto-playbook.md)

If the user asks about platform choice, fees, lot sizes, minimum order sizes, or whether the plan can realistically be executed, load:
[references/platform-checklist.md](references/platform-checklist.md)

If the user's jurisdiction affects legality or operational guidance, load:
[references/jurisdiction-guardrails.md](references/jurisdiction-guardrails.md)

If the user wants reusable prompts, load:
[references/prompt-library.md](references/prompt-library.md)

## Source Policy

For time-sensitive claims, verify with current primary sources and state exact dates.

This is required for:

- prices, NAVs, and yield figures
- exchange, broker, or platform availability
- fees, FX costs, board lots, and minimum order sizes
- earnings dates or major catalyst dates
- laws, licensing status, and product eligibility

Source priority:

1. regulators, exchanges, fund houses, issuers, brokers, and platform help centers
2. official filings, factsheets, prospectuses, and investor-relations pages
3. official developer or API documentation when execution tooling matters

Use media articles, influencer posts, or forums only as discovery aids, never as final evidence.

## Workflow

### Step 1: Determine the user's objective

Identify the lightest objective that matches the request:

- `Asset choice memo`: choose between fund-first, equity-first, and crypto-first
- `Starter plan`: build a first allocation for a small account
- `Fund plan`: give a direct fund allocation or 定投 suggestion
- `Fund scorecard`: grade one named fund or compare `2-5` funds
- `Fund portfolio review`: analyze holdings screenshots or P/L screenshots
- `Equity plan`: build a Hong Kong/U.S. stock or ETF starter plan
- `Equity scorecard`: grade one stock or ETF
- `Daily or weekly review`: summarize what changed and whether the plan still holds
- `Simulation plan`: use this when legality, access, or friction makes real-money execution inappropriate

If the user is vague, default to `Asset choice memo`.

### Step 2: Determine jurisdiction, risk, and account access

Before suggesting real-money execution, identify or infer:

- where the user is located
- investment horizon
- maximum tolerable drawdown
- monthly contribution or total capital
- need for low volatility versus long-term growth
- whether overseas or QDII exposure is acceptable
- which asset classes are legally and practically available
- whether brokerage or exchange access is already in place
- whether fractional shares or practical lot sizes exist for the equity lane

If legality or access is unclear, keep the answer generic and low-risk, or default to `simulation-first` where appropriate.

If the user provides fund holdings screenshots or P/L screenshots, extract the visible fields before giving advice. Load:
[references/fund-portfolio-review.md](references/fund-portfolio-review.md)

### Step 3: Route to the right asset lane

Load:
[references/asset-routing.md](references/asset-routing.md)

Default routing logic:

- use `fund-first` for most beginners, mainland China users, and savings-style goals
- use `equity-first` only when broker access, fractional-share support, or practical lot sizes exist
- use `crypto-first` only when the user explicitly wants crypto and the jurisdiction allows it

Avoid mixing all lanes into one tiny account unless the user has enough capital to support it without fake diversification.

Lane-specific rules:

- `fund-first`: prefer one broad China equity index fund, one bond fund, one money-market or cash-management fund, and one optional overseas QDII sleeve
- `equity-first`: prefer U.S. broad ETFs before single names, and use Hong Kong ETFs when board lots make single stocks impractical
- `crypto-first`: keep it spot-only, `BTC` first, and minimize transaction count

If the lane is `fund-first`, load:
[references/fund-playbook.md](references/fund-playbook.md)

If the lane is `equity-first`, load:
[references/equity-playbook.md](references/equity-playbook.md)

If the lane is `crypto-first`, load:
[references/crypto-playbook.md](references/crypto-playbook.md)

### Step 4: Size the starter allocation or investable universe

Load:
[references/starter-allocations.md](references/starter-allocations.md)

Treat `starter-allocations.md` as a route-level summary only. Once a lane-specific playbook is loaded, that playbook becomes the canonical source for concrete sizing, examples, and starter buckets.

Keep the first version intentionally small:

- prefer one core exposure before several small speculative positions
- add single stocks only after a stable core is in place
- cap crypto as a satellite unless the user explicitly wants a crypto-first plan

For named funds, screenshots, or direct fund questions:

- avoid more than `4-5` funds in a beginner portfolio
- avoid overlapping broad-index funds unless each has a distinct role
- default to broad index, bond, money-market, and optional QDII blocks before themes

For named stocks, ETFs, or Hong Kong/U.S. watchlists:

- keep the universe tight: U.S. broad ETF, U.S. growth ETF, one Hong Kong tech ETF, and a few quality large-cap stocks
- if Hong Kong board lots or fees distort sizing, prefer the Hong Kong ETF or skip the single name
- use scorecards and catalyst tracking before any buy-watch conclusion

For `equity-first`, use [references/equity-playbook.md](references/equity-playbook.md) as the only starter-tier and allocation source of truth.

If the user asks whether a named fund is worth buying, load:
[references/fund-scorecard.md](references/fund-scorecard.md)

If the user asks whether a named stock or ETF is worth buying, load:
[references/equity-scorecard.md](references/equity-scorecard.md)

If the user provides fund screenshots, load:
[references/fund-portfolio-review.md](references/fund-portfolio-review.md)

### Step 5: Make execution practical

Load:
[references/platform-checklist.md](references/platform-checklist.md)

For small accounts, optimize for:

- fewer venues
- fewer transactions
- lower fee drag
- practical minimum order sizes
- avoiding unnecessary FX or on-chain transfers

If exact fee or lot information is unknown, state the assumption explicitly.

### Step 6: Give AI narrow jobs only

AI should help with:

- asset-lane selection based on stated goals and constraints
- fund and ETF shortlist scoring
- fund screenshot diagnosis and overlap checks
- earnings-watch, watchlist scoring, and thesis tracking for Hong Kong/U.S. equities
- summarizing material changes
- keeping a weekly review cadence
- enforcing pre-defined risk rules
- journaling decisions to reduce impulsive trading

AI should not:

- receive unrestricted trading autonomy
- override legal or platform constraints
- generate certain-sounding short-term predictions

If the user wants prompts, load:
[references/prompt-library.md](references/prompt-library.md)

### Step 7: Produce an action layer

For beginner-facing outputs, always include:

- assumptions
- jurisdiction guardrail
- chosen asset lane and why
- starter allocation
- execution steps
- scorecard or diagnosis when relevant
- prohibited actions
- review cadence
- invalidation or pause conditions

## Output Defaults

### A) Asset Choice Memo

Output in this order:

1. `Assumptions`
2. `Goal and constraint summary`
3. `Recommended asset lane`
4. `Why not the other lanes yet`
5. `Next action`

### B) Starter Plan

Output in this order:

1. `Assumptions`
2. `Jurisdiction guardrail`
3. `Starter allocation`
4. `Execution steps`
5. `Risk rules`
6. `Next review checkpoint`

For 定投 requests, make `Execution steps` a `Monthly split`.
For lump-sum requests, make `Execution steps` a `Deploy schedule`.

### C) Fund scorecard or comparison

Output in this order:

1. `Latest verified facts`
2. `Fit for the stated objective`
3. `Score by factor`
4. `Key risks`
5. `Conclusion`: `Core / Satellite / Skip`

### D) Fund portfolio review from screenshot

Output in this order:

1. `Visible portfolio snapshot`
2. `Assumptions and missing fields`
3. `Portfolio diagnosis`
4. `Fund-by-fund comments`
5. `Action suggestions`
6. `Risk warnings`

### E) Equity scorecard

Output in this order:

1. `Latest verified facts`
2. `Why the market may care`
3. `Score by factor`
4. `Key risks`
5. `Invalidation`
6. `Conclusion`: `Buy-watch / Track / Skip`

### F) Equity plan

Output in this order:

1. `Assumptions`
2. `Jurisdiction guardrail`
3. `Starter allocation`
4. `Watchlist and role of each slot`
5. `Catalysts and review cadence`
6. `Risk rules and invalidation conditions`
7. `Next review checkpoint`

### G) Daily or weekly review

Output in this order:

1. `What changed`
2. `Risk state`
3. `Action`: `Hold / Wait / Add scheduled buy only / Re-score`
4. `Next checkpoint`

### H) Simulation Plan

Use this when legality, access, or fee friction makes real-money execution inappropriate.

Output in this order:

1. `Why simulation first`
2. `Paper plan`
3. `What to log`
4. `Go-live criteria`

## Hard Rules

- Never promise returns or imply certainty.
- Never default beginners into leverage, options, perpetuals, or copy trading.
- Never treat crypto as the default lane when risk preference, jurisdiction, or legality is unclear.
- Never default beginners into concentrated theme funds or all-single-stock portfolios.
- Never ignore board lots, minimum orders, fees, or transfer friction on a small account.
- Never present stale prices, NAVs, earnings dates, or licensing status as current.
- Never recommend a fund only because it recently ranked first in returns.
- Never treat floating P/L alone as a buy, hold, or sell signal.
- Prefer `1-2` core exposures over fake diversification for tiny accounts.

## References

- [references/asset-routing.md](references/asset-routing.md): choose between fund-first, equity-first, and crypto-first lanes
- [references/starter-allocations.md](references/starter-allocations.md): starter templates by lane and capital tier
- [references/fund-playbook.md](references/fund-playbook.md): fund-first templates, building blocks, and deployment rules
- [references/fund-scorecard.md](references/fund-scorecard.md): score named funds and shortlist comparisons
- [references/fund-portfolio-review.md](references/fund-portfolio-review.md): analyze fund holdings screenshots and P/L screenshots
- [references/equity-playbook.md](references/equity-playbook.md): Hong Kong/U.S. equity starter plans and watchlist rules
- [references/equity-scorecard.md](references/equity-scorecard.md): score Hong Kong/U.S. stocks and ETFs
- [references/crypto-playbook.md](references/crypto-playbook.md): crypto-first starter tiers, simulation fallback, and execution rules
- [references/platform-checklist.md](references/platform-checklist.md): fee, lot-size, and minimum-order screening
- [references/jurisdiction-guardrails.md](references/jurisdiction-guardrails.md): legality and operational guardrails by location
- [references/prompt-library.md](references/prompt-library.md): reusable AI prompts for plan building and review
