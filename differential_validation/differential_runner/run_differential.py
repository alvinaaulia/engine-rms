from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENGINE_URL = "http://127.0.0.1:8081/execute"
QUANTUM = Decimal("0.000001")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def money(value) -> str:
    return f"{Decimal(str(value)).quantize(QUANTUM, rounding=ROUND_HALF_UP):.6f}"


def verify_freeze() -> dict:
    frozen_path = ROOT / ".oracle_frozen.json"
    if not frozen_path.exists():
        raise RuntimeError("Expected results are not frozen; run verify_oracle.py first")
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if frozen.get("status") != "FROZEN_REFERENCE_ORACLE":
        raise RuntimeError("Oracle freeze status is invalid")
    for name, expected_hash in frozen["hashes"].items():
        actual_hash = digest(ROOT / name)
        if actual_hash != expected_hash:
            raise RuntimeError(f"Frozen artifact changed: {name}")
    return frozen


def build_canonical_payload(policy: dict, facts: dict) -> dict:
    bridge = ROOT / "differential_runner" / "laravel_tpr_bridge.php"
    process = subprocess.run(
        ["php", str(bridge)],
        input=json.dumps({"policy": policy, "facts": facts}, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=60,
    )
    try:
        response = json.loads(process.stdout)
    except json.JSONDecodeError as exception:
        raise RuntimeError(f"Laravel bridge returned invalid JSON: {process.stderr}") from exception
    if process.returncode != 0 or response.get("status") != "SUCCESS":
        raise RuntimeError(f"Laravel adapter rejected frozen rules: {response}")
    return response["payload"]


def active_rules(policy: dict, salary_date: str) -> list[dict]:
    return [
        rule for rule in policy["rules"]
        if (not rule.get("effective_date") or salary_date >= rule["effective_date"])
        and (not rule.get("end_date") or salary_date <= rule["end_date"])
    ]


def legacy_definitions(policy: dict, salary_date: str) -> list[dict]:
    return [{
        "conditions": rule["conditions"],
        "action": {"type": rule["action_type"], "code": rule["component_code"], "formula": rule["formula"]},
        "meta": {
            "rule_version_id": rule["version_id"], "rule_id": rule["rule_id"], "version": rule["version"],
            "priority": rule["priority"], "effective_date": rule["effective_date"], "end_date": rule["end_date"],
        },
    } for rule in active_rules(policy, salary_date)]


def active_signature(policy: dict, salary_date: str) -> str:
    return ",".join(str(rule["version_id"]) for rule in active_rules(policy, salary_date))


def execute_case(case: dict, canonical_payloads: dict[str, dict], policy: dict, engine_url: str) -> dict:
    if case["execution_route"] == "LEGACY_ADAPTER":
        payload = {
            "rules": legacy_definitions(policy, case["facts"]["salary_date"]),
            "facts": case["facts"], "component_types": policy["component_types"],
        }
    else:
        base_payload = canonical_payloads[active_signature(policy, case["facts"]["salary_date"])]
        payload = {
            "schema_version": base_payload["schema_version"], "ruleset": base_payload["ruleset"],
            "facts": case["facts"], "component_types": base_payload["component_types"],
        }
    request = urllib.request.Request(
        engine_url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
            return {"case_id": case["case_id"], "execution_route": case["execution_route"], "actual_status": "SUCCESS", "http_status": response.status, "body": body}
    except urllib.error.HTTPError as exception:
        raw = exception.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"error_code": "NON_JSON_ERROR", "message": raw}
        return {"case_id": case["case_id"], "execution_route": case["execution_route"], "actual_status": "REJECTED", "http_status": exception.code, "body": body}
    except Exception as exception:  # Captures transport failure without losing the rest of the experiment.
        error_code = "TIMEOUT" if "timed out" in str(exception).lower() else "RUNTIME_ERROR"
        return {
            "case_id": case["case_id"],
            "execution_route": case["execution_route"],
            "actual_status": "TRANSPORT_ERROR",
            "http_status": None,
            "body": {"error_code": error_code, "message": str(exception)},
        }


def canonical_actual(result: dict, case: dict, policy: dict) -> dict:
    if result["actual_status"] != "SUCCESS":
        return {
            "case_id": result["case_id"],
            "execution_route": result["execution_route"],
            "actual_status": result["actual_status"],
            "http_status": result["http_status"],
            "error_code": result["body"].get("error_code"),
            "error_path": result["body"].get("path"),
            "error_message": result["body"].get("message"),
            "components": [],
        }

    components = []
    for component in result["body"].get("components", []):
        components.append({
            "code": component["code"],
            "component_type": policy["component_types"].get(component["code"]),
            "rounded_amount": money(component["amount"]),
            "source_rule_id": component.get("source_rule_id"),
            "source_rule_version_id": component.get("source_rule_version_id"),
            "source_rule_ids": component.get("source_rule_ids", []),
            "source_rule_version_ids": component.get("source_rule_version_ids", []),
        })
    components.sort(key=lambda item: item["code"])

    engine_summary = result["body"].get("summary", {})
    # A negative case can unexpectedly succeed. Use the engine-normalized basic
    # salary so the comparator records STATUS_MISMATCH instead of crashing while
    # trying to reinterpret an intentionally invalid corpus value.
    basic = Decimal(str(engine_summary.get("basic_salary", 0)))
    taxable = basic + sum(
        (Decimal(item["rounded_amount"]) for item in components if item["code"] in policy["taxable_components"]),
        Decimal(),
    )
    tax = sum((Decimal(item["rounded_amount"]) for item in components if item["code"] == "TAX_FLAT"), Decimal())
    summary = {
        "basic_salary": money(engine_summary.get("basic_salary", 0)),
        "gross_salary": money(engine_summary.get("gross_salary", 0)),
        "total_deductions": money(engine_summary.get("total_deductions", 0)),
        "taxable_amount": money(taxable),
        "tax": money(tax),
        "net_salary": money(engine_summary.get("net_salary", 0)),
    }
    return {
        "case_id": result["case_id"],
        "execution_route": result["execution_route"],
        "actual_status": "SUCCESS",
        "http_status": result["http_status"],
        "components": components,
        "summary": summary,
    }


def row(case: dict, scope: str, item: str, expected, actual, matched: bool, category: str = "", details: str = "") -> dict:
    render = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else "" if value is None else str(value)
    return {
        "case_id": case["case_id"],
        "primary_category": case["primary_category"],
        "secondary_categories": "|".join(case["secondary_categories"]),
        "execution_route": case["execution_route"],
        "validity": case["validity"],
        "comparison_scope": scope,
        "item": item,
        "expected": render(expected),
        "actual": render(actual),
        "match": "YES" if matched else "NO",
        "mismatch_category": category,
        "details": details,
    }


def compare(case: dict, expected: dict, actual: dict, policy: dict) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    mismatches: list[dict] = []
    status_match = expected["expected_status"] == actual["actual_status"]
    status_category = "" if status_match else "TIMEOUT" if actual.get("error_code") == "TIMEOUT" else "RUNTIME_ERROR"
    rows.append(row(case, "STATUS", "execution_status", expected["expected_status"], actual["actual_status"], status_match, status_category))
    if not status_match:
        mismatches.append({"case_id": case["case_id"], "category": status_category, "expected": expected["expected_status"], "actual": actual["actual_status"]})
        return rows, mismatches

    if expected["expected_status"] == "REJECTED":
        matched = expected["expected_error_code"] == actual.get("error_code")
        category = "" if matched else "RUNTIME_ERROR"
        rows.append(row(case, "ERROR", "error_code", expected["expected_error_code"], actual.get("error_code"), matched, category, actual.get("error_message", "")))
        if not matched:
            mismatches.append({"case_id": case["case_id"], "category": category, "expected": expected["expected_error_code"], "actual": actual.get("error_code"), "path": actual.get("error_path")})
        return rows, mismatches

    expected_components = {item["code"]: item for item in expected["components"]}
    actual_components = {item["code"]: item for item in actual["components"]}
    for code in sorted(set(expected_components) | set(actual_components)):
        left = expected_components.get(code)
        right = actual_components.get(code)
        if left is None:
            category, matched = "UNEXPECTED_COMPONENT", False
        elif right is None:
            category, matched = "MISSING_COMPONENT", False
        else:
            amount_match = left["rounded_amount"] == right["rounded_amount"]
            component_type_match = policy["component_types"].get(code) == right.get("component_type")
            provenance_match = all(left.get(key, []) == right.get(key, []) for key in ("source_rule_ids", "source_rule_version_ids")) and left.get("source_rule_id") == right.get("source_rule_id") and left.get("source_rule_version_id") == right.get("source_rule_version_id")
            matched = amount_match and component_type_match and provenance_match
            category = "" if matched else "ROUNDED_AMOUNT_MISMATCH" if not amount_match else "COMPONENT_TYPE_MISMATCH" if not component_type_match else "RULE_PROVENANCE_MISMATCH"
        expected_view = None if left is None else {**{key: left.get(key) for key in ("rounded_amount", "source_rule_id", "source_rule_version_id", "source_rule_ids", "source_rule_version_ids")}, "component_type": policy["component_types"].get(code)}
        rows.append(row(case, "COMPONENT", code, expected_view, right, matched, category))
        if not matched:
            mismatches.append({"case_id": case["case_id"], "category": category, "component_code": code, "expected": expected_view, "actual": right})

    for key, expected_value in expected["summary"].items():
        actual_value = actual["summary"].get(key)
        matched = expected_value == actual_value
        mismatch_by_field = {
            "basic_salary": "GROSS_MISMATCH", "gross_salary": "GROSS_MISMATCH",
            "total_deductions": "DEDUCTION_MISMATCH", "taxable_amount": "TAXABLE_BASE_MISMATCH",
            "tax": "TAX_MISMATCH", "net_salary": "NET_MISMATCH",
        }
        category = "" if matched else mismatch_by_field[key]
        rows.append(row(case, "SUMMARY", key, expected_value, actual_value, matched, category))
        if not matched:
            mismatches.append({"case_id": case["case_id"], "category": category, "summary_field": key, "expected": expected_value, "actual": actual_value})
    return rows, mismatches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the frozen differential corpus against a live Go engine")
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="Directory for actual, comparison, and mismatch artifacts")
    parser.add_argument("--engine-url", default=DEFAULT_ENGINE_URL)
    parser.add_argument("--run-id", default="fixed")
    parser.add_argument("--allow-mismatches", action="store_true", help="Record mismatches without returning a failing exit status")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with localcontext() as context:
        context.prec = 50
        frozen = verify_freeze()
        policy = json.loads((ROOT / "reference_policy.json").read_text(encoding="utf-8"))
        corpus = json.loads((ROOT / "oracle_input_cases.json").read_text(encoding="utf-8"))
        expected_payload = json.loads((ROOT / "oracle_expected_results.json").read_text(encoding="utf-8"))
        expected_by_id = {item["case_id"]: item for item in expected_payload["results"]}
        canonical_payloads: dict[str, dict] = {}
        for case in corpus["cases"]:
            if case["execution_route"] != "CANONICAL_TPR_IR":
                continue
            signature = active_signature(policy, case["facts"]["salary_date"])
            if signature not in canonical_payloads:
                canonical_payloads[signature] = build_canonical_payload(policy, case["facts"])

        raw_results: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(execute_case, case, canonical_payloads, policy, args.engine_url): case["case_id"]
                for case in corpus["cases"]
            }
            for completed, future in enumerate(as_completed(futures), 1):
                result = future.result()
                raw_results[result["case_id"]] = result
                if completed % 100 == 0:
                    print(f"executed {completed}/{len(futures)}", flush=True)

        actual_results = []
        detail_rows: list[dict] = []
        mismatches: list[dict] = []
        for case in corpus["cases"]:
            actual = canonical_actual(raw_results[case["case_id"]], case, policy)
            actual_results.append(actual)
            rows, case_mismatches = compare(case, expected_by_id[case["case_id"]], actual, policy)
            detail_rows.extend(rows)
            mismatches.extend(case_mismatches)

    actual_payload = {
        "artifact_version": "2.0",
        "schema_version": "2.0",
        "run_id": args.run_id,
        "engine_url": args.engine_url,
        "adapter": "Laravel TypedPayrollRuleIrService",
        "frozen_oracle_hash": frozen["hashes"]["oracle_expected_results.json"],
        "case_count": len(actual_results),
        "results": actual_results,
    }
    (output_dir / "actual_results.json").write_text(json.dumps(actual_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "differential_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(detail_rows[0]))
        writer.writeheader()
        writer.writerows(detail_rows)
    mismatch_payload = {
        "artifact_version": "2.0",
        "schema_version": "2.0",
        "run_id": args.run_id,
        "case_count": len(corpus["cases"]),
        "mismatch_count": len(mismatches),
        "mismatched_case_count": len({item["case_id"] for item in mismatches}),
        "mismatches": mismatches,
    }
    (output_dir / "mismatch_details.json").write_text(json.dumps(mismatch_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "output_dir": str(output_dir), "case_count": len(corpus["cases"]), "comparison_count": len(detail_rows), "mismatch_count": len(mismatches), "mismatched_case_count": mismatch_payload["mismatched_case_count"]}))
    if mismatches and not args.allow_mismatches:
        sys.exit(1)


if __name__ == "__main__":
    main()
