from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "oracle_input_cases.json"
POLICY_PATH = ROOT / "reference_policy.json"
JSON_PATH = ROOT / "oracle_expected_results.json"
CSV_PATH = ROOT / "oracle_expected_results.csv"
QUANTUM = Decimal("0.000001")


def d(value) -> Decimal:
    return Decimal(str(value))


def q(value: Decimal) -> Decimal:
    return value.quantize(QUANTUM, rounding=ROUND_HALF_UP)


def text(value: Decimal) -> str:
    return f"{q(value):.6f}"


def add_component(components: list[dict], trace: list[dict], code: str, raw: Decimal, rule_id: str,
                  version_id: int, formula: str, inputs: dict) -> None:
    rounded = q(raw)
    components.append({
        "code": code,
        "raw_amount": format(raw, "f"),
        "rounded_amount": text(rounded),
        "source_rule_id": rule_id,
        "source_rule_version_id": version_id,
        "source_rule_ids": [rule_id],
        "source_rule_version_ids": [version_id],
    })
    trace.append({
        "rule_id": rule_id,
        "component_code": code,
        "formula": formula,
        "inputs": {key: str(value) for key, value in inputs.items()},
        "raw_result": format(raw, "f"),
        "rounding_point": "candidate",
        "rounded_result": text(rounded),
    })


def active_rule_versions(policy: dict, salary_date: str) -> set[int]:
    return {
        int(rule["version_id"])
        for rule in policy["rules"]
        if (not rule.get("effective_date") or salary_date >= rule["effective_date"])
        and (not rule.get("end_date") or salary_date <= rule["end_date"])
    }


def verification_metadata() -> dict:
    return {
        "verification_status": "REFERENCE_GENERATED",
        "verifier": None,
        "verification_method": "Independent Decimal reference calculator generated from frozen policy",
        "verification_timestamp": None,
        "adjudication_reference": None,
        "notes": "Awaiting independent verifier classification.",
    }


def calculate(case: dict, policy: dict) -> dict:
    if case["validity"] == "INVALID":
        return {
            "case_id": case["case_id"],
            "primary_category": case["primary_category"],
            "secondary_categories": case["secondary_categories"],
            **verification_metadata(),
            "expected_status": "REJECTED",
            "expected_error_code": case["expected_error_code"],
            "components": [],
            "trace": [{"reason": "Invalid guard case; no payroll amount is expected."}],
        }

    facts = case["facts"]
    employee = facts["employee"]
    attendance = facts["attendance"]
    rates = facts["rates"]
    basic = d(employee["basic_salary"])
    status = employee["status"]
    score = d(employee["performance_score"])
    components: list[dict] = []
    trace: list[dict] = []
    active_versions = active_rule_versions(policy, facts["salary_date"])

    if 1 in active_versions and status != "nonaktif":
        add_component(components, trace, "TAX_FLAT", d(rates["tax_flat_amount"]), "rule-version-1", 1,
                      "rates.tax_flat_amount", {"tax_flat_amount": rates["tax_flat_amount"]})

    if 3 in active_versions and status == "tetap" and d(attendance["overtime_minutes"]) > 0:
        raw = d(attendance["overtime_minutes"]) * d(rates["overtime_per_minute"])
        add_component(components, trace, "OVERTIME_PAY", raw, "rule-version-3", 3,
                      "attendance.overtime_minutes * rates.overtime_per_minute",
                      {"overtime_minutes": attendance["overtime_minutes"], "overtime_per_minute": rates["overtime_per_minute"]})

    if 4 in active_versions and status == "tetap" and score >= 90:
        rate_key, rule_id, version_id = "performance_bonus_90_ke_atas", "rule-version-4", 4
    elif 5 in active_versions and status == "tetap" and 80 <= score <= 89:
        rate_key, rule_id, version_id = "performance_bonus_80_89", "rule-version-5", 5
    elif 6 in active_versions and status == "tetap" and 70 <= score <= 79:
        rate_key, rule_id, version_id = "performance_bonus_70_79", "rule-version-6", 6
    else:
        rate_key = rule_id = None
        version_id = 0
    if rate_key:
        raw = basic * d(rates[rate_key])
        add_component(components, trace, "PERFORMANCE_BONUS", raw, rule_id, version_id,
                      f"employee.basic_salary * rates.{rate_key}",
                      {"basic_salary": basic, rate_key: rates[rate_key]})

    if 7 in active_versions and status == "tetap" and employee["annual_bonus_eligible"] is True:
        raw = basic * d(rates["annual_bonus_factor"])
        add_component(components, trace, "ANNUAL_BONUS", raw, "rule-version-7", 7,
                      "employee.basic_salary * rates.annual_bonus_factor",
                      {"basic_salary": basic, "annual_bonus_factor": rates["annual_bonus_factor"]})

    if 8 in active_versions and status == "tetap" and employee["thr_eligible"] is True:
        raw = basic * d(rates["thr_factor"])
        add_component(components, trace, "THR", raw, "rule-version-8", 8,
                      "employee.basic_salary * rates.thr_factor",
                      {"basic_salary": basic, "thr_factor": rates["thr_factor"]})

    if (9 in active_versions and status == "tetap" and d(attendance["days_absent"]) == 0
            and d(attendance["unpaid_leave_days"]) == 0 and d(attendance["late_minutes"]) == 0):
        add_component(components, trace, "ATTENDANCE_INCENTIVE", d(rates["attendance_incentive"]),
                      "rule-version-9", 9, "rates.attendance_incentive",
                      {"attendance_incentive": rates["attendance_incentive"]})

    if 10 in active_versions and status == "tetap" and d(attendance["unpaid_leave_days"]) > 0:
        raw = d(attendance["unpaid_leave_days"]) * d(rates["unpaid_leave_per_day"])
        add_component(components, trace, "UNPAID_LEAVE_DEDUCTION", raw, "rule-version-10", 10,
                      "attendance.unpaid_leave_days * rates.unpaid_leave_per_day",
                      {"unpaid_leave_days": attendance["unpaid_leave_days"], "unpaid_leave_per_day": rates["unpaid_leave_per_day"]})

    if 11 in active_versions and status == "tetap" and d(attendance["late_minutes"]) > 0:
        raw = d(attendance["late_minutes"]) * d(rates["late_deduction_per_minute"])
        add_component(components, trace, "LATE_DEDUCTION", raw, "rule-version-11", 11,
                      "attendance.late_minutes * rates.late_deduction_per_minute",
                      {"late_minutes": attendance["late_minutes"], "late_deduction_per_minute": rates["late_deduction_per_minute"]})

    if 12 in active_versions and status == "tetap" and d(attendance["days_absent"]) > 0:
        raw = d(attendance["days_absent"]) * d(rates["absence_deduction_per_day"])
        add_component(components, trace, "ABSENCE_DEDUCTION", raw, "rule-version-12", 12,
                      "attendance.days_absent * rates.absence_deduction_per_day",
                      {"days_absent": attendance["days_absent"], "absence_deduction_per_day": rates["absence_deduction_per_day"]})

    components.sort(key=lambda item: item["code"])
    earning_codes = {code for code, kind in policy["component_types"].items() if kind == "EARNING"}
    deduction_codes = {code for code, kind in policy["component_types"].items() if kind == "DEDUCTION"}
    earnings = sum((d(item["rounded_amount"]) for item in components if item["code"] in earning_codes), Decimal(0))
    deductions = sum((d(item["rounded_amount"]) for item in components if item["code"] in deduction_codes), Decimal(0))
    gross = q(basic + earnings)
    total_deductions = q(deductions)
    net = q(gross - total_deductions)
    taxable_earnings = sum((d(item["rounded_amount"]) for item in components
                            if item["code"] in policy["taxable_components"]), Decimal(0))
    taxable_amount = q(basic + taxable_earnings)
    tax = next((d(item["rounded_amount"]) for item in components if item["code"] == "TAX_FLAT"), Decimal(0))

    return {
        "case_id": case["case_id"],
        "primary_category": case["primary_category"],
        "secondary_categories": case["secondary_categories"],
        **verification_metadata(),
        "expected_status": "SUCCESS",
        "components": components,
        "summary": {
            "basic_salary": text(basic),
            "gross_salary": text(gross),
            "total_deductions": text(total_deductions),
            "taxable_amount": text(taxable_amount),
            "tax": text(tax),
            "net_salary": text(net),
        },
        "trace": trace,
        "formula_source": policy["source"],
        "rounding_policy": policy["rounding"],
        "creator": "Independent Python Decimal reference oracle",
        "domain_verification": "NOT_HRD_VERIFIED",
    }


