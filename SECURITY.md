# Security policy

Do not report vulnerabilities in public issues when payroll or employee data is
involved. Contact the repository owner privately and include only synthetic or
redacted reproduction data.

The `/execute` and `/replay` endpoints are internal service endpoints. Keep the
default loopback bind, configure `RULE_ENGINE_INTERNAL_TOKEN` in both services,
and never commit that value. The `/health` endpoint intentionally contains no
business data.
