<?php

declare(strict_types=1);

use App\Services\TypedPayrollRuleIrService;
use Illuminate\Contracts\Console\Kernel;
use Illuminate\Validation\ValidationException;

$laravelRoot = dirname(__DIR__, 3).DIRECTORY_SEPARATOR.'papa-website-v2';
require $laravelRoot.DIRECTORY_SEPARATOR.'vendor'.DIRECTORY_SEPARATOR.'autoload.php';
$app = require $laravelRoot.DIRECTORY_SEPARATOR.'bootstrap'.DIRECTORY_SEPARATOR.'app.php';
$app->make(Kernel::class)->bootstrap();

$raw = stream_get_contents(STDIN);
$request = json_decode($raw ?: '', true, 512, JSON_THROW_ON_ERROR);
$policy = $request['policy'] ?? [];
$facts = $request['facts'] ?? [];

$definitions = array_map(static function (array $rule): array {
    return [
        'conditions' => $rule['conditions'],
        'action' => [
            'type' => $rule['action_type'],
            'code' => $rule['component_code'],
            'formula' => $rule['formula'],
        ],
        'meta' => [
            'rule_version_id' => $rule['version_id'],
            'rule_id' => $rule['rule_id'],
            'version' => $rule['version'],
            'priority' => $rule['priority'],
            'effective_date' => $rule['effective_date'],
            'end_date' => $rule['end_date'],
        ],
    ];
}, $policy['rules'] ?? []);

try {
    $payload = $app->make(TypedPayrollRuleIrService::class)->buildExecutePayload(
        $definitions,
        $facts,
        $policy['component_types'] ?? [],
        'differential-reference-payroll-2026.1'
    );
    fwrite(STDOUT, json_encode(['status' => 'SUCCESS', 'payload' => $payload], JSON_THROW_ON_ERROR | JSON_PRESERVE_ZERO_FRACTION));
} catch (ValidationException $exception) {
    fwrite(STDOUT, json_encode(['status' => 'REJECTED', 'errors' => $exception->errors()], JSON_THROW_ON_ERROR));
    exit(2);
} catch (Throwable $exception) {
    fwrite(STDOUT, json_encode(['status' => 'ERROR', 'error_class' => get_class($exception), 'message' => $exception->getMessage()], JSON_THROW_ON_ERROR));
    exit(3);
}
