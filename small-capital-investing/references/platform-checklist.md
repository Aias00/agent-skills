# Platform Checklist

Use this file when the user asks:

- `用哪个平台`
- `手续费高不高`
- `我这么点钱能不能做`
- `要不要分批`

## What to verify

Before proposing a platform or execution pattern, verify:

- legal availability in the user's jurisdiction
- minimum order size
- fee model: fixed fee, percentage fee, spread, custody fee, FX fee, or withdrawal fee
- lot-size practicality for HK stocks or ETFs
- whether fractional shares or recurring buys are supported
- whether the plan can stay off-chain or on one venue during the starter phase

## Fund-specific checks

- minimum subscription amount
- front-end or sales fees
- redemption timing and settlement
- whether the same exposure can be accessed more cheaply through an ETF

## Equity-specific checks

- commission and platform fee
- FX spread or conversion fee
- board lot size for Hong Kong names
- fractional-share support for U.S. names

## Crypto-specific checks

- trading fee plus spread
- minimum trade size
- network withdrawal fee
- whether the starter plan can remain custodial to avoid early fee drag
- whether the venue is licensed or otherwise compliant for the user's jurisdiction

## Decision rules for tiny accounts

### Under `500` yuan

- if total upfront friction is roughly `1.5%-2%` or more, simplify further or prefer simulation
- if the platform uses fixed fees, prefer one buy over multiple small buys
- if the minimum order size nearly consumes the full budget, do not propose a laddered plan

### `500-2000` yuan

- two scheduled buys can be acceptable only when fees are low and proportional
- avoid unnecessary FX or on-chain transfers
- prefer one venue, one lane, and minimal turnover

### Above `2000` yuan

- fee optimization still matters, but discipline matters more
- recurring buys and a core-satellite split become more practical

## Practical output guidance

When this file applies, include:

- whether the platform is legally usable in the assumed jurisdiction
- whether one buy or two buys is more practical
- which friction is the main limiting factor
- the exact assumptions that the recommendation depends on