def write_csv(results: list[dict], policy: dict) -> None:
    columns = [
        "case_id", "primary_category", "secondary_categories", "verification_status", "verifier",
        "verification_method", "verification_timestamp", "adjudication_reference", "notes",
        "expected_status", "expected_error_code",
        "component_code", "component_type", "raw_amount", "rounded_amount", "taxable_component",
        "source_rule_id", "source_rule_version_id", "basic_salary", "gross_salary",
        "total_deductions", "taxable_amount", "tax", "net_salary",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in results:
            if result["expected_status"] == "REJECTED":
                writer.writerow({
                    "case_id": result["case_id"], "primary_category": result["primary_category"],
                    "secondary_categories": "|".join(result["secondary_categories"]),
                    **{key: result.get(key) for key in ("verification_status", "verifier", "verification_method", "verification_timestamp", "adjudication_reference", "notes")},
                    "expected_status": "REJECTED",
                    "expected_error_code": result["expected_error_code"], "component_code": "__ERROR__",
                })
                continue
            summary = result["summary"]
            for component in result["components"]:
                code = component["code"]
                writer.writerow({
                    "case_id": result["case_id"], "primary_category": result["primary_category"],
                    "secondary_categories": "|".join(result["secondary_categories"]),
                    **{key: result.get(key) for key in ("verification_status", "verifier", "verification_method", "verification_timestamp", "adjudication_reference", "notes")},
                    "expected_status": "SUCCESS",
                    "component_code": code, "component_type": policy["component_types"][code],
                    "raw_amount": component["raw_amount"], "rounded_amount": component["rounded_amount"],
                    "taxable_component": code in policy["taxable_components"],
                    "source_rule_id": component["source_rule_id"],
                    "source_rule_version_id": component["source_rule_version_id"], **summary,
                })


def main() -> None:
    with localcontext() as context:
        context.prec = 50
        corpus = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        results = [calculate(case, policy) for case in corpus["cases"]]
    payload = {
        "artifact_version": "2.0",
        "schema_version": "2.0",
        "oracle_id": "independent-decimal-reference-oracle-v1",
        "oracle_status": policy["oracle_status"],
        "policy_version": policy["policy_version"],
        "case_count": len(results),
        "results": results,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    JSON_PATH.write_text(encoded, encoding="utf-8")
    write_csv(results, policy)
    print(json.dumps({"case_count": len(results), "sha256": hashlib.sha256(encoded.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
