
# Corpus category audit

Category assignment is derived from facts, matched rules, route, boundaries, and explicit treatments. The generator validator rejects missing treatments, fake legacy routing, boundary cases without boundary metadata, and invalid cases without expected error codes.

| Primary category | Cases |
|---|---|
| BOUNDARY_CASE | 583 |
| EFFECTIVE_DATE | 3 |
| INVALID_INPUT | 24 |
| LEGACY_ADAPTER | 1 |
| NORMAL_CASE | 3 |
| ROUNDING_SENSITIVE | 3 |
| RULE_INTERACTION | 6 |
| ZERO_VALUE | 1 |

| Execution route | Cases |
|---|---|
| CANONICAL_TPR_IR | 504 |
| LEGACY_ADAPTER | 120 |

The three effective-date cases execute before, exactly at, and during the open-ended effective period. No category is assigned using a display-balancing modulo. Modulo remains only where it creates deterministic input variation; category predicates are evaluated from the resulting facts.
