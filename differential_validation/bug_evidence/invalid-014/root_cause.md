# Root cause

Case `INVALID-014` was rejected by the frozen oracle but accepted by the reconstructed baseline. The formula field was checked for existence, while the runtime type of its referenced fact was not validated. Consequently an invalid `employee.basic_salary` runtime type reached execution. The fix validates formula-fact runtime types before GRULE execution. The expected result was not changed.

Mismatch artifact: `[{"case_id": "INVALID-014", "category": "RUNTIME_ERROR", "expected": "REJECTED", "actual": "SUCCESS"}]`
