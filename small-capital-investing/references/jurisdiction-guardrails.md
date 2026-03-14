# Jurisdiction Guardrails

Use this file whenever the user's location, residency, or account access affects whether a real-money plan should be proposed.

## Mainland China

- Treat domestic funds, A-share funds, and generic fund-first education as the default compliant lane.
- Do not assume HK/US equity brokerage access without confirmation.
- Treat real-money crypto operational guidance as blocked unless current primary sources clearly allow it.
- Do not provide platform-bypass or workaround steps.
- For crypto requests, default to `simulation-first`, education, journaling, and risk explanation.

## Hong Kong

- Verify the current licensed or eligible platform status before naming brokers or crypto venues.
- Distinguish clearly between securities brokerage access and virtual-asset platform access.
- Default to broad funds or ETFs first for beginners even when multiple lanes are available.
- For crypto, distinguish clearly between `licensed` and `applicant` status and default to spot-only.

## United States or other retail-permitted jurisdictions

- Verify current broker or exchange availability, fee schedule, and product eligibility.
- If tax treatment or reporting rules materially affect the choice, say so explicitly.
- Do not assume yield products, staking, or margin are available or suitable.
- For crypto, verify current fee schedules and yield-product restrictions instead of assuming availability.

## Unknown jurisdiction

- State the assumption clearly.
- Keep the plan generic and low-risk.
- Avoid naming specific venues until legality and availability are confirmed.
- Fall back to `simulation-first` when real-money access cannot be established safely.

## Output guidance

Whenever this file applies, include one short `Jurisdiction guardrail` section that states:

- the assumed jurisdiction
- which asset lanes are appropriate
- which lanes are blocked or deferred
