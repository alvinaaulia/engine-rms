from __future__ import annotations

import hashlib
import csv
import json
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "oracle_input_cases.json"
EXPECTED_PATH = ROOT / "oracle_expected_results.json"
POLICY_PATH = ROOT / "reference_policy.json"
REPORT_PATH = ROOT / "ORACLE_ADJUDICATION_REPORT.md"
FREEZE_PATH = ROOT / ".oracle_frozen.json"
EXPECTED_CSV_PATH = ROOT / "oracle_expected_results.csv"
SCALE = 1_000_000


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction(value) -> Fraction:
    return Fraction(str(value))


def quantize(value: Fraction) -> Fraction:
    scaled = value * SCALE
    quotient, remainder = divmod(abs(scaled.numerator), scaled.denominator)
    if remainder * 2 >= scaled.denominator:
        quotient += 1
    signed = quotient if scaled >= 0 else -quotient
    return Fraction(signed, SCALE)


def amount(value: Fraction) -> str:
    rounded = quantize(value)
    scaled = rounded.numerator * SCALE // rounded.denominator
    sign = "-" if scaled < 0 else ""
    scaled = abs(scaled)
    return f"{sign}{scaled // SCALE}.{scaled % SCALE:06d}"


def exact_amount(value: Fraction) -> str:
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1
        denominator //= 2
    while denominator % 5 == 0:
        fives += 1
        denominator //= 5
    if denominator != 1:
        raise ValueError("Expected a terminating decimal")
    places = max(twos, fives)
    scaled = value.numerator * (10 ** places) // value.denominator
    sign = "-" if scaled < 0 else ""
    scaled = abs(scaled)
    if places == 0:
        return f"{sign}{scaled}"
    return f"{sign}{scaled // (10 ** places)}.{scaled % (10 ** places):0{places}d}"


def add(items: list[dict], code: str, raw: Fraction, rule_id: str, version_id: int) -> None:
    value = amount(raw)
    items.append({
        "code": code,
        "raw_amount": exact_amount(raw),
        "rounded_amount": value,
        "source_rule_id": rule_id,
        "source_rule_version_id": version_id,
        "source_rule_ids": [rule_id],
        "source_rule_version_ids": [version_id],
    })


def independently_calculate(case: dict, policy: dict) -> dict:
    if case["validity"] == "INVALID":
        return {
            "expected_status": "REJECTED",
            "expected_error_code": case["expected_error_code"],
            "components": [],
        }

    facts = case["facts"]
    employee = facts["employee"]
    attendance = facts["attendance"]
    rates = facts["rates"]
    components: list[dict] = []
    permanent = employee["status"] == "tetap"

    if employee["status"] != "nonaktif":
        add(components, "TAX_FLAT", fraction(rates["tax_flat_amount"]), "rule-version-1", 1)
    if permanent and attendance["overtime_minutes"] > 0:
        add(components, "OVERTIME_PAY", fraction(attendance["overtime_minutes"]) * fraction(rates["overtime_per_minute"]), "rule-version-3", 3)

    score = fraction(employee["performance_score"])
    salary = fraction(employee["basic_salary"])
    if permanent and score >= 90:
        add(components, "PERFORMANCE_BONUS", salary * fraction(rates["performance_bonus_90_ke_atas"]), "rule-version-4", 4)
    elif permanent and 80 <= score <= 89:
        add(components, "PERFORMANCE_BONUS", salary * fraction(rates["performance_bonus_80_89"]), "rule-version-5", 5)
    elif permanent and 70 <= score <= 79:
        add(components, "PERFORMANCE_BONUS", salary * fraction(rates["performance_bonus_70_79"]), "rule-version-6", 6)

    if permanent and employee["annual_bonus_eligible"] is True:
        add(components, "ANNUAL_BONUS", salary * fraction(rates["annual_bonus_factor"]), "rule-version-7", 7)
    if permanent and employee["thr_eligible"] is True:
        add(components, "THR", salary * fraction(rates["thr_factor"]), "rule-version-8", 8)
    if permanent and attendance["days_absent"] == 0 and attendance["unpaid_leave_days"] == 0 and attendance["late_minutes"] == 0:
        add(components, "ATTENDANCE_INCENTIVE", fraction(rates["attendance_incentive"]), "rule-version-9", 9)
    if permanent and attendance["unpaid_leave_days"] > 0:
        add(components, "UNPAID_LEAVE_DEDUCTION", fraction(attendance["unpaid_leave_days"]) * fraction(rates["unpaid_leave_per_day"]), "rule-version-10", 10)
    if permanent and attendance["late_minutes"] > 0:
        add(components, "LATE_DEDUCTION", fraction(attendance["late_minutes"]) * fraction(rates["late_deduction_per_minute"]), "rule-version-11", 11)
    if permanent and attendance["days_absent"] > 0:
        add(components, "ABSENCE_DEDUCTION", fraction(attendance["days_absent"]) * fraction(rates["absence_deduction_per_day"]), "rule-version-12", 12)

    components.sort(key=lambda item: item["code"])
    basic = quantize(salary)
    earnings = sum((fraction(item["rounded_amount"]) for item in components if policy["component_types"][item["code"]] == "EARNING"), Fraction())
    deductions = sum((fraction(item["rounded_amount"]) for item in components if policy["component_types"][item["code"]] == "DEDUCTION"), Fraction())
    taxable = sum((fraction(item["rounded_amount"]) for item in components if item["code"] in policy["taxable_components"]), basic)
    tax = sum((fraction(item["rounded_amount"]) for item in components if item["code"] == "TAX_FLAT"), Fraction())
    gross = quantize(basic + earnings)
    deductions = quantize(deductions)
    return {
        "expected_status": "SUCCESS",
        "components": components,
        "summary": {
            "basic_salary": amount(basic),
            "gross_salary": amount(gross),
            "total_deductions": amount(deductions),
            "taxable_amount": amount(quantize(taxable)),
            "tax": amount(quantize(tax)),
            "net_salary": amount(quantize(gross - deductions)),
        },
    }


