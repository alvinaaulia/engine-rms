<?php

declare(strict_types=1);

if ($argc !== 2 || !is_dir($argv[1])) {
    fwrite(STDERR, "usage: php verify_temporal_v2_payload_hashes.php RUN_DIR\n");
    exit(2);
}

$run = realpath($argv[1]);
$files = [];
$cases = $run.DIRECTORY_SEPARATOR.'cases';
if (is_dir($cases)) {
    $iterator = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($cases, FilesystemIterator::SKIP_DOTS));
    foreach ($iterator as $file) {
        if ($file->isFile() && in_array(strtolower($file->getExtension()), ['json', 'jsonl'], true)) {
            $files[] = $file->getPathname();
        }
    }
}
foreach (['replay-results.jsonl', 'temporal-execution-manifests.jsonl', 'runtime-correlation-events.jsonl', 'forbidden-query-traces.jsonl'] as $name) {
    if (is_file($run.DIRECTORY_SEPARATOR.$name)) {
        $files[] = $run.DIRECTORY_SEPARATOR.$name;
    }
}

function normalizeCanonical(mixed $value): mixed
{
    if (!is_array($value)) {
        return $value;
    }
    foreach ($value as $key => $child) {
        $value[$key] = normalizeCanonical($child);
    }
    if (!array_is_list($value)) {
        ksort($value, SORT_STRING);
    }
    return $value;
}

function canonicalHash(mixed $value): string
{
    $encoded = json_encode(
        normalizeCanonical($value),
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION | JSON_THROW_ON_ERROR
    );
    return hash('sha256', $encoded);
}

$checked = 0;
$errors = [];
$errorCount = 0;
$recordError = static function (array $error) use (&$errors, &$errorCount): void {
    $errorCount++;
    if (count($errors) < 100) {
        $errors[] = $error;
    }
};
foreach ($files as $path) {
    $values = [];
    if (str_ends_with(strtolower($path), '.jsonl')) {
        foreach (preg_split('/\R/', trim((string) file_get_contents($path))) ?: [] as $lineNumber => $line) {
            if ($line !== '') {
                $values[] = [json_decode($line, true, 512, JSON_THROW_ON_ERROR), $lineNumber + 1];
            }
        }
    } else {
        $values[] = [json_decode((string) file_get_contents($path), true, 512, JSON_THROW_ON_ERROR), null];
    }
    foreach ($values as [$value, $lineNumber]) {
        $checked++;
        if (!is_array($value) || !isset($value['payload_sha256']) || !array_key_exists('payload', $value)) {
            $recordError(['path' => $path, 'line' => $lineNumber, 'error' => 'not_an_artifact_envelope']);
            continue;
        }
        $actual = canonicalHash($value['payload']);
        if (!hash_equals((string) $value['payload_sha256'], $actual)) {
            $recordError(['path' => $path, 'line' => $lineNumber, 'error' => 'payload_hash_mismatch', 'actual' => $actual]);
        }
    }
}

$result = ['status' => $errorCount === 0 ? 'PASS' : 'FAIL', 'checked' => $checked, 'error_count' => $errorCount, 'errors_sample' => $errors];
echo json_encode($result, JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR), PHP_EOL;
exit($errorCount === 0 ? 0 : 1);
