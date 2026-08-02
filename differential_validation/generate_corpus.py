from __future__ import annotations

import csv
import hashlib
import json
import random
from calendar import monthrange
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path

from canonical_json import encode_frozen_json


ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "reference_policy.json"
JSON_PATH = ROOT / "oracle_input_cases.json"
CSV_PATH = ROOT / "oracle_input_cases.csv"
SEED = 20260801
PERFORMANCE_THRESHOLDS = (70, 80, 90)


def money(value: Decimal | int | str) -> str:
    return f"{Decimal(value):.6f}"


def build_profiles() -> list[dict]:
    rng = random.Random(SEED)
    salary_boundaries = [
        "1.000000", "999999.999999", "1000000.000000", "1000000.000001",
        "2199999.999999", "2200000.000000", "2200000.000001", "4999999.999999",
        "5000000.000000", "5000000.000001", "7499999.999999", "7500000.000000",
        "7500000.000001", "9999999.999999", "10000000.000000", "10000000.000001",
    ]
    score_boundaries = [0, 1, 69, 70, 71, 78, 79, 80, 81, 88, 89, 90, 91, 99, 100]
    profiles = []
    for index in range(1, 51):
        permanent = index <= 40
        salary = salary_boundaries[(index - 1) % len(salary_boundaries)]
        if index > len(salary_boundaries):
            salary = money(Decimal(rng.randrange(2_200_000, 15_000_001)))
        profiles.append({
            "profile_id": f"EMP-{index:03d}",
            "status": "tetap" if permanent else "freelance",
            "contract_type": "karyawan_tetap" if permanent else "freelancer",
            "has_npwp": index % 3 != 0,
            "ptkp_status": ["TK/0", "TK/1", "K/0", "K/1", "K/I/0"][(index - 1) % 5],
            "grade": ["A1", "A2", "B1", "B2", "C1"][(index - 1) % 5],
            "join_date": f"{2016 + (index % 10):04d}-{(index % 12) + 1:02d}-01",
            "years_of_service": index % 11,
            "performance_score": score_boundaries[(index - 1) % len(score_boundaries)],
            "basic_salary": salary,
        })
    return profiles


def rule_active(rule: dict, salary_date: str) -> bool:
    start = rule.get("effective_date")
    end = rule.get("end_date")
    return (not start or salary_date >= start) and (not end or salary_date <= end)


def rule_matches(rule: dict, facts: dict) -> bool:
    if not rule_active(rule, facts["salary_date"]):
        return False
    for condition in rule["conditions"]:
        namespace, name = condition["field"].split(".", 1)
        value = facts.get(namespace, {}).get(name)
        target = condition["value"]
        operator = condition["operator"]
        if operator == "==":
            matched = value == target
        elif operator == "!=":
            matched = value != target
        elif value is None:
            matched = False
        else:
            left, right = Decimal(str(value)), Decimal(str(target))
            matched = {">": left > right, ">=": left >= right, "<": left < right, "<=": left <= right}.get(operator, False)
        if not matched:
            return False
    return True


def boundary_metadata(facts: dict) -> list[dict]:
    boundaries: list[dict] = []
    score = int(facts["employee"]["performance_score"])
    for threshold in PERFORMANCE_THRESHOLDS:
        if score in (threshold - 1, threshold, threshold + 1):
            boundaries.append({"boundary_name": f"performance_score_{threshold}", "boundary": threshold, "value": score, "offset": score - threshold})
    overtime = int(facts["attendance"]["overtime_minutes"])
    if overtime in (59, 60, 61):
        boundaries.append({"boundary_name": "overtime_minutes_60", "boundary": 60, "value": overtime, "offset": overtime - 60})
    for field in ("days_absent", "late_minutes", "unpaid_leave_days", "overtime_minutes"):
        value = int(facts["attendance"][field])
        if value in (0, 1):
            boundaries.append({"boundary_name": f"{field}_zero", "boundary": 0, "value": value, "offset": value})
    return boundaries


