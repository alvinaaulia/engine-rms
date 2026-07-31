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

ROOT = Path(__file__).resolve().parent
POLICY_PATH = ROOT / "reference_policy.json"
JSON_PATH = ROOT / "oracle_input_cases.json"
CSV_PATH = ROOT / "oracle_input_cases.csv"
SEED = 20260801


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


def primary_category(profile_index: int, month: int) -> str:
    categories = [
        "NORMAL", "BOUNDARY", "ZERO_VALUE", "RULE_INTERACTION", "RATE_TAX_VARIATION",
        "ROUNDING_SENSITIVE", "EFFECTIVE_DATE", "LEGACY_ADAPTER", "TPR_IR_CANONICAL",
    ]
    return categories[(profile_index + month - 2) % len(categories)]


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
    days_present = max(0, 22 - absent - unpaid)
    work_minutes = days_present * 480
    rates = deepcopy(policy["default_rates"])

    if (profile_index + month) % 7 == 0:
        rates["late_deduction_per_minute"] = "1000.000001"
    if (profile_index + month) % 11 == 0:
        rates["overtime_per_minute"] = "1999.999999"
    if profile_index in (1, 17, 33) and month in (3, 6, 9, 12):
        rates["performance_bonus_70_79"] = "0.0000005"
    tax_selector = (profile_index + month) % 4
    rates["tax_flat_amount"] = ["0.000000", "50000.000000", "125000.500000", "250000.000001"][tax_selector]

    annual_eligible = profile["status"] == "tetap" and month == 12 and profile_index % 2 == 0
    thr_eligible = profile["status"] == "tetap" and month == 4 and profile_index % 3 != 0
    category = primary_category(profile_index, month)
    tags = [category, "PERMANENT" if profile["status"] == "tetap" else "FREELANCER"]
    if profile["performance_score"] in [69, 70, 71, 79, 80, 81, 89, 90, 91]:
        tags.append("PERFORMANCE_BOUNDARY")
    if 0 in [late, overtime, absent, unpaid]:
        tags.append("ZERO_BOUNDARY")
    if any(str(value).endswith(("000001", "999999", "0000005")) for value in rates.values()):
        tags.append("DECIMAL_BOUNDARY")

    facts = {
        "salary_date": salary_date,
        "employee": {
            **{key: profile[key] for key in [
                "status", "contract_type", "has_npwp", "ptkp_status", "grade", "join_date",
                "years_of_service", "performance_score", "basic_salary",
            ]},
            "annual_bonus_eligible": annual_eligible,
            "thr_eligible": thr_eligible,
        },
        "attendance": {
            "days_present": days_present,
            "work_minutes": work_minutes,
            "work_hours": money(Decimal(work_minutes) / Decimal(60)),
            "days_absent": absent,
            "late_minutes": late,
            "unpaid_leave_days": unpaid,
            "overtime_minutes": overtime,
            "overtime_hours": money(Decimal(overtime) / Decimal(60)),
        },
        "rates": rates,
        "components": {"BASIC_SALARY": profile["basic_salary"]},
        "source": {
            "period_start": date(2026, month, 1).isoformat(),
            "period_end": salary_date,
            "payroll_effective_date": salary_date,
        },
    }
    return {
        "case_id": f"PAY-{profile_index:03d}-{month:02d}",
        "profile_id": profile["profile_id"],
        "period": f"2026-{month:02d}",
        "category": category,
        "tags": sorted(set(tags)),
        "validity": "VALID",
        "facts": facts,
    }


def invalid_cases(valid_cases: list[dict]) -> list[dict]:
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
        case["category"] = "NEGATIVE_INVALID_GUARD"
        case["tags"] = ["NEGATIVE_INVALID_GUARD", mutation]
        case["validity"] = "INVALID"
        case["expected_error_code"] = error_code
        if mutation == "MISSING_STATUS":
            del case["facts"]["employee"]["status"]
        elif mutation == "INVALID_BASIC_SALARY_TYPE":
            case["facts"]["employee"]["basic_salary"] = "not-a-number"
            case["facts"]["components"]["BASIC_SALARY"] = "not-a-number"
        else:
            case["facts"]["employee"]["annual_bonus_eligible"] = "yes"
        cases.append(case)
    return cases


def write_csv(cases: list[dict]) -> None:
    columns = [
        "case_id", "profile_id", "period", "category", "tags", "validity", "expected_error_code",
        "status", "contract_type", "has_npwp", "ptkp_status", "grade", "years_of_service",
        "performance_score", "basic_salary", "annual_bonus_eligible", "thr_eligible", "days_present",
        "days_absent", "late_minutes", "unpaid_leave_days", "overtime_minutes", "work_minutes",
        "tax_flat_amount", "salary_date",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for case in cases:
            employee = case["facts"].get("employee", {})
            attendance = case["facts"].get("attendance", {})
            writer.writerow({
                "case_id": case["case_id"], "profile_id": case["profile_id"], "period": case["period"],
                "category": case["category"], "tags": "|".join(case["tags"]), "validity": case["validity"],
                "expected_error_code": case.get("expected_error_code", ""), "status": employee.get("status", ""),
                "contract_type": employee.get("contract_type", ""), "has_npwp": employee.get("has_npwp", ""),
                "ptkp_status": employee.get("ptkp_status", ""), "grade": employee.get("grade", ""),
                "years_of_service": employee.get("years_of_service", ""),
                "performance_score": employee.get("performance_score", ""),
                "basic_salary": employee.get("basic_salary", ""),
                "annual_bonus_eligible": employee.get("annual_bonus_eligible", ""),
                "thr_eligible": employee.get("thr_eligible", ""), "days_present": attendance.get("days_present", ""),
                "days_absent": attendance.get("days_absent", ""), "late_minutes": attendance.get("late_minutes", ""),
                "unpaid_leave_days": attendance.get("unpaid_leave_days", ""),
                "overtime_minutes": attendance.get("overtime_minutes", ""),
                "work_minutes": attendance.get("work_minutes", ""),
                "tax_flat_amount": case["facts"].get("rates", {}).get("tax_flat_amount", ""),
                "salary_date": case["facts"].get("salary_date", ""),
            })


def main() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    profiles = build_profiles()
    valid = [valid_case(profile, index, month, policy) for index, profile in enumerate(profiles, 1) for month in range(1, 13)]
    cases = valid + invalid_cases(valid)
    payload = {
        "schema_version": "1.0",
        "dataset_id": "tpr-differential-corpus-v1",
        "random_seed": SEED,
        "profile_count": len(profiles),
        "period_count": 12,
        "case_count": len(cases),
        "valid_case_count": len(valid),
        "invalid_case_count": len(cases) - len(valid),
        "cases": cases,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    JSON_PATH.write_text(encoded, encoding="utf-8")
    write_csv(cases)
    print(json.dumps({
        "case_count": len(cases),
        "valid": len(valid),
        "invalid": len(cases) - len(valid),
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
    }))


if __name__ == "__main__":
    main()
