# Reference oracle method

The primary calculator uses Python `Decimal` and the frozen `reference_policy.json`; it does not import Go or Laravel production calculation code. A second implementation uses exact `Fraction` arithmetic and a separately implemented HALF_UP quantizer over a deterministic stratified sample plus all invalid cases.

Rows independently recalculated are `INDEPENDENTLY_VERIFIED`. Remaining rows are `POLICY_DERIVED`. `ADJUDICATED` is reserved for a written external decision and is currently unused. The freeze proves reproducibility against the policy artifact, not business authority.

