# Asset Routing

Use this file when the user asks:

- `基金/股票/加密怎么选`
- `我只有一点钱先买什么`
- `我适合基金还是比特币`
- `要不要直接买股票`

## Default routing order

For users who do not clearly prefer an asset class:

1. `fund-first`
2. `equity-first`
3. `crypto-first`

Reason:

- funds and broad ETFs usually tolerate small capital better
- single stocks require more judgment and sometimes more trading friction
- crypto carries the highest volatility and legality risk

## Fund-first lane

Prefer this lane when:

- the user is a beginner
- the user is capital-constrained
- the goal is steady long-term exposure rather than fast gains
- the user is in mainland China and wants the simplest compliant starting point
- the user is not comfortable with large drawdowns

Typical instruments:

- broad-market index funds
- broad-market ETFs
- money-market or short-duration cash-like funds when the goal is parking cash rather than growth

## Equity-first lane

Prefer this lane when:

- the user already has brokerage access
- fractional shares or practical lot sizes are available
- the user wants direct company or ETF exposure
- the account is large enough that fees and FX do not dominate outcomes

Default structure:

- broad ETF first
- one quality single-stock slot only after the core is established

## Crypto-first lane

Prefer this lane only when:

- the user explicitly wants crypto
- the jurisdiction allows real-money access
- the user accepts high volatility and possible deep drawdowns
- the user understands that the first version should still be spot-only and simple

Default structure:

- `BTC` first
- `ETH` second
- avoid meme coins and high-turnover strategies

## Mixing lanes

For tiny accounts, do not mix all three lanes at once.

Rules of thumb:

- under `1000` yuan: usually stick to one lane
- `1000-5000` yuan: at most two lanes if the user is deliberate and fee drag is low
- above `5000` yuan: a core-satellite structure becomes more practical