def assign_treatment(case: dict, policy: dict, explicit: dict | None = None) -> dict:
    facts = case["facts"]
    route = "LEGACY_ADAPTER" if facts["employee"].get("contract_type") == "freelancer" else "CANONICAL_TPR_IR"
    boundaries = boundary_metadata(facts)
    rate_variations = {
        key: {"default": policy["default_rates"].get(key), "actual": value}
        for key, value in facts["rates"].items()
        if policy["default_rates"].get(key) != value
    }
    matched_rules = [rule["id"] for rule in policy["rules"] if rule_matches(rule, facts)]
    secondary: list[str] = [route]
    if boundaries:
        secondary.append("BOUNDARY_CASE")
    if rate_variations:
        secondary.append("RATE_TAX_VARIATION")
    if len(matched_rules) >= 2:
        secondary.append("RULE_INTERACTION")
    activity = facts["attendance"]
    if all(int(activity[name]) == 0 for name in ("days_absent", "late_minutes", "unpaid_leave_days", "overtime_minutes")):
        secondary.append("ZERO_VALUE")

    parameters: dict = {
        "execution_route": route,
        "boundaries": boundaries,
        "rate_variations": rate_variations,
        "matched_rule_ids": matched_rules,
        "matched_rule_count": len(matched_rules),
    }
    if explicit:
        secondary.extend(explicit.get("secondary_categories", []))
        parameters.update(explicit.get("treatment_parameters", {}))
        primary = explicit["primary_category"]
        treatment = explicit["treatment"]
        expected_behavior = explicit["expected_behavior"]
        rationale = explicit["rationale"]
    elif "BOUNDARY_CASE" in secondary:
        primary, treatment = "BOUNDARY_CASE", "BOUNDARY_VALUE_EXECUTION"
        expected_behavior = "Rule selection and amount follow the recorded B-1/B/B+1 boundary position."
        rationale = "At least one supported field is explicitly at a documented boundary position."
    elif route == "LEGACY_ADAPTER":
        primary, treatment = "LEGACY_ADAPTER", "GO_LEGACY_PAYLOAD_ADAPTATION"
        expected_behavior = "Legacy payload is adapted to canonical TPR-IR and matches the reference result."
        rationale = "Freelancer profiles are intentionally routed through the actual Go legacy adapter."
    elif not rate_variations:
        primary, treatment = "NORMAL_CASE", "STANDARD_CANONICAL_EXECUTION"
        expected_behavior = "Canonical execution matches the frozen reference result."
        rationale = "Valid canonical input with default rates and no dedicated special treatment."
    elif len(matched_rules) >= 4:
        primary, treatment = "RULE_INTERACTION", "MULTI_RULE_CANDIDATE_EXECUTION"
        expected_behavior = "All independently matching rules contribute under their component policies."
        rationale = "At least four active rules match the same payroll facts."
    else:
        primary, treatment = "RATE_TAX_VARIATION", "NON_DEFAULT_RATE_EXECUTION"
        expected_behavior = "Amounts reflect the explicitly varied rate/tax values."
        rationale = "One or more executed rates differ from the frozen defaults."

    case.update({
        "primary_category": primary,
        "secondary_categories": sorted(set(secondary)),
        "execution_route": route,
        "treatment": treatment,
        "treatment_parameters": parameters,
        "expected_behavior": expected_behavior,
        "rationale": rationale,
    })
    return case


