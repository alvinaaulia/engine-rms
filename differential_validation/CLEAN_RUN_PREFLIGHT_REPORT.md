# Clean-run preflight report

| Item | Value | Source command | Status |
|---|---|---|---|
| Laravel commit | 569a2ba0ff7fe31457c4d3a5dffc7cc99f1d2dc8 | git rev-parse HEAD (Laravel) | VERIFIED |
| Go/validation commit | 9f2406474bdc42811a2557df28315de580a10aac | git rev-parse HEAD (engine-rms) | VERIFIED |
| Branch Laravel | main | git branch --show-current | VERIFIED |
| Branch Go | main | git branch --show-current | VERIFIED |
| Tag | tpr-ir-clean-closure-v3 | git rev-list -n 1 tpr-ir-clean-closure-v3 | VERIFIED |
| Working trees | clean | git status --porcelain | VERIFIED |
| PHP | PHP 8.4.20 (cli) (built: Apr  8 2026 08:28:30) (ZTS Visual C++ 2022 x64) | php --version | VERIFIED |
| Composer | NOT_AVAILABLE | composer --version | NOT_AVAILABLE |
| Laravel | Laravel Framework 10.50.2 | php artisan --version | VERIFIED |
| PHPUnit | PHPUnit 10.5.64 by Sebastian Bergmann and contributors. | php vendor/bin/phpunit --version | VERIFIED |
| Go | go version go1.26.2 windows/amd64 | go version | VERIFIED |
| Python | Python 3.14.4 | C:\Users\LENOVO\AppData\Local\Python\pythoncore-3.14-64\python.exe --version | VERIFIED |
| Docker | NOT_AVAILABLE | docker --version | NOT_AVAILABLE |
| Docker Compose | NOT_AVAILABLE | docker compose version | NOT_AVAILABLE |
| MySQL | 8.0.30 / utf8mb4_0900_ai_ci | PHP DB query: SELECT VERSION(), @@collation_database | VERIFIED |
| GRULE | require github.com/hyperjumptech/grule-rule-engine v1.20.4 | go.mod | VERIFIED |
| OS | Windows-10-10.0.19045-SP0 | Python platform.platform() | VERIFIED |
| Architecture | AMD64 | Python platform.machine() | VERIFIED |
| Timezone | Asia/Jakarta (clean specification); host=SE Asia Standard Time | TZ specification / Python time.tzname | VERIFIED |
| Locale | English_United States | Python locale.getlocale() | VERIFIED |
