# Crypto Playbook

Use this file when the user explicitly wants crypto, asks for a `BTC` or `BTC/ETH` spot plan, or mentions `200 元`, `500 元`, `1000 元`, `小资金`, or `试试` in a crypto context.

## Default assumptions

- this is learning capital, not emergency cash
- spot only
- `BTC` first, `ETH` second
- no leverage, perpetuals, meme coins, or copy trading
- minimize transaction count
- do not use on-chain transfers below roughly `2000` yuan unless the user explicitly accepts network-fee drag

## Starter tiers

### Tier S: under `500` yuan

Default:

- if legally tradable and fees are tolerable: `100% BTC`
- if legality or fees are poor: `simulation` instead of real trading

Rules:

- keep it to `1` asset
- make `1` buy if the platform uses fixed or high fees
- make at most `2` buys in `30` days if the fee rate is low
- do not add `ETH`, DeFi, staking, lending, or withdrawals

### Tier A: `500-2000` yuan

Default:

- `80% BTC`
- `20% cash`

Optional only when fees are low and the user explicitly wants a second sleeve:

- `70% BTC`
- `20% ETH`
- `10% cash`

Rules:

- max `2` assets plus cash
- max `2` buys per month
- no on-chain activity
- no yield products as the first version

### Tier B: `2000-10000` yuan

Default:

- `65% BTC`
- `20% ETH`
- `15% cash`

Only introduce a stablecoin sleeve if the user already understands custodian and protocol risk.

Rules:

- max `3` sleeves including cash
- keep at least `10%` dry powder if the user plans to keep adding capital
- do not automate live trading until there is at least `30` days of paper-trade discipline

## Execution rules

- if the platform charges a fixed fee, prefer fewer transactions
- if the fee is proportional and low, split into `2-4` scheduled buys at most
- only rebalance when weights drift materially or the thesis changes
- avoid moving assets on-chain unless there is a clear reason that outweighs fees and complexity

## Behavioral rules

- do not chase pumps
- add only on schedule or after a review checkpoint
- if the user cannot add fresh capital later, simplify further and prefer `BTC` only
- if the user loses sleep over volatility, reduce size before adding complexity
