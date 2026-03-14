# Fund Portfolio Review

Use this file when the user uploads fund holdings screenshots, account screenshots, or floating profit/loss screenshots and wants analysis.

## Goal

Turn a screenshot into a portfolio diagnosis. Focus on concentration, overlap, risk balance, and next actions rather than only commenting on short-term profit or loss.

## Extraction order

Read the screenshot directly before asking the user to transcribe anything.

Extract whatever is clearly visible:

- fund name
- fund code
- current market value or holding amount
- holding weight
- average cost or holding cost
- floating profit/loss amount
- floating profit/loss ratio
- cumulative profit/loss if shown
- available cash if shown
- total assets if shown
- account date or timestamp if shown

If a field is not readable, mark it as `unknown`.

## Minimal table

Build a compact table before analysis:

| Fund | Code | Value | Weight | Cost | P/L | P/L % | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |

Use `Notes` for unreadable or ambiguous fields.

## Analysis priorities

### 1. Portfolio structure

Check:

- too many overlapping broad-index funds
- heavy concentration in one sector, theme, or market
- missing bond or cash buffer
- excessive QDII exposure for the stated risk tolerance
- whether one losing position dominates the account

### 2. Profit and loss interpretation

Explain:

- floating loss alone is not enough to decide to sell
- judge each fund by role, overlap, horizon, and thesis
- high profit can still justify reduction if the position has become too large
- high loss can still justify exit if the role is weak or the allocation is broken

### 3. Decision framing

Classify each holding as:

- `Hold`
- `Keep adding`
- `Stop adding`
- `Trim`
- `Replace candidate`

Base this on portfolio fit, not recent return alone.

## Missing-field rules

If the screenshot lacks key fields, say what is missing and proceed with explicit assumptions.

Typical missing fields:

- investment horizon
- whether this is the user's full portfolio or only one account
- planned future contributions
- emergency cash outside the account
- tax or liquidity constraints

## Output template

```markdown
## Visible portfolio snapshot
- Total assets: ...
- Cash: ...
- Number of funds: ...
- Timestamp: ...

## Assumptions and missing fields
- ...

## Portfolio diagnosis
- Concentration: ...
- Diversification: ...
- Risk balance: ...
- Biggest issue: ...

## Fund-by-fund comments
- Fund A: Hold / Keep adding / Stop adding / Trim / Replace candidate
- Fund B: ...

## Action suggestions
- ...

## Risk warnings
- ...
```

## Hard rules

- Do not invent hidden holdings from partial screenshots.
- Do not call a fund `good` or `bad` from P/L alone.
- If the screenshot likely shows only part of the account, say so.
- If the screenshot is too blurry to extract core fields, ask for a clearer image or typed holdings.