def valid_case(profile: dict, profile_index: int, month: int, policy: dict) -> dict:
    last_day = monthrange(2026, month)[1]
    salary_date = date(2026, month, last_day).isoformat()
    late_values = [0, 1, 14, 15, 16, 59, 60, 61]
    overtime_values = [0, 1, 59, 60, 61, 119, 120, 121]
    absent_values = [0, 1, 2, 3]
    unpaid_values = [0, 1, 2, 7]
    late = late_values[(profile_index + month) % len(late_values)]
    overtime = overtime_values[(profile_index * 2 + month) % len(overtime_values)]
    absent = absent_values[(profile_index + month * 2) % len(absent_values)]
    unpaid = unpaid_values[(profile_index * 3 + month) % len(unpaid_values)]
    rates = deepcopy(policy["default_rates"])
    if (profile_index + month) % 7 == 0:
        rates["late_deduction_per_minute"] = "1000.000001"
    if (profile_index + month) % 11 == 0:
        rates["overtime_per_minute"] = "1999.999999"
    rates["tax_flat_amount"] = ["0.000000", "50000.000000", "125000.500000", "250000.000001"][(profile_index + month) % 4]

    employee = {**profile}
    employee.pop("profile_id")
    explicit: dict | None = None
    case_id = f"PAY-{profile_index:03d}-{month:02d}"
    if case_id in {"PAY-001-03", "PAY-001-04", "PAY-001-05"}:
        employee["performance_score"] = 70
        employee["basic_salary"] = "1.000000"
        position = {"PAY-001-03": ("BELOW_TIE", "0.0000004"), "PAY-001-04": ("AT_TIE", "0.0000005"), "PAY-001-05": ("ABOVE_TIE", "0.0000006")}[case_id]
        rates["performance_bonus_70_79"] = position[1]
        explicit = {
            "primary_category": "ROUNDING_SENSITIVE",
            "secondary_categories": ["BOUNDARY_CASE"],
            "treatment": "SIX_DECIMAL_HALF_UP_TIE",
            "treatment_parameters": {"rounding_position": position[0], "raw_candidate": position[1], "scale": 6, "mode": "HALF_UP"},
            "expected_behavior": "Performance bonus rounds at six decimals according to BELOW/AT/ABOVE tie position.",
            "rationale": "The raw candidate is explicitly constructed around the six-decimal HALF_UP tie.",
        }
    if case_id == "PAY-002-02":
        late = overtime = absent = unpaid = 0
        explicit = {
            "primary_category": "ZERO_VALUE", "secondary_categories": [],
            "treatment": "ALL_ATTENDANCE_ADJUSTMENTS_ZERO", "treatment_parameters": {},
            "expected_behavior": "No attendance deduction/overtime is produced and perfect-attendance incentive may apply.",
            "rationale": "All attendance adjustment inputs are explicitly zero.",
        }
    effective_cases = {
        "PAY-001-01": ("2025-12-31", "BEFORE_EFFECTIVE_FROM"),
        "PAY-002-01": ("2026-01-01", "AT_EFFECTIVE_FROM"),
        "PAY-003-01": ("2026-01-31", "DURING_OPEN_ENDED_PERIOD"),
    }
    if case_id in effective_cases:
        salary_date, state = effective_cases[case_id]
        explicit = {
            "primary_category": "EFFECTIVE_DATE", "secondary_categories": [],
            "treatment": "ACTIVE_RULE_EFFECTIVE_PERIOD_SELECTION",
            "treatment_parameters": {"effective_from": "2026-01-01", "effective_to": None, "position": state, "after_effective_to": "NOT_APPLICABLE_NO_END_DATE"},
            "expected_behavior": "Laravel-side active-rule selection includes rules only when salary_date is within their effective period.",
            "rationale": "Salary date is deliberately placed before, at, or during the audited open-ended rule period.",
        }

    days_present = max(0, 22 - absent - unpaid)
    work_minutes = days_present * 480
    annual_eligible = employee["status"] == "tetap" and month == 12 and profile_index % 2 == 0
    thr_eligible = employee["status"] == "tetap" and month == 4 and profile_index % 3 != 0
    facts = {
        "salary_date": salary_date,
        "employee": {**employee, "annual_bonus_eligible": annual_eligible, "thr_eligible": thr_eligible},
        "attendance": {
            "days_present": days_present, "work_minutes": work_minutes,
            "work_hours": money(Decimal(work_minutes) / Decimal(60)),
            "days_absent": absent, "late_minutes": late, "unpaid_leave_days": unpaid,
            "overtime_minutes": overtime, "overtime_hours": money(Decimal(overtime) / Decimal(60)),
        },
        "rates": rates,
        "components": {"BASIC_SALARY": employee["basic_salary"]},
        "source": {"period_start": date.fromisoformat(salary_date).replace(day=1).isoformat(), "period_end": salary_date, "payroll_effective_date": salary_date},
    }
    case = {"case_id": case_id, "profile_id": profile["profile_id"], "period": salary_date[:7], "validity": "VALID", "facts": facts}
    return assign_treatment(case, policy, explicit)