def select_sample(cases: list[dict]) -> list[dict]:
    valid = [case for case in cases if case["validity"] == "VALID"]
    invalid = [case for case in cases if case["validity"] == "INVALID"]
    # Every tenth valid case spans all 12 periods and all profile families; every
    # rejection case is included because guard semantics deserve complete review.
    return valid[::10] + invalid


def components_equal(independent: list[dict], recorded: list[dict]) -> bool:
    if len(independent) != len(recorded):
        return False
    for left, right in zip(independent, recorded):
        if Fraction(left["raw_amount"]) != Fraction(right["raw_amount"]):
            return False
        left_without_raw = {key: value for key, value in left.items() if key != "raw_amount"}
        right_without_raw = {key: value for key, value in right.items() if key != "raw_amount"}
        if left_without_raw != right_without_raw:
            return False
    return True


def main() -> None:
    corpus = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    by_id = {result["case_id"]: result for result in expected["results"]}
    sample = select_sample(corpus["cases"])
    disagreements: list[dict] = []

    for case in sample:
        independent = independently_calculate(case, policy)
        recorded = by_id[case["case_id"]]
        for key in ("expected_status", "expected_error_code", "components", "summary"):
            equal = components_equal(independent.get(key, []), recorded.get(key, [])) if key == "components" else independent.get(key) == recorded.get(key)
            if not equal:
                disagreements.append({
                    "case_id": case["case_id"],
                    "field": key,
                    "independent": independent.get(key),
                    "recorded": recorded.get(key),
                })

    if disagreements:
        REPORT_PATH.write_text(
            "# Oracle Adjudication Report\n\n"
            f"Status: **FAILED**\n\nIndependent evaluator found {len(disagreements)} disagreement(s). "
            "Expected results were not frozen.\n\n```json\n"
            + json.dumps(disagreements, ensure_ascii=False, indent=2)
            + "\n```\n",
            encoding="utf-8",
        )
        raise SystemExit(f"Oracle verification failed: {len(disagreements)} disagreement(s)")

    sample_ids = {case["case_id"] for case in sample}
    for result in expected["results"]:
        result["verification_status"] = "VERIFIED" if result["case_id"] in sample_ids else "ADJUDICATED"
    expected["oracle_status"] = "FROZEN_REFERENCE_ONLY"
    expected["verification"] = {
        "method": "Independent Fraction-based evaluator with custom HALF_UP quantization",
        "sample_count": len(sample),
        "sample_percent": round(len(sample) * 100 / len(corpus["cases"]), 2),
        "disagreement_count": 0,
        "hrd_verified": False,
    }
    EXPECTED_PATH.write_text(json.dumps(expected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status_by_id = {result["case_id"]: result["verification_status"] for result in expected["results"]}
    with EXPECTED_CSV_PATH.open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
        fieldnames = list(csv_rows[0]) if csv_rows else []
    for csv_row in csv_rows:
        csv_row["verification_status"] = status_by_id[csv_row["case_id"]]
    with EXPECTED_CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    counts: dict[str, int] = {}
    for case in sample:
        counts[case["category"]] = counts.get(case["category"], 0) + 1
    REPORT_PATH.write_text(
        "# Oracle Adjudication Report\n\n"
        "## Decision\n\n"
        "Status: **FROZEN_REFERENCE_ONLY**. The expected results are technically frozen for the experiment; "
        "they are not asserted as HRD-authoritative because the cited HRD spreadsheet is unavailable.\n\n"
        "## Independent verification\n\n"
        f"- Population: {len(corpus['cases'])} cases\n"
        f"- Independently recalculated: {len(sample)} cases ({len(sample) * 100 / len(corpus['cases']):.2f}%)\n"
        f"- Valid cases sampled: {sum(c['validity'] == 'VALID' for c in sample)}\n"
        f"- Invalid/guard cases sampled: {sum(c['validity'] == 'INVALID' for c in sample)}\n"
        "- Arithmetic: exact rational numbers (`Fraction`) with a separately implemented HALF_UP quantizer\n"
        "- Shared production code: none\n"
        "- Disagreements: 0\n\n"
        "## Stratification\n\n```json\n"
        + json.dumps(counts, indent=2, sort_keys=True)
        + "\n```\n\n"
        "Sampled rows are marked `VERIFIED`; the remaining rows are marked `ADJUDICATED` under the same frozen policy.\n",
        encoding="utf-8",
    )

    frozen_at = datetime.now(timezone.utc).isoformat()
    freeze = {
        "schema_version": "1.0",
        "status": "FROZEN_REFERENCE_ONLY",
        "frozen_at_utc": frozen_at,
        "policy_version": policy["policy_version"],
        "case_count": len(corpus["cases"]),
        "independently_verified_count": len(sample),
        "disagreement_count": 0,
        "hashes": {
            "reference_policy.json": sha256(POLICY_PATH),
            "oracle_input_cases.json": sha256(INPUT_PATH),
            "oracle_expected_results.json": sha256(EXPECTED_PATH),
        },
    }
    FREEZE_PATH.write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(freeze))


if __name__ == "__main__":
    main()