def invalid_cases(valid_cases: list[dict], policy: dict) -> list[dict]:
    cases = []
    mutations = [
        ("MISSING_STATUS", "MISSING_REQUIRED_FACT"),
        ("INVALID_BASIC_SALARY_TYPE", "INVALID_FACT_TYPE"),
        ("INVALID_ELIGIBILITY_TYPE", "INVALID_FACT_TYPE"),
    ]
    for index in range(24):
        case = deepcopy(valid_cases[index * 7])
        mutation, error_code = mutations[index % len(mutations)]
        case["case_id"] = f"INVALID-{index + 1:03d}"
        case["validity"] = "INVALID"
        case["expected_error_code"] = error_code
        if mutation == "MISSING_STATUS":
            del case["facts"]["employee"]["status"]
        elif mutation == "INVALID_BASIC_SALARY_TYPE":
            case["facts"]["employee"]["basic_salary"] = "not-a-number"
            case["facts"]["components"]["BASIC_SALARY"] = "not-a-number"
        else:
            case["facts"]["employee"]["annual_bonus_eligible"] = "yes"
        case.update({
            "primary_category": "INVALID_INPUT", "secondary_categories": [case["execution_route"]],
            "treatment": mutation, "treatment_parameters": {"mutation": mutation, "expected_error_code": error_code},
            "expected_behavior": f"Structured rejection with error_code {error_code}.",
            "rationale": "The input intentionally violates a required fact or declared runtime type.",
        })
        cases.append(case)
    return cases


def validate_cases(cases: list[dict]) -> None:
    seen: set[str] = set()
    for case in cases:
        case_id = case.get("case_id")
        if not case_id or case_id in seen:
            raise ValueError(f"Duplicate or missing case ID: {case_id}")
        seen.add(case_id)
        for field in ("primary_category", "secondary_categories", "execution_route", "treatment", "treatment_parameters", "expected_behavior", "rationale"):
            if field not in case or case[field] in ("", None):
                raise ValueError(f"{case_id}: missing treatment field {field}")
        if case["primary_category"] == "BOUNDARY_CASE" and not case["treatment_parameters"].get("boundaries"):
            raise ValueError(f"{case_id}: boundary case lacks boundary metadata")
        if "LEGACY_ADAPTER" in case["secondary_categories"] and case["execution_route"] != "LEGACY_ADAPTER":
            raise ValueError(f"{case_id}: legacy category does not use legacy route")
        if case["validity"] == "INVALID" and not case.get("expected_error_code"):
            raise ValueError(f"{case_id}: invalid case lacks expected error code")
        if case["primary_category"] == "EFFECTIVE_DATE" and "position" not in case["treatment_parameters"]:
            raise ValueError(f"{case_id}: effective-date treatment has no evaluated position")


def write_csv(cases: list[dict]) -> None:
    columns = ["case_id", "profile_id", "period", "primary_category", "secondary_categories", "execution_route", "treatment", "treatment_parameters", "expected_behavior", "rationale", "validity", "expected_error_code", "facts_json"]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for case in cases:
            writer.writerow({
                "case_id": case["case_id"], "profile_id": case["profile_id"], "period": case["period"],
                "primary_category": case["primary_category"], "secondary_categories": "|".join(case["secondary_categories"]),
                "execution_route": case["execution_route"], "treatment": case["treatment"],
                "treatment_parameters": json.dumps(case["treatment_parameters"], ensure_ascii=False, sort_keys=True),
                "expected_behavior": case["expected_behavior"], "rationale": case["rationale"],
                "validity": case["validity"], "expected_error_code": case.get("expected_error_code", ""),
                "facts_json": json.dumps(case["facts"], ensure_ascii=False, sort_keys=True),
            })


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    profiles = build_profiles()
    valid = [valid_case(profile, index, month, policy) for index, profile in enumerate(profiles, 1) for month in range(1, 13)]
    cases = valid + invalid_cases(valid, policy)
    validate_cases(cases)
    payload = {
        "artifact_version": "2.0", "schema_version": "2.0", "dataset_id": "tpr-differential-corpus-v2",
        "random_seed": SEED, "profile_count": len(profiles), "period_count": 12,
        "case_count": len(cases), "valid_case_count": len(valid), "invalid_case_count": len(cases) - len(valid), "cases": cases,
    }
    encoded = encode_frozen_json(payload)
    JSON_PATH.write_bytes(encoded)
    write_csv(cases)
    print(json.dumps({"case_count": len(cases), "valid": len(valid), "invalid": len(cases) - len(valid), "sha256": hashlib.sha256(encoded).hexdigest()}))


if __name__ == "__main__":
    main()
